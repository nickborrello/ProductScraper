# ⚠️ DEPRECATED: Mazuri Scraper Apify Actor

> **This scraper has been migrated to the new modular system.** Please use the YAML configuration at `src/scrapers/configs/mazuri.yaml` instead.

This Apify actor scrapes product information from the Mazuri website.

## Migration Status

- ✅ **Migration Complete**: This scraper has been successfully migrated to the new modular scraper system
- 📅 **Deprecation Timeline**: This legacy scraper will be removed in a future version
- 📖 **Migration Guide**: See `docs/SCRAPER_MIGRATION_GUIDE.md` for detailed migration instructions

## New Location

The new Mazuri scraper configuration is located at:
```
src/scrapers/configs/mazuri.yaml
```

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
