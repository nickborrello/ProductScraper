# ProductScraper Documentation

This documentation covers the ProductScraper project, which provides a modular, YAML-based web scraping framework with comprehensive anti-detection capabilities.

## Overview

The ProductScraper framework provides a modular, YAML-based web scraping system with comprehensive anti-detection capabilities.

### 🆕 **Modular YAML-Based System**
- **Declarative Configuration**: YAML-based scraper definitions
- **WorkflowExecutor**: Unified execution engine with anti-detection
- **Built-in Anti-Detection**: CAPTCHA handling, rate limiting, human simulation
- **Extensible Architecture**: Easy to add new scrapers and features

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


## Documentation Sections

### New Modular System
- **[Migration Guide](SCRAPER_MIGRATION_GUIDE.md)** - Migrate from legacy to modular system
- **[Configuration Guide](SCRAPER_CONFIGURATION_GUIDE.md)** - YAML schema and examples
- **[Anti-Detection Guide](ANTI_DETECTION_GUIDE.md)** - Anti-detection modules and best practices
- **[Developer Guide](SCRAPER_DEVELOPER_GUIDE.md)** - Creating new scrapers and extending functionality


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


## Available Scrapers

### Modular System Scrapers
- ✅ amazon - E-commerce product scraper
- ✅ central_pet - Pet supplies scraper
- ✅ coastal - Wholesale product scraper
- ✅ mazuri - Animal nutrition scraper
- ✅ orgill - Hardware wholesaler scraper
- ✅ petfoodex - Pet food exhibition scraper
- ✅ phillips - Agricultural products scraper


## Available Scrapers

| Scraper | Status | Description |
|---------|--------|-------------|
| amazon | ✅ Available | E-commerce product scraper |
| central_pet | ✅ Available | Pet supplies scraper |
| coastal | ✅ Available | Wholesale product scraper |
| mazuri | ✅ Available | Animal nutrition scraper |
| orgill | ✅ Available | Hardware wholesaler scraper |
| petfoodex | ✅ Available | Pet food exhibition scraper |
| phillips | ✅ Available | Agricultural products scraper |

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


## Testing and Validation

### Modular System Testing
```bash
# Run modular scraper tests
python -m pytest tests/unit/test_workflow_executor.py
python -m pytest tests/integration/test_scraper_integration.py

# Test specific scraper
python test_migrated_scrapers.py --scraper amazon
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

### Utility Scripts
- Various utility scripts in `scripts/` directory

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
