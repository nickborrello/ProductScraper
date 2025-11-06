# Task 1.2: Refactor Core Logic from `main.py` - Completion

**Status:** Completed

**Summary:** The `main.py` file was successfully refactored. The core functionalities (scraping, discontinued check, XML processing, etc.) were encapsulated into individual functions, decoupling them from the CLI menu. The `main_cli()` function now orchestrates calls to these functions, preserving the original command-line functionality while making the core logic accessible for the GUI to import and use.
