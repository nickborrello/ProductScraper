# Scraper Development Tools

This document describes the enhanced debugging and development tools available for improving your scraper development workflow.

## Overview

The scraper development tools provide:

- **Visual Selector Debugging**: Test CSS/XPath selectors against live pages with visual feedback
- **Mock Server**: Test scrapers against controlled HTML content without hitting live sites
- **Web-based GUI**: Interactive development interface for selector testing
- **Test Suite Management**: Create and run comprehensive selector test suites
- **CLI Integration**: Command-line tools that integrate with your existing testing framework

## Installation

The tools require additional dependencies. Install them with:

```bash
pip install flask requests beautifulsoup4
```

## Quick Start

### 1. Visual Selector Testing

Test a CSS selector against a live page:

```bash
python src/utils/scraping/dev_cli.py debug-selector "https://amazon.com/dp/B07G5J5FYP" "h1#productTitle"
```

Test an XPath selector with highlighting:

```bash
python src/utils/scraping/dev_cli.py debug-selector "https://amazon.com/dp/B07G5J5FYP" "//h1[@id='productTitle']" --type xpath --highlight
```

### 2. Start Development GUI

Launch the interactive web-based development interface:

```bash
python src/utils/scraping/dev_cli.py gui
```

This opens a browser window at `http://127.0.0.1:8080` where you can:
- Load pages and test selectors interactively
- Highlight elements in the browser
- Create and test mock pages
- Run common selector tests

### 3. Mock Server for Testing

Start a local mock server for testing without hitting live sites:

```bash
python src/utils/scraping/dev_cli.py mock-server
```

Access mock pages at `http://127.0.0.1:5000/mock/<page-name>`

## Available Tools

### Command Line Interface

The `dev_cli.py` script provides the following commands:

#### `test`
Run existing scraper tests (integrates with your current testing framework).

```bash
# Test all scrapers
python src/utils/scraping/dev_cli.py test --all

# Test specific scraper
python src/utils/scraping/dev_cli.py test --scraper amazon --verbose
```

#### `debug-selector`
Test individual selectors against live pages.

```bash
# Basic CSS selector test
python src/utils/scraping/dev_cli.py debug-selector <url> <selector>

# XPath with highlighting
python src/utils/scraping/dev_cli.py debug-selector <url> <xpath> --type xpath --highlight
```

#### `create-suite`
Create a test suite for a scraper with common selectors.

```bash
python src/utils/scraping/dev_cli.py create-suite amazon "https://amazon.com/dp/B07G5J5FYP"
```

#### `run-suite`
Run a saved test suite.

```bash
python src/utils/scraping/dev_cli.py run-suite tests/fixtures/amazon_selectors.json
```

#### `gui`
Start the web-based development GUI.

```bash
python src/utils/scraping/dev_cli.py gui --port 8080
```

#### `mock-server`
Start the mock server for testing.

```bash
python src/utils/scraping/dev_cli.py mock-server --port 5000
```

#### `generate-scraper`
Generate a basic scraper template.

```bash
python src/utils/scraping/dev_cli.py generate-scraper newstore "https://newstore.com"
```

#### `compare`
Compare two scrapers against the same URL.

```bash
python src/utils/scraping/dev_cli.py compare amazon bradley "https://example.com/product/123"
```

### Development GUI Features

The web GUI (`http://127.0.0.1:8080`) provides:

1. **Page Loading**: Load any URL for testing
2. **Selector Testing**: Test CSS or XPath selectors with real-time feedback
3. **Visual Highlighting**: Highlight matching elements directly in the browser
4. **Mock Page Creation**: Create custom HTML pages for testing
5. **Quick Tests**: Test common selectors (title, price, images, etc.)

### Mock Server

The mock server allows you to:

- Create custom HTML pages for testing
- Test scrapers against known content
- Develop without hitting rate limits
- Simulate different page structures

Default mock pages:
- `amazon-product`: Sample Amazon product page
- `pet-product`: Sample pet food product page

Add custom pages via the GUI or programmatically:

```python
from src.utils.scraping.dev_tools import MockServer

server = MockServer()
server.add_mock_page("custom", "<html><body><h1>Custom Page</h1></body></html>")
server.start()
```

### Selector Test Suites

Create comprehensive test suites for your scrapers:

```json
{
  "scraper_name": "amazon",
  "test_url": "https://amazon.com/dp/B07G5J5FYP",
  "test_cases": [
    {
      "name": "Product Title",
      "selector": "h1#productTitle",
      "selector_type": "css",
      "expected_count": 1,
      "expected_text": "Sample Product",
      "description": "Main product title"
    }
  ]
}
```

## Integration with Existing Workflow

### During Development

1. **Start GUI**: `python src/utils/scraping/dev_cli.py gui`
2. **Load Target Page**: Use the GUI to load a product page
3. **Test Selectors**: Try different selectors until you find the right ones
4. **Create Test Suite**: `python src/utils/scraping/dev_cli.py create-suite <scraper> <url>`
5. **Implement Scraper**: Use the tested selectors in your scraper code
6. **Run Tests**: `python src/utils/scraping/dev_cli.py test --scraper <scraper>`

### Before Deployment

1. **Run Test Suite**: `python src/utils/scraping/dev_cli.py run-suite <test_file>`
2. **Mock Testing**: Test against mock server for edge cases
3. **Integration Tests**: Run full scraper tests with existing framework

## Best Practices

### Selector Testing

1. **Start Broad**: Use general selectors first (e.g., `h1`, `.price`)
2. **Be Specific**: Narrow down with IDs, classes, or attribute selectors
3. **Test Variations**: Check selectors across different products/pages
4. **Handle Changes**: Use flexible selectors that work with site updates

### Mock Testing

1. **Realistic HTML**: Use actual page structures in mock pages
2. **Edge Cases**: Include pages with missing data, different formats
3. **Error Conditions**: Test how scrapers handle malformed HTML

### Test Suites

1. **Comprehensive**: Cover all data fields your scraper extracts
2. **Maintainable**: Update test expectations when site changes
3. **Automated**: Run test suites as part of CI/CD pipeline

## Troubleshooting

### Common Issues

**GUI won't start**: Check if port 8080 is available
**Mock server errors**: Ensure Flask is installed
**Browser won't highlight**: Make sure you're not in headless mode

### Debug Mode

Enable debug mode for more detailed output:

```bash
DEBUG_MODE=true python dev_cli.py <command>
```

### Logging

The tools integrate with your existing logging system. Check logs for detailed error information.

## Advanced Usage

### Custom Selector Testing

```python
from src.utils.scraping.dev_tools import SelectorDebugger

debugger = SelectorDebugger()
debugger.load_page("https://example.com")
result = debugger.test_selector("h1.title", "css")
print(f"Found: {result.found}, Count: {result.count}")
debugger.close()
```

### Programmatic Mock Server

```python
from src.utils.scraping.dev_tools import MockServer, create_mock_html_template

server = MockServer()
server.add_mock_page("test-product", create_mock_html_template("Test Product", "$9.99"))
server.start()
# Server runs at http://127.0.0.1:5000/mock/test-product
```

### Custom Test Suites

```python
from src.utils.scraping.dev_tools import ScraperTestSuite, SelectorTest

suite = ScraperTestSuite()
suite.add_test_case(SelectorTest(
    name="Custom Test",
    selector=".custom-selector",
    selector_type="css",
    expected_count=1
))

results = suite.run_tests("https://example.com")
print(f"Success rate: {results['success_rate']}%")
```

## Contributing

When adding new scrapers:

1. Use the GUI to test selectors on target pages
2. Create a test suite for the scraper
3. Add mock pages for common scenarios
4. Update this documentation

## Related Documentation

- [Scraper Architecture](SCRAPER_ARCHITECTURE.md)