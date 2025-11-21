import os
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Constants
MIN_FIELD_LENGTH = 3
TRUNCATION_LENGTH = 50


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
    field_results: dict[str, FieldTestResult]
    total_duration: float = 0.0


class GranularScraperTester:
    """Test individual fields for each scraper to identify specific failures."""

    def __init__(self):
        self.test_timeout = 30  # seconds per field test
        self.scraper_timeout = 60  # seconds per scraper

    def discover_scrapers(self) -> dict[str, Any]:
        """Discover all scraper modules dynamically."""
        import glob  # noqa: PLC0415 - Dynamic import for scraper discovery
        import importlib.util  # noqa: PLC0415

        scrapers_dir = os.path.join(PROJECT_ROOT, "scrapers")
        scraper_files = glob.glob(os.path.join(scrapers_dir, "*.py"))
        scraper_files = [f for f in scraper_files if not f.endswith("__init__.py")]

        # Exclude archived scrapers
        archive_dir = os.path.join(scrapers_dir, "archive")
        if os.path.exists(archive_dir):
            archived_files = glob.glob(os.path.join(archive_dir, "*.py"))
            archived_names = [os.path.basename(f) for f in archived_files]
            scraper_files = [f for f in scraper_files if os.path.basename(f) not in archived_names]

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

    def get_scraper_function(self, module) -> Callable | None:
        """Find the scrape function in a module."""
        for attr_name in dir(module):
            if attr_name.startswith("scrape_"):
                func = getattr(module, attr_name)
                # Check if the function is defined in this module (not imported)
                if hasattr(func, "__module__") and func.__module__ == module.__name__:
                    return func
        return None

    def test_single_field(
        self, scraper_func: callable, test_sku: str, field_name: str
    ) -> FieldTestResult:
        """Test a single field for a scraper."""
        start_time = time.time()

        def run_test():
            try:
                # Run the scraper
                results = scraper_func([test_sku])

                if not results or len(results) == 0:
                    return FieldTestResult(
                        field_name=field_name,
                        status=FieldTestStatus.FAIL,
                        error_message="No results returned",
                        duration=time.time() - start_time,
                    )

                product = results[0]
                if not isinstance(product, dict):
                    return FieldTestResult(
                        field_name=field_name,
                        status=FieldTestStatus.FAIL,
                        error_message="Invalid product data type",
                        duration=time.time() - start_time,
                    )

                # Check the specific field
                return self.validate_field(product, field_name, time.time() - start_time)

            except Exception as e:
                return FieldTestResult(
                    field_name=field_name,
                    status=FieldTestStatus.ERROR,
                    error_message=str(e),
                    duration=time.time() - start_time,
                )

        # Run test with timeout
        result_container = {"result": None, "completed": False}

        def run_test_thread():
            result_container["result"] = run_test()
            result_container["completed"] = True

        thread = threading.Thread(target=run_test_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.test_timeout)

        if not result_container["completed"]:
            return FieldTestResult(
                field_name=field_name,
                status=FieldTestStatus.TIMEOUT,
                error_message=f"Test timed out after {self.test_timeout}s",
                duration=self.test_timeout,
            )

        result = result_container["result"]
        result.duration = time.time() - start_time
        return result

    def validate_field(  # noqa: PLR0911 - Validation requires multiple return paths
        self, product: dict, field_name: str, duration: float
    ) -> FieldTestResult:
        """Validate a specific field in the product data."""
        value = product.get(field_name)

        # Dispatch to specific validation methods
        if field_name == "SKU":
            return self._validate_sku(value, field_name, duration)
        elif field_name == "Name":
            return self._validate_name(value, field_name, duration)
        elif field_name == "Brand":
            return self._validate_brand(value, field_name, duration)
        elif field_name == "Weight":
            return self._validate_weight(value, field_name, duration)
        elif field_name == "Image URLs":
            return self._validate_image_urls(value, field_name, duration)
        elif field_name in ["Special Order", "Product Disabled"]:
            return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)
        else:
            return self._validate_generic(value, field_name, duration)

    def _validate_sku(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if not value or str(value).strip() == "":
            return FieldTestResult(
                field_name, FieldTestStatus.FAIL, value, "SKU is empty", duration
            )
        if len(str(value).strip()) < MIN_FIELD_LENGTH:
            return FieldTestResult(
                field_name, FieldTestStatus.FAIL, value, "SKU too short", duration
            )
        return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)

    def _validate_name(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if not value or str(value).strip() == "" or str(value).strip().upper() == "N/A":
            return FieldTestResult(
                field_name,
                FieldTestStatus.FAIL,
                value,
                "Name is empty or N/A",
                duration,
            )
        if len(str(value).strip()) < MIN_FIELD_LENGTH:
            return FieldTestResult(
                field_name, FieldTestStatus.FAIL, value, "Name too short", duration
            )
        return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)

    def _validate_brand(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if value is None or str(value).strip() == "" or str(value).strip().upper() == "N/A":
            return FieldTestResult(
                field_name,
                FieldTestStatus.FAIL,
                value,
                "Brand is empty or N/A",
                duration,
            )
        return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)

    def _validate_weight(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if value is None or str(value).strip() == "" or str(value).strip().upper() == "N/A":
            return FieldTestResult(
                field_name,
                FieldTestStatus.FAIL,
                value,
                "Weight is empty or N/A",
                duration,
            )
        return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)

    def _validate_image_urls(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if not value or (isinstance(value, list) and len(value) == 0):
            return FieldTestResult(
                field_name,
                FieldTestStatus.FAIL,
                value,
                "No image URLs found",
                duration,
            )
        if isinstance(value, list) and len(value) > 0:
            return FieldTestResult(
                field_name,
                FieldTestStatus.PASS,
                f"{len(value)} images",
                "",
                duration,
            )
        return FieldTestResult(
            field_name,
            FieldTestStatus.FAIL,
            value,
            "Invalid image URLs format",
            duration,
        )

    def _validate_generic(self, value: Any, field_name: str, duration: float) -> FieldTestResult:
        if value is not None and str(value).strip() != "":
            return FieldTestResult(field_name, FieldTestStatus.PASS, value, "", duration)
        return FieldTestResult(field_name, FieldTestStatus.FAIL, value, "Field is empty", duration)

    def get_fields_to_test(self, scraper_name: str) -> list[str]:
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
        """Test all fields for a single scraper."""
        start_time = time.time()

        print(f"\n🔍 Testing {scraper_name}...")

        # Get scraper function
        scraper_func = self.get_scraper_function(module)
        if not scraper_func:
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

        # Test each field
        field_results = {}
        for field_name in fields_to_test:
            print(f"   Testing {field_name}...", end=" ", flush=True)
            result = self.test_single_field(scraper_func, test_sku, field_name)
            field_results[field_name] = result
            print(f"{result.status.value}")

            if result.status != FieldTestStatus.PASS:
                print(f"      {result.error_message}")

        # Determine overall status
        if any(r.status == FieldTestStatus.ERROR for r in field_results.values()):
            overall_status = FieldTestStatus.ERROR
        elif any(r.status == FieldTestStatus.FAIL for r in field_results.values()):
            overall_status = FieldTestStatus.FAIL
        elif any(r.status == FieldTestStatus.TIMEOUT for r in field_results.values()):
            overall_status = FieldTestStatus.TIMEOUT
        else:
            overall_status = FieldTestStatus.PASS

        return ScraperTestResult(
            scraper_name=scraper_name,
            overall_status=overall_status,
            field_results=field_results,
            total_duration=time.time() - start_time,
        )

    def run_all_tests(self, scraper_names: list[str] | None = None) -> dict[str, ScraperTestResult]:
        """Run granular field tests for all or specified scrapers."""
        print("\n" + "=" * 80)
        print("🔬 GRANULAR SCRAPER FIELD TESTS")
        print("=" * 80)
        print("Testing individual fields for each scraper to identify specific failures...")
        print("=" * 80)

        modules = self.discover_scrapers()
        results = {}

        # Filter to specified scrapers if provided
        if scraper_names:
            modules = {name: module for name, module in modules.items() if name in scraper_names}

        for scraper_name, module in modules.items():
            result = self.test_scraper(scraper_name, module)
            results[scraper_name] = result

        # Print summary
        self.print_summary(results)

        return results

    def print_summary(  # noqa: PLR0912 - Summary requires many conditional branches
        self, results: dict[str, ScraperTestResult]
    ):
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
                    str(field_result.value)[:TRUNCATION_LENGTH] + "..."
                    if field_result.value and len(str(field_result.value)) > TRUNCATION_LENGTH
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
                    f for f, r in result.field_results.items() if r.status != FieldTestStatus.PASS
                ]
                print(f"   • {scraper} (failed: {', '.join(failed_fields)})")

        if error_scrapers:
            print(f"🔥 COMPLETELY BROKEN ({len(error_scrapers)}):")
            for scraper in error_scrapers:
                print(f"   • {scraper}")

        total_scrapers = len(results)
        success_rate = len(passed_scrapers) / total_scrapers * 100 if total_scrapers > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")


def run_granular_tests(scraper_names: list[str] | None = None):
    """Convenience function to run granular scraper tests."""
    tester = GranularScraperTester()
    return tester.run_all_tests(scraper_names)


if __name__ == "__main__":
    # Run tests for all scrapers
    results = run_granular_tests()
