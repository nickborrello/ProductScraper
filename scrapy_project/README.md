# Scrapy Integration for ProductScraper

This directory contains a complete Scrapy project that integrates with your existing Selenium-based ProductScraper system.

## Overview

While your existing scrapers handle complex e-commerce sites requiring JavaScript execution, login sessions, and browser automation, this Scrapy setup provides:

- **Faster scraping** for sites that don't require JavaScript
- **Built-in concurrency** and request management
- **Automatic data cleaning** and normalization
- **Respectful crawling** with throttling and caching
- **Multiple output formats** (JSON, CSV, Excel)
- **Easy integration** with your existing database and GUI

## Project Structure

```
scrapy_project/
├── scrapy.cfg                 # Scrapy project configuration
├── scrapy_project/
│   ├── __init__.py
│   ├── items.py               # Data models for scraped items
│   ├── loaders.py             # Data cleaning processors
│   ├── middlewares.py         # Custom middleware (if needed)
│   ├── pipelines.py           # Data processing pipeline
│   ├── settings.py            # Scrapy settings
│   └── spiders/
│       ├── __init__.py
│       └── product_spider.py  # Main spider and site-specific spiders
├── data/                      # Output directory for scraped data
└── README.md                  # This file
```

## Quick Start

### 1. Test the Setup

```bash
cd scrapy_project
python -m scrapy crawl product_spider -a skus=035585499741
```

### 2. Use from Your Existing Code

```python
from src.scrapers.scrapy_scraper import scrape_with_scrapy

# Scrape products by SKU
skus = ['035585499741', '123456789012']
results = scrape_with_scrapy(skus)

for result in results:
    if result:
        print(f"Found: {result['Name']}")
    else:
        print("Product not found")
```

## Configuration

### Settings (`settings.py`)

Key settings for respectful scraping:
- `AUTOTHROTTLE_ENABLED`: Automatically adjusts request delays
- `DOWNLOAD_DELAY`: Minimum delay between requests
- `ROBOTSTXT_OBEY`: Respects robots.txt files
- `USER_AGENT`: Identifies your scraper

### Items (`items.py`)

Defines the data structure for scraped products, matching your existing database schema:
- SKU, Name, Price, Brand, Weight
- Image URLs, Category, Product Type
- Cross-sell relationships and metadata

### Pipeline (`pipelines.py`)

Processes scraped items and saves them in multiple formats:
- JSON for API integration
- CSV for spreadsheet import
- Excel for direct database import

## Creating Site-Specific Spiders

### 1. Basic Spider

```python
from scrapy_project.spiders.product_spider import ProductSpider

class MySiteSpider(ProductSpider):
    name = 'my_site_spider'

    def __init__(self, *args, **kwargs):
        super().__init__(
            site_url='https://www.mysite.com',
            search_url='https://www.mysite.com/search?q={query}',
            *args, **kwargs
        )

    def _get_product_url(self, sku):
        return f"https://www.mysite.com/product/{sku}"

    def parse_product(self, response):
        loader = ProductLoader(response=response)
        loader.add_value('sku', response.meta['sku'])

        # Site-specific selectors
        loader.add_css('name', '.product-title::text')
        loader.add_css('price', '.price::text')
        loader.add_css('brand', '.brand::text')

        yield loader.load_item()
```

### 2. JavaScript-Heavy Sites

For sites requiring JavaScript (like Amazon, complex login flows), you'll need Scrapy-Splash:

```bash
pip install scrapy-splash
```

Then configure Splash middleware in `settings.py`:
```python
SPLASH_URL = 'http://localhost:8050'
DOWNLOADER_MIDDLEWARES = {
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}
```

## Integration with Existing System

### Database Import

The pipeline outputs data in formats compatible with your `database_import.py`:

```python
# In your database_import.py, add support for Scrapy output
def import_scrapy_data(excel_file):
    # Read Excel file from scrapy_project/data/
    df = pd.read_excel(excel_file)
    # Process and import to database
    # ... existing logic ...
```

### Master Scraper Integration

Update your `master.py` to use Scrapy for appropriate sites:

```python
def scrape_products(skus, site):
    # Use Scrapy for simple sites
    if site in ['simple_site', 'basic_ecommerce']:
        return scrape_with_scrapy(skus, spider_name=f"{site}_spider")

    # Use Selenium for complex sites
    else:
        return scrape_with_selenium(skus, site)
```

## Best Practices

### Respectful Scraping
- Always obey robots.txt
- Use reasonable delays between requests
- Identify your scraper in User-Agent
- Monitor for rate limiting

### Data Quality
- Validate scraped data before saving
- Handle missing fields gracefully
- Normalize prices and weights consistently
- Clean HTML artifacts from text

### Error Handling
- Log failures for debugging
- Retry failed requests appropriately
- Handle network timeouts gracefully

### Performance
- Use concurrent requests judiciously
- Cache responses when possible
- Monitor memory usage for large scrapes

## Troubleshooting

### Common Issues

1. **404 Errors**: Check URL patterns and site structure
2. **Blocked Requests**: Increase delays, rotate User-Agents
3. **JavaScript Content**: Install Scrapy-Splash for JS sites
4. **Data Not Extracted**: Verify CSS selectors match site HTML

### Debugging

```bash
# Run with detailed logging
scrapy crawl product_spider -a skus=035585499741 -L DEBUG

# Test selectors in Scrapy shell
scrapy shell "https://example.com/product/123"
response.css('.product-title::text').get()
```

## Migration Strategy

1. **Start Small**: Convert one simple site first
2. **Test Thoroughly**: Compare Scrapy results with Selenium
3. **Gradual Migration**: Move sites incrementally
4. **Hybrid Approach**: Use both Scrapy and Selenium as needed

## Next Steps

- [ ] Create spider for a specific site you scrape
- [ ] Test with real product URLs
- [ ] Integrate output with your database
- [ ] Add error handling and monitoring
- [ ] Consider Scrapy-Splash for JavaScript sites

## Resources

- [Scrapy Documentation](https://docs.scrapy.org/)
- [Scrapy-Splash for JavaScript](https://github.com/scrapy-plugins/scrapy-splash)
- [Web Scraping Best Practices](https://blog.apify.com/web-scraping-best-practices/)

---

*This Scrapy integration maintains compatibility with your existing ProductScraper system while providing a modern, efficient alternative for sites that don't require complex browser automation.*