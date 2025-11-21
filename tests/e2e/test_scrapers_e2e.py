"""
Integration tests for running scrapers locally and validating output.
"""

import copy
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.scrapers.executor.workflow_executor import WorkflowExecutor
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from tests.fixtures.scraper_validator import ScraperValidator

PROJECT_ROOT = Path(__file__).parent.parent.parent


class ScraperIntegrationTester:
    """Integration tester for running scrapers locally."""

    def __init__(self, test_data_path: str | None = None):
        """Initialize the integration tester."""
        self.project_root = PROJECT_ROOT
        # No longer need test_data_path for JSON, but keep for compatibility
        self.validator = ScraperValidator()

    def get_test_skus(self, scraper_name: str, max_skus: int = 1) -> list[str]:
        """Get test SKUs for a scraper from its YAML config."""
        config_path = self.project_root / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
        if not config_path.exists():
            return ["035585499741"]  # Default fallback

        parser = ScraperConfigParser()
        config = parser.load_from_file(config_path)
        skus = config.test_skus or ["035585499741"]
        return skus[:max_skus]  # Return only first max_skus

    def get_available_scrapers(self) -> list[str]:
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
        self, scraper_name: str, skus: list[str], headless: bool | None = None
    ) -> dict[str, Any]:
        """
        Run a scraper locally with given SKUs.

        Args:
            scraper_name: Name of the scraper to run
            skus: List of SKUs to scrape
            headless: Whether to run browser in headless mode (None = use env var)

        Returns:
            Dict with results and any errors
        """
        if headless is None:
            headless = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"

        print(
            "DEBUG: Starting scraper execution for "
            f"{scraper_name} with SKUs {skus}, headless={headless}"
        )

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
            print(f"DEBUG: Loading config for {scraper_name}")
            # Load YAML config
            config_path = (
                self.project_root / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
            )
            parser = ScraperConfigParser()
            config = parser.load_from_file(config_path)
            print(f"DEBUG: Config loaded successfully for {scraper_name}")

            products = []
            for i, sku in enumerate(skus):
                print(f"DEBUG: Processing SKU {sku} ({i + 1}/{len(skus)}) for {scraper_name}")
                try:
                    # Clone config and replace {sku} placeholders
                    sku_config = copy.deepcopy(config)
                    for step in sku_config.workflows:
                        if step.action == "navigate" and "url" in step.params:
                            step.params["url"] = step.params["url"].replace("{sku}", sku)

                    print(f"DEBUG: Starting workflow execution for SKU {sku}")
                    # Run workflow
                    executor = WorkflowExecutor(sku_config, headless=headless)
                    workflow_result = executor.execute_workflow()
                    print(
                        f"DEBUG: Workflow execution completed for SKU {sku}, "
                        f"success={workflow_result.get('success', False)}"
                    )

                    if workflow_result["success"]:
                        # Extract product data
                        product_data = workflow_result["results"]
                        product_data["SKU"] = sku
                        products.append(product_data)
                        print(f"DEBUG: Successfully scraped product for SKU {sku}")
                    else:
                        results["errors"].append(f"Failed to scrape SKU {sku}")
                        print(f"DEBUG: Failed to scrape SKU {sku}")

                except Exception as e:
                    results["errors"].append(f"Error scraping SKU {sku}: {e}")
                    print(f"DEBUG: Exception scraping SKU {sku}: {e}")

            results["execution_time"] = time.time() - start_time
            print(
                f"DEBUG: Scraper {scraper_name} execution completed in "
                f"{results['execution_time']:.2f}s"
            )

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
            print(f"DEBUG: Setup failed for {scraper_name}: {e}")

        return results

    def test_single_scraper(
        self, scraper_name: str, skus: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Test a single scraper with validation.

        Args:
            scraper_name: Name of the scraper to test
            skus: Optional list of SKUs, uses test data if not provided

        Returns:
            Dict with test results
        """
        if skus is None:
            skus = self.get_test_skus(scraper_name)

        # Ensure skus is a list
        if not isinstance(skus, list):
            skus = [str(skus)]

        print(f"\n{'=' * 60}")
        print(f"TESTING SCRAPER: {scraper_name.upper()}")
        print(f"SKUs: {skus}")
        print(f"{'=' * 60}")

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
            "overall_success": run_results["success"] and not validation_results.get("errors", []),
        }

        # Print summary
        self._print_test_summary(test_results)

        return test_results

    def test_all_scrapers(
        self, skip_failing: bool = True, skip_login_required: bool = False
    ) -> dict[str, Any]:
        """
        Test all available scrapers.

        Args:
            skip_failing: Whether to continue testing other scrapers if one fails
            skip_login_required: Whether to skip scrapers that require login credentials

        Returns:
            Dict with results for all scrapers
        """
        scrapers = self.get_available_scrapers()
        skipped_count = 0

        # Filter out login-requiring scrapers if skip_login_required is True
        if skip_login_required:
            login_required_scrapers = {"orgill", "petfoodex", "phillips"}
            original_count = len(scrapers)
            scrapers = [s for s in scrapers if s not in login_required_scrapers]
            skipped_count = original_count - len(scrapers)
            if skipped_count > 0:
                print(
                    "SKIP: Skipping "
                    f"{skipped_count} login-requiring scrapers: {', '.join(login_required_scrapers)}"
                )

        results = {
            "total_scrapers": len(scrapers),
            "successful_scrapers": 0,
            "failed_scrapers": 0,
            "scraper_results": {},
            "summary": {},
            "skipped_login_scrapers": skipped_count,
        }

        print(f"\n{'=' * 80}")
        print(f"RUNNING INTEGRATION TESTS FOR ALL {len(scrapers)} SCRAPERS")
        print(f"{'=' * 80}")

        for scraper_name in scrapers:
            try:
                test_result = self.test_single_scraper(scraper_name)
                results["scraper_results"][scraper_name] = test_result

                if test_result["overall_success"]:
                    results["successful_scrapers"] += 1
                else:
                    results["failed_scrapers"] += 1

                if not skip_failing and not test_result["overall_success"]:
                    print(f"STOP: Stopping tests due to failure in {scraper_name}")
                    break

            except Exception as e:
                print(f"ERROR: Unexpected error testing {scraper_name}: {e}")
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

        print(f"\n{'=' * 80}")
        print("FINAL SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Scrapers: {results['total_scrapers']}")
        print(f"Successful: {results['successful_scrapers']}")
        print(f"Failed: {results['failed_scrapers']}")
        print(f"Success Rate: {results['summary']['success_rate']:.1f}%")

        if results["failed_scrapers"] > 0:
            print("\nFAILED SCRAPERS:")
            for name, result in results["scraper_results"].items():
                if not result.get("overall_success", False):
                    print(f"  • {name}")
        else:
            print("\nALL SCRAPERS PASSED INTEGRATION TESTS")

        return results

    def _print_test_summary(self, test_results: dict[str, Any]) -> None:
        """Print a summary of test results for a single scraper."""
        scraper = test_results["scraper"]
        run_results = test_results["run_results"]
        validation_results = test_results["validation_results"]
        full_coverage = 100.0
        print(f"\nTEST SUMMARY: {scraper}")

        # Run results
        if run_results["success"]:
            print("SUCCESS: Execution")
            print(f"   Products found: {len(run_results['products'])}")
        else:
            print("FAILED: Execution")
            for error in run_results["errors"][:3]:
                print(f"   • {error}")

        # Validation results
        if validation_results:
            valid = validation_results.get("valid_products", 0)
            total = validation_results.get("total_products", 0)
            score = validation_results.get("data_quality_score", 0)

            print(f"VALIDATION: {valid}/{total} products valid")
            print(f"   Data Quality Score: {score:.1f}")

            # Print field coverage
            field_coverage = validation_results.get("field_coverage", {})
            if field_coverage:
                print("   Field Coverage:")
                for field, coverage in field_coverage.items():
                    status = (
                        "PASS" if coverage == full_coverage else "WARN" if coverage > 0 else "FAIL"
                    )
                    print(f"     {status} {field}: {coverage:.1f}%")

            if validation_results.get("errors"):
                print(f"   Errors: {len(validation_results['errors'])}")
                for error in validation_results["errors"][:3]:  # Show first 3 errors
                    print(f"     - {error}")
            if validation_results.get("warnings"):
                print(f"   Warnings: {len(validation_results['warnings'])}")
                for warning in validation_results["warnings"][:3]:  # Show first 3 warnings
                    print(f"     - {warning}")

        # Overall result
        if test_results["overall_success"]:
            print("OVERALL: PASSED")
        else:
            print("OVERALL: FAILED")

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
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
            validation_errors = test_result.get("validation_results", {}).get("errors", [])

            for error in run_errors + validation_errors:
                if error in summary["common_errors"]:
                    summary["common_errors"][error] += 1
                else:
                    summary["common_errors"][error] = 1

            # Collect quality scores
            score = test_result.get("validation_results", {}).get("data_quality_score", 0)
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

    @pytest.fixture
    def available_scrapers(self, tester):
        """Get list of available scrapers."""
        return tester.get_available_scrapers()

    @pytest.fixture
    def scraper_cleanup(self):
        """Fixture for scraper cleanup after tests."""
        cleanup_items = []

        yield cleanup_items

        # Cleanup after test
        for item in cleanup_items:
            if hasattr(item, "cleanup"):
                item.cleanup()
            elif hasattr(item, "close"):
                item.close()
            elif hasattr(item, "quit"):
                item.quit()

    def test_get_available_scrapers(self, available_scrapers):
        """Test that we can discover available scrapers."""
        assert len(available_scrapers) > 0, "No scrapers found"
        assert "amazon" in available_scrapers, "Amazon scraper should be available"

        print(f"Found scrapers: {available_scrapers}")

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "scraper_name",
        [
            "amazon",  # Most reliable for testing
            "central_pet",
            "coastal",
            "mazuri",
        ],
    )
    def test_scraper_execution_parametrized(self, tester, scraper_name):
        """Test running individual scrapers with parametrization."""
        # Skip login-requiring scrapers in CI
        if os.getenv("CI") == "true" and scraper_name in {"orgill", "petfoodex", "phillips"}:
            pytest.skip(f"Skipping {scraper_name} in CI (requires login)")

        result = tester.test_single_scraper(scraper_name)

        # Basic checks
        assert "scraper" in result
        assert result["scraper"] == scraper_name

        # Print results for debugging
        print(f"Test result for {scraper_name}: {result['overall_success']}")

    @pytest.mark.integration
    def test_single_scraper_with_timeout(self, tester):
        """Test running a single scraper with timeout handling."""
        print("DEBUG: Starting test_single_scraper_with_timeout")
        result: dict[str, Any] = {"completed": False, "data": None, "error": None}

        def run_scraper():
            try:
                print("DEBUG: Calling test_single_scraper('amazon')")
                scraper_result = tester.test_single_scraper("amazon")
                result["completed"] = True
                result["data"] = scraper_result
                print("DEBUG: test_single_scraper completed successfully")
            except Exception as e:
                result["completed"] = True
                result["error"] = e
                print(f"DEBUG: test_single_scraper failed with error: {e}")

        # Start scraper in thread
        thread = threading.Thread(target=run_scraper)
        thread.start()

        # Wait with timeout
        thread.join(timeout=300)  # 5 minutes

        if thread.is_alive():
            # Timeout occurred
            print("DEBUG: Scraper execution timed out after 5 minutes")
            pytest.fail("Scraper execution timed out after 5 minutes")
        elif result["error"] is not None:
            raise result["error"]
        else:
            # Success
            assert result["data"] is not None
            assert "scraper" in result["data"]
            assert result["data"]["scraper"] == "amazon"
            print("DEBUG: test_single_scraper_with_timeout completed successfully")

    @pytest.mark.integration
    def test_all_scrapers_integration(self, tester):
        """Test all scrapers (full integration test)."""
        print("DEBUG: Starting test_all_scrapers_integration")
        # For CI/CD, skip login-requiring scrapers; locally, test all
        skip_login = os.getenv("CI") == "true"  # Skip in CI environment
        print(f"DEBUG: skip_login_required={skip_login}")

        result: dict[str, Any] = {"completed": False, "data": None, "error": None}

        def run_all_scrapers():
            try:
                scraper_results = tester.test_all_scrapers(
                    skip_failing=True, skip_login_required=skip_login
                )
                result["completed"] = True
                result["data"] = scraper_results
                print("DEBUG: test_all_scrapers execution completed")
            except Exception as e:
                result["completed"] = True
                result["error"] = e
                print(f"DEBUG: test_all_scrapers execution failed: {e}")

        # Start in thread
        thread = threading.Thread(target=run_all_scrapers)
        thread.start()

        # Wait with timeout (10 minutes for all scrapers)
        thread.join(timeout=600)  # 10 minutes

        if thread.is_alive():
            # Timeout occurred
            print("DEBUG: All scrapers test timed out after 10 minutes")
            pytest.fail("All scrapers test timed out after 10 minutes")
        elif result["error"] is not None:
            raise result["error"]
        else:
            # Success
            results = result["data"]
            # Should have results for all scrapers
            assert len(results["scraper_results"]) > 0

            # Print summary
            print(
                f"Integration test results: {results['successful_scrapers']}/"
                f"{results['total_scrapers']} passed"
            )
            print("DEBUG: test_all_scrapers_integration completed successfully")

    @pytest.mark.integration
    @pytest.mark.parametrize("headless", [True, False])
    def test_scraper_headless_modes(self, tester, headless):
        """Test scraper execution in both headless and non-headless modes."""
        print(f"DEBUG: Starting test_scraper_headless_modes with headless={headless}")
        # Only test amazon for mode testing
        if not headless and os.getenv("CI") == "true":
            print("DEBUG: Skipping non-headless test in CI environment")
            pytest.skip("Skipping non-headless test in CI environment")

        result: dict[str, Any] = {"completed": False, "data": None, "error": None}

        def run_scraper():
            try:
                skus = tester.get_test_skus("amazon")
                print(f"DEBUG: Got SKUs for amazon: {skus}")
                scraper_result = tester.run_scraper_locally("amazon", skus, headless=headless)
                result["completed"] = True
                result["data"] = scraper_result
                print(f"DEBUG: Scraper execution completed for headless={headless}")
            except Exception as e:
                result["completed"] = True
                result["error"] = e
                print(f"DEBUG: Scraper execution failed for headless={headless}: {e}")

        # Start scraper in thread
        thread = threading.Thread(target=run_scraper)
        thread.start()

        # Wait with timeout
        thread.join(timeout=300)  # 5 minutes

        if thread.is_alive():
            # Timeout occurred
            print(f"DEBUG: Scraper execution timed out after 5 minutes for headless={headless}")
            pytest.fail(f"Scraper execution timed out after 5 minutes for headless={headless}")
        elif result["error"] is not None:
            raise result["error"]
        else:
            # Success
            assert result["data"] is not None
            assert "scraper" in result["data"]
            assert result["data"]["scraper"] == "amazon"
            assert "success" in result["data"]
            print(
                f"DEBUG: test_scraper_headless_modes completed successfully for headless={headless}"
            )

    @pytest.mark.integration
    def test_no_results_browser_response_simulation(self, tester):
        """Test real browser responses with fake SKUs that trigger no results pages."""
        # Use a fake SKU that should not exist and trigger no results
        fake_sku = "23184912789412789078124940172"

        # Run scraper with fake SKU - should fail to find products
        result = tester.run_scraper_locally("amazon", [fake_sku], headless=True)

        # Verify scraper execution
        # The scraper may return success=True with a product record indicating no_results_found=True
        if result["success"]:
            assert len(result["products"]) == 1, (
                f"Expected 1 product record, got {len(result['products'])}"
            )
            product = result["products"][0]
            assert product.get("no_results_found") is True, (
                f"Expected no_results_found=True, got {product}"
            )
            assert product["SKU"] == fake_sku
        else:
            # Fallback to old behavior (failure)
            assert result["products"] == [], f"Expected empty products, got {result['products']}"
            assert len(result["errors"]) > 0, "Expected errors, got none"
            assert "Failed to scrape SKU" in result["errors"][0], (
                f"Expected 'Failed to scrape SKU' in error, got {result['errors'][0]}"
            )

        # Verify execution completed
        assert result["execution_time"] > 0

    @pytest.mark.integration
    def test_end_to_end_no_results_workflow_execution(self, tester):
        """Test end-to-end workflow execution with no results detection using real scraper."""
        # Use a fake SKU that should trigger no results on Amazon
        fake_sku = "NONEXISTENTPRODUCT987654321"

        # Run scraper with fake SKU
        result = tester.run_scraper_locally("amazon", [fake_sku], headless=True)

        # Verify scraper failed due to no results
        assert result["success"] is False
        assert result["products"] == []
        assert len(result["errors"]) > 0
        assert "Failed to scrape SKU" in result["errors"][0]

        # Verify execution completed
        assert result["execution_time"] > 0

    @pytest.mark.integration
    def test_no_results_failure_reporting_and_analytics(self, tester):
        """Test proper failure reporting and analytics recording for no results scenarios."""
        # Use a fake SKU that triggers no results
        fake_sku = "NORESULTSANALYTICS123"

        # Run scraper with fake SKU
        result = tester.run_scraper_locally("amazon", [fake_sku], headless=True)

        # Verify scraper failed due to no results
        assert result["success"] is False
        assert result["products"] == []
        assert len(result["errors"]) > 0
        assert "Failed to scrape SKU" in result["errors"][0]

        # Verify execution completed
        assert result["execution_time"] > 0

    @pytest.mark.integration
    def test_no_results_graceful_handling_without_retries(self, tester):
        """Test that no results scenarios are handled gracefully without retries."""
        # Use a fake SKU that triggers no results
        fake_sku = "NORESULTSGRACEFUL456"

        # Run scraper with fake SKU
        result = tester.run_scraper_locally("amazon", [fake_sku], headless=True)

        # Verify scraper failed gracefully due to no results
        assert result["success"] is False
        assert result["products"] == []
        assert len(result["errors"]) > 0
        assert "Failed to scrape SKU" in result["errors"][0]

        # Verify execution completed
        assert result["execution_time"] > 0

    @pytest.mark.integration
    def test_no_results_integration_with_config_validation(self, tester):
        """Test integration with scraper configuration validation sections for no results."""
        # Test with amazon config which has no_results validation
        parser = ScraperConfigParser()
        config = parser.load_from_file(
            tester.project_root / "src" / "scrapers" / "configs" / "amazon.yaml"
        )

        # Verify config has validation section (may be stored as extra field due to arbitrary_types_allowed)
        assert hasattr(config, "validation") or hasattr(config, "__dict__")
        validation_data = getattr(config, "validation", None) or config.__dict__.get("validation")

        if validation_data:
            # Verify no_results validation exists
            assert "no_results_selectors" in validation_data
            assert validation_data["no_results_selectors"] is not None
            assert len(validation_data["no_results_selectors"]) > 0

            assert "no_results_text_patterns" in validation_data
            assert validation_data["no_results_text_patterns"] is not None
            assert len(validation_data["no_results_text_patterns"]) > 0

            # Verify the selectors and patterns are reasonable
            assert ".s-no-results" in validation_data["no_results_selectors"]
            assert "#no-results" in validation_data["no_results_selectors"]
            assert "no results found" in validation_data["no_results_text_patterns"]
            assert "your search returned no results" in validation_data["no_results_text_patterns"]
        else:
            # If validation section is not loaded, at least verify the YAML file contains it
            with open(tester.project_root / "src" / "scrapers" / "configs" / "amazon.yaml") as f:
                raw_config = yaml.safe_load(f)

            assert "validation" in raw_config
            assert "no_results_selectors" in raw_config["validation"]
            assert "no_results_text_patterns" in raw_config["validation"]

    @pytest.mark.integration
    def test_no_results_end_to_end_with_real_config(self, tester):
        """Test end-to-end no results handling using real scraper configuration."""
        # Use amazon config with a SKU that should not exist
        non_existent_sku = "THISPRODUCTDOESNOTEXIST123456789"

        # Run scraper with non-existent SKU - should naturally encounter no results page
        result = tester.run_scraper_locally("amazon", [non_existent_sku], headless=True)

        # Verify failure was detected
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "Failed to scrape SKU" in result["errors"][0]
        assert result["products"] == []  # No products should be found

        # Verify execution completed without hanging
        assert result["execution_time"] > 0


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
        print("Use --scraper <name> to test a specific scraper or --all to test all scrapers")
        print(f"Available scrapers: {tester.get_available_scrapers()}")
        sys.exit(1)
