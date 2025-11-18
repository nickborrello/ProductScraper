# ⚠️ DEPRECATED: Phillips Scraper Apify Actor

> **This scraper has been migrated to the new modular system.** Please use the YAML configuration at `src/scrapers/configs/phillips.yaml` instead.

This Apify actor scrapes product information from the Phillips Pet website.

## Migration Status

- ✅ **Migration Complete**: This scraper has been successfully migrated to the new modular scraper system
- 📅 **Deprecation Timeline**: This legacy scraper will be removed in a future version
- 📖 **Migration Guide**: See `docs/SCRAPER_MIGRATION_GUIDE.md` for detailed migration instructions

## New Location

The new Phillips scraper configuration is located at:
```
src/scrapers/configs/phillips.yaml
```

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
