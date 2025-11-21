# Copilot Instructions for ProductScraper Repository

These instructions guide GitHub Copilot's behavior when working in this repository.

## General Guidelines

- Write concise, readable Python code with proper error handling
- Use descriptive variable names and add comments for complex logic
- Prefer modern Python features (f-strings, type hints, dataclasses)
- Follow PEP 8 style guidelines and ensure code passes ruff linting as configured in pyproject.toml
- **Pre-Commit Checks**: Always run `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/` before committing to ensure code quality and formatting
- Handle exceptions appropriately in web scraping code
- Use logging instead of print statements for debugging
- Test on products that have all the needed fields filled in, like 035585499741

## Project-Specific Rules

- This tool is very powerful and has access to live data on the site. Be careful. This isn't a dev environment.
- When scraping websites, always include user-agent headers and respect robots.txt
- Store scraped data in pandas DataFrames for consistency
- Use Selenium with explicit waits to avoid flaky tests
- Save cookies and profiles to maintain session state
- Parse weights from product names and normalize to consistent units (LB)
- Ensure cross-sell relationships are properly saved to Excel output
- **Standalone Scrapers**: All scrapers are standalone Python modules with async main() functions
- **Testing Protocol**: Always test scraping functionality locally first using the enhanced testing framework
- Use the Actions Framework for complex workflows with parse_weight and process_images actions
- Extract Weight and Images fields using the new processing actions
- Bradley Caldwell scraper is now available alongside other scrapers

## Actions Framework

### Overview

The Actions Framework provides a registry-based system for building modular, reusable scraping workflows. Actions are registered using the @ActionRegistry.register decorator and can be composed into complex scraping pipelines.

### parse_weight Action

Parses weight strings from product descriptions and normalizes them to consistent units (lb, kg, oz, g). Handles various formats like "5 lb", "2.5kg", "16 oz".

### process_images Action

Filters, deduplicates, and upgrades image URLs. Removes invalid URLs, eliminates duplicates, and converts relative URLs to absolute ones.

### Custom Actions

To create custom actions, use the @ActionRegistry.register decorator:

```python
from src.scrapers.actions.registry import ActionRegistry

@ActionRegistry.register('my_custom_action')
class MyCustomAction:
    async def execute(self, context, **kwargs):
        # Custom logic here
        pass
```

## Building and Testing Scrapers Locally

### Local Development Setup

1. **Install Dependencies**: Install project dependencies from the root directory:

   ```bash
   pip install -e .
   ```

2. **Environment Variables**: Create a `.env` file in the scraper directory if needed for API keys or configuration:
   ```bash
   cd src/scrapers/{scraper_name}
   cp .env.example .env  # If .env.example exists
   # Edit .env with your actual values
   ```

### Running Scrapers Locally

1. **Use the Workflow Executor**: Run scrapers using YAML configuration files:

   ```bash
   python -m src.scrapers.main --config src/scrapers/configs/{scraper_name}.yaml --sku {test_sku}
   ```

2. **Run with Test Framework**: Use the enhanced testing framework:

   ```bash
   python scripts/test_scrapers.py --scraper {scraper_name}
   ```

### Testing Protocol

**CRITICAL**: Always test scraping functionality locally first. Use the enhanced testing framework for validation.

1. **Use Test SKUs**: Test with products that have all needed fields filled in (e.g., SKU: 035585499741)
2. **Verify Output**: Check that scraped data includes:

   - Product name
   - Price
   - Images (comma-separated URLs)
   - Weight (normalized to LB)
   - Brand
   - Category and product type
   - Cross-sell relationships

3. **Quality Validation**: Ensure data quality scores >85% using the DataQualityScorer
4. **Performance Checks**: Verify <5 min execution time with <500MB memory usage

### Enhanced Testing Framework

The project includes a comprehensive testing system with multiple modes:

#### Local Testing Mode (Default)

- Runs scrapers directly with local storage
- No API keys required
- File-based storage for datasets
- Full quality scoring and validation

#### Testing Commands

```bash
# Run all scrapers locally
python test_scrapers.py --all

# Test specific scraper
python test_scrapers.py --scraper amazon

# Quality validation
python -m pytest tests/unit/test_data_quality_scorer.py

# Performance testing
python -m pytest tests/unit/test_performance.py
```

### Validation Checks

The testing system validates:

- **Data Format**: Required fields present (SKU, Name)
- **Data Quality**: No invalid values (N/A, null, empty strings)
- **Field Coverage**: Expected fields populated
- **Weight Units**: Normalized to LB
- **Image URLs**: Valid HTTP/HTTPS URLs
- **Price Format**: Proper numeric format
- **Cross-sell Data**: Pipe-separated format
- **Quality Score**: >85% threshold met

### Pre-Deployment Checklist

- [ ] All scrapers pass `python test_scrapers.py --all`
- [ ] No validation errors in output data
- [ ] Data quality score > 85% for all scrapers
- [ ] All required fields populated for test SKUs
- [ ] Ready for deployment

## GUI Development Guidelines

- **Async Threading**: Use the enhanced Worker class that supports async operations with asyncio event loops
- **Progress Updates**: Implement real-time progress signals with metrics (elapsed time, processed count, current operation, ETA)
- **Cancellation Support**: Add cancel buttons with proper cleanup of worker threads and resources
- **UI Responsiveness**: Ensure GUI remains responsive during long-running operations

## Code Patterns

- Use context managers for file operations and database connections
- Implement retry logic for network requests
- Validate data before saving to prevent corrupted outputs
- Separate scraping logic from data processing logic

## Database

- Our database uses SQLite and is managed with SQLAlchemy
- These are the columns:
  - id INTEGER PRIMARY KEY AUTOINCREMENT, // Auto-incrementing primary key
  - SKU TEXT UNIQUE, // Unique Stock Keeping Unit
  - Name TEXT, // Product name
  - Price TEXT, // Price
  - Images TEXT, // Comma-separated list of image URLs
  - Weight TEXT, // Product weight
  - Product_Field_16 TEXT, // Brand
  - Product_Field_11 TEXT, // Special Order
  - Product_Field_24 TEXT, // Category
  - Product_Field_25 TEXT, // Product Type
  - Product_On_Pages TEXT, // Pages where the product appears, separated by |
  - Product_Field_32 TEXT, // Product Cross Sells, separated by |
  - last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP // Timestamp of last update
  - ProductDisabled TEXT, // Indicates if the product is disabled (checked or uncheck)

## ShopSite XML API

### Downloading Data

- **Program**: `db_xml.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `dbname=products` (required) - Database to access (products/pages)
  - `version=14.0` (optional) - XML format version (14.0, 12.0, 11.2, 11.1, 11.0, 10.2, 10.1, 10.0, 9.0, 8.3, 8.2, 8.1, 8.0, 7.1)
  - `fields` (optional) - Comma-separated list of fields to download, or "all" for everything
  - `fieldmap` (optional) - Predefined field mapping name
- **Authentication**: Basic HTTP authentication (username/password)
- **Response**: Uses chunked transfer encoding (no Content-Length header available)
- **Current Implementation**: Downloads all product fields, shows progress with speed/time estimates

### Uploading Data

- **Program**: `dbupload.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `dbname=products` (required) - Database to upload to (products/pages)
  - `filename` (optional) - Name of XML file previously uploaded to ShopSite's HTML output directory
  - `uniqueName` (optional) - Unique database key field (defaults to "Name", can be "SKU", "Product GUID", "File Name", or "(none)" for duplicates)
  - `newRecords=yes/no` (optional) - Whether to include new records (default: yes)
  - `defer_linking=yes/no` (optional) - Defer record linking for batch uploads (default: no)
  - `restart=1` (optional) - Restart interrupted upload from where it left off
- **Authentication**: Basic HTTP authentication (username/password)
- **Notes**:
  - For large databases (>10,000 records), break uploads into batches
  - Use `defer_linking=yes` for all files except the last in a batch
  - Can upload MIME-encoded XML or reference pre-uploaded files

### Publishing Changes

- **Program**: `generate.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `htmlpages=1` (optional) - Generate HTML pages
  - `custompages=1` (optional) - Generate custom pages
  - `index=1` (optional) - Update search index
  - `regen=1` (optional) - Regenerate all content (overrides incremental updates)
  - `sitemap=1` (optional) - Generate Google XML sitemap
- **Notes**: If publish times out, call again with same parameters to restart from interruption point

### Current Usage

- **Download**: ✅ Implemented and working (`import_from_shopsite_xml()`)
- **Upload**: ❌ Not implemented (could be useful for bulk product updates)
- **Publish**: ✅ Implemented and working (`publish_shopsite_changes()`)

## Building and Testing Scrapers Locally

### Local Development Setup

1. **Install Dependencies**: Install project dependencies from the root directory:

   ```bash
   pip install -e .
   ```

2. **Environment Variables**: Create a `.env` file in the scraper directory if needed for API keys or configuration:
   ```bash
   cd src/scrapers/{scraper_name}
   cp .env.example .env  # If .env.example exists
   # Edit .env with your actual values
   ```

### Running Scrapers Locally

1. **Navigate to Scraper Directory**:

   ```bash
   cd src/scrapers/{scraper_name}
   ```

2. **Run with Test SKUs**: Use the workflow executor with YAML configs:

   ```bash
   python -m src.scrapers.main --config src/scrapers/configs/{scraper_name}.yaml --sku {test_sku}
   ```

3. **Run with Test Framework**: Use the testing script:

   ```bash
   python scripts/test_scrapers.py --scraper {scraper_name}
   ```

### Testing Protocol

**CRITICAL**: Always test scraping functionality locally first. Use the enhanced testing framework for validation.

1. **Use Test SKUs**: Test with products that have all needed fields filled in (e.g., SKU: 035585499741)
2. **Verify Output**: Check that scraped data includes:

   - Product name
   - Price
   - Images (comma-separated URLs)
   - Weight (normalized to LB)
   - Brand
   - Category and product type
   - Cross-sell relationships

3. **Browser Testing**:

   - Set `HEADLESS = False` in scraper code for visual debugging
   - Set `HEADLESS = True` (default) for headless operation
   - Only set to `False` if CAPTCHA solving or user interaction is required

4. **Error Handling**: Verify that the scraper handles:

   - Network timeouts
   - Missing products
   - Invalid SKUs
   - Anti-bot measures

5. **Data Validation**: Ensure output data:
   - Is saved to pandas DataFrames
   - Has consistent field formats
   - Includes proper cross-sell relationships
   - Normalizes weights to LB units

## Scraper Testing and Debugging System

The project includes a comprehensive testing system to ensure scrapers work properly. All testing must be done locally.

### Testing Tools

#### Command-Line Test Runner (`test_scrapers.py`)

The main testing tool is `test_scrapers.py` in the project root. It provides:

```bash
# Test all scrapers
python test_scrapers.py --all

# Test specific scraper
python test_scrapers.py --scraper amazon

# Test with custom SKUs
python test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW

# List available scrapers
python test_scrapers.py --list

# Validate scraper structure only
python test_scrapers.py --validate amazon

# Verbose output for debugging
python test_scrapers.py --scraper amazon --verbose
```

#### Test Fixtures (`tests/fixtures/`)

- **`scraper_test_data.json`**: Contains test SKUs and expected fields for each scraper
- **`scraper_validator.py`**: Validation utilities for checking output data format and quality

#### Integration Tests (`tests/integration/`)

- **`test_scraper_integration.py`**: Automated integration tests that run scrapers and validate output

### Testing Workflow

**CRITICAL**: Always run local tests before deployment.

1. **Structure Validation**:

   ```bash
   python test_scrapers.py --validate <scraper_name>
   ```

2. **Individual Scraper Testing**:

   ```bash
   python test_scrapers.py --scraper <scraper_name>
   ```

3. **Full Test Suite**:

   ```bash
   python test_scrapers.py --all
   ```

4. **Debugging Failed Tests**:
   ```bash
   python test_scrapers.py --scraper <scraper_name> --verbose
   ```

## Database

- Our database uses SQLite and is managed with SQLAlchemy
- These are the columns:
  - id INTEGER PRIMARY KEY AUTOINCREMENT, // Auto-incrementing primary key
  - SKU TEXT UNIQUE, // Unique Stock Keeping Unit
  - Name TEXT, // Product name
  - Price TEXT, // Price
  - Images TEXT, // Comma-separated list of image URLs
  - Weight TEXT, // Product weight
  - Product_Field_16 TEXT, // Brand
  - Product_Field_11 TEXT, // Special Order
  - Product_Field_24 TEXT, // Category
  - Product_Field_25 TEXT, // Product Type
  - Product_On_Pages TEXT, // Pages where the product appears, separated by |
  - Product_Field_32 TEXT, // Product Cross Sells, separated by |
  - last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP // Timestamp of last update
  - ProductDisabled TEXT, // Indicates if the product is disabled (checked or uncheck)

## ShopSite XML API

### Downloading Data

- **Program**: `db_xml.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `dbname=products` (required) - Database to access (products/pages)
  - `version=14.0` (optional) - XML format version (14.0, 12.0, 11.2, 11.1, 11.0, 10.2, 10.1, 10.0, 9.0, 8.3, 8.2, 8.1, 8.0, 7.1)
  - `fields` (optional) - Comma-separated list of fields to download, or "all" for everything
  - `fieldmap` (optional) - Predefined field mapping name
- **Authentication**: Basic HTTP authentication (username/password)
- **Response**: Uses chunked transfer encoding (no Content-Length header available)
- **Current Implementation**: Downloads all product fields, shows progress with speed/time estimates

### Uploading Data

- **Program**: `dbupload.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `dbname=products` (required) - Database to upload to (products/pages)
  - `filename` (optional) - Name of XML file previously uploaded to ShopSite's HTML output directory
  - `uniqueName` (optional) - Unique database key field (defaults to "Name", can be "SKU", "Product GUID", "File Name", or "(none)" for duplicates)
  - `newRecords=yes/no` (optional) - Whether to include new records (default: yes)
  - `defer_linking=yes/no` (optional) - Defer record linking for batch uploads (default: no)
  - `restart=1` (optional) - Restart interrupted upload from where it left off
- **Authentication**: Basic HTTP authentication (username/password)
- **Notes**:
  - For large databases (>10,000 records), break uploads into batches
  - Use `defer_linking=yes` for all files except the last in a batch
  - Can upload MIME-encoded XML or reference pre-uploaded files

### Publishing Changes

- **Program**: `generate.cgi`
- **Parameters**:
  - `clientApp=1` (required) - Client application version identifier
  - `htmlpages=1` (optional) - Generate HTML pages
  - `custompages=1` (optional) - Generate custom pages
  - `index=1` (optional) - Update search index
  - `regen=1` (optional) - Regenerate all content (overrides incremental updates)
  - `sitemap=1` (optional) - Generate Google XML sitemap
- **Notes**: If publish times out, call again with same parameters to restart from interruption point

### Current Usage

- **Download**: ✅ Implemented and working (`import_from_shopsite_xml()`)
- **Upload**: ❌ Not implemented (could be useful for bulk product updates)
- **Publish**: ✅ Implemented and working (`publish_shopsite_changes()`)
