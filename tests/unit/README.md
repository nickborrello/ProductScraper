# ProductScraper Test Suite

This directory contains tests for the ProductScraper system.

## Test Files

- `test_scrapers.py`: Comprehensive test suite for all scraper modules
- `test_xml_parsing.py`: Tests for XML parsing functionality

## Running Tests

### Basic Validation Tests

```bash
python -m pytest test/test_scrapers.py -v
```

### Integration Tests (Live Scraping)

```bash
# Enable integration tests that make real network calls
RUN_INTEGRATION_TESTS=true python -m pytest test/test_scrapers.py::TestScrapers::test_scraper_with_test_product -v
```

## Adding Tests to Scrapers

To enable integration testing for a scraper module:

1. Add a `TEST_SKU` variable to the scraper module with a SKU that exists on that site:

   ```python
   HEADLESS = True
   TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM
   ```

2. The test will automatically use this SKU when running integration tests.

3. If no `TEST_SKU` is defined, it falls back to the default test SKU.

## Test Coverage

The test suite validates:

- Module imports
- Function existence and signatures
- HEADLESS settings
- Required dependencies
- Basic functionality (optional integration tests)
- Real scraping capability with known products (optional)
