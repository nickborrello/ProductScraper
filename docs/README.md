# ProductScraper Testing Framework Documentation

This documentation covers the comprehensive testing framework for the ProductScraper project, which supports both local and platform testing modes for web scraping actors.

## Overview

The ProductScraper testing framework provides:

- **Unified Testing Interface**: Same API for local and platform testing modes
- **Comprehensive Validation**: Data quality scoring and field coverage analysis
- **CI/CD Integration**: Automated testing and deployment pipelines
- **Platform API Integration**: Direct interaction with Apify platform for production deployments

## Quick Start

### Local Testing
```bash
# Test all scrapers locally
python platform_test_scrapers.py --all

# Test specific scraper
python platform_test_scrapers.py --scraper amazon

# Test with custom SKUs
python platform_test_scrapers.py --scraper amazon --skus B07G5J5FYP B08N5WRWNW
```

### Platform Testing
```bash
# Test all scrapers on platform
python platform_test_scrapers.py --all --platform

# Test specific scraper on platform
python platform_test_scrapers.py --scraper amazon --platform
```

## Documentation Sections

- [Testing Guide](TESTING_GUIDE.md) - Detailed testing procedures and validation
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment procedures
- [Maintenance Guide](MAINTENANCE_GUIDE.md) - Ongoing maintenance and monitoring
- [API Integration](API_INTEGRATION.md) - Platform API integration details
- [CI/CD Pipelines](../.github/workflows/) - Automated testing and deployment workflows

## Architecture

### Core Components

- **ApifyPlatformClient**: Handles platform API interactions (datasets, actor runs, results)
- **PlatformTestingClient**: Unified interface for local/platform testing modes
- **PlatformScraperIntegrationTester**: Extended integration testing with validation
- **ScraperValidator**: Data quality validation and scoring

### Testing Modes

#### Local Mode
- Runs scrapers using local Apify simulation
- Fast iteration and debugging
- No API costs or rate limits
- Full control over execution environment

#### Platform Mode
- Runs scrapers on Apify platform
- Production-like environment
- Handles real-world conditions (rate limits, CAPTCHAs)
- Required for production deployments

## Configuration

### Settings Configuration

Create or update `settings.json`:

```json
{
  "apify_api_token": "your-apify-api-token",
  "apify_base_url": "https://api.apify.com/v2",
  "testing_mode": "local"
}
```

### Environment Variables

```bash
export APIFY_API_TOKEN=your-apify-api-token
export APIFY_BASE_URL=https://api.apify.com/v2
```

## Available Scrapers

The framework automatically discovers scrapers with proper Apify actor structure:

- amazon
- bradley
- central_pet
- coastal
- mazuri
- orgill
- petfoodex
- phillips

## Validation and Quality Assurance

### Data Quality Scoring
- Field coverage analysis
- Data format validation
- Cross-sell relationship verification
- Weight normalization checks

### Test Data
Test SKUs are defined in `tests/fixtures/scraper_test_data.json` for each scraper.

## CI/CD Integration

### Automated Testing
GitHub Actions workflows provide:
- Automated testing on pull requests
- Platform testing validation
- Data quality checks
- Deployment preparation

### Deployment Scripts
- `scripts/deploy_scrapers.py`: Deploy all scrapers to platform
- `scripts/validate_deployment.py`: Post-deployment validation
- `scripts/rollback.py`: Rollback procedures

## Support

For issues or questions:
1. Check the relevant guide in this documentation
2. Review test output and validation results
3. Check platform API status and authentication
4. Review scraper-specific error logs

## Contributing

When adding new scrapers:
1. Follow the Apify actor structure requirements
2. Add test data to `scraper_test_data.json`
3. Update documentation as needed
4. Test both local and platform modes
5. Validate data quality and field coverage