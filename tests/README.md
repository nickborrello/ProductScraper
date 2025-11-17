# Scraper Testing and Debugging System

This directory contains a comprehensive testing system for the ProductScraper project. The system ensures all scrapers work properly and output the correct data.

## Quick Start

```bash
# Test all scrapers
python platform_test_scrapers.py --all

# Test a specific scraper
python platform_test_scrapers.py --scraper amazon

# List available scrapers
python platform_test_scrapers.py --list

# Validate scraper structure
python platform_test_scrapers.py --validate amazon
```

## Directory Structure

```
tests/
├── fixtures/
│   ├── scraper_test_data.json    # Test SKUs and expected fields for each scraper
│   └── scraper_validator.py      # Data validation utilities
├── integration/
│   └── test_scraper_integration.py  # Integration tests that run scrapers locally
└── unit/
    └── test_scrapers.py          # Unit tests for scraper modules
```

## Testing Workflow

### 1. Structure Validation

Before running scrapers, validate that each scraper has the correct YAML configuration:

```bash
python platform_test_scrapers.py --validate <scraper_name>
```

This checks for:

- Required YAML configuration file (`<scraper_name>.yaml`)
- Proper scraper configuration structure

### 2. Individual Scraper Testing

Test a single scraper with its predefined test SKUs:

```bash
python platform_test_scrapers.py --scraper <scraper_name>
```

Or test with custom SKUs:

```bash
python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
```

### 3. Full Test Suite

Run comprehensive tests on all scrapers:

```bash
python platform_test_scrapers.py --all
```

This will:

- Test all 8 scrapers (amazon, bradley, central_pet, coastal, mazuri, petfoodex, phillips, orgill)
- Validate output data format and quality
- Generate a detailed report with success/failure rates
- Identify common issues across scrapers

## Validation Checks

The testing system validates:

### Data Format

- Required fields present (SKU, Name)
- No invalid values (N/A, null, empty strings)
- Proper data types

### Data Quality

- Field coverage percentages
- Weight units normalized to LB
- Image URLs are valid HTTP/HTTPS
- Price format validation

### Execution

- Scrapers run without errors
- Workflow execution completes successfully
- Timeout handling
- Browser compatibility

## Test Data

Each scraper has predefined test SKUs that are known to work:

| Scraper     | Test SKUs                          | Description               |
| ----------- | ---------------------------------- | ------------------------- |
| amazon      | B07G5J5FYP, B08N5WRWNW, B07VDG2ZT4 | Amazon products           |
| bradley     | 035585499741                       | Bradley Caldwell products |
| central_pet | CP001, CP002                       | Central Pet products      |
| coastal     | CO001, CO002                       | Coastal Pet products      |
| mazuri      | MZ001, MZ002                       | Mazuri products           |
| petfoodex   | PF001, PF002                       | Pet Food Experts products |
| phillips    | PH001, PH002                       | Phillips products         |
| orgill      | OR001, OR002                       | Orgill products           |

## Debugging

### Verbose Output

Get detailed output for debugging:

```bash
python platform_test_scrapers.py --scraper amazon --verbose
```

### Common Issues

1. **Structure Issues**: Run validation first

   ```bash
   python platform_test_scrapers.py --validate <scraper_name>
   ```

2. **Import Errors**: Check dependencies in `requirements.txt`

3. **Network Issues**: Scrapers may fail due to:

   - Website changes
   - Anti-bot measures
   - Network timeouts

4. **Data Format Issues**: Check validation errors for specific field problems

### Browser Debugging

For visual debugging, temporarily set `HEADLESS = False` in scraper code:

```python
HEADLESS = False  # Set to True for production
```

## Pre-Deployment Checklist

- [ ] All scrapers pass `python platform_test_scrapers.py --all`
- [ ] No validation errors in output data
- [ ] Data quality score > 80% for all scrapers
- [ ] All required fields populated for test SKUs
- [ ] Browser runs successfully in headless mode
- [ ] No sensitive information in logs
- [ ] Dependencies properly listed in requirements.txt

## Integration with CI/CD

The testing system can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Test Scrapers
  run: |
    python platform_test_scrapers.py --all
```

## Contributing

When adding new scrapers:

1. Add test data to `fixtures/scraper_test_data.json`
2. Create YAML configuration file in `src/scrapers/configs/`
3. Test locally before committing
4. Update this README if needed

## Troubleshooting

### Test Script Not Found

Make sure you're running from the project root:

```bash
cd /path/to/ProductScraper
python platform_test_scrapers.py --list
```

### Import Errors

Install test dependencies:

```bash
pip install -r requirements.txt
```

### Permission Issues

On Windows, you may need to run as administrator for browser automation.

### Timeout Issues

Increase timeout values in scraper code for slow-loading sites.