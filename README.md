# ProductScraper

A comprehensive product data management and scraping platform built with Python. This application scrapes product information from multiple e-commerce sites, manages product databases, and provides both CLI and GUI interfaces with advanced testing capabilities.

<!-- Trigger CI -->

## Features

### 🔍 Multi-Site Scraping

- **8 Active Scrapers**: Amazon, Bradley Caldwell, Central Pet, Coastal, Orgill, PetFoodEx, Phillips, and more
- **YAML Configuration**: Flexible scraper configuration with CSS selectors and workflows
- **Local Testing**: Comprehensive testing framework with quality validation
- **Automated Data Extraction**: Intelligent parsing of product information with quality scoring
- **Data Normalization**: Consistent formatting across different sources with >85% quality threshold

### 💾 Database Management

- **SQLite Database**: Local storage with SQLAlchemy ORM
- **ShopSite Integration**: XML import/export capabilities with publish automation
- **Product Classification**: Interactive UI with LLM-powered categorization

### 🧪 Advanced Testing Framework

- **Local Testing**: Comprehensive scraper validation with quality scoring
- **Data Quality Scoring**: Comprehensive validation with completeness, accuracy, and consistency metrics
- **Performance Monitoring**: <5 min execution time with <500MB memory usage
- **CI/CD Integration**: Automated testing pipelines

### 🖥️ Enhanced User Interfaces

- **Modern GUI**: Real-time progress updates, cancellation support, and async threading
- **Command Line Interface**: Full-featured CLI with comprehensive local testing
- **Batch Processing**: Handle large datasets efficiently with progress tracking
- **Status Monitoring**: Live execution metrics (elapsed time, processed count, ETA)

## Installation

### Prerequisites

- Python 3.11
- PyQt6 (for GUI components)

### Setup

```bash
# Clone the repository
git clone https://github.com/nickborrello/ProductScraper.git
cd ProductScraper

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment configuration
cp .env.example .env
# Edit .env with your actual credentials
```

## Usage

### Desktop Application (Recommended)

The ProductScraper features a modern, professional desktop application with enhanced capabilities:

```bash
# Launch the GUI application
python src/main.py --run gui
```

**New Features:**

- 🎨 Modern interface with real-time progress updates and cancellation support
- 📊 Live execution metrics (elapsed time, processed count, current operation, ETA)
- 📋 Enhanced log viewer with async operation handling
- ⚡ Responsive threading for long-running scraper operations
- 💾 Progress tracking with graceful cancellation

**Available Operations:**

- **Scraping Operations**: Start scraping with progress monitoring
- **Database Management**: Refresh from XML, download XML, view/edit products
- **Testing Framework**: Run comprehensive tests with quality validation and performance monitoring

### Command-Line Interface

For automation and advanced usage:

```bash
# Run scraper with progress tracking
python src/main.py --run scraper --file path/to/your/excel_file.xlsx

# Run comprehensive tests
pytest

# Run scraper integration tests
python scripts/run_scraper_tests.py --all
```

### Testing Framework

The project uses a comprehensive pytest-based testing framework with unit, integration, and performance tests:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_data_quality_scorer.py

# Run tests with coverage
pytest --cov=src

# Run tests with verbose output
pytest -v
```

**Scraper Testing:**

```bash
# Test specific scraper using CLI script
python scripts/run_scraper_tests.py --scraper amazon

# Test all scrapers
python scripts/run_scraper_tests.py --all

# List available scrapers
python scripts/run_scraper_tests.py --list
```

**Testing Features:**

- **Unit Tests**: Individual component testing with comprehensive coverage
- **Integration Tests**: End-to-end scraper validation with real browser execution
- **Data Quality Scoring**: >85% threshold validation for data completeness and accuracy
- **Performance Monitoring**: Ensures <5 min execution with <500MB memory usage
- **CI/CD Integration**: Automated testing in GitHub Actions workflows
- **Headless/Local Modes**: Flexible testing environments for development and CI

## Project Structure

```
ProductScraper/
├── src/                    # Main source code
│   ├── main.py            # Main entry point
│   ├── core/              # Business logic and APIs
│   │   ├── data_quality_scorer.py      # Quality scoring algorithms
│   │   ├── scraper_testing_client.py  # Local testing interface
│   │   └── classification/             # Product classification
│   ├── scrapers/          # YAML-based scrapers
│   │   ├── configs/       # Scraper configurations
│   │   └── main.py        # Scraping orchestrator
│   ├── ui/                # Enhanced GUI components
│   │   ├── main_window.py # Async threading and progress updates
│   │   └── ...
│   └── utils/             # Utility functions
├── tests/                 # Comprehensive test suite
│   ├── unit/             # Unit tests with quality validation
│   ├── integration/      # SDK integration tests
│   └── fixtures/         # Test data and quality scoring
├── docs/                  # Complete documentation
│   ├── TESTING_GUIDE.md  # Testing procedures
│   ├── DEPLOYMENT_GUIDE.md # Production deployment
│   ├── MAINTENANCE_GUIDE.md # Ongoing maintenance
│   └── API_INTEGRATION.md # Platform API details
├── scripts/               # Utility scripts
├── .github/workflows/    # CI/CD pipelines
│   ├── ci-testing.yml    # Automated testing
│   ├── cd-deployment.yml # Deployment pipeline
│   └── platform-testing.yml # Platform validation
└── requirements.txt      # Python dependencies
```

## Configuration

### Environment Variables

**Required for Scrapers:**
```env
PETFOOD_USERNAME=your_username
PETFOOD_PASSWORD=your_password
PHILLIPS_USERNAME=your_username
PHILLIPS_PASSWORD=your_password
ORGILL_USERNAME=your_username
ORGILL_PASSWORD=your_password
```

**Required for ShopSite Integration:**
```env
SHOPSITE_CLIENT_ID=your_client_id
SHOPSITE_SECRET_KEY=your_secret_key
SHOPSITE_AUTHORIZATION_CODE=your_auth_code
SHOPSITE_AUTH_URL=https://yourstore.shopsite.com/xml/
```


**Optional for LLM Classification:**
```env
OPENROUTER_API_KEY=your_openrouter_api_key
OLLAMA_MODEL=llama3
```


## Safety & Best Practices

⚠️ **Important**: This tool accesses live e-commerce data

- **Test Locally First**: Always use local testing before production use
- **Quality Thresholds**: Ensure >85% data quality scores before production use
- **Rate Limiting**: Respect website terms and robots.txt files
- **Environment Variables**: Never commit credentials to version control

## Development

### Adding New Scrapers

1. Create new YAML configuration in `src/scrapers/configs/`
2. Define selectors and workflows for data extraction
3. Add comprehensive unit tests with quality validation
4. Update testing framework integration
5. Test locally before production use

### Code Quality

- Use type hints and comprehensive docstrings
- Follow PEP 8 with modern Python patterns
- Implement proper async/await error handling
- Write tests with >85% quality validation
- Use YAML configuration for scraper definitions

## Contributing

1. Follow the established YAML configuration patterns
2. Test locally with quality validation
3. Update documentation for new features
4. Ensure CI/CD pipelines pass
5. Create comprehensive test coverage

## License

This project is private and proprietary. All rights reserved.

## Support

For questions or issues, please create an issue in this repository or refer to the documentation in the `docs/` directory.
