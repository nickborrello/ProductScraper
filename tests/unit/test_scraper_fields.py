import os
import sys
import time
import threading
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.general.display import display_success, display_error, display_warning


class FieldTestStatus(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    ERROR = "🔥 ERROR"
    SKIP = "⏭️  SKIP"
    TIMEOUT = "⏰ TIMEOUT"


@dataclass
class FieldTestResult:
    field_name: str
    status: FieldTestStatus
    value: Any = None
    error_message: str = ""
    duration: float = 0.0


@dataclass
class ScraperTestResult:
    scraper_name: str
    overall_status: FieldTestStatus
    field_results: Dict[str, FieldTestResult]
    total_duration: float = 0.0


class GranularScraperTester:
    """Test individual fields for each scraper to identify specific failures."""

    def __init__(self):
        self.test_timeout = 30  # seconds per field test
        self.scraper_timeout = 60  # seconds per scraper

    def discover_scrapers(self) -> Dict[str, Any]:
        """Discover all scraper modules dynamically."""
        import glob
        import importlib.util

        scrapers_dir = os.path.join(PROJECT_ROOT, "scrapers")
        scraper_files = glob.glob(os.path.join(scrapers_dir, "*.py"))
        scraper_files = [f for f in scraper_files if not f.endswith("__init__.py")]

        # Exclude archived scrapers
        archive_dir = os.path.join(scrapers_dir, "archive")
        if os.path.exists(archive_dir):
            archived_files = glob.glob(os.path.join(archive_dir, "*.py"))
            archived_names = [os.path.basename(f) for f in archived_files]
            scraper_files = [
                f for f in scraper_files if os.path.basename(f) not in archived_names
            ]

        modules = {}
        for scraper_file in scraper_files:
            module_name = os.path.basename(scraper_file)[:-3]  # Remove .py extension

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, scraper_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[module_name] = module
            except Exception as e:
                print(f"❌ Failed to import scraper module {module_name}: {e}")

        return modules

    def get_scraper_function(self, module) -> Optional[callable]:
        """Find the scrape function in a module."""
        # Look for scrape_* functions
        for attr_name in dir(module):
            if attr_name.startswith("scrape_") and callable(getattr(module, attr_name)):
                return getattr(module, attr_name)
        return None

    def validate_field(
        self, product: dict, field_name: str, scrape_duration: float
    ) -> FieldTestResult:
        """Validate a specific field in the product data."""
        value = product.get(field_name)

        # Field-specific validation rules
        if field_name == "SKU":
            if not value or str(value).strip() == "":
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "SKU is empty",
                    scrape_duration,
                )
            if len(str(value).strip()) < 3:
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "SKU too short",
                    scrape_duration,
                )
            return FieldTestResult(
                field_name, FieldTestStatus.PASS, value, "", scrape_duration
            )

        elif field_name == "Name":
            if (
                not value
                or str(value).strip() == ""
                or str(value).strip().upper() == "N/A"
            ):
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "Name is empty or N/A",
                    scrape_duration,
                )
            if len(str(value).strip()) < 3:
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "Name too short",
                    scrape_duration,
                )
            return FieldTestResult(
                field_name, FieldTestStatus.PASS, value, "", scrape_duration
            )

        elif field_name == "Brand":
            if (
                value is None
                or str(value).strip() == ""
                or str(value).strip().upper() == "N/A"
            ):
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "Brand is empty or N/A",
                    scrape_duration,
                )
            return FieldTestResult(
                field_name, FieldTestStatus.PASS, value, "", scrape_duration
            )

        elif field_name == "Weight":
            if (
                value is None
                or str(value).strip() == ""
                or str(value).strip().upper() == "N/A"
            ):
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "Weight is empty or N/A",
                    scrape_duration,
                )
            return FieldTestResult(
                field_name, FieldTestStatus.PASS, value, "", scrape_duration
            )

        elif field_name == "Image URLs":
            if not value or (isinstance(value, list) and len(value) == 0):
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "No image URLs found",
                    scrape_duration,
                )
            if isinstance(value, list) and len(value) > 0:
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.PASS,
                    f"{len(value)} images",
                    "",
                    scrape_duration,
                )
            return FieldTestResult(
                field_name,
                FieldTestStatus.FAIL,
                value,
                "Invalid image URLs format",
                scrape_duration,
            )

        elif field_name in ["Special Order", "Product Disabled", "Product Cross Sell"]:
            # These are optional fields - pass if present or empty
            return FieldTestResult(
                field_name, FieldTestStatus.PASS, value, "", scrape_duration
            )

        else:
            # Unknown field - just check if it has a value
            if value is not None and str(value).strip() != "":
                return FieldTestResult(
                    field_name, FieldTestStatus.PASS, value, "", scrape_duration
                )
            else:
                return FieldTestResult(
                    field_name,
                    FieldTestStatus.FAIL,
                    value,
                    "Field is empty",
                    scrape_duration,
                )

    def get_fields_to_test(self, scraper_name: str) -> List[str]:
        """Get the list of fields to test for a specific scraper."""
        # Standard fields that all scrapers should have
        standard_fields = ["SKU", "Name", "Brand", "Weight", "Image URLs"]

        # Scraper-specific additional fields
        scraper_specific_fields = {
            "central_pet": ["Short Description"],
            "orgill": [],  # No additional fields
            "bradley_caldwell": [],  # No additional fields
            "coastal": [],
            "mazuri": [],
            "petfoodex": [],
            "phillips": [],
            "nassau_candy": [],
        }

        fields = standard_fields.copy()
        if scraper_name in scraper_specific_fields:
            fields.extend(scraper_specific_fields[scraper_name])

        return fields

    def test_scraper(self, scraper_name: str, module: Any) -> ScraperTestResult:
        """Test a scraper by scraping one product and checking if all required fields are present."""
        start_time = time.time()

        print(f"🔍 Testing {scraper_name}...")

        # Get scraper function
        scraper_func = self.get_scraper_function(module)
        if not scraper_func:
            print(f"   {FieldTestStatus.ERROR.value}")
            return ScraperTestResult(
                scraper_name=scraper_name,
                overall_status=FieldTestStatus.ERROR,
                field_results={},
                total_duration=time.time() - start_time,
            )

        # Get test SKU
        test_sku = getattr(module, "TEST_SKU", "035585499741")  # Default KONG product

        # Get fields to test
        fields_to_test = self.get_fields_to_test(scraper_name)

        try:
            # Temporarily suppress scraping summary output during testing
            from src.utils.general.display import set_suppress_summary

            set_suppress_summary(True)

            try:
                # Scrape the product
                results = scraper_func([test_sku])
            finally:
                # Restore summary display
                set_suppress_summary(False)

            # Check if we got results
            if not results or len(results) == 0 or results[0] is None:
                print(f"   {FieldTestStatus.FAIL.value}")
                return ScraperTestResult(
                    scraper_name=scraper_name,
                    overall_status=FieldTestStatus.FAIL,
                    field_results={},
                    total_duration=time.time() - start_time,
                )

            product = results[0]
            if not isinstance(product, dict):
                print(f"   {FieldTestStatus.FAIL.value}")
                return ScraperTestResult(
                    scraper_name=scraper_name,
                    overall_status=FieldTestStatus.FAIL,
                    field_results={},
                    total_duration=time.time() - start_time,
                )

            # Validate all fields
            field_results = {}
            all_passed = True

            for field_name in fields_to_test:
                result = self.validate_field(
                    product, field_name, time.time() - start_time
                )
                field_results[field_name] = result
                if result.status != FieldTestStatus.PASS:
                    all_passed = False

                # Print individual field status
                status_emoji = result.status.value
                print(f"   {field_name}: {status_emoji}")
                if result.status != FieldTestStatus.PASS:
                    print(f"      Error: {result.error_message}")

            # Return result
            overall_status = (
                FieldTestStatus.PASS if all_passed else FieldTestStatus.FAIL
            )
            print(
                f"   Overall: {overall_status.value} ({time.time() - start_time:.1f}s)"
            )

            return ScraperTestResult(
                scraper_name=scraper_name,
                overall_status=overall_status,
                field_results=field_results,
                total_duration=time.time() - start_time,
            )

        except Exception as e:
            # Restore summary display in case of error
            try:
                set_suppress_summary(False)
            except:
                pass

            print(f"   {FieldTestStatus.ERROR.value}")
            return ScraperTestResult(
                scraper_name=scraper_name,
                overall_status=FieldTestStatus.ERROR,
                field_results={},
                total_duration=time.time() - start_time,
            )

    def run_all_tests(
        self, scraper_names: Optional[List[str]] = None
    ) -> Dict[str, ScraperTestResult]:
        """Run granular field tests for all or specified scrapers."""
        print("\n" + "=" * 80)
        print("🔬 GRANULAR SCRAPER FIELD TESTS")
        print("=" * 80)
        print(
            "Testing individual fields for each scraper to identify specific failures..."
        )
        print("=" * 80)

        modules = self.discover_scrapers()
        results = {}

        # Filter to specified scrapers if provided
        if scraper_names:
            modules = {
                name: module
                for name, module in modules.items()
                if name in scraper_names
            }

        for scraper_name, module in modules.items():
            result = self.test_scraper(scraper_name, module)
            results[scraper_name] = result

        # Print summary
        self.print_summary(results)

        return results

    def print_summary(self, results: Dict[str, ScraperTestResult]):
        """Print a detailed summary of test results."""
        print("\n" + "=" * 80)
        print("📊 GRANULAR TEST RESULTS SUMMARY")
        print("=" * 80)

        passed_scrapers = []
        failed_scrapers = []
        error_scrapers = []

        for scraper_name, result in results.items():
            print(f"\n{scraper_name.upper()}:")
            print(f"Overall: {result.status.value} ({result.total_duration:.1f}s)")

            for field_name, field_result in result.field_results.items():
                status_emoji = field_result.status.value
                value_display = (
                    str(field_result.value)[:50] + "..."
                    if field_result.value and len(str(field_result.value)) > 50
                    else str(field_result.value)
                )
                print(f"  {field_name}: {status_emoji}")
                if field_result.status != FieldTestStatus.PASS:
                    print(f"    Error: {field_result.error_message}")
                elif field_result.value is not None:
                    print(f"    Value: {value_display}")

            # Categorize scrapers
            if result.overall_status == FieldTestStatus.PASS:
                passed_scrapers.append(scraper_name)
            elif result.overall_status == FieldTestStatus.ERROR:
                error_scrapers.append(scraper_name)
            else:
                failed_scrapers.append(scraper_name)

        print("\n" + "=" * 80)
        print("🎯 SUMMARY BY SCRAPER")
        print("=" * 80)

        if passed_scrapers:
            print(f"✅ FULLY WORKING ({len(passed_scrapers)}):")
            for scraper in passed_scrapers:
                print(f"   • {scraper}")

        if failed_scrapers:
            print(f"❌ PARTIALLY FAILING ({len(failed_scrapers)}):")
            for scraper in failed_scrapers:
                result = results[scraper]
                failed_fields = [
                    f
                    for f, r in result.field_results.items()
                    if r.status != FieldTestStatus.PASS
                ]
                print(f"   • {scraper} (failed: {', '.join(failed_fields)})")

        if error_scrapers:
            print(f"🔥 COMPLETELY BROKEN ({len(error_scrapers)}):")
            for scraper in error_scrapers:
                print(f"   • {scraper}")

        total_scrapers = len(results)
        success_rate = (
            len(passed_scrapers) / total_scrapers * 100 if total_scrapers > 0 else 0
        )
        print(f"Success rate: {success_rate:.1f}%")


def run_granular_tests(scraper_names: Optional[List[str]] = None):
    """Convenience function to run granular scraper tests."""
    tester = GranularScraperTester()
    return tester.run_all_tests(scraper_names)


if __name__ == "__main__":
    # Run tests for all scrapers
    results = run_granular_tests()
