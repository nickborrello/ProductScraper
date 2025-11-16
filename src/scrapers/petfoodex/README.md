# Pet Food Experts Product Scraper

This Apify actor scrapes product information from the Pet Food Experts website for a given list of SKUs.

## Features

- Scrapes product Name, Brand, Image URLs, and Weight.
- Handles login authentication.
- Navigates search results to find the correct product page.
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
# Run the PetFoodEx scraper in debug mode
HEADLESS=False DEBUG_MODE=True python src/scrapers/petfoodex/src/main.py
```

This is useful for observing the scraper's behavior and debugging issues with selectors or site changes.
