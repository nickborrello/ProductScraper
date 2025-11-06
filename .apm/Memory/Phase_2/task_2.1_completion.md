# Task 2.1: Integrate File Selection and the "Start Scraping" Feature - Completion

**Status:** Completed

**Summary:** The `gui.py` file was updated to implement the core user workflow for starting a scraping process. The "Start Scraping" button is now connected to a slot that opens a file dialog, instantiates a `Worker` thread with the `run_scraping` function, and connects the worker's signals to update the progress bar and log area. This task successfully integrates the UI, the background worker, and the refactored core logic.
