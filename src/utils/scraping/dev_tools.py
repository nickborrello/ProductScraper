"""
Scraper Development Tools for Local Testing and Debugging

This module provides utilities to improve the local development workflow for scrapers,
including visual debugging, mock servers, and interactive testing tools.
"""

import os
import sys
import json
import time
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import webbrowser

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from flask import Flask, request, jsonify, render_template_string, send_from_directory
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    import requests
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("WARNING: Flask not available. Install with: pip install flask requests beautifulsoup4")


@dataclass
class SelectorTest:
    """Represents a selector test case."""
    name: str
    selector: str
    selector_type: str  # 'css', 'xpath'
    expected_count: Optional[int] = None
    expected_text: Optional[str] = None
    description: str = ""


@dataclass
class ScraperTestResult:
    """Result of a scraper test."""
    selector_name: str
    found: bool
    count: int
    text: str
    html: str
    success: bool


class SelectorDebugger:
    """Visual debugger for CSS selectors and XPath expressions."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.current_url = None

    def start_driver(self):
        """Start Chrome driver with debugging enabled."""
        if not self.driver:
            options = Options()
            if not self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1200,800")
            options.add_experimental_option("detach", True)  # Keep browser open

            self.driver = webdriver.Chrome(options=options)

    def load_page(self, url: str) -> bool:
        """Load a page and prepare for debugging."""
        try:
            self.start_driver()
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            self.current_url = url
            return True
        except Exception as e:
            print(f"ERROR: Failed to load page {url}: {e}")
            return False

    def test_selector(self, selector: str, selector_type: str = 'css') -> ScraperTestResult:
        """Test a selector and return detailed results."""
        if not self.driver:
            return ScraperTestResult("No Driver", False, 0, "", "", False)

        try:
            if selector_type.lower() == 'css':
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            elif selector_type.lower() == 'xpath':
                elements = self.driver.find_elements(By.XPATH, selector)
            else:
                return ScraperTestResult(selector, False, 0, "Invalid selector type", "", False)

            count = len(elements)
            found = count > 0

            # Get text content
            text = ""
            if elements:
                text = elements[0].text.strip() if elements[0].text else elements[0].get_attribute('textContent') or ""

            # Get HTML
            html = ""
            if elements:
                html = elements[0].get_attribute('outerHTML') or ""

            success = found

            return ScraperTestResult(
                selector,
                found,
                count,
                text,
                html,
                success
            )

        except Exception as e:
            return ScraperTestResult(selector, False, 0, f"Error: {str(e)}", "", False)

    def highlight_element(self, selector: str, selector_type: str = 'css'):
        """Highlight an element in the browser for visual debugging."""
        if not self.driver:
            return

        try:
            script = f"""
            // Remove existing highlights
            document.querySelectorAll('.scraper-debug-highlight').forEach(el => el.remove());

            // Find and highlight elements
            let elements;
            if ('{selector_type}' === 'css') {{
                elements = document.querySelectorAll('{selector}');
            }} else {{
                elements = document.evaluate('{selector}', document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                let result = [];
                for (let i = 0; i < elements.snapshotLength; i++) {{
                    result.push(elements.snapshotItem(i));
                }}
                elements = result;
            }}

            elements.forEach((el, index) => {{
                el.style.outline = '3px solid red';
                el.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                el.setAttribute('data-scraper-highlight', index + 1);

                // Add label
                let label = document.createElement('div');
                label.textContent = `#{index + 1}`;
                label.style.cssText = `
                    position: absolute;
                    background: red;
                    color: white;
                    padding: 2px 4px;
                    font-size: 10px;
                    border-radius: 2px;
                    z-index: 9999;
                `;
                el.style.position = 'relative';
                el.appendChild(label);
            }});

            return elements.length;
            """

            if selector_type.lower() == 'css':
                count = self.driver.execute_script(script.replace('{selector}', selector))
            else:
                count = self.driver.execute_script(script.replace('{selector}', selector))

            print(f"SUCCESS: Highlighted {count} elements with selector: {selector}")

        except Exception as e:
            print(f"ERROR: Failed to highlight elements: {e}")

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None


class MockServer:
    """Mock server for testing scrapers against known HTML content."""

    def __init__(self, port: int = 5000):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask required for MockServer. Install with: pip install flask")

        self.port = port
        self.app = Flask(__name__)
        self.mock_pages: Dict[str, str] = {}
        self.server_thread = None
        self.running = False

        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes."""

        @self.app.route('/')
        def index():
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Scraper Mock Server</title></head>
            <body>
                <h1>Scraper Development Mock Server</h1>
                <p>Available mock pages:</p>
                <ul>
                {% for path in mock_pages %}
                    <li><a href="{{ path }}">{{ path }}</a></li>
                {% endfor %}
                </ul>
            </body>
            </html>
            """, mock_pages=self.mock_pages.keys())

        @self.app.route('/mock/<path:page>')
        def mock_page(page):
            if page in self.mock_pages:
                return self.mock_pages[page]
            return f"<h1>Mock page '{page}' not found</h1>", 404

        @self.app.route('/api/mock', methods=['POST'])
        def add_mock():
            data = request.get_json()
            path = data.get('path', '').lstrip('/')
            html = data.get('html', '')
            self.mock_pages[path] = html
            return jsonify({"status": "added", "path": path})

    def add_mock_page(self, path: str, html_content: str):
        """Add a mock page."""
        self.mock_pages[path] = html_content

    def start(self):
        """Start the mock server in a background thread."""
        if self.running:
            return

        def run_server():
            self.app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True

        # Wait for server to start
        time.sleep(1)
        print(f"Mock server started on http://127.0.0.1:{self.port}")

    def stop(self):
        """Stop the mock server."""
        self.running = False
        print("Mock server stopped")

    def get_url(self, path: str = "") -> str:
        """Get the full URL for a mock page."""
        return f"http://127.0.0.1:{self.port}/{path}"


class ScraperDevGUI:
    """Web-based GUI for scraper development and testing."""

    def __init__(self, port: int = 8080):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask required for ScraperDevGUI. Install with: pip install flask")

        self.port = port
        self.app = Flask(__name__, static_folder=str(PROJECT_ROOT / "static"))
        self.debugger = SelectorDebugger(headless=False)
        self.mock_server = MockServer(port=5001)
        self.current_url = None

        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes for the GUI."""

        @self.app.route('/')
        def index():
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Scraper Development GUI</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
                    input, button { padding: 8px; margin: 5px; }
                    .result { background: #f9f9f9; padding: 10px; margin: 10px 0; }
                    .success { color: green; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1>Scraper Development GUI</h1>

                <div class="section">
                    <h2>Load Page</h2>
                    <input type="text" id="pageUrl" placeholder="Enter URL to load" size="50">
                    <button onclick="loadPage()">Load Page</button>
                    <button onclick="loadMockPage()">Load Mock Page</button>
                    <div id="pageStatus"></div>
                </div>

                <div class="section">
                    <h2>Test Selector</h2>
                    <select id="selectorType">
                        <option value="css">CSS Selector</option>
                        <option value="xpath">XPath</option>
                    </select>
                    <input type="text" id="selector" placeholder="Enter selector" size="40">
                    <button onclick="testSelector()">Test Selector</button>
                    <button onclick="highlightSelector()">Highlight</button>
                    <div id="selectorResult"></div>
                </div>

                <div class="section">
                    <h2>Mock Pages</h2>
                    <textarea id="mockHtml" rows="10" cols="80" placeholder="Enter HTML content"></textarea><br>
                    <input type="text" id="mockPath" placeholder="Path (e.g., test-page)">
                    <button onclick="addMockPage()">Add Mock Page</button>
                </div>

                <div class="section">
                    <h2>Quick Tests</h2>
                    <button onclick="testCommonSelectors()">Test Common Selectors</button>
                    <div id="quickTestsResult"></div>
                </div>
            </body>
            <script>
                function loadPage() {
                    const url = document.getElementById('pageUrl').value;
                    fetch('/api/load_page', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    })
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('pageStatus').innerHTML =
                            data.success ? '<span class="success">SUCCESS: Page loaded</span>' :
                                          '<span class="error">ERROR: Failed to load page</span>';
                    });
                }

                function testSelector() {
                    const selector = document.getElementById('selector').value;
                    const type = document.getElementById('selectorType').value;
                    fetch('/api/test_selector', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({selector: selector, type: type})
                    })
                    .then(r => r.json())
                    .then(data => {
                        const result = data.result;
                        document.getElementById('selectorResult').innerHTML = `
                            <div class="result">
                                <strong>${result.selector_name}</strong><br>
                                Found: ${result.found ? 'YES' : 'NO'} (${result.count} elements)<br>
                                Text: ${result.text.substring(0, 100)}${result.text.length > 100 ? '...' : ''}<br>
                                Success: ${result.success ? '<span class="success">SUCCESS</span>' : '<span class="error">FAILED</span>'}
                            </div>
                        `;
                    });
                }

                function highlightSelector() {
                    const selector = document.getElementById('selector').value;
                    const type = document.getElementById('selectorType').value;
                    fetch('/api/highlight_selector', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({selector: selector, type: type})
                    });
                }

                function addMockPage() {
                    const html = document.getElementById('mockHtml').value;
                    const path = document.getElementById('mockPath').value;
                    fetch('/api/add_mock', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({path: path, html: html})
                    })
                    .then(r => r.json())
                    .then(data => alert('Mock page added: ' + data.path));
                }

                function loadMockPage() {
                    const path = document.getElementById('mockPath').value;
                    if (path) {
                        document.getElementById('pageUrl').value = `http://127.0.0.1:5001/mock/${path}`;
                        loadPage();
                    }
                }

                function testCommonSelectors() {
                    fetch('/api/test_common_selectors')
                    .then(r => r.json())
                    .then(data => {
                        let html = '<div class="result">';
                        data.results.forEach(result => {
                            html += `<strong>${result.name}:</strong> ${result.found ? 'YES' : 'NO'} (${result.count})<br>`;
                        });
                        html += '</div>';
                        document.getElementById('quickTestsResult').innerHTML = html;
                    });
                }
            </script>
            </html>
            """)

        @self.app.route('/api/load_page', methods=['POST'])
        def api_load_page():
            data = request.get_json()
            url = data.get('url')
            success = self.debugger.load_page(url)
            if success:
                self.current_url = url
            return jsonify({"success": success})

        @self.app.route('/api/test_selector', methods=['POST'])
        def api_test_selector():
            data = request.get_json()
            selector = data.get('selector')
            selector_type = data.get('type', 'css')
            result = self.debugger.test_selector(selector, selector_type)
            return jsonify({"result": {
                "selector_name": result.selector_name,
                "found": result.found,
                "count": result.count,
                "text": result.text,
                "success": result.success
            }})

        @self.app.route('/api/highlight_selector', methods=['POST'])
        def api_highlight_selector():
            data = request.get_json()
            selector = data.get('selector')
            selector_type = data.get('type', 'css')
            self.debugger.highlight_element(selector, selector_type)
            return jsonify({"status": "highlighted"})

        @self.app.route('/api/add_mock', methods=['POST'])
        def api_add_mock():
            data = request.get_json()
            path = data.get('path')
            html = data.get('html')
            self.mock_server.add_mock_page(path, html)
            return jsonify({"status": "added", "path": path})

        @self.app.route('/api/test_common_selectors', methods=['GET'])
        def api_test_common_selectors():
            common_selectors = [
                {"name": "Title", "selector": "title", "type": "css"},
                {"name": "H1", "selector": "h1", "type": "css"},
                {"name": "Product Title", "selector": "[data-cy='title-recipe'], .product-title, #productTitle", "type": "css"},
                {"name": "Price", "selector": ".a-price .a-offscreen, [data-cy='price-recipe']", "type": "css"},
                {"name": "Images", "selector": "#altImages img, .product-image img", "type": "css"},
            ]

            results = []
            for sel in common_selectors:
                result = self.debugger.test_selector(sel["selector"], sel["type"])
                results.append({
                    "name": sel["name"],
                    "found": result.found,
                    "count": result.count
                })

            return jsonify({"results": results})

    def start(self):
        """Start the development GUI."""
        self.mock_server.start()

        def run_gui():
            self.app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False)

        gui_thread = threading.Thread(target=run_gui, daemon=True)
        gui_thread.start()

        print(f"Scraper Development GUI started on http://127.0.0.1:{self.port}")
        webbrowser.open(f"http://127.0.0.1:{self.port}")

    def stop(self):
        """Stop the development GUI."""
        self.debugger.close()
        self.mock_server.stop()


class ScraperTestSuite:
    """Comprehensive test suite for scraper development."""

    def __init__(self):
        self.debugger = SelectorDebugger()
        self.test_cases: List[SelectorTest] = []

    def add_test_case(self, test: SelectorTest):
        """Add a test case."""
        self.test_cases.append(test)

    def load_test_cases_from_file(self, file_path: str):
        """Load test cases from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                for test_data in data.get('test_cases', []):
                    test = SelectorTest(
                        name=test_data['name'],
                        selector=test_data['selector'],
                        selector_type=test_data.get('selector_type', 'css'),
                        expected_count=test_data.get('expected_count'),
                        expected_text=test_data.get('expected_text'),
                        description=test_data.get('description', '')
                    )
                    self.test_cases.append(test)
        except Exception as e:
            print(f"ERROR: Failed to load test cases: {e}")

    def run_tests(self, url: str) -> Dict[str, Any]:
        """Run all test cases against a URL."""
        if not self.debugger.load_page(url):
            return {"error": "Failed to load page"}

        results = []
        passed = 0
        failed = 0

        for test in self.test_cases:
            result = self.debugger.test_selector(test.selector, test.selector_type)

            # Check expectations
            success = True
            if test.expected_count is not None and result.count != test.expected_count:
                success = False
            if test.expected_text and test.expected_text not in result.text:
                success = False

            if success:
                passed += 1
            else:
                failed += 1

            results.append({
                "test_name": test.name,
                "selector": test.selector,
                "expected_count": test.expected_count,
                "actual_count": result.count,
                "expected_text": test.expected_text,
                "actual_text": result.text[:100],
                "success": success,
                "description": test.description
            })

        return {
            "total_tests": len(self.test_cases),
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / len(self.test_cases)) * 100 if self.test_cases else 0,
            "results": results
        }

    def save_test_cases(self, file_path: str):
        """Save test cases to a JSON file."""
        data = {
            "test_cases": [
                {
                    "name": test.name,
                    "selector": test.selector,
                    "selector_type": test.selector_type,
                    "expected_count": test.expected_count,
                    "expected_text": test.expected_text,
                    "description": test.description
                }
                for test in self.test_cases
            ]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def close(self):
        """Clean up resources."""
        self.debugger.close()


# Convenience functions for quick testing
def quick_selector_test(url: str, selector: str, selector_type: str = 'css') -> ScraperTestResult:
    """Quick test a single selector."""
    debugger = SelectorDebugger()
    try:
        if debugger.load_page(url):
            return debugger.test_selector(selector, selector_type)
        else:
            return ScraperTestResult(selector, False, 0, "Failed to load page", "", False)
    finally:
        debugger.close()


def create_mock_html_template(product_name: str = "Test Product", price: str = "$29.99") -> str:
    """Create a basic HTML template for testing."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>{product_name} - Test Store</title></head>
    <body>
        <div class="product-page">
            <h1 class="product-title">{product_name}</h1>
            <div class="price-container">
                <span class="price">{price}</span>
            </div>
            <div class="product-images">
                <img src="image1.jpg" alt="{product_name}">
                <img src="image2.jpg" alt="{product_name}">
            </div>
            <div class="product-description">
                <p>This is a test product description for {product_name}.</p>
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "gui":
            gui = ScraperDevGUI()
            gui.start()
            input("Press Enter to stop...")
            gui.stop()

        elif command == "test":
            if len(sys.argv) > 3:
                url = sys.argv[2]
                selector = sys.argv[3]
                selector_type = sys.argv[4] if len(sys.argv) > 4 else 'css'

                result = quick_selector_test(url, selector, selector_type)
                print(f"Selector: {selector}")
                print(f"Found: {result.found} ({result.count} elements)")
                print(f"Text: {result.text}")
            else:
                print("Usage: python dev_tools.py test <url> <selector> [css|xpath]")

        elif command == "mock":
            server = MockServer()
            server.add_mock_page("test", create_mock_html_template())
            server.start()
            print("Mock server running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                server.stop()
    else:
        print("Scraper Development Tools")
        print("Commands:")
        print("  gui     - Start development GUI")
        print("  test    - Quick selector test")
        print("  mock    - Start mock server")