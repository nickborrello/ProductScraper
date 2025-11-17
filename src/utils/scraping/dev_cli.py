#!/usr/bin/env python3
"""
Scraper Development CLI Tool

Enhanced command-line interface for scraper development and debugging.
Integrates with existing testing framework and provides new debugging capabilities.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.scraping.dev_tools import (
    SelectorDebugger,
    MockServer,
    ScraperDevGUI,
    ScraperTestSuite,
    create_mock_html_template,
    quick_selector_test
)


class ScraperDevCLI:
    """Command-line interface for scraper development tools."""

    def __init__(self):
        self.debugger = SelectorDebugger()
        self.mock_server = MockServer()
        self.test_suite = ScraperTestSuite()

    def run_existing_tests(self, scraper_name: Optional[str] = None, verbose: bool = False):
        """Run existing scraper tests."""
        cmd = [sys.executable, "tests/unit/test_scrapers.py"]

        if scraper_name:
            cmd.extend(["--scraper", scraper_name])
        else:
            cmd.append("--all")

        if verbose:
            cmd.append("--verbose")

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode == 0

    def debug_selector(self, url: str, selector: str, selector_type: str = 'css', highlight: bool = False):
        """Debug a selector against a live page."""
        print(f"Testing selector: {selector} ({selector_type})")
        print(f"URL: {url}")

        if highlight:
            self.debugger.headless = False  # Need visible browser for highlighting

        if not self.debugger.load_page(url):
            print("ERROR: Failed to load page")
            return False

        result = self.debugger.test_selector(selector, selector_type)

        print(f"\nResults:")
        print(f"  Found: {'YES' if result.found else 'NO'} ({result.count} elements)")
        print(f"  Text: {result.text[:200]}{'...' if len(result.text) > 200 else ''}")

        if result.html:
            print(f"  HTML: {result.html[:200]}{'...' if len(result.html) > 200 else ''}")

        if highlight and result.found:
            print("Highlighting elements in browser...")
            self.debugger.highlight_element(selector, selector_type)
            input("Press Enter to continue...")

        return result.success

    def create_test_suite(self, scraper_name: str, url: str):
        """Create a test suite for a scraper."""
        test_file = PROJECT_ROOT / "tests" / "fixtures" / f"{scraper_name}_selectors.json"

        print(f"Creating test suite for {scraper_name}")
        print(f"Test file: {test_file}")

        # Common selectors to test
        common_tests = [
            {
                "name": "Page Title",
                "selector": "title",
                "selector_type": "css",
                "description": "Page title element"
            },
            {
                "name": "Product Title",
                "selector": "h1, .product-title, #productTitle",
                "selector_type": "css",
                "description": "Main product title"
            },
            {
                "name": "Price",
                "selector": ".price, .product-price, [data-price]",
                "selector_type": "css",
                "description": "Product price"
            },
            {
                "name": "Images",
                "selector": "img",
                "selector_type": "css",
                "description": "Product images"
            }
        ]

        # Test selectors against the URL
        print(f"Testing selectors against: {url}")
        if self.debugger.load_page(url):
            for test in common_tests:
                result = self.debugger.test_selector(test["selector"], test["selector_type"])
                test["expected_count"] = str(result.count if result.found else 0)
                test["expected_text"] = result.text[:50] if result.found else ""

        # Save test suite
        data = {
            "scraper_name": scraper_name,
            "test_url": url,
            "test_cases": common_tests
        }

        test_file.parent.mkdir(exist_ok=True)
        with open(test_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"SUCCESS: Test suite created with {len(common_tests)} tests")
        return str(test_file)

    def run_test_suite(self, test_file: str):
        """Run a test suite."""
        if not os.path.exists(test_file):
            print(f"ERROR: Test file not found: {test_file}")
            return False

        print(f"Running test suite: {test_file}")

        self.test_suite.load_test_cases_from_file(test_file)

        # Get test URL from file
        with open(test_file, 'r') as f:
            data = json.load(f)
            test_url = data.get("test_url")

        if not test_url:
            print("ERROR: No test URL found in test file")
            return False

        results = self.test_suite.run_tests(test_url)

        print(f"\nTest Results:")
        print(f"  Total: {results['total_tests']}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Success Rate: {results['success_rate']:.1f}%")

        if results['failed'] > 0:
            print(f"\nFailed Tests:")
            for result in results['results']:
                if not result['success']:
                    print(f"  • {result['test_name']}: expected {result['expected_count']} elements, got {result['actual_count']}")

        return results['failed'] == 0

    def start_mock_server(self, port: int = 5000):
        """Start mock server for testing."""
        self.mock_server.port = port

        # Add some default mock pages
        self.mock_server.add_mock_page("amazon-product", create_mock_html_template(
            "Test Amazon Product", "$19.99"
        ))
        self.mock_server.add_mock_page("pet-product", create_mock_html_template(
            "Premium Dog Food", "$49.99"
        ))

        self.mock_server.start()
        print(f"Mock server running on http://127.0.0.1:{port}")
        print("Available pages:")
        for path in self.mock_server.mock_pages.keys():
            print(f"  • http://127.0.0.1:{port}/mock/{path}")

        return True

    def start_dev_gui(self, port: int = 8080):
        """Start the development GUI."""
        gui = ScraperDevGUI(port=port)
        gui.start()
        return gui

    def compare_scrapers(self, scraper1: str, scraper2: str, url: str):
        """Compare two scrapers against the same URL."""
        print(f"Comparing {scraper1} vs {scraper2} on {url}")

        # This would integrate with their existing scraper testing
        # For now, just run both tests
        print(f"Testing {scraper1}...")
        success1 = self.run_existing_tests(scraper1, verbose=True)

        print(f"\nTesting {scraper2}...")
        success2 = self.run_existing_tests(scraper2, verbose=True)

        print(f"\nComparison Results:")
        print(f"  {scraper1}: {'PASS' if success1 else 'FAIL'}")
        print(f"  {scraper2}: {'PASS' if success2 else 'FAIL'}")

        return success1 and success2

    def generate_scraper_template(self, scraper_name: str, base_url: str):
        """Generate a basic YAML-based scraper template."""
        scraper_dir = PROJECT_ROOT / "src" / "scrapers" / scraper_name

        print(f"Generating YAML scraper template: {scraper_name}")

        # Create directory structure
        scraper_dir.mkdir(parents=True, exist_ok=True)

        # Generate YAML config
        yaml_content = f'''# {scraper_name} Scraper Configuration
name: "{scraper_name}"
description: "Product scraper for {scraper_name}"
base_url: "{base_url}"

# Browser settings
browser:
  headless: true
  timeout: 30
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Product page detection
product_page_patterns:
  - "{base_url}/product/*"
  - "{base_url}/item/*"
  - "{base_url}/p/*"

# Selectors for product data extraction
selectors:
  name:
    css: "h1.product-title, .product-name, #productTitle"
    xpath: "//h1[@class='product-title'] | //div[@class='product-name'] | //span[@id='productTitle']"
    required: true

  price:
    css: ".price, .product-price, [data-price]"
    xpath: "//span[@class='price'] | //div[@class='product-price'] | //meta[@property='product:price:amount']/@content"
    required: false

  brand:
    css: ".brand, .manufacturer, [data-brand]"
    xpath: "//span[@class='brand'] | //div[@class='manufacturer']"
    required: false

  sku:
    css: "[data-sku], .sku, .product-id"
    xpath: "//span[@class='sku'] | //div[@class='product-id']"
    required: false

  weight:
    css: ".weight, .product-weight, [data-weight]"
    xpath: "//span[@class='weight'] | //div[@class='product-weight']"
    required: false

  images:
    css: ".product-image img, .gallery img, #product-images img"
    xpath: "//div[@class='product-image']//img | //div[@class='gallery']//img"
    attribute: "src"
    multiple: true
    required: false

# Workflow steps for scraping
workflow:
  - name: "load_page"
    type: "navigation"
    description: "Load the product page"

  - name: "extract_data"
    type: "extraction"
    description: "Extract product data using selectors"

  - name: "validate_data"
    type: "validation"
    description: "Validate extracted data"

# Test configuration
test:
  enabled: true
  sample_urls:
    - "{base_url}/product/sample123"
  expected_fields:
    - name
    - sku
'''

        # Write YAML config
        config_file = scraper_dir / f"{scraper_name}.yaml"
        with open(config_file, 'w') as f:
            f.write(yaml_content)

        print("SUCCESS: YAML scraper template generated!")
        print(f"Location: {scraper_dir}")
        print(f"Config file: {config_file}")
        print("Next steps:")
        print("  1. Customize the selectors in the YAML config")
        print("  2. Test with: python src/utils/scraping/dev_cli.py debug-selector <url> <selector>")
        print("  3. Run tests: python platform_test_scrapers.py --scraper {scraper_name}")

        return str(scraper_dir)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scraper Development CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test existing scrapers
  python dev_cli.py test --scraper amazon
  python dev_cli.py test --all

  # Debug selectors
  python dev_cli.py debug-selector "https://amazon.com/dp/B07G5J5FYP" "h1#productTitle"
  python dev_cli.py debug-selector "https://amazon.com/dp/B07G5J5FYP" "//h1[@id='productTitle']" --type xpath --highlight

  # Create test suite
  python dev_cli.py create-suite amazon "https://amazon.com/dp/B07G5J5FYP"

  # Run test suite
  python dev_cli.py run-suite tests/fixtures/amazon_selectors.json

  # Start development tools
  python dev_cli.py gui          # Start web GUI
  python dev_cli.py mock-server  # Start mock server

  # Generate scraper template
  python dev_cli.py generate-scraper newstore "https://newstore.com"

  # Compare scrapers
  python dev_cli.py compare amazon bradley "https://example.com/product/123"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Test command
    test_parser = subparsers.add_parser('test', help='Run existing scraper tests')
    test_parser.add_argument('--scraper', help='Specific scraper to test')
    test_parser.add_argument('--all', action='store_true', help='Test all scrapers')
    test_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # Debug selector command
    debug_parser = subparsers.add_parser('debug-selector', help='Debug a CSS/XPath selector')
    debug_parser.add_argument('url', help='URL to test against')
    debug_parser.add_argument('selector', help='CSS or XPath selector')
    debug_parser.add_argument('--type', choices=['css', 'xpath'], default='css', help='Selector type')
    debug_parser.add_argument('--highlight', action='store_true', help='Highlight elements in browser')

    # Create test suite command
    suite_parser = subparsers.add_parser('create-suite', help='Create a selector test suite')
    suite_parser.add_argument('scraper_name', help='Name of the scraper')
    suite_parser.add_argument('url', help='URL to test selectors against')

    # Run test suite command
    run_suite_parser = subparsers.add_parser('run-suite', help='Run a selector test suite')
    run_suite_parser.add_argument('test_file', help='Path to test suite JSON file')

    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Start development GUI')
    gui_parser.add_argument('--port', type=int, default=8080, help='Port for GUI server')

    # Mock server command
    mock_parser = subparsers.add_parser('mock-server', help='Start mock server')
    mock_parser.add_argument('--port', type=int, default=5000, help='Port for mock server')

    # Generate scraper command
    gen_parser = subparsers.add_parser('generate-scraper', help='Generate scraper template')
    gen_parser.add_argument('scraper_name', help='Name of the new scraper')
    gen_parser.add_argument('base_url', help='Base URL for the scraper')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two scrapers')
    compare_parser.add_argument('scraper1', help='First scraper name')
    compare_parser.add_argument('scraper2', help='Second scraper name')
    compare_parser.add_argument('url', help='URL to test against')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cli = ScraperDevCLI()

    try:
        if args.command == 'test':
            if args.all or not args.scraper:
                success = cli.run_existing_tests(verbose=args.verbose)
            else:
                success = cli.run_existing_tests(args.scraper, args.verbose)
            return 0 if success else 1

        elif args.command == 'debug-selector':
            success = cli.debug_selector(args.url, args.selector, args.type, args.highlight)
            return 0 if success else 1

        elif args.command == 'create-suite':
            test_file = cli.create_test_suite(args.scraper_name, args.url)
            print(f"SUCCESS: Test suite created: {test_file}")
            return 0

        elif args.command == 'run-suite':
            success = cli.run_test_suite(args.test_file)
            return 0 if success else 1

        elif args.command == 'gui':
            gui = cli.start_dev_gui(args.port)
            input("Press Enter to stop GUI...")
            gui.stop()
            return 0

        elif args.command == 'mock-server':
            cli.start_mock_server(args.port)
            input("Press Enter to stop mock server...")
            cli.mock_server.stop()
            return 0

        elif args.command == 'generate-scraper':
            path = cli.generate_scraper_template(args.scraper_name, args.base_url)
            print(f"SUCCESS: Scraper template generated at: {path}")
            return 0

        elif args.command == 'compare':
            success = cli.compare_scrapers(args.scraper1, args.scraper2, args.url)
            return 0 if success else 1

    except KeyboardInterrupt:
        print("\nINTERRUPTED: Stopped by user")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        cli.debugger.close()


if __name__ == "__main__":
    sys.exit(main())