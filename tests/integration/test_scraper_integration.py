"""
Integration tests for running scrapers locally and validating output.
"""

import os
import sys
import json
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.fixtures.scraper_validator import ScraperValidator
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor


class ScraperIntegrationTester:
    """Integration tester for running scrapers locally."""

    def __init__(self, test_data_path: Optional[str] = None):
        """Initialize the integration tester."""
        self.project_root = PROJECT_ROOT
        self.test_data_path = test_data_path or "tests/fixtures/scraper_test_data.json"

        with open(self.test_data_path, "r") as f:
            self.test_config = json.load(f)

        self.validator = ScraperValidator(self.test_data_path)

    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names."""
        configs_dir = self.project_root / "src" / "scrapers" / "configs"
        scrapers = []

        if not configs_dir.exists():
            return scrapers

        for item in configs_dir.glob("*.yaml"):
            scraper_name = item.stem  # Remove .yaml extension
            scrapers.append(scraper_name)

        return sorted(scrapers)

    def run_scraper_locally(
        self, scraper_name: str, skus: List[str], headless: bool = True
    ) -> Dict[str, Any]:
        """
        Run a scraper locally with given SKUs.

        Args:
            scraper_name: Name of the scraper to run
            skus: List of SKUs to scrape
            headless: Whether to run browser in headless mode

        Returns:
            Dict with results and any errors
        """
        results = {
            "scraper": scraper_name,
            "skus": skus,
            "success": False,
            "products": [],
            "errors": [],
            "execution_time": 0,
            "output": "",
        }

        start_time = time.time()

        try:
            # Load YAML config
            config_path = (
                self.project_root
                / "src"
                / "scrapers"
                / "configs"
                / f"{scraper_name}.yaml"
            )
            parser = ScraperConfigParser()
            config = parser.load_from_file(config_path)

            products = []
            for sku in skus:
                try:
                    # Clone config and replace {sku} placeholders
                    import copy

                    sku_config = copy.deepcopy(config)
                    for step in sku_config.workflows:
                        if step.action == "navigate" and "url" in step.params:
                            step.params["url"] = step.params["url"].replace(
                                "{sku}", sku
                            )

                    # Run workflow
                    executor = WorkflowExecutor(sku_config, headless=headless)
                    workflow_result = executor.execute_workflow()

                    if workflow_result["success"]:
                        # Extract product data
                        product_data = workflow_result["results"]
                        product_data["sku"] = sku
                        products.append(product_data)
                    else:
                        results["errors"].append(f"Failed to scrape SKU {sku}")

                except Exception as e:
                    results["errors"].append(f"Error scraping SKU {sku}: {e}")

            results["execution_time"] = time.time() - start_time

            if products:
                results["products"] = products
                results["success"] = True
                results["output"] = f"Successfully scraped {len(products)} products"
            else:
                results["success"] = False
                results["output"] = "No products scraped"

        except Exception as e:
            results["errors"].append(f"Setup failed: {e}")
            results["execution_time"] = time.time() - start_time

        return results

    def test_single_scraper(
        self, scraper_name: str, skus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Test a single scraper with validation.

        Args:
            scraper_name: Name of the scraper to test
            skus: Optional list of SKUs, uses test data if not provided

        Returns:
            Dict with test results
        """
        if skus is None:
            scraper_config = self.test_config.get(scraper_name, {})
            skus = scraper_config.get("test_skus", ["035585499741"])

        # Ensure skus is a list
        if not isinstance(skus, list):
            skus = [str(skus)]

        print(f"\n{'='*60}")
        print(f"TESTING SCRAPER: {scraper_name.upper()}")
        print(f"SKUs: {skus}")
        print(f"{'='*60}")

        # Run the scraper
        run_results = self.run_scraper_locally(scraper_name, skus)

        # Validate results
        validation_results = {}
        if run_results["success"] and run_results["products"]:
            validation_results = self.validator.validate_product_data(
                run_results["products"], scraper_name
            )

        # Combine results
        test_results = {
            "scraper": scraper_name,
            "run_results": run_results,
            "validation_results": validation_results,
            "overall_success": run_results["success"]
            and not validation_results.get("errors", []),
        }

        # Print summary
        self._print_test_summary(test_results)

        return test_results

    def test_all_scrapers(self, skip_failing: bool = True) -> Dict[str, Any]:
        """
        Test all available scrapers.

        Args:
            skip_failing: Whether to continue testing other scrapers if one fails

        Returns:
            Dict with results for all scrapers
        """
        scrapers = self.get_available_scrapers()
        results = {
            "total_scrapers": len(scrapers),
            "successful_scrapers": 0,
            "failed_scrapers": 0,
            "scraper_results": {},
            "summary": {},
        }

        print(f"\n{'='*80}")
        print(f"RUNNING INTEGRATION TESTS FOR ALL {len(scrapers)} SCRAPERS")
        print(f"{'='*80}")

        for scraper_name in scrapers:
            try:
                test_result = self.test_single_scraper(scraper_name)
                results["scraper_results"][scraper_name] = test_result

                if test_result["overall_success"]:
                    results["successful_scrapers"] += 1
                else:
                    results["failed_scrapers"] += 1

                if not skip_failing and not test_result["overall_success"]:
                    print(f"❌ Stopping tests due to failure in {scraper_name}")
                    break

            except Exception as e:
                print(f"❌ Unexpected error testing {scraper_name}: {e}")
                results["scraper_results"][scraper_name] = {
                    "scraper": scraper_name,
                    "overall_success": False,
                    "error": str(e),
                }
                results["failed_scrapers"] += 1

                if not skip_failing:
                    break

        # Generate summary
        results["summary"] = self._generate_summary(results)

        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print(f"{'='*80}")
        print(f"Total Scrapers: {results['total_scrapers']}")
        print(f"Successful: {results['successful_scrapers']}")
        print(f"Failed: {results['failed_scrapers']}")
        print(f"Success Rate: {results['summary']['success_rate']:.1f}%")

        if results["failed_scrapers"] > 0:
            print(f"\n❌ FAILED SCRAPERS:")
            for name, result in results["scraper_results"].items():
                if not result.get("overall_success", False):
                    print(f"  • {name}")
        else:
            print(f"\n✅ ALL SCRAPERS PASSED INTEGRATION TESTS")

        return results

    def _print_test_summary(self, test_results: Dict[str, Any]) -> None:
        """Print a summary of test results for a single scraper."""
        scraper = test_results["scraper"]
        run_results = test_results["run_results"]
        validation_results = test_results["validation_results"]

        print(f"\n📊 TEST SUMMARY: {scraper}")

        # Run results
        if run_results["success"]:
            print(f"✅ Execution: SUCCESS")
            print(f"   Products found: {len(run_results['products'])}")
        else:
            print(f"❌ Execution: FAILED")
            for error in run_results["errors"][:3]:
                print(f"   • {error}")

        # Validation results
        if validation_results:
            valid = validation_results.get("valid_products", 0)
            total = validation_results.get("total_products", 0)
            score = validation_results.get("data_quality_score", 0)

            print(f"🔍 Validation: {valid}/{total} products valid")
            print(f"   Data Quality Score: {score:.1f}")

            # Print field coverage
            field_coverage = validation_results.get("field_coverage", {})
            if field_coverage:
                print(f"   Field Coverage:")
                for field, coverage in field_coverage.items():
                    status = (
                        "✅" if coverage == 100.0 else "⚠️" if coverage > 0 else "❌"
                    )
                    print(f"     {status} {field}: {coverage:.1f}%")

            if validation_results.get("errors"):
                print(f"   Errors: {len(validation_results['errors'])}")
                for error in validation_results["errors"][:3]:  # Show first 3 errors
                    print(f"     - {error}")
            if validation_results.get("warnings"):
                print(f"   Warnings: {len(validation_results['warnings'])}")
                for warning in validation_results["warnings"][
                    :3
                ]:  # Show first 3 warnings
                    print(f"     - {warning}")

        # Overall result
        if test_results["overall_success"]:
            print(f"✅ OVERALL: PASSED")
        else:
            print(f"❌ OVERALL: FAILED")

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all test results."""
        summary = {
            "total_scrapers": results["total_scrapers"],
            "successful_scrapers": results["successful_scrapers"],
            "failed_scrapers": results["failed_scrapers"],
            "success_rate": 0.0,
            "failed_scrapers_list": [],
            "common_errors": {},
            "average_quality_score": 0.0,
        }

        if results["total_scrapers"] > 0:
            summary["success_rate"] = (
                results["successful_scrapers"] / results["total_scrapers"]
            ) * 100

        quality_scores = []
        for scraper_name, test_result in results["scraper_results"].items():
            if not test_result.get("overall_success", False):
                summary["failed_scrapers_list"].append(scraper_name)

            # Collect common errors
            run_errors = test_result.get("run_results", {}).get("errors", [])
            validation_errors = test_result.get("validation_results", {}).get(
                "errors", []
            )

            for error in run_errors + validation_errors:
                if error in summary["common_errors"]:
                    summary["common_errors"][error] += 1
                else:
                    summary["common_errors"][error] = 1

            # Collect quality scores
            score = test_result.get("validation_results", {}).get(
                "data_quality_score", 0
            )
            if score > 0:
                quality_scores.append(score)

        if quality_scores:
            summary["average_quality_score"] = sum(quality_scores) / len(quality_scores)

        return summary


# Pytest integration
class TestScraperIntegration:
    """Pytest test class for scraper integration tests."""

    @pytest.fixture
    def tester(self):
        """Create a ScraperIntegrationTester instance."""
        return ScraperIntegrationTester()

    def test_get_available_scrapers(self, tester):
        """Test that we can discover available scrapers."""
        scrapers = tester.get_available_scrapers()
        assert len(scrapers) > 0, "No scrapers found"
        assert "amazon" in scrapers, "Amazon scraper should be available"

        print(f"Found scrapers: {scrapers}")

    @pytest.mark.integration
    def test_single_scraper_execution(self, tester):
        """Test running a single scraper (integration test)."""
        # Use amazon as it's most likely to work
        result = tester.test_single_scraper("amazon")

        # Basic checks
        assert "scraper" in result
        assert result["scraper"] == "amazon"

        # Print results for debugging
        print(f"Test result: {result['overall_success']}")

    @pytest.mark.integration
    def test_all_scrapers_integration(self, tester):
        """Test all scrapers (full integration test)."""
        results = tester.test_all_scrapers(skip_failing=True)

        # Should have results for all scrapers
        assert len(results["scraper_results"]) > 0

        # Print summary
        print(
            f"Integration test results: {results['successful_scrapers']}/{results['total_scrapers']} passed"
        )


if __name__ == "__main__":
    # Allow running from command line
    import argparse

    parser = argparse.ArgumentParser(description="Run scraper integration tests")
    parser.add_argument("--scraper", help="Test specific scraper")
    parser.add_argument("--all", action="store_true", help="Test all scrapers")
    parser.add_argument("--skus", nargs="+", help="SKUs to test with")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    tester = ScraperIntegrationTester()

    if args.scraper:
        result = tester.test_single_scraper(args.scraper, args.skus)
        if not result["overall_success"]:
            sys.exit(1)
    elif args.all:
        results = tester.test_all_scrapers()
        if results["failed_scrapers"] > 0:
            sys.exit(1)
    else:
        print(
            "Use --scraper <name> to test a specific scraper or --all to test all scrapers"
        )
        print(f"Available scrapers: {tester.get_available_scrapers()}")
        sys.exit(1)
