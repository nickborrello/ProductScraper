# Gemini Instructions

## Project Overview: ProductScraper
This is a modular web scraping application with a modern PyQt6 UI ("Meridian") and a robust scraping engine managed by `uv`.

### Key Directories
- `src/ui/meridian/`: The desktop GUI (Launchpad, Pulse, Results).
- `src/scrapers/`: Scraper definitions (YAML configs) and logic.
- `src/core/`: Browser automation and core scraping engine.
- `.github/agents/`: Specialized agent definitions.
- `results/`: Output data.

## Workflow Standards

### 1. Code Quality & Safety
- **Formatting:** Always run `ruff format .` before committing.
- **Linting:** Always run `uv run ruff check src/ tests/ --fix` before committing.
- **Testing:** 
  - Run specific scraper tests: `python scripts/test_scrapers.py --scrapers <name>`
  - Run unit tests: `pytest tests/unit`
- **Commits:** Write semantic commit messages. Verify with `git status` after committing.

### 2. Agent Utilization
Use the specialized agents for complex tasks to maintain focus and quality:
- **UI/Frontend:** Use `Meridian UI Architect` for any changes in `src/ui/`.
- **Scraping Logic:** Use `New Scraper` or `Scraper Repair` for `src/scrapers/`.
- **Infrastructure:** Use `Stealth & Infrastructure` for Docker, browser profiles, or anti-bot issues.
- **Data:** Use `Data Analyst` for schema validation and result processing.
- **Orchestration:** Use `Scraper Testing` to run bulk validations.

### 3. Development Context
- **Context7 & DevTools:** Use these MCP servers when debugging live pages or requiring external documentation.
- **Memory:** Update this file or the `save_memory` tool if a new architectural decision is made that needs to be persisted.

## Common Commands Reference
```bash
# Run the App
python src/main.py

# Test a specific scraper (Headless)
python scripts/test_scrapers.py --scrapers amazon

# Test a specific scraper (Headed/Visible for debugging)
python scripts/test_scrapers.py --scrapers amazon --headed

# Run Type Checks
uv run mypy src/

# Install Dependencies
uv sync
```

## Active Context (Dynamic)
- **Current Focus:** Optimizing agent workflows and ensuring robust scraping infrastructure.
- **Recent Changes:** Added Meridian UI, integrated Scraper Repair agent, created specialized agents.
