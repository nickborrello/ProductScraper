# ⚠️ DEPRECATED: Coastal Scraper Apify Actor

> **This scraper has been migrated to the new modular system.** Please use the YAML configuration at `src/scrapers/configs/coastal.yaml` instead.

This Apify actor scrapes product information from the Coastal Pet website.

## Migration Status

- ✅ **Migration Complete**: This scraper has been successfully migrated to the new modular scraper system
- 📅 **Deprecation Timeline**: This legacy scraper will be removed in a future version
- 📖 **Migration Guide**: See `docs/SCRAPER_MIGRATION_GUIDE.md` for detailed migration instructions

## New Location

The new Coastal scraper configuration is located at:
```
src/scrapers/configs/coastal.yaml
```

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
