# Mazuri Scraper Apify Actor

This Apify actor scrapes product information from the Mazuri website.

## Input

The actor accepts the following input:

```json
{
  "skus": ["string"]
}
```

- `skus`: Array of SKU strings to search for on Mazuri website

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

- Searches Mazuri website for products by SKU
- Extracts product name, brand, weight, and image URLs
- Handles multiple product variants from JSON data
- Parses embedded product JSON for robust extraction
- Handles weight conversion and formatting
- Limits images to 7 per product
- Runs in headless mode for production deployment

## Dependencies

- apify
- selenium
- webdriver-manager
- beautifulsoup4
- lxml
