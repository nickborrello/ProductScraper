# ProductScraper Documentation

This documentation covers the ProductScraper project, which provides a modular, YAML-based web scraping framework with comprehensive anti-detection capabilities.

## Overview

The ProductScraper framework supports multiple scraping architectures:

### 🆕 **Modular YAML-Based System (Recommended)**
- **Declarative Configuration**: YAML-based scraper definitions
- **WorkflowExecutor**: Unified execution engine with anti-detection
- **Built-in Anti-Detection**: CAPTCHA handling, rate limiting, human simulation
- **Extensible Architecture**: Easy to add new scrapers and features

### ⚠️ **Legacy Apify Actor System (Deprecated)**
- **Monolithic Python Files**: Traditional scraper implementations
- **Apify Platform Integration**: Cloud-based execution
- **Limited Anti-Detection**: Basic rate limiting only

## Quick Start

### Using the New Modular System
```python
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

# Load scraper configuration
parser = YAMLParser()
config = parser.parse("src/scrapers/configs/amazon.yaml")

# Execute scraping workflow
executor = WorkflowExecutor(config, headless=True)
results = executor.execute_workflow()

print(results)
```

### Legacy System (Deprecated)
```bash
# Test all scrapers locally (deprecated)
python platform_test_scrapers.py --all

# Test specific scraper (deprecated)
python platform_test_scrapers.py --scraper amazon
```

## Documentation Sections

### New Modular System
- **[Migration Guide](SCRAPER_MIGRATION_GUIDE.md)** - Migrate from legacy to modular system
- **[Configuration Guide](SCRAPER_CONFIGURATION_GUIDE.md)** - YAML schema and examples
- **[Anti-Detection Guide](ANTI_DETECTION_GUIDE.md)** - Anti-detection modules and best practices
- **[Developer Guide](SCRAPER_DEVELOPER_GUIDE.md)** - Creating new scrapers and extending functionality

### Legacy System (Deprecated)
- [Testing Guide](TESTING_GUIDE.md) - Legacy testing procedures
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Legacy deployment procedures
- [Maintenance Guide](MAINTENANCE_GUIDE.md) - Legacy maintenance
- [API Integration](API_INTEGRATION.md) - Legacy platform API integration

## Architecture

### Modular System Components

- **YAMLParser**: Configuration parsing and validation
- **WorkflowExecutor**: Core execution engine with workflow management
- **AntiDetectionManager**: Comprehensive anti-detection capabilities
- **SelectorConfig**: Reusable data extraction definitions
- **ScraperConfig**: Complete scraper configuration model

### Anti-Detection Modules

- **CAPTCHA Detection**: Automatic CAPTCHA detection and handling
- **Rate Limiting**: Intelligent delays with exponential backoff
- **Human Behavior Simulation**: Realistic browsing patterns
- **Session Rotation**: Automatic browser session management
- **Blocking Detection**: Access denied page handling

### Legacy System Components (Deprecated)

- **ApifyPlatformClient**: Platform API interactions
- **PlatformTestingClient**: Legacy testing interface
- **ScraperValidator**: Data quality validation

## Configuration

### Modular System Configuration

Create YAML configuration files in `src/scrapers/configs/`:

```yaml
name: "my_scraper"
base_url: "https://www.example.com"
selectors:
  - name: "product_name"
    selector: "#product-title"
    attribute: "text"
workflows:
  - action: "navigate"
    params:
      url: "https://www.example.com/product/{sku}"
  - action: "extract"
    params:
      fields: ["product_name"]
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
```

### Legacy System Configuration (Deprecated)

Settings in `settings.json`:
```json
{
  "apify_api_token": "your-apify-api-token",
  "apify_base_url": "https://api.apify.com/v2",
  "testing_mode": "local"
}
```

## Available Scrapers

### Modular System Scrapers
- ✅ amazon - E-commerce product scraper
- ✅ central_pet - Pet supplies scraper
- ✅ coastal - Wholesale product scraper
- ✅ mazuri - Animal nutrition scraper
- ✅ orgill - Hardware wholesaler scraper
- ✅ petfoodex - Pet food exhibition scraper
- ✅ phillips - Agricultural products scraper

### Legacy System Scrapers (Deprecated)
- ⚠️ amazon (legacy)
- ⚠️ bradley (legacy)
- ⚠️ central_pet (legacy)
- ⚠️ coastal (legacy)
- ⚠️ mazuri (legacy)
- ⚠️ orgill (legacy)
- ⚠️ petfoodex (legacy)
- ⚠️ phillips (legacy)

## Migration Status

| Scraper | Modular System | Legacy System | Migration Status |
|---------|----------------|---------------|------------------|
| amazon | ✅ Available | ⚠️ Deprecated | Complete |
| central_pet | ✅ Available | ⚠️ Deprecated | Complete |
| coastal | ✅ Available | ⚠️ Deprecated | Complete |
| mazuri | ✅ Available | ⚠️ Deprecated | Complete |
| orgill | ✅ Available | ⚠️ Deprecated | Complete |
| petfoodex | ✅ Available | ⚠️ Deprecated | Complete |
| phillips | ✅ Available | ⚠️ Deprecated | Complete |

## Development Workflow

### Creating New Scrapers (Recommended)
1. Analyze target website structure
2. Create YAML configuration file
3. Test with WorkflowExecutor
4. Add comprehensive tests
5. Update documentation

### Extending Functionality
- Add custom workflow actions
- Create new anti-detection modules
- Extend selector resolution
- Implement custom validation

### Legacy Development (Deprecated)
1. Follow Apify actor structure
2. Add test data to fixtures
3. Test local and platform modes
4. Validate data quality

## Testing and Validation

### Modular System Testing
```bash
# Run modular scraper tests
python -m pytest tests/unit/test_workflow_executor.py
python -m pytest tests/integration/test_scraper_integration.py

# Test specific scraper
python test_migrated_scrapers.py --scraper amazon
```

### Legacy System Testing (Deprecated)
```bash
# Test legacy scrapers
python platform_test_scrapers.py --all
python platform_test_scrapers.py --scraper amazon --platform
```

### Data Quality Validation
- Field coverage analysis
- Data format validation
- Cross-reference verification
- Anti-detection effectiveness monitoring

## CI/CD Integration

### Automated Testing
GitHub Actions workflows provide:
- Unit and integration testing
- Data quality validation
- Performance monitoring
- Automated deployment

### Deployment Scripts
- `scripts/deploy_scrapers.py`: Deploy legacy scrapers (deprecated)
- `scripts/validate_deployment.py`: Post-deployment validation
- `scripts/rollback.py`: Rollback procedures

## Support and Migration

### Getting Help
1. Check the appropriate guide for your system
2. Review test output and validation results
3. Check scraper-specific error logs
4. Consult migration guide for transition questions

### Migration Assistance
- **[Migration Guide](SCRAPER_MIGRATION_GUIDE.md)**: Step-by-step migration instructions
- **Before/After Examples**: Code comparison for common patterns
- **Troubleshooting**: Common migration issues and solutions
- **Best Practices**: Recommended approaches for new development

## Contributing

### For Modular System
1. Follow YAML configuration standards
2. Add comprehensive unit tests
3. Update developer documentation
4. Test anti-detection integration
5. Validate data quality and performance

### For Legacy System (Deprecated)
⚠️ **New development should use the modular system**

When maintaining legacy scrapers:
1. Follow existing Apify actor structure
2. Add test data to `scraper_test_data.json`
3. Test both local and platform modes
4. Plan migration to modular system

## Roadmap

### Immediate Priorities
- Complete migration of all legacy scrapers
- Enhance anti-detection capabilities
- Improve documentation and examples
- Add performance monitoring

### Future Enhancements
- Machine learning-based selector discovery
- Advanced CAPTCHA solving integration
- Multi-threaded execution support
- Cloud-native deployment options
- API-based scraper management

---

**📋 Note**: The legacy Apify actor system is deprecated. All new development should use the modular YAML-based system. Existing legacy scrapers will continue to work but will not receive new features or security updates.