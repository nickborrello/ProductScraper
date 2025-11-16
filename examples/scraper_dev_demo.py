#!/usr/bin/env python3
"""
Scraper Development Tools Demo

This script demonstrates the key features of the scraper development tools.
Run this to see how the tools work together.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.scraping.dev_tools import (
    SelectorDebugger,
    MockServer,
    ScraperTestSuite,
    create_mock_html_template,
    quick_selector_test
)


def demo_selector_debugging():
    """Demonstrate selector debugging capabilities."""
    print("🔍 Selector Debugging Demo")
    print("=" * 40)

    # Create a mock page for testing
    mock_html = create_mock_html_template("Demo Product", "$29.99")
    mock_html += """
    <div class="product-info">
        <h2>Additional Product Info</h2>
        <span class="sku">SKU: DEMO123</span>
        <div class="specs">
            <strong>Weight:</strong> 5 lbs<br>
            <strong>Brand:</strong> Demo Brand
        </div>
    </div>
    """

    server = MockServer()
    server.add_mock_page("demo", mock_html)
    server.start()

    try:
        # Test selectors against mock page
        base_url = "http://127.0.0.1:5000/mock/demo"

        test_cases = [
            ("h1", "Product title"),
            (".price", "Product price"),
            ("img", "Product images"),
            (".sku", "SKU information"),
            ("h2", "Section headers"),
        ]

        print(f"Testing selectors against: {base_url}")
        print()

        for selector, description in test_cases:
            result = quick_selector_test(base_url, selector)
            status = "✅" if result.found else "❌"
            print(f"{status} {selector:<10} ({result.count} found) - {description}")
            if result.found and result.text:
                print(f"    Text: {result.text[:50]}...")

        print()

    finally:
        server.stop()


def demo_test_suite():
    """Demonstrate test suite functionality."""
    print("🧪 Test Suite Demo")
    print("=" * 40)

    # Create test suite
    suite = ScraperTestSuite()

    # Add test cases
    from src.utils.scraping.dev_tools import SelectorTest

    test_cases = [
        SelectorTest("Title", "h1", "css", 1, description="Main product title"),
        SelectorTest("Price", ".price", "css", 1, description="Product price"),
        SelectorTest("Images", "img", "css", expected_count=1, description="Product images"),
    ]

    for test in test_cases:
        suite.add_test_case(test)

    # Create mock page
    mock_html = create_mock_html_template("Suite Test Product", "$39.99")
    server = MockServer()
    server.add_mock_page("suite-test", mock_html)
    server.start()

    try:
        # Run test suite
        test_url = "http://127.0.0.1:5000/mock/suite-test"
        results = suite.run_tests(test_url)

        print(f"Test Results for: {test_url}")
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")

        if results['failed'] > 0:
            print("\nFailed Tests:")
            for result in results['results']:
                if not result['success']:
                    print(f"  ❌ {result['test_name']}: expected {result['expected_count']}, got {result['actual_count']}")

        print()

    finally:
        server.stop()


def demo_cli_tools():
    """Show how to use the CLI tools."""
    print("💻 CLI Tools Demo")
    print("=" * 40)

    print("Available CLI commands:")
    print("  python src/utils/scraping/dev_cli.py test --all")
    print("  python src/utils/scraping/dev_cli.py gui")
    print("  python src/utils/scraping/dev_cli.py mock-server")
    print("  python src/utils/scraping/dev_cli.py debug-selector <url> <selector>")
    print("  python src/utils/scraping/dev_cli.py create-suite <name> <url>")
    print("  python src/utils/scraping/dev_cli.py generate-scraper <name> <base_url>")
    print()

    print("Example usage:")
    print("  # Test all scrapers")
    print("  python src/utils/scraping/dev_cli.py test --all")
    print()
    print("  # Debug a selector")
    print("  python src/utils/scraping/dev_cli.py debug-selector \\")
    print("    'https://amazon.com/dp/B07G5J5FYP' 'h1#productTitle'")
    print()
    print("  # Start development GUI")
    print("  python src/utils/scraping/dev_cli.py gui")
    print()


def main():
    """Run all demos."""
    print("🕷️ Scraper Development Tools Demo")
    print("=" * 50)
    print()

    try:
        demo_selector_debugging()
        demo_test_suite()
        demo_cli_tools()

        print("✅ Demo completed successfully!")
        print()
        print("Next steps:")
        print("1. Try the web GUI: python src/utils/scraping/dev_cli.py gui")
        print("2. Start mock server: python src/utils/scraping/dev_cli.py mock-server")
        print("3. Test selectors: python src/utils/scraping/dev_cli.py debug-selector <url> <selector>")
        print("4. Read full docs: docs/SCRAPER_DEV_TOOLS.md")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())