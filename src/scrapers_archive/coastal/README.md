# Coastal Scraper Apify Actor

This Apify actor scrapes product information from the Coastal Pet website.

## Input

The actor accepts the following input:

```json
{
  "skus": ["string"]
}
```

- `skus`: Array of SKU strings to search for on Coastal Pet website

## Output

The actor outputs product data in the following format:

```json
{
  "SKU": "string",
  "Name": "string",
  "Brand": "string",
  "Weight": "string",
  "Image URLs": ["string"]
}
```

## Features

- Searches Coastal Pet website for products by SKU
- Extracts product name, brand, weight, and image URLs
- Handles weight conversion to pounds
- Limits images to 7 per product
- Runs in headless mode for production deployment

## Dependencies

- apify
- selenium
- webdriver-manager
- beautifulsoup4
- lxml
