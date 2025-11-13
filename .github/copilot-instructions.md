# Copilot Instructions for ProductScraper Repository

These instructions guide GitHub Copilot's behavior when working in this repository.

## General Guidelines

- Write concise, readable Python code with proper error handling
- Use descriptive variable names and add comments for complex logic
- Prefer modern Python features (f-strings, type hints, dataclasses)
- Follow PEP 8 style guidelines
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
- **Scraper Development**: When creating new scrapers, add `HEADLESS = True` (default) or `HEADLESS = False` at module level. Set to `False` only if the scraper requires visible browser for CAPTCHA solving, user interaction, or other visual elements.
- **Testing Protocol**: Always test scraping functionality locally before pushing to Apify hosting. Never run scrapes with Apify hosting during testing phases - use local execution only for development and validation.

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
- **Publish**: ❌ Not implemented (could be useful for automated site updates)
