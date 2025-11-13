# Phillips Scraper Apify Actor

This Apify actor scrapes product information from the Phillips Pet website.

## Input

The actor accepts the following input:

```json
{
  "skus": ["string"]
}
```

- `skus`: Array of SKU strings to search for on Phillips Pet website

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

- Searches Phillips Pet website for products by SKU
- Handles login authentication using stored credentials
- Extracts product name, brand, and image URLs
- Matches exact UPC codes for accurate results
- Runs in headless mode for production deployment

## Environment Variables

Requires Phillips login credentials configured in settings.

## Dependencies

- apify
- selenium
- webdriver-manager
- beautifulsoup4
- lxml
- pandas
