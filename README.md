# ProductScraper

A comprehensive product data management and scraping tool built with Python. This application scrapes product information from multiple e-commerce sites, manages product databases, and provides both CLI and GUI interfaces for data processing.

## Features

### 🔍 Multi-Site Scraping

- **8 Active Scrapers**: Amazon, Bradley Caldwell, Central Pet, Coastal, Orgill, PetFoodEx, Phillips, and more
- **Automated Data Extraction**: Intelligent parsing of product information
- **Data Normalization**: Consistent formatting across different sources
- **Excel Integration**: Smart column mapping for input/output

### 💾 Database Management

- **SQLite Database**: Local storage with SQLAlchemy ORM
- **ShopSite Integration**: XML import/export capabilities
- **Product Classification**: Interactive UI for categorizing products
- **Cross-sell Relationships**: Advanced product relationship mapping

### 🧪 Testing Framework

- **Unit Tests**: Comprehensive test coverage for all scrapers
- **Integration Tests**: Real network call validation
- **Field Validation**: Granular data quality checks

### 🖥️ User Interfaces

- **Command Line Interface**: Full-featured CLI for automation
- **Graphical User Interface**: User-friendly desktop application
- **Batch Processing**: Handle large datasets efficiently

## Installation

### Prerequisites

- Python 3.8+
- PyQt6 (for GUI components)

### Setup

```bash
# Clone the repository
git clone https://github.com/nickborrello/ProductScraper.git
cd ProductScraper

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for APM - optional)
npm install

# Set up environment configuration
cp .env.example .env
# Edit .env with your actual credentials
```

## Usage

### Desktop Application (Recommended)

The ProductScraper now features a modern, professional desktop application interface:

```bash
# Launch the GUI application
python src/main.py --run gui
```

**Features:**

- 🎨 Modern, intuitive interface with organized action cards
- 📊 Real-time status updates and database statistics
- 📋 Professional log viewer with color-coded messages
- ⚡ All operations accessible through menu bar and buttons
- 💾 Progress tracking for all operations

**Available Operations:**

- **Scraping Operations**: Start scraping
- **Database Management**: Refresh from XML, download XML, view/edit products, database statistics
- **Tools**: Classify Excel files, run automated tests

### Command-Line Interface

For automation and scripting, you can use the command-line interface:

```bash
# Run the scraper
python src/main.py --run scraper --file path/to/your/excel_file.xlsx
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/unit/test_scrapers.py

# Run integration tests (makes real network calls)
python -m pytest tests/integration/ -v

# Test with coverage
python -m pytest --cov=src
```

## Project Structure

```
ProductScraper/
├── src/                    # Main source code
│   ├── main.py            # Main entry point for the application
│   ├── core/              # Business logic and database
│   │   ├── classification/ # Product classification system
│   │   └── database_import.py
│   ├── scrapers/          # Web scraping modules
│   │   ├── amazon/
│   │   ├── bradley/
│   │   ├── ...
│   │   └── main.py        # Main scraping orchestrator
│   ├── ui/                # User interface components
│   │   ├── main_window.py # Main application window
│   │   ├── product_editor.py
│   │   └── ...
│   └── utils/             # Utility functions
│       ├── tests.py       # Test utilities
│       └── ...
├── tests/                 # Test suites
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test data
├── data/                  # Data files and databases
│   ├── databases/        # SQLite databases
│   ├── input/            # Input Excel files
│   ├── output/           # Generated output files
│   ├── images/           # Downloaded product images
│   └── exports/          # Export files
├── docs/                  # Documentation
└── requirements.txt      # Python dependencies
```

## Configuration

The application uses environment-based configuration. Sensitive settings can be configured through environment variables or a `.env` file:

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials and settings
3. The application will automatically load variables from `.env`

### Required Environment Variables

```env
# Scraper Credentials (required for respective scrapers)
PETFOOD_USERNAME=your_username
PETFOOD_PASSWORD=your_password
PHILLIPS_USERNAME=your_username
PHILLIPS_PASSWORD=your_password
ORGILL_USERNAME=your_username
ORGILL_PASSWORD=your_password

# ShopSite API Credentials (required for database sync)
SHOPSITE_CLIENT_ID=your_client_id
SHOPSITE_SECRET_KEY=your_secret_key
SHOPSITE_AUTHORIZATION_CODE=your_auth_code
SHOPSITE_AUTH_URL=https://yourstore.shopsite.com/xml/
```

### Optional Environment Variables

```env
# Database settings
DATABASE_PATH=data/databases/products.db

# Scraping settings
DEBUG=false
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30

# LLM Classification (optional - improves product categorization)
OPENROUTER_API_KEY=your_openrouter_api_key
OLLAMA_MODEL=llama3
```

### LLM Classification Setup

The application supports AI-powered product classification using either cloud APIs or local models:

#### OpenRouter API (Cloud)

1. Sign up at [OpenRouter.ai](https://openrouter.ai)
2. Get your API key
3. Set `OPENROUTER_API_KEY` in your environment or `settings.json`

#### Local Ollama (Free, no API key required)

1. Install Ollama: `winget install Ollama.Ollama`
2. Pull a model: `ollama pull llama3` (or `mistral`, `codellama`, etc.)
3. The application will automatically detect and use local models
4. Configure model in `settings.json`: `"ollama_model": "llama3"`

**Note**: Local models provide privacy and no API costs, but require more system resources.

## Safety & Best Practices

⚠️ **Important**: This tool accesses live e-commerce data

- **Test First**: Always test with small batches using SKU `035585499741`
- **Rate Limiting**: Respect website terms of service and robots.txt
- **Data Privacy**: Handle customer data responsibly
- **Environment Variables**: Never commit credentials to version control
- **Browser Profiles**: Use separate profiles for different sites to avoid conflicts

## Development

### Adding New Scrapers

1. Create a new scraper in `src/scrapers/`
2. Follow the existing pattern with proper error handling
3. Add unit tests in `tests/unit/`
4. Update the scraper discovery in `src/scrapers/master.py`

### Code Quality

- Use type hints and docstrings
- Follow PEP 8 style guidelines
- Add comprehensive error handling
- Write tests for new functionality

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is private and proprietary. All rights reserved.

## Support

For questions or issues, please create an issue in this repository.
