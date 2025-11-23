#!/usr/bin/env python3
"""
CLI test runner script for scraper tests.

This script provides easy command-line access to run scraper tests using pytest.
Supports running tests for individual scrapers, all scrapers, with various options
for headless mode, verbosity, coverage, and timeout.

Usage:
    python scripts/run_scraper_tests.py --scraper amazon
    python scripts/run_scraper_tests.py --all --verbose --coverage
    python scripts/run_scraper_tests.py --list
"""

import argparse
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_scrapers_e2e import ScraperIntegrationTester


def main():
    """Main function to run the CLI test runner."""
    parser = argparse.ArgumentParser(
        description="CLI test runner for scraper tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_scraper_tests.py --scraper amazon
  python scripts/run_scraper_tests.py --all --verbose --coverage
  python scripts/run_scraper_tests.py --list
  python scripts/run_scraper_tests.py --scraper amazon --no-headless --timeout 600
        """,
    )

    parser.add_argument(
        "--scraper", help="Run tests for specific scraper (e.g., amazon, central_pet)"
    )
    parser.add_argument("--all", action="store_true", help="Run tests for all available scrapers")
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode (default in CI)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in non-headless mode (default locally)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument(
        "--timeout", type=int, default=300, help="Test timeout in seconds (default: 300)"
    )
    parser.add_argument("--list", action="store_true", help="List available scrapers and exit")
    parser.add_argument(
        "--no-results", action="store_true", help="Run the 'no results' test for the scraper(s)"
    )

    args = parser.parse_args()

    # Handle --list option
    if args.list:
        try:
            tester = ScraperIntegrationTester()
            scrapers = tester.get_available_scrapers()
            print("Available scrapers:")
            for scraper in sorted(scrapers):
                print(f"  - {scraper}")
            return 0
        except Exception as e:
            print(f"Error listing scrapers: {e}", file=sys.stderr)
            return 1

    # Validate arguments
    if args.scraper and args.all:
        print("Error: Cannot specify both --scraper and --all", file=sys.stderr)
        return 1

    if not args.scraper and not args.all:
        parser.print_help()
        print("\nError: Must specify --scraper <name> or --all", file=sys.stderr)
        return 1

    # Determine headless mode
    if args.headless and args.no_headless:
        print("Error: Cannot specify both --headless and --no-headless", file=sys.stderr)
        return 1
    elif args.headless:
        headless = True
    elif args.no_headless:
        headless = False
    else:
        # Default: headless in CI, non-headless locally
        headless = os.getenv("CI") is not None

    # Set environment variable for tests
    os.environ["SCRAPER_HEADLESS"] = str(headless).lower()

    # Build pytest arguments
    pytest_args: list[str] = [
        "tests/e2e/test_scrapers_e2e.py",
        "--tb=short",
    ]

    if args.verbose:
        pytest_args.append("-v")

    if args.coverage:
        pytest_args.extend(["--cov=src", "--cov-report=term-missing"])

    # Determine which test to run
    test_name = (
        "test_scraper_no_results_parametrized"
        if args.no_results
        else "test_scraper_execution_parametrized"
    )

    if args.scraper:
        # Validate scraper exists
        try:
            tester = ScraperIntegrationTester()
            available_scrapers = tester.get_available_scrapers()
            if args.scraper not in available_scrapers:
                print(
                    f"Error: Scraper '{args.scraper}' not found. Available scrapers: {', '.join(sorted(available_scrapers))}",
                    file=sys.stderr,
                )
                return 1
        except Exception as e:
            print(f"Error validating scraper: {e}", file=sys.stderr)
            return 1

        # Run specific scraper tests
        pytest_args.extend(["-k", f"{test_name} and {args.scraper}"])

    elif args.all:
        # Run all integration tests for the chosen test type
        pytest_args.extend(["-k", f"{test_name}"])

    # Print execution info
    print(f"Running scraper tests with headless={headless}")
    if args.scraper:
        print(f"Target scraper: {args.scraper}")
    if args.no_results:
        print("Test mode: No Results")
    print(f"Pytest command: {' '.join(pytest_args)}")
    print()

    # Run pytest
    try:
        exit_code = pytest.main(pytest_args)
        return exit_code
    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
