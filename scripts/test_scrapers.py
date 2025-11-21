#!/usr/bin/env python3
"""
Test script to run scraper configs using WorkflowExecutor.

This script loads each scraper configuration, gets the test SKU from test data,
and executes the scraper using WorkflowExecutor. Results and errors are logged
for each test run.

Usage:
    python test_scrapers.py --all                    # Test all scrapers
    python test_scrapers.py --scrapers amazon orgill # Test specific scrapers
    python test_scrapers.py --no-results amazon      # Test no results scenario for amazon
    python test_scrapers.py                          # Default: test all scrapers
"""

import argparse
import copy
import logging
import sys
import time
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.executor.workflow_executor import WorkflowExecutor
from src.scrapers.parser.yaml_parser import ScraperConfigParser

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Suppress noisy third-party logs
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def get_all_scrapers() -> list[str]:
    """Dynamically find all scraper config files."""
    configs_path = PROJECT_ROOT / "src" / "scrapers" / "configs"
    scraper_files = [f for f in configs_path.glob("*.yaml")]
    # Exclude sample_config.yaml and get the base name
    all_scrapers = [f.stem for f in scraper_files if f.name != "sample_config.yaml"]
    return sorted(all_scrapers)


# Dynamically discover scraper configs to test
ALL_SCRAPER_CONFIGS = get_all_scrapers()


def parse_args():
    parser = argparse.ArgumentParser(description="Run scraper tests.")
    parser.add_argument(
        "--scrapers",
        nargs="+",
        help="List of scraper names to test (space-separated, e.g., --scrapers amazon orgill)",
    )
    parser.add_argument("--all", action="store_true", help="Test all scrapers")
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode (default: True)"
    )
    parser.add_argument(
        "--no-results",
        nargs="?",
        const=True,
        help="Test no results scenario using a fake SKU that produces no products. Optionally specify scraper name directly.",
    )
    return parser.parse_args()


def get_test_sku(scraper_name: str) -> str:
    """Get the first test SKU for a scraper from its YAML config file."""
    config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        test_skus = config_dict.get("test_skus", [])
        if test_skus:
            return test_skus[0]
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.warning(f"Failed to load test_skus from {config_path}: {e}")
    # Fallback SKU
    return "035585499741"


def replace_sku_placeholders(config, sku: str):
    """Replace {sku} placeholders in workflow steps."""
    for step in config.workflows:
        if step.action == "navigate" and "url" in step.params:
            step.params["url"] = step.params["url"].replace("{sku}", sku)


def perform_data_quality_check(extracted_data: dict[str, Any]) -> list[str]:
    """
    Performs a data quality check on the extracted data.
    Returns a list of issues found.
    """
    issues = []
    required_fields = ["Name", "Brand", "Images"]

    for field in required_fields:
        if field not in extracted_data:
            issues.append(f"Missing field: {field}")
        elif not extracted_data[field]:
            issues.append(f"Empty field: {field}")
        elif field == "Images" and not isinstance(extracted_data[field], list):
            issues.append(
                f"Invalid format for Images: expected a list, got {type(extracted_data[field])}"
            )
        elif (
            field == "Images"
            and isinstance(extracted_data[field], list)
            and not all(
                isinstance(item, str) and item.startswith("http") for item in extracted_data[field]
            )
        ):
            issues.append("Invalid image URLs in Images field: expected list of http(s) URLs")

    return issues


def perform_data_quality_check(extracted_data: dict[str, Any]) -> list[str]:
    """
    Performs a data quality check on the extracted data.
    Returns a list of issues found.
    """
    issues = []
    required_fields = ["Name", "Brand", "Images"]

    for field in required_fields:
        if field not in extracted_data:
            issues.append(f"Missing field: {field}")
        elif not extracted_data[field]:
            issues.append(f"Empty field: {field}")
        elif field == "Images" and not isinstance(extracted_data[field], list):
            issues.append(
                f"Invalid format for Images: expected a list, got {type(extracted_data[field])}"
            )
        elif (
            field == "Images"
            and isinstance(extracted_data[field], list)
            and not all(
                isinstance(item, str) and item.startswith("http") for item in extracted_data[field]
            )
        ):
            issues.append("Invalid image URLs in Images field: expected list of http(s) URLs")

    return issues


def test_scraper_config(
    scraper_name: str,
    headless: bool = True,
    test_no_results: bool = False,
    temp_dir: str | None = None,
) -> dict[str, Any]:
    """
    Test a single scraper configuration.

    Args:
        scraper_name: Name of the scraper config
        headless: Whether to run browser in headless mode

    Returns:
        Dict with test results
    """
    logger.info(f"Testing scraper: {scraper_name}")

    result = {
        "scraper": scraper_name,
        "success": False,
        "execution_time": 0,
        "results": None,
        "error": None,
        "data_quality_issues": [],
    }

    start_time = time.time()

    try:
        # Get test SKU - use fake SKU for no results testing

        if test_no_results:
            sku = "24811283904712894120798"  # Fake SKU that should produce no results

            logger.info(f"Testing NO RESULTS scenario with fake SKU: {sku}")

        else:
            sku = get_test_sku(scraper_name)

            logger.info(f"Using test SKU: {sku}")

        # Load YAML config

        config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"

        parser = ScraperConfigParser()

        config = parser.load_from_file(config_path)

        # Clone config and replace SKU placeholders

        sku_config = copy.deepcopy(config)

        replace_sku_placeholders(sku_config, sku)

        # For no-results testing, disable rate limiting detection to avoid false positives

        if test_no_results:
            if hasattr(sku_config, "anti_detection"):
                sku_config.anti_detection.enable_rate_limiting = False

                logger.info("Disabled rate limiting detection for no-results test")

        # Execute workflow

        executor = WorkflowExecutor(sku_config, headless=headless)

        workflow_result = executor.execute_workflow()

        result["execution_time"] = time.time() - start_time

        result["results"] = workflow_result

        if workflow_result.get("success", False):
            extracted_data = workflow_result.get("results", {})

            if test_no_results:
                if extracted_data.get("no_results_found"):
                    result["success"] = True

                    result["data_quality_issues"] = []

                    logger.info(f"✅ {scraper_name}: SUCCESS - No results detected correctly.")

                else:
                    result["success"] = False

                    result["error"] = "No results test failed: no_results_found flag not set"

                    logger.error(
                        f"❌ {scraper_name}: FAILED - No results test failed: no_results_found flag not set"
                    )

            else:
                result["data_quality_issues"] = perform_data_quality_check(extracted_data)

                if not result["data_quality_issues"]:
                    result["success"] = True

                    logger.info(
                        f"✅ {scraper_name}: SUCCESS - {workflow_result.get('steps_executed', 0)} steps executed. Data quality check passed."
                    )

                    if extracted_data:
                        logger.info(f"   Extracted fields: {list(extracted_data.keys())}")

                        for field, value in extracted_data.items():
                            if isinstance(value, str) and len(value) > 50:
                                logger.info(f"   {field}: {value[:50]}...")

                            else:
                                logger.info(f"   {field}: {value}")

                else:
                    result["success"] = False

                    logger.error(
                        f"❌ {scraper_name}: FAILED - Data quality issues found: {', '.join(result['data_quality_issues'])}"
                    )

        else:
            result["success"] = False

            logger.error(f"❌ {scraper_name}: FAILED - Workflow execution failed")

    except Exception as e:
        result["execution_time"] = time.time() - start_time

        result["error"] = str(e)

        logger.error(f"❌ {scraper_name}: ERROR - {e}")

    return result


def main():
    """Main function to run all scraper tests."""
    args = parse_args()

    # Determine which scrapers to test and whether to use no-results mode
    test_no_results_mode = False
    scrapers_to_test = []

    if args.no_results:
        # No results testing - can specify scraper directly with --no-results or use --scrapers
        if args.no_results is True:
            # --no-results used without argument, check --scrapers or --all
            if args.all:
                # --all --no-results: test all scrapers with no-results
                logger.info("Testing NO RESULTS scenario for ALL scrapers")
                scrapers_to_test = ALL_SCRAPER_CONFIGS
                test_no_results_mode = True
            elif args.scrapers:
                # --scrapers with --no-results: test specified scrapers with no-results
                invalid = [s for s in args.scrapers if s not in ALL_SCRAPER_CONFIGS]
                if invalid:
                    logger.error(
                        f"Invalid scraper names: {invalid}. Available scrapers: {ALL_SCRAPER_CONFIGS}"
                    )
                    return
                scrapers_to_test = args.scrapers
                test_no_results_mode = True
            else:
                logger.error("--no-results requires --all or --scrapers scraper_name(s)")
                return
        else:
            # --no-results used with scraper name directly
            if args.scrapers or args.all:
                logger.error(
                    "Cannot use both --no-results scraper_name and --scrapers/--all together"
                )
                return
            scrapers_to_test = [args.no_results]
            test_no_results_mode = True
    # Regular testing mode
    elif args.all or not args.scrapers:
        scrapers_to_test = ALL_SCRAPER_CONFIGS
    else:
        scrapers_to_test = args.scrapers
        invalid = [s for s in scrapers_to_test if s not in ALL_SCRAPER_CONFIGS]
        if invalid:
            logger.error(
                f"Invalid scraper names: {invalid}. Available scrapers: {ALL_SCRAPER_CONFIGS}"
            )
            return

    logger.info(f"Starting {'NO RESULTS ' if test_no_results_mode else ''}scraper tests")
    logger.info(f"Testing configs: {scrapers_to_test}")

    # Test each scraper
    results = {}
    successful = 0
    failed = 0

    for scraper_name in scrapers_to_test:
        result = test_scraper_config(
            scraper_name, headless=args.headless, test_no_results=test_no_results_mode
        )
        results[scraper_name] = result

        if result["success"]:
            successful += 1
        else:
            failed += 1

        # Log summary for this scraper
        exec_time = result["execution_time"]
        test_type = "NO RESULTS" if test_no_results_mode else "REGULAR"
        logger.info(
            f"{scraper_name}: {'PASS' if result['success'] else 'FAIL'} ({exec_time:.2f}s) - {test_type}"
        )
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info(f"{'NO RESULTS ' if test_no_results_mode else ''}TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total scrapers tested: {len(scrapers_to_test)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if failed > 0:
        logger.info("\n❌ FAILED SCRAPERS:")
        for name, result in results.items():
            if not result["success"]:
                error = result.get("error", "Unknown error")
                data_quality_issues = result.get("data_quality_issues", [])
                if data_quality_issues:
                    logger.info(
                        f"  • {name}: Data quality issues: {', '.join(data_quality_issues)}"
                    )
                else:
                    logger.info(f"  • {name}: {error}")
    else:
        logger.info("\n✅ ALL SCRAPERS PASSED")

    # Detailed results
    logger.info("\n" + "=" * 60)
    logger.info("DETAILED RESULTS")
    logger.info("=" * 60)
    for name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        exec_time = result["execution_time"]
        logger.info(f"{name}: {status} ({exec_time:.2f}s)")


if __name__ == "__main__":
    main()
