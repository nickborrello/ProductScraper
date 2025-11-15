#!/usr/bin/env python3
"""
Command-line tool for platform and local testing of scrapers.

This script provides an easy way to:
- Test individual scrapers with validation in local or platform mode
- Run all scrapers and get a comprehensive report
- Debug scraper output and identify issues
- Validate data format and quality before deployment

Usage:
    python platform_test_scrapers.py --all                    # Test all scrapers (local mode)
    python platform_test_scrapers.py --scraper amazon         # Test specific scraper (local mode)
    python platform_test_scrapers.py --scraper amazon --platform  # Test on platform
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
from src.core.platform_testing_client import TestingMode
from tests.fixtures.scraper_validator import ScraperValidator


def list_available_scrapers():
    """List all available scrapers."""
    tester = PlatformScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    print("Available Scrapers:")
    print("=" * 40)

    for scraper in scrapers:
        print(f"📦 {scraper}")
        print()

    return scrapers


def validate_scraper_structure(scraper_name: str):
    """Validate that a scraper has the correct structure."""
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / scraper_name

    print(f"Validating structure for: {scraper_name}")
    print("=" * 50)

    checks = {
        "Scraper directory exists": scraper_dir.exists(),
        "src/ directory exists": (scraper_dir / "src").exists(),
        "__main__.py exists": (scraper_dir / "src" / "__main__.py").exists(),
        "main.py exists": (scraper_dir / "src" / "main.py").exists(),
        ".actor/ directory exists": (scraper_dir / ".actor").exists(),
        "actor.json exists": (scraper_dir / ".actor" / "actor.json").exists(),
        "input_schema.json exists": (scraper_dir / ".actor" / "input_schema.json").exists(),
        "output_schema.json exists": (scraper_dir / ".actor" / "output_schema.json").exists(),
        "dataset_schema.json exists": (scraper_dir / ".actor" / "dataset_schema.json").exists(),
        "requirements.txt exists": (scraper_dir / "requirements.txt").exists(),
        "Dockerfile exists": (scraper_dir / "Dockerfile").exists(),
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ Scraper structure is valid!")
    else:
        print("❌ Scraper structure has issues. Check the failed items above.")

    return all_passed


async def test_single_scraper(scraper_name: str, skus: Optional[List[str]] = None, mode: TestingMode = TestingMode.LOCAL, verbose: bool = False):
    """Test a single scraper."""
    tester = PlatformScraperIntegrationTester(mode=mode)

    # First validate structure
    if not validate_scraper_structure(scraper_name):
        print(f"\n❌ Skipping execution test due to structure issues")
        return False

    print(f"\n{'='*60}")
    print(f"EXECUTING SCRAPER TEST: {scraper_name.upper()} ({mode.value.upper()} MODE)")
    print(f"{'='*60}")

    try:
        result = await tester.run_scraper_test(scraper_name, skus)

        if verbose and result["run_results"]["products"]:
            print(f"\n📄 SCRAPER OUTPUT:")
            print("-" * 40)
            # Show first few products
            for i, product in enumerate(result["run_results"]["products"][:3]):
                print(f"Product {i+1}: {json.dumps(product, indent=2)[:500]}...")
                if i < len(result["run_results"]["products"]) - 1:
                    print("---")
            if len(result["run_results"]["products"]) > 3:
                print(f"... and {len(result['run_results']['products']) - 3} more products")
            print("-" * 40)

        return result["overall_success"]

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


async def test_all_scrapers(mode: TestingMode = TestingMode.LOCAL, verbose: bool = False):
    """Test all available scrapers."""
    tester = PlatformScraperIntegrationTester(mode=mode)
    scrapers = tester.get_available_scrapers()

    print(f"🧪 RUNNING {mode.value.upper()} COMPREHENSIVE SCRAPER TESTS")
    print(f"Testing {len(scrapers)} scrapers: {', '.join(scrapers)}")
    print(f"{'='*80}")

    results = await tester.run_all_scrapers_test(skip_failing=True)

    if verbose:
        print(f"\n📊 DETAILED RESULTS:")
        print("-" * 50)
        for scraper_name, result in results["scraper_results"].items():
            status = "✅" if result.get("overall_success", False) else "❌"
            products = len(result.get("run_results", {}).get("products", []))
            print(f"{status} {scraper_name}: {products} products")

    print(f"\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}")
    print(f"Total Scrapers Tested: {results['total_scrapers']}")
    print(f"Passed: {results['successful_scrapers']}")
    print(f"Failed: {results['failed_scrapers']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Testing Mode: {mode.value.upper()}")

    if results["failed_scrapers"] > 0:
        print(f"\n❌ FAILED SCRAPERS:")
        for name in results["summary"]["failed_scrapers_list"]:
            print(f"  • {name}")

        print(f"\n🔧 COMMON ISSUES:")
        common_errors = results["summary"]["common_errors"]
        for error, count in sorted(common_errors.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {error} ({count} times)")

    if results["successful_scrapers"] > 0:
        print(f"Average Quality Score: {results['summary']['average_quality_score']:.1f}")

    success = results["failed_scrapers"] == 0
    if success:
        print(f"\n🎉 ALL SCRAPERS PASSED {mode.value.upper()} TESTS! Ready for deployment.")
    else:
        print(f"\n⚠️  SOME SCRAPERS FAILED {mode.value.upper()} TESTS. Fix issues before deploying.")

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
  python platform_test_scrapers.py --scraper amazon --platform  # Test amazon on platform
  python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
  python platform_test_scrapers.py --list                   # List available scrapers
  python platform_test_scrapers.py --validate amazon        # Validate structure only
        """
    )

    parser.add_argument("--all", action="store_true",
                       help="Test all available scrapers")
    parser.add_argument("--scraper", type=str,
                       help="Test specific scraper by name")
    parser.add_argument("--skus", nargs="+",
                       help="Custom SKUs to test with (space-separated)")
    parser.add_argument("--platform", action="store_true",
                       help="Run tests on Apify platform (requires API token)")
    parser.add_argument("--list", action="store_true",
                       help="List all available scrapers")
    parser.add_argument("--validate", type=str,
                       help="Validate scraper structure without running")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output and debug information")

    args = parser.parse_args()

    # Determine testing mode
    mode = TestingMode.PLATFORM if args.platform else TestingMode.LOCAL

    if mode == TestingMode.PLATFORM:
        # Check if API token is configured
        from src.core.settings_manager import settings
        if not settings.get("apify_api_token"):
            print("❌ ERROR: Apify API token not configured. Please set 'apify_api_token' in settings.")
            print("   You can configure it in settings.json or environment variable APIFY_API_TOKEN")
            return 1

    # Handle different modes
    if args.list:
        list_available_scrapers()
        return 0

    if args.validate:
        success = validate_scraper_structure(args.validate)
        return 0 if success else 1

    if args.scraper:
        success = await test_single_scraper(args.scraper, args.skus, mode, args.verbose)
        return 0 if success else 1

    if args.all:
        success = await test_all_scrapers(mode, args.verbose)
        return 0 if success else 1

    # No arguments provided
    show_help()
    return 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))