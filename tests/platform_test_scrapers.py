#!/usr/bin/env python3
"""
Command-line tool for local testing of scrapers.

This script provides an easy way to:
- Test individual scrapers with validation in local mode
- Run all scrapers and get a comprehensive report
- Debug scraper output and identify issues
- Validate data format and quality

Usage:
    python platform_test_scrapers.py --all                    # Test all scrapers (local mode)
    python platform_test_scrapers.py --scraper amazon         # Test specific scraper (local mode)
    python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
    python platform_test_scrapers.py --list                   # List available scrapers
    python platform_test_scrapers.py --validate amazon        # Validate scraper structure only
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.platform_testing_integration import PlatformScraperIntegrationTester
from tests.fixtures.scraper_validator import ScraperValidator


def list_available_scrapers():
    """List all available scrapers."""
    tester = PlatformScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    print("Available Scrapers:")
    print("=" * 40)

    for scraper in scrapers:
        print(f"[SCRAPER] {scraper}")
        print()

    return scrapers


def validate_scraper_structure(scraper_name: str):
    """Validate that a scraper has the correct structure."""
    config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"

    print(f"Validating config for: {scraper_name}")
    print("=" * 50)

    checks = {
        "Scraper YAML config exists": config_path.exists(),
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("[PASS] Scraper config is valid!")
    else:
        print("[FAIL] Scraper config has issues. Check the failed items above.")

    return all_passed


async def test_single_scraper(
    scraper_name: str, skus: Optional[List[str]] = None, verbose: bool = False
):
    """Test a single scraper."""
    tester = PlatformScraperIntegrationTester()

    # First validate structure
    if not validate_scraper_structure(scraper_name):
        print(f"\n[FAIL] Skipping execution test due to structure issues")
        return False

    print(f"\n{'='*60}")
    print(f"EXECUTING SCRAPER TEST: {scraper_name.upper()} (LOCAL MODE)")
    print(f"{'='*60}")

    try:
        result = await tester.run_scraper_test(scraper_name, skus)

        if verbose and result["run_results"]["products"]:
            print(f"\n[OUTPUT] SCRAPER OUTPUT:")
            print("-" * 40)
            # Show first few products
            for i, product in enumerate(result["run_results"]["products"][:3]):
                print(f"Product {i+1}: {json.dumps(product, indent=2)[:500]}...")
                if i < len(result["run_results"]["products"]) - 1:
                    print("---")
            if len(result["run_results"]["products"]) > 3:
                print(
                    f"... and {len(result['run_results']['products']) - 3} more products"
                )
            print("-" * 40)

        return result["overall_success"]

    except Exception as e:
        print(f"[FAIL] Test failed with exception: {e}")
        return False


async def test_all_scrapers(verbose: bool = False):
    """Test all available scrapers."""
    tester = PlatformScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    print(f"[TEST] RUNNING LOCAL COMPREHENSIVE SCRAPER TESTS")
    print(f"Testing {len(scrapers)} scrapers: {', '.join(scrapers)}")
    print(f"{'='*80}")

    results = await tester.run_all_scrapers_test(skip_failing=True)

    if verbose:
        print(f"\n[RESULTS] DETAILED RESULTS:")
        print("-" * 50)
        for scraper_name, result in results["scraper_results"].items():
            status = "[PASS]" if result.get("overall_success", False) else "[FAIL]"
            products = len(result.get("run_results", {}).get("products", []))
            print(f"{status} {scraper_name}: {products} products")

    print(f"\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}")
    print(f"Total Scrapers Tested: {results['total_scrapers']}")
    print(f"Passed: {results['successful_scrapers']}")
    print(f"Failed: {results['failed_scrapers']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Testing Mode: LOCAL")

    if results["failed_scrapers"] > 0:
        print(f"\n[FAIL] FAILED SCRAPERS:")
        for name in results["summary"]["failed_scrapers_list"]:
            print(f"  • {name}")

        print(f"\n[ISSUES] COMMON ISSUES:")
        common_errors = results["summary"]["common_errors"]
        for error, count in sorted(
            common_errors.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"  • {error} ({count} times)")

    if results["successful_scrapers"] > 0:
        print(
            f"Average Quality Score: {results['summary']['average_quality_score']:.1f}"
        )

    success = results["failed_scrapers"] == 0
    if success:
        print(f"\n[SUCCESS] ALL SCRAPERS PASSED LOCAL TESTS!")
    else:
        print(
            f"\n[WARNING] SOME SCRAPERS FAILED LOCAL TESTS. Fix issues before deploying."
        )

    return success


def show_help():
    """Show help information."""
    print(__doc__)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test and debug ProductScraper scrapers in local or platform mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
   python platform_test_scrapers.py --all                    # Test all scrapers (local)
   python platform_test_scrapers.py --scraper amazon         # Test amazon scraper (local)
   python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
   python platform_test_scrapers.py --list                   # List available scrapers
   python platform_test_scrapers.py --validate amazon        # Validate structure only
         """,
    )

    parser.add_argument(
        "--all", action="store_true", help="Test all available scrapers"
    )
    parser.add_argument("--scraper", type=str, help="Test specific scraper by name")
    parser.add_argument(
        "--skus", nargs="+", help="Custom SKUs to test with (space-separated)"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available scrapers"
    )
    parser.add_argument(
        "--validate", type=str, help="Validate scraper structure without running"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output and debug information",
    )

    args = parser.parse_args()

    # Handle different modes
    if args.list:
        list_available_scrapers()
        return 0

    if args.validate:
        success = validate_scraper_structure(args.validate)
        return 0 if success else 1

    if args.scraper:
        success = await test_single_scraper(args.scraper, args.skus, args.verbose)
        return 0 if success else 1

    if args.all:
        success = await test_all_scrapers(args.verbose)
        return 0 if success else 1

    # No arguments provided
    show_help()
    return 1


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
