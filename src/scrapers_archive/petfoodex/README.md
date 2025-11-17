# ⚠️ DEPRECATED: Pet Food Experts Scraper Apify Actor

> **This scraper has been migrated to the new modular system.** Please use the YAML configuration at `src/scrapers/configs/petfoodex.yaml` instead.

This Apify actor scrapes product information from the Pet Food Experts website.

## Migration Status

- ✅ **Migration Complete**: This scraper has been successfully migrated to the new modular scraper system
- 📅 **Deprecation Timeline**: This legacy scraper will be removed in a future version
- 📖 **Migration Guide**: See `docs/SCRAPER_MIGRATION_GUIDE.md` for detailed migration instructions

## New Location

The new Pet Food Experts scraper configuration is located at:
```
src/scrapers/configs/petfoodex.yaml
```

## Input

The actor accepts the following input:

```json
{
  "skus": ["string"]
}
```

- `skus`: Array of SKU strings to search for on Pet Food Experts website

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

- Searches Pet Food Experts website for products by SKU
- Handles login authentication using stored credentials
- Extracts product name, brand, weight, and image URLs
- Parses weight from product names and converts to pounds
- Handles main product images and slider thumbnails
- Runs in headless mode for production deployment

## Environment Variables

Requires Pet Food Experts login credentials configured in settings.

## Dependencies

- apify
- selenium
- webdriver-manager
- beautifulsoup4
- lxml
- python-dotenv
