# Copilot Instructions for ProductScraper Repository

These instructions guide GitHub Copilot's behavior when working in this repository.

## General Guidelines

- Write concise, readable Python code with proper error handling
- Use descriptive variable names and add comments for complex logic
- Prefer modern Python features (f-strings, type hints, dataclasses)
- Follow PEP 8 style guidelines
- Handle exceptions appropriately in web scraping code
- Use logging instead of print statements for debugging
- Test on products that have all the needed fields filled in, like 035585499741

## Project-Specific Rules

- This tool is very powerful and has access to live data on the site. Be careful. This isn't a dev environment.
- When scraping websites, always include user-agent headers and respect robots.txt
- Store scraped data in pandas DataFrames for consistency
- Use Selenium with explicit waits to avoid flaky tests
- Save cookies and profiles to maintain session state
- Parse weights from product names and normalize to consistent units (LB)
- Ensure cross-sell relationships are properly saved to Excel output
- **Scraper Development**: When creating new scrapers, add `HEADLESS = True` (default) or `HEADLESS = False` at module level. Set to `False` only if the scraper requires visible browser for CAPTCHA solving, user interaction, or other visual elements.

## Code Patterns

- Use context managers for file operations and database connections
- Implement retry logic for network requests
- Validate data before saving to prevent corrupted outputs
- Separate scraping logic from data processing logic

## Database

- Our database uses SQLite and is managed with SQLAlchemy
- These are the columns:
  - id INTEGER PRIMARY KEY AUTOINCREMENT, // Auto-incrementing primary key
  - SKU TEXT UNIQUE, // Unique Stock Keeping Unit
  - Name TEXT, // Product name
  - Price TEXT, // Price
  - Images TEXT, // Comma-separated list of image URLs
  - Weight TEXT, // Product weight
  - Product_Field_16 TEXT, // Brand
  - Product_Field_11 TEXT, // Special Order
  - Product_Field_24 TEXT, // Category
  - Product_Field_25 TEXT, // Product Type
  - Product_On_Pages TEXT, // Pages where the product appears, separated by |
  - Product_Field_32 TEXT, // Product Cross Sells, separated by |
  - last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP // Timestamp of last update
  - ProductDisabled TEXT, // Indicates if the product is disabled (checked or uncheck)

## Agentic Project Management (APM)

- This project uses APM for AI-assisted project management and task tracking.
- Key resources for context and navigation:
  - `.apm/README.md`: Quick start guide and project overview.
  - `.apm/Memory/Memory_Root.md`: Current project state, architecture, priorities, and recent changes.
  - `.apm/guides/`: Detailed guides including setup, implementation planning, memory system, and task assignment.
  - `.apm/Implementation_Plan.md`: Active development tasks, progress tracking, and next steps.
- Always reference these files for project context, current state, and to avoid redundant work.
- Update memory files when making significant changes to maintain project awareness.
