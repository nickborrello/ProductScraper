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
        print(f"🔍 Testing selector: {selector} ({selector_type})")
        print(f"📄 URL: {url}")

        if highlight:
            self.debugger.headless = False  # Need visible browser for highlighting

        if not self.debugger.load_page(url):
            print("❌ Failed to load page")
            return False

        result = self.debugger.test_selector(selector, selector_type)

        print(f"\n📊 Results:")
        print(f"  Found: {'✅' if result.found else '❌'} ({result.count} elements)")
        print(f"  Text: {result.text[:200]}{'...' if len(result.text) > 200 else ''}")

        if result.html:
            print(f"  HTML: {result.html[:200]}{'...' if len(result.html) > 200 else ''}")

        if highlight and result.found:
            print("🎨 Highlighting elements in browser...")
            self.debugger.highlight_element(selector, selector_type)
            input("Press Enter to continue...")

        return result.success

    def create_test_suite(self, scraper_name: str, url: str):
        """Create a test suite for a scraper."""
        test_file = PROJECT_ROOT / "tests" / "fixtures" / f"{scraper_name}_selectors.json"

        print(f"🧪 Creating test suite for {scraper_name}")
        print(f"📄 Test file: {test_file}")

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
                test["expected_count"] = result.count if result.found else 0
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

        print(f"✅ Test suite created with {len(common_tests)} tests")
        return str(test_file)

    def run_test_suite(self, test_file: str):
        """Run a test suite."""
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return False

        print(f"🧪 Running test suite: {test_file}")

        self.test_suite.load_test_cases_from_file(test_file)

        # Get test URL from file
        with open(test_file, 'r') as f:
            data = json.load(f)
            test_url = data.get("test_url")

        if not test_url:
            print("❌ No test URL found in test file")
            return False

        results = self.test_suite.run_tests(test_url)

        print(f"\n📊 Test Results:")
        print(f"  Total: {results['total_tests']}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Success Rate: {results['success_rate']:.1f}%")

        if results['failed'] > 0:
            print(f"\n❌ Failed Tests:")
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
        print(f"🌐 Mock server running on http://127.0.0.1:{port}")
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
        print(f"🔄 Comparing {scraper1} vs {scraper2} on {url}")

        # This would integrate with their existing scraper testing
        # For now, just run both tests
        print(f"Testing {scraper1}...")
        success1 = self.run_existing_tests(scraper1, verbose=True)

        print(f"\nTesting {scraper2}...")
        success2 = self.run_existing_tests(scraper2, verbose=True)

        print(f"\n📊 Comparison Results:")
        print(f"  {scraper1}: {'✅' if success1 else '❌'}")
        print(f"  {scraper2}: {'✅' if success2 else '❌'}")

        return success1 and success2

    def generate_scraper_template(self, scraper_name: str, base_url: str):
        """Generate a basic scraper template."""
        scraper_dir = PROJECT_ROOT / "src" / "scrapers" / scraper_name
        src_dir = scraper_dir / "src"

        print(f"🛠️ Generating scraper template: {scraper_name}")

        # Create directory structure
        src_dir.mkdir(parents=True, exist_ok=True)
        (scraper_dir / ".actor").mkdir(exist_ok=True)

        # Generate main.py
        main_py_content = f'''"""{{scraper_name}} Product Scraper Actor"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Import Actor
try:
    if os.getenv('APIFY_ACTOR_ID') or os.getenv('APIFY_TOKEN'):
        from apify import Actor
    else:
        from src.core.local_apify import Actor
except ImportError:
    from apify import Actor

from src.utils.scraping.dev_tools import SelectorDebugger

# {scraper_name} scraper configuration
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'


def scrape_product(url: str) -> dict[str, Any] | None:
    """Scrape a single product from {scraper_name}."""
    debugger = SelectorDebugger(headless=HEADLESS)

    try:
        if not debugger.load_page(url):
            return None

        # TODO: Implement scraping logic
        # Use debugger.test_selector() to test selectors during development

        product_data = {{
            "SKU": "",  # Extract from URL or page
            "Name": "",  # Extract product name
            "Price": "",  # Extract price
            "Brand": "",  # Extract brand
            "Image URLs": [],  # Extract image URLs
            "Weight": "",  # Extract weight
        }}

        return product_data

    finally:
        debugger.close()


async def main() -> None:
    """Main actor function."""
    async with Actor:
        actor_input = await Actor.get_input() or {{}}
        skus = actor_input.get('skus', [])

        if not skus:
            Actor.log.error("No SKUs provided")
            return

        Actor.log.info(f"Starting {{scraper_name}} scraping for {{len(skus)}} SKUs")

        products = []
        for sku in skus:
            # Convert SKU to URL - customize this logic
            url = f"{base_url}/product/{{sku}}"

            product = scrape_product(url)
            if product:
                products.append(product)
                Actor.log.info(f"✅ Scraped: {{product.get('Name', 'Unknown')}}")
            else:
                Actor.log.warning(f"❌ Failed to scrape SKU: {{sku}}")

        await Actor.push_data(products)
        Actor.log.info(f"Successfully scraped {{len(products)}} products")


if __name__ == "__main__":
    asyncio.run(main())
'''

        # Generate Dockerfile
        dockerfile_content = f'''FROM apify/actor-python:3.11

# Copy source code
COPY src/ ./src/

# Install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Set environment
ENV PYTHONPATH=/home/myuser/src:$PYTHONPATH

# Run the scraper
CMD ["python", "src/main.py"]
'''

        # Generate requirements.txt
        requirements_content = '''apify==1.8.1
selenium==4.15.2
webdriver-manager==4.0.1
fake-useragent==1.4.0
beautifulsoup4==4.12.2
lxml==4.9.3
'''

        # Generate actor.json
        actor_json = {
            "name": f"{scraper_name}-scraper",
            "version": "0.1.0",
            "description": f"Product scraper for {scraper_name}",
            "dockerfile": "./Dockerfile",
            "input": {
                "type": "object",
                "properties": {
                    "skus": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of SKUs to scrape"
                    }
                },
                "required": ["skus"]
            }
        }

        # Write files
        (src_dir / "main.py").write_text(main_py_content)
        (scraper_dir / "Dockerfile").write_text(dockerfile_content)
        (scraper_dir / "requirements.txt").write_text(requirements_content)

        with open(scraper_dir / ".actor" / "actor.json", 'w') as f:
            json.dump(actor_json, f, indent=2)

        print("✅ Scraper template generated!")
        print(f"📁 Location: {scraper_dir}")
        print("📝 Next steps:")
        print("  1. Customize the scraping logic in src/main.py")
        print("  2. Test with: python src/utils/scraping/dev_cli.py debug-selector <url> <selector>")
        print("  3. Run tests: python tests/unit/test_scrapers.py --scraper {scraper_name}")

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
            print(f"✅ Test suite created: {test_file}")
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
            print(f"✅ Scraper template generated at: {path}")
            return 0

        elif args.command == 'compare':
            success = cli.compare_scrapers(args.scraper1, args.scraper2, args.url)
            return 0 if success else 1

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        cli.debugger.close()


if __name__ == "__main__":
    sys.exit(main())