# Scrape Display Utility

This utility provides standardized functions for displaying scrape results across all scrapers in the ProductScraper project.

## Usage

Import the functions you need:

```python
from util.scrape_display import (
    display_product_result,
    display_scraping_progress,
    display_scraping_summary,
    display_error,
    display_success,
    display_warning,
    display_info
)
```

## Functions

### `display_product_result(product, index=None, total=None)`

Displays a single product result in a standardized format.

**Parameters:**

- `product`: Dictionary containing product information
- `index`: Current product index (1-based) for progress display
- `total`: Total number of products being scraped

**Example:**

```python
product = {
    'SKU': '123456789',
    'Name': 'Premium Dog Food',
    'Brand': 'Premium Pet Foods',
    'Weight': '15.00',
    'Image URLs': ['https://example.com/image1.jpg']
}
display_product_result(product, 1, 10)
```

### `display_scraping_progress(current, total, start_time, scraper_name="Scraper")`

Displays scraping progress with timing information.

**Parameters:**

- `current`: Number of products completed
- `total`: Total number of products to scrape
- `start_time`: Time when scraping started (from `time.time()`)
- `scraper_name`: Name of the scraper for display

**Example:**

```python
import time
start_time = time.time()
# ... scraping loop ...
for i in range(1, total_products + 1):
    # ... scrape product ...
    display_scraping_progress(i, total_products, start_time, "My Scraper")
```

### `display_scraping_summary(products, start_time, scraper_name="Scraper")`

Displays a summary of scraping results.

**Parameters:**

- `products`: List of scraped product dictionaries
- `start_time`: Time when scraping started (from `time.time()`)
- `scraper_name`: Name of the scraper for display

**Example:**

```python
successful_products = [p for p in products if p]
display_scraping_summary(successful_products, start_time, "My Scraper")
```

### Message Functions

- `display_error(message, sku=None)`: Display error messages
- `display_success(message)`: Display success messages
- `display_warning(message)`: Display warning messages
- `display_info(message)`: Display informational messages

## Integration Example

Here's how to integrate this into a scraper:

```python
import time
from util.scrape_display import (
    display_product_result,
    display_scraping_progress,
    display_scraping_summary,
    display_error
)

def scrape_my_store(skus):
    products = []
    start_time = time.time()

    # ... setup browser ...

    for i, sku in enumerate(skus, 1):
        product_info = scrape_single_product(sku, browser)
        if product_info:
            products.append(product_info)
            display_product_result(product_info, i, len(skus))
        else:
            display_error(f"No product found for SKU {sku}")
            products.append(None)

        display_scraping_progress(i, len(skus), start_time, "My Store")

    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "My Store")

    return products
```

## Benefits

- **Consistent Output**: All scrapers display results in the same format
- **Progress Tracking**: Users can see real-time progress during scraping
- **Debugging**: Individual product results are shown as they're scraped
- **Statistics**: Automatic calculation of rates, success/failure counts, etc.
- **Error Handling**: Standardized error message formatting
