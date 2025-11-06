# ProductScraper Project Memory

## Project Overview
**Type:** Web Scraping & Inventory Management System  
**Status:** Active Production  
**Last Updated:** 2025-11-06

## Core Purpose
Multi-site product data scraper with SQLite database management for e-commerce inventory synchronization.

## Key Components

### 1. Main Application (`main.py`)
- Interactive CLI menu system
- 9 operational modes including scraping, database management, testing
- Excel file validation with column mapping
- Integration with inventory and scraping modules

### 2. Scrapers (`scrapers/`)
Active scrapers:
- Amazon
- Bradley Caldwell  
- Central Pet
- Coastal
- Mazuri
- Orgill
- Pet Food Express
- Phillips
- Generic scraper base
- Discontinued product checker

**Headless Mode:** All scrapers default to `HEADLESS = True` unless visual interaction needed.

### 3. Inventory System (`inventory/`)
- SQLite database with SQLAlchemy ORM
- ShopSite XML import/export
- Product classification viewer
- Database schema: SKU, Name, Price, Images, Weight, Brand, Special Order, Category, Product Type, Pages, Cross Sells, Last Updated, ProductDisabled

### 4. Utilities (`util/`)
- Browser automation (`browser_util.py`)
- Cookie management (`cookies.py`)
- Image processing (`image_util.py`, `image_convert.py`, `download_images.py`)
- Cross-sell assignment (`assign_cross_sell.py`)
- Display scraping (`scrape_display.py`)

## Technical Stack
- **Python:** 3.8+
- **Browser:** Selenium with Chrome/Chromium
- **Data:** Pandas, SQLAlchemy
- **File Formats:** Excel (XLSX), XML, SQLite

## Environment Requirements
- `.env` file with ShopSite credentials (SHOPSITE_USERNAME, SHOPSITE_PASSWORD, SHOPSITE_URL)
- ChromeDriver via webdriver-manager
- PowerShell 7+ for command execution

## Critical Safety Rules
⚠️ **LIVE PRODUCTION DATA**
- Always backup before bulk operations
- Test with small batches first
- Never commit credentials to git
- Use test product: SKU 035585499741 (has all fields)

## Excel Column Mapping
**Required:** SKU, Name  
**Optional:** Brand, Weight, Image URLs, Price, Sites

Automatic column mapping for variations:
- SKU: SKU_NO, Sku
- Name: DESCRIPTION1, Product Name, PRODUCT_NAME
- Price: LIST_PRICE, List Price
- Brand: BRAND, Manufacturer, MANUFACTURER
- Weight: WEIGHT, Size, SIZE
- Image URLs: IMAGE_URLS, Images, IMAGES
- Sites: Site Selection, Sites to Scrape, SCRAPE_SITES

## Testing
- Unit tests: `test/test_scrapers.py`
- Integration tests: Optional via environment variable `RUN_INTEGRATION_TESTS=1`
- Granular field tests: Available via main menu option 8

## Recent Changes
- APM initialized (2025-11-06)
- requirements.txt created
- Setup guide documented in `.apm/guides/SETUP.md`

## Dependencies Status
✅ All core packages installed:
- selenium==4.32.0
- pandas==2.2.3
- openpyxl==3.1.5
- requests==2.32.3
- beautifulsoup4==4.13.5
- pillow==11.2.1

## Known Limitations
- Threading removed from main scraper (sequential mode only)
- Cross-sell assignment deprecated (use SQLite queries instead)
- Some modules may have ImportError handling (e.g., ProductScraper, DiscontinuedChecker)

## Next Development Priorities
[To be populated based on Implementation_Plan.md]
