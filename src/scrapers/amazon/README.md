# Amazon Product Scraper

This Apify actor scrapes product information from Amazon for a given list of SKUs, ASINs, or UPCs.

## Features

- Scrapes product Name, Brand, Image URLs, and Weight.
- Advanced anti-detection techniques.
- Smart rate limiting and session rotation.
- Data validation and quality scoring.
- Detailed logging for debugging.

## Input

The actor accepts a JSON object with a list of SKUs:

```json
{
  "skus": ["SKU1", "SKU2", ...]
}
```

## Debugging

To run the scraper in debug mode, you can use the `HEADLESS` and `DEBUG_MODE` environment variables. This will run the browser in a visible window and pause the script at certain points for manual inspection.

```bash
# Run the Amazon scraper in debug mode
HEADLESS=False DEBUG_MODE=True python src/scrapers/amazon/src/main.py
```

This is useful for observing the scraper's behavior and debugging issues with selectors or site changes.
