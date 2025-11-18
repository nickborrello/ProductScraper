#!/usr/bin/env python3
"""
Test script to run scraper configs using WorkflowExecutor.

This script loads each scraper configuration, gets the test SKU from test data,
and executes the scraper using WorkflowExecutor. Results and errors are logged
for each test run.

Usage:
    python test_scrapers.py --all                    # Test all scrapers
    python test_scrapers.py --scrapers amazon orgill # Test specific scrapers
    python test_scrapers.py                          # Default: test all scrapers
"""

import sys
import json
import yaml
import time
import logging
import argparse
import copy
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scraper configs to test
ALL_SCRAPER_CONFIGS = [
    'amazon',
    'central_pet',
    'coastal',
    'mazuri',
    'orgill',
    'petfoodex',
    'phillips'
]

def parse_args():
    parser = argparse.ArgumentParser(description="Run scraper tests.")
    parser.add_argument(
        "--scrapers",
        nargs='+',
        help="List of scraper names to test (space-separated, e.g., --scrapers amazon orgill)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all scrapers"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: True)"
    )
    return parser.parse_args()

def get_test_sku(scraper_name: str) -> str:
    """Get the first test SKU for a scraper from its YAML config file."""
    config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
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

def test_scraper_config(scraper_name: str, headless: bool = True) -> Dict[str, Any]:
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
        "error": None
    }

    start_time = time.time()

    try:
        # Get test SKU
        sku = get_test_sku(scraper_name)
        logger.info(f"Using test SKU: {sku}")

        # Load YAML config
        config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
        parser = ScraperConfigParser()
        config = parser.load_from_file(config_path)

        # Clone config and replace SKU placeholders
        sku_config = copy.deepcopy(config)
        replace_sku_placeholders(sku_config, sku)

        # Execute workflow
        executor = WorkflowExecutor(sku_config, headless=headless)
        workflow_result = executor.execute_workflow()

        result["execution_time"] = time.time() - start_time
        result["results"] = workflow_result
        result["success"] = workflow_result.get("success", False)

        if result["success"]:
            logger.info(f"✅ {scraper_name}: SUCCESS - {workflow_result.get('steps_executed', 0)} steps executed")
            # Log extracted data
            extracted_data = workflow_result.get("results", {})
            if extracted_data:
                logger.info(f"   Extracted fields: {list(extracted_data.keys())}")
                for field, value in extracted_data.items():
                    if isinstance(value, str) and len(value) > 50:
                        logger.info(f"   {field}: {value[:50]}...")
                    else:
                        logger.info(f"   {field}: {value}")
        else:
            logger.error(f"❌ {scraper_name}: FAILED - Workflow execution failed")

    except Exception as e:
        result["execution_time"] = time.time() - start_time
        result["error"] = str(e)
        logger.error(f"❌ {scraper_name}: ERROR - {e}")

    return result

def main():
    """Main function to run all scraper tests."""
    args = parse_args()

    if args.all or not args.scrapers:
        SCRAPER_CONFIGS = ALL_SCRAPER_CONFIGS
    else:
        SCRAPER_CONFIGS = args.scrapers
        invalid = [s for s in SCRAPER_CONFIGS if s not in ALL_SCRAPER_CONFIGS]
        if invalid:
            logger.error(f"Invalid scraper names: {invalid}. Available scrapers: {ALL_SCRAPER_CONFIGS}")
            return

    logger.info("Starting scraper tests")
    logger.info(f"Testing configs: {SCRAPER_CONFIGS}")

    # Test each scraper
    results = {}
    successful = 0
    failed = 0

    for scraper_name in SCRAPER_CONFIGS:
        result = test_scraper_config(scraper_name, headless=args.headless)
        results[scraper_name] = result

        if result["success"]:
            successful += 1
        else:
            failed += 1

        # Log summary for this scraper
        exec_time = result["execution_time"]
        logger.info(f"{scraper_name}: {'PASS' if result['success'] else 'FAIL'} ({exec_time:.2f}s)")
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total scrapers tested: {len(SCRAPER_CONFIGS)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if failed > 0:
        logger.info("\n❌ FAILED SCRAPERS:")
        for name, result in results.items():
            if not result["success"]:
                error = result.get("error", "Unknown error")
                logger.info(f"  • {name}: {error}")
    else:
        logger.info("\n✅ ALL SCRAPERS PASSED")

    # Detailed results
    logger.info("\n" + "="*60)
    logger.info("DETAILED RESULTS")
    logger.info("="*60)
    for name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        exec_time = result["execution_time"]
        logger.info(f"{name}: {'PASS' if result['success'] else 'FAIL'} ({exec_time:.2f}s)")

if __name__ == "__main__":
    main()