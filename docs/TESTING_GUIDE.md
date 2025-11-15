# Testing Guide

This guide provides detailed procedures for testing ProductScraper scrapers in both local and platform modes.

## Table of Contents

- [Local Testing](#local-testing)
- [Platform Testing](#platform-testing)
- [Validation and Quality Assurance](#validation-and-quality-assurance)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)
- [Test Data Management](#test-data-management)

## Local Testing

Local testing runs scrapers using simulated Apify environment without platform costs or rate limits.

### Prerequisites

1. **Python Environment**: Python 3.8+ with required dependencies
2. **Test Data**: Valid test SKUs in `tests/fixtures/scraper_test_data.json`
3. **Scraper Structure**: Proper Apify actor directory structure

### Basic Commands

```bash
# List available scrapers
python platform_test_scrapers.py --list

# Validate scraper structure
python platform_test_scrapers.py --validate amazon

# Test single scraper
python platform_test_scrapers.py --scraper amazon

# Test with custom SKUs
python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW

# Test all scrapers
python platform_test_scrapers.py --all

# Verbose output
python platform_test_scrapers.py --scraper amazon --verbose
```

### Local Testing Workflow

1. **Structure Validation**
   ```bash
   python platform_test_scrapers.py --validate <scraper_name>
   ```
   Ensures scraper has required files and directories.

2. **Individual Testing**
   ```bash
   python platform_test_scrapers.py --scraper <scraper_name>
   ```
   Runs scraper and validates output data.

3. **Comprehensive Testing**
   ```bash
   python platform_test_scrapers.py --all
   ```
   Tests all scrapers and provides summary report.

### Local Test Output

```
============================================================
TESTING SCRAPER: AMAZON (LOCAL MODE)
SKUs: ['B07G5J5FYP']
============================================================

📊 TEST SUMMARY: amazon (local)
✅ Execution: SUCCESS
   Products found: 1
🔍 Validation: 1/1 products valid
   Data Quality Score: 95.0
   Field Coverage:
     ✅ Name: 100.0%
     ✅ Price: 100.0%
     ✅ Images: 100.0%
     ✅ Weight: 100.0%
     ✅ Brand: 100.0%
     ✅ Category: 100.0%
     ✅ Product Type: 100.0%
✅ OVERALL: PASSED
```

## Platform Testing

Platform testing runs scrapers on the Apify platform in production-like conditions.

### Prerequisites

1. **Apify Account**: Valid Apify account with API token
2. **API Token**: Configured in settings or environment
3. **Credits**: Sufficient Apify platform credits
4. **Deployed Actors**: Scrapers must be deployed to platform

### Configuration

#### Settings Configuration
```json
{
  "apify_api_token": "your-apify-api-token-here",
  "apify_base_url": "https://api.apify.com/v2"
}
```

#### Environment Variables
```bash
export APIFY_API_TOKEN=your-apify-api-token-here
export APIFY_BASE_URL=https://api.apify.com/v2
```

### Platform Testing Commands

```bash
# Test single scraper on platform
python platform_test_scrapers.py --scraper amazon --platform

# Test all scrapers on platform
python platform_test_scrapers.py --all --platform

# Test with custom SKUs on platform
python platform_test_scrapers.py --scraper amazon --platform --skus B07G5J5FYP B08N5WRWNW
```

### Platform Testing Workflow

1. **Authentication Check**
   - Verifies API token configuration
   - Tests platform connectivity

2. **Actor Deployment Check**
   - Confirms scrapers are deployed as actors
   - Validates actor IDs and versions

3. **Execution**
   - Starts platform actor runs
   - Monitors execution progress
   - Retrieves results from datasets

4. **Validation**
   - Validates data quality and format
   - Compares with expected field coverage

### Platform Test Output

```
============================================================
TESTING SCRAPER: AMAZON (PLATFORM MODE)
SKUs: ['B07G5J5FYP']
============================================================

📊 TEST SUMMARY: amazon (platform)
✅ Execution: SUCCESS
   Products found: 1
   Run ID: abc123def456
   Dataset ID: def789ghi012
🔍 Validation: 1/1 products valid
   Data Quality Score: 95.0
   Field Coverage:
     ✅ Name: 100.0%
     ✅ Price: 100.0%
     ✅ Images: 100.0%
     ✅ Weight: 100.0%
     ✅ Brand: 100.0%
     ✅ Category: 100.0%
     ✅ Product Type: 100.0%
✅ OVERALL: PASSED
```

## Validation and Quality Assurance

### Data Quality Metrics

The framework validates several quality aspects:

- **Field Coverage**: Percentage of required fields populated
- **Data Format**: Correct data types and formats
- **Cross-sell Relationships**: Proper pipe-separated format
- **Weight Normalization**: Consistent LB units
- **Image URLs**: Valid HTTP/HTTPS URLs

### Quality Score Calculation

```
Data Quality Score = (Field Coverage % + Format Score + Relationship Score) / 3
```

- **Field Coverage**: Average percentage of populated fields
- **Format Score**: 100 if all formats valid, 0 if any invalid
- **Relationship Score**: 100 if cross-sell format correct, 0 if invalid

### Validation Rules

#### Required Fields
- SKU (unique identifier)
- Name (product name)
- Price (numeric format)
- Images (comma-separated URLs)
- Weight (normalized to LB)
- Brand
- Category
- Product Type

#### Field Format Validation
- **Price**: Numeric values only
- **Images**: Valid HTTP/HTTPS URLs, comma-separated
- **Weight**: Numeric with LB unit
- **Cross-sell**: Pipe-separated SKUs

### Validation Output Example

```
🔍 Validation: 1/1 products valid
   Data Quality Score: 95.0
   Field Coverage:
     ✅ Name: 100.0%
     ✅ Price: 100.0%
     ✅ Images: 100.0%
     ✅ Weight: 100.0%
     ✅ Brand: 100.0%
     ✅ Category: 100.0%
     ✅ Product Type: 100.0%
   Errors: 0
   Warnings: 1
     - Weight not in LB units (found KG)
```

## Debugging and Troubleshooting

### Common Issues

#### Local Mode Issues

**Scraper Structure Errors**
```
❌ Scraper structure has issues. Check the failed items above.
```
- Verify all required files exist
- Check file permissions
- Validate JSON schema files

**Import Errors**
```
ModuleNotFoundError: No module named 'src.core.apify_platform_client'
```
- Install dependencies: `pip install -r requirements.txt`
- Check Python path configuration

**Data Validation Failures**
```
❌ OVERALL: FAILED
   Errors: 2
     - Missing required field: Name
     - Invalid price format: "N/A"
```
- Check scraper output format
- Verify test data quality
- Review scraper parsing logic

#### Platform Mode Issues

**Authentication Errors**
```
❌ ERROR: Apify API token not configured
```
- Set API token in settings.json or environment
- Verify token validity

**Actor Not Found**
```
ApifyPlatformError: Actor 'amazon-scraper' not found
```
- Deploy scraper to platform first
- Check actor name matches exactly

**Timeout Errors**
```
ApifyPlatformTimeoutError: Run timed out after 300 seconds
```
- Increase timeout in settings
- Check scraper performance
- Review network connectivity

**Rate Limiting**
```
ApifyPlatformError: Rate limit exceeded
```
- Wait before retrying
- Reduce concurrent requests
- Upgrade Apify plan

### Debug Commands

```bash
# Verbose output for detailed logs
python platform_test_scrapers.py --scraper amazon --verbose

# Test with specific SKUs for targeted debugging
python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP --verbose

# Validate structure only
python platform_test_scrapers.py --validate amazon
```

### Log Analysis

**Execution Logs**
- Check for scraper-specific errors
- Review network request failures
- Analyze parsing exceptions

**Validation Logs**
- Identify missing or invalid fields
- Review data format issues
- Check cross-sell relationship problems

## Test Data Management

### Test Data Structure

Test data is stored in `tests/fixtures/scraper_test_data.json`:

```json
{
  "amazon": {
    "test_skus": ["B07G5J5FYP", "B08N5WRWNW"],
    "expected_fields": ["Name", "Price", "Images", "Weight"],
    "validation_rules": {
      "price_format": "numeric",
      "weight_unit": "LB"
    }
  }
}
```

### Adding Test Data

1. **Identify Test SKUs**
   - Choose products with complete field data
   - Prefer products that exist across retailers
   - Include edge cases (missing data, special characters)

2. **Update Test Configuration**
   ```json
   {
     "new_scraper": {
       "test_skus": ["SKU001", "SKU002"],
       "expected_fields": ["Name", "Price", "Images"],
       "validation_rules": {}
     }
   }
   ```

3. **Validate Test Data**
   ```bash
   python platform_test_scrapers.py --scraper new_scraper --validate
   ```

### Test Data Best Practices

- **Real Data**: Use actual product SKUs that return data
- **Complete Coverage**: Include products with all required fields
- **Edge Cases**: Test with missing data, special characters, long descriptions
- **Consistency**: Maintain same test SKUs across environments
- **Updates**: Regularly update test data as products change

## Performance Optimization

### Local Testing Performance
- **Fast Iteration**: No network delays or API costs
- **Parallel Testing**: Test multiple scrapers simultaneously
- **Debugging**: Full access to local environment

### Platform Testing Performance
- **Real Conditions**: Test under production constraints
- **Scalability**: Validate performance at scale
- **Cost Monitoring**: Track API usage and costs

### Optimization Tips

1. **Batch Testing**: Use `--all` flag for comprehensive testing
2. **Selective Testing**: Test individual scrapers during development
3. **Parallel Execution**: Run tests in CI/CD pipelines
4. **Caching**: Cache test results for faster re-runs
5. **Monitoring**: Track test execution times and success rates