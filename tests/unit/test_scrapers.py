#!/usr/bin/env python3
"""
Command-line tool for testing and debugging scrapers locally.

This script provides an easy way to:
- Test individual scrapers with validation
- Run all scrapers and get a comprehensive report
- Debug scraper output and identify issues
- Validate data format and quality before deployment

Usage:
    python test_scrapers.py --all                    # Test all scrapers
    python test_scrapers.py --scraper amazon         # Test specific scraper
    python test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW  # Test with custom SKUs
    python test_scrapers.py --list                   # List available scrapers
    python test_scrapers.py --validate amazon        # Validate scraper structure only
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.integration.test_scraper_integration import ScraperIntegrationTester
from tests.fixtures.scraper_validator import ScraperValidator


def list_available_scrapers():
    """List all available scrapers."""
    tester = ScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    print("Available Scrapers:")
    print("=" * 40)

    for scraper in scrapers:
        config = tester.test_config.get(scraper, {})
        test_skus = config.get("test_skus", [])
        description = config.get("description", "No description")

        print(f"📦 {scraper}")
        print(f"   Description: {description}")
        print(f"   Test SKUs: {', '.join(test_skus) if test_skus else 'None'}")
        print()


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


def test_single_scraper(scraper_name: str, skus: Optional[List[str]] = None, verbose: bool = False):
    """Test a single scraper."""
    tester = ScraperIntegrationTester()

    # First validate structure
    if not validate_scraper_structure(scraper_name):
        print(f"\n❌ Skipping execution test due to structure issues")
        return False

    print(f"\n{'='*60}")
    print(f"EXECUTING SCRAPER TEST: {scraper_name.upper()}")
    print(f"{'='*60}")

    try:
        result = tester.test_single_scraper(scraper_name, skus)

        if verbose and result["run_results"]["output"]:
            print(f"\n📄 SCRAPER OUTPUT:")
            print("-" * 40)
            print(result["run_results"]["output"][:2000])  # Limit output
            if len(result["run_results"]["output"]) > 2000:
                print("... (output truncated)")
            print("-" * 40)

        return result["overall_success"]

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


def test_all_scrapers(verbose: bool = False):
    """Test all available scrapers."""
    tester = ScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    print(f"🧪 RUNNING COMPREHENSIVE SCRAPER TESTS")
    print(f"Testing {len(scrapers)} scrapers: {', '.join(scrapers)}")
    print(f"{'='*80}")

    results = tester.test_all_scrapers(skip_failing=True)

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
    print(".1f")

    if results["failed_scrapers"] > 0:
        print(f"\n❌ FAILED SCRAPERS:")
        for name in results["summary"]["failed_scrapers_list"]:
            print(f"  • {name}")

        print(f"\n🔧 COMMON ISSUES:")
        common_errors = results["summary"]["common_errors"]
        for error, count in sorted(common_errors.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {error} ({count} times)")

    if results["successful_scrapers"] > 0:
        print(".1f")

    success = results["failed_scrapers"] == 0
    if success:
        print(f"\n🎉 ALL SCRAPERS PASSED! Ready for deployment to Apify.")
    else:
        print(f"\n⚠️  SOME SCRAPERS FAILED. Fix issues before deploying to Apify.")

    return success


def show_help():
    """Show help information."""
    print(__doc__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test and debug ProductScraper scrapers locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_scrapers.py --all                    # Test all scrapers
  python test_scrapers.py --scraper amazon         # Test amazon scraper
  python test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
  python test_scrapers.py --list                   # List available scrapers
  python test_scrapers.py --validate amazon        # Validate structure only
        """
    )

    parser.add_argument("--all", action="store_true",
                       help="Test all available scrapers")
    parser.add_argument("--scraper", type=str,
                       help="Test specific scraper by name")
    parser.add_argument("--skus", nargs="+",
                       help="Custom SKUs to test with (space-separated)")
    parser.add_argument("--list", action="store_true",
                       help="List all available scrapers")
    parser.add_argument("--validate", type=str,
                       help="Validate scraper structure without running")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output and debug information")

    args = parser.parse_args()

    # Handle different modes
    if args.list:
        list_available_scrapers()
        return 0

    if args.validate:
        success = validate_scraper_structure(args.validate)
        return 0 if success else 1

    if args.scraper:
        success = test_single_scraper(args.scraper, args.skus, args.verbose)
        return 0 if success else 1

    if args.all:
        success = test_all_scrapers(args.verbose)
        return 0 if success else 1

    # No arguments provided
    show_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
