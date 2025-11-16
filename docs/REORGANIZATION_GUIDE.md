# ProductScraper Project Reorganization Guide

This guide outlines the desired final project structure and provides step-by-step instructions for completing the reorganization of the ProductScraper codebase.

## 🎯 Desired Final Structure

```
ProductManager/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── database_import.py    # ShopSite import logic
│   │   ├── database_refresh.py   # XML to DB processing
│   │   ├── database_queries.py   # DB query functions
│   │   ├── database_validation.py # Final DB checks
│   │   ├── database_verification.py # DB verification
│   │   ├── field_mapping.py      # Field mapping logic
│   │   └── classification/       # Product classification
│   │       ├── __init__.py
│   │       └── classification_ui.py
│   ├── scrapers/                 # Individual scraper modules
│   │   ├── __init__.py
│   │   ├── amazon.py
│   │   ├── central_pet.py
│   │   ├── phillips.py
│   │   └── master.py
│   ├── ui/                       # User interface components
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── product_viewer.py
│   │   ├── product_editor.py
│   │   └── components/           # Reusable UI components
│   ├── utils/                    # Organized utilities
│   │   ├── __init__.py
│   │   ├── scraping/             # Scraping-specific utilities
│   │   │   ├── __init__.py
│   │   │   ├── scraping.py       # General scraping functions
│   │   │   └── browser.py        # Browser utilities
│   │   ├── images/               # Image processing utilities
│   │   │   ├── __init__.py
│   │   │   ├── processing.py
│   │   │   └── download.py
│   │   ├── file/                 # File operations
│   │   │   ├── __init__.py
│   │   │   └── excel.py
│   │   └── general/              # General utilities
│   │       ├── __init__.py
│   │       ├── display.py        # Display functions
│   │       └── helpers.py
│   └── config/                   # Configuration management
│       ├── __init__.py
│       ├── shopsite_constants.py
│       └── shopsite_pages.py
├── scripts/                      # Executable scripts
│   ├── run_scraper.py           # CLI entry point
│   ├── run_gui.py               # GUI entry point
│   ├── check_dataset.py         # Dataset analysis
│   └── classify_excel.py        # Excel classification
├── tests/                       # All tests consolidated
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_scrapers.py
│   │   ├── test_utils.py
│   │   └── test_database.py
│   ├── integration/
│   │   └── test_full_workflow.py
│   └── fixtures/                # Test data
├── data/                        # Data files (gitignored)
│   ├── input/                   # Input files
│   ├── output/                  # Generated outputs
│   ├── databases/               # SQLite databases
│   ├── exports/                 # Exported data
│   ├── spreadsheets/            # Excel files
│   └── browser_profiles/        # Browser profiles
├── docs/                        # Documentation
│   ├── README.md
│   ├── API.md
│   └── setup.md
├── .github/
│   └── copilot-instructions.md
├── requirements.txt
├── pyproject.toml               # Modern Python packaging
├── .gitignore
├── .env.example                # Environment template
└── REORGANIZATION_GUIDE.md     # This file
```

## 📋 Remaining Files to Move

Based on the current project state, these files still need to be moved:

### From inventory/ → src/core/

- `inventory/field_mapping.py` → `src/core/field_mapping.py`
- `inventory/final_db_check.py` → `src/core/database_validation.py`
- `inventory/verify_db.py` → `src/core/database_verification.py`

### From inventory/classify/ → src/core/classification/

- `inventory/classify/classification_ui.py` → `src/core/classification/classification_ui.py`

### From inventory/constants/ → src/config/

- `inventory/constants/shopsite_constants.py` → `src/config/shopsite_constants.py`
- `inventory/constants/shopsite_pages.py` → `src/config/shopsite_pages.py`

### Data Files → data/

- `inventory/data/*.xml` → `data/databases/`
- `inventory/exports/` → `data/exports/`

### Other Remaining Files

- Any remaining `.py` files at root level → appropriate `src/` subfolder
- `scrapers/input/`, `scrapers/output/`, `scrapers/images/` → `data/`
- `browser_profiles/`, `selenium_profiles/`, `scrapers/browser_profiles/` → `data/browser_profiles/`

## 🔧 Step-by-Step Instructions

### 1. Create Missing Directories

```bash
mkdir -p src/core/classification
mkdir -p src/config
mkdir -p data/databases data/exports data/browser_profiles
mkdir -p tests/unit tests/integration tests/fixtures
mkdir -p docs
```

### 2. Move Files in Batches

**Batch 1: Core Database Files**

```bash
mv inventory/field_mapping.py src/core/
mv inventory/final_db_check.py src/core/database_validation.py
mv inventory/verify_db.py src/core/database_verification.py
```

**Batch 2: Classification**

```bash
mv inventory/classify/classification_ui.py src/core/classification/
```

**Batch 3: Configuration**

```bash
mv inventory/constants/shopsite_constants.py src/config/
mv inventory/constants/shopsite_pages.py src/config/
```

**Batch 4: Data Files**

```bash
mv inventory/data/*.xml data/databases/
mv inventory/exports/* data/exports/ 2>/dev/null || true
```

### 3. Update Import Statements

After moving files, update imports in all affected files. Common patterns:

**Old → New**

- `from inventory.field_mapping import ...` → `from src.core.field_mapping import ...`
- `from inventory.classify.classification_ui import ...` → `from src.core.classification.classification_ui import ...`
- `from inventory.constants.shopsite_constants import ...` → `from src.config.shopsite_constants import ...`
- `from util.scrape_display import ...` → `from src.utils.general.display import ...`
- `from scrapers.master import ...` → `from src.scrapers.master import ...`

### 4. Create **init**.py Files

Ensure all new directories have `__init__.py` files:

```bash
touch src/__init__.py
touch src/core/__init__.py
touch src/core/classification/__init__.py
touch src/config/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

### 5. Update Entry Points

Modify `scripts/run_scraper.py` and `scripts/run_gui.py` to import from new locations:

- Change imports from `main.py` functions to the appropriate `src.` modules
- Update any hardcoded paths

### 6. Clean Up

```bash
# Remove empty directories
rmdir inventory/classify inventory/constants inventory/data inventory/exports 2>/dev/null || true
rmdir inventory 2>/dev/null || true

# Remove any remaining scattered files
# Check for and move any leftover .py files from root
```

### 7. Test the Reorganization

```bash
# Test imports
python -c "import src.core.field_mapping; print('Core imports work')"

# Test GUI
python scripts/run_gui.py

# Test CLI
python scripts/run_scraper.py --help
```

## ⚠️ Important Notes

- **Backup First**: Create a git commit or backup before major moves
- **Update Imports Carefully**: Use find/replace or IDE refactoring tools
- **Test Incrementally**: Move files in small batches and test after each
- **Git Ignore**: Ensure `data/` and large files are in `.gitignore`
- **Dependencies**: Update `requirements.txt` if needed
- **Documentation**: Move relevant docs to `docs/` folder

## 🎯 Benefits of This Structure

1. **Clear Separation**: Code, data, tests properly separated
2. **Scalable**: Easy to add new features without clutter
3. **Importable**: Proper package structure
4. **Maintainable**: Related code grouped together
5. **Professional**: Follows Python best practices

## 📞 Need Help?

If you encounter issues during reorganization:

1. Check this guide for the correct destination
2. Verify import paths are updated
3. Test small changes incrementally
4. Use `python -m py_compile file.py` to check syntax

This reorganization will transform the project into a professional, maintainable codebase. Take it one step at a time! 🚀
