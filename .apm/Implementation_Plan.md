# ProductScraper – Implementation Plan

**Memory Strategy:** [To be determined by Manager Agent]
**Last Modification:** [None]
**Project Overview:** This project overhauls the ProductScraper's orchestration system by replacing local scraper execution with a new `ApifyScraperClient`. The goal is to create a scalable, reliable, and maintainable system for distributed web scraping by properly leveraging the Apify API, while preserving all existing data flows and UI/CLI interfaces.

---
## Phase 1: API Client Implementation

### Task 1.1 – Design and Implement the Core `ApifyScraperClient` Class Structure │ Agent_APIClient
- **Objective:** To create the foundational file and class structure for the new `ApifyScraperClient`, ensuring it integrates with the existing settings management for secure API key access.
- **Output:** A new file `src/core/scrapers/apify_client.py` containing the `ApifyScraperClient` class skeleton, with a constructor, type-hinted attributes, and all necessary imports.
- **Guidance:** The class should be designed for asynchronous operations from the start. Use the existing `SettingsManager` to handle credentials; do not hardcode them.

- Create the new file `src/core/scrapers/apify_client.py`.
- Define the `ApifyScraperClient` class. Its `__init__` constructor should initialize an `httpx.AsyncClient` for making API calls.
- In the constructor, integrate the `SettingsManager` to securely fetch the Apify API token and base URL, storing them as private, type-hinted class attributes.
- Add all necessary top-level imports, including `httpx`, `typing`, `logging`, and the `SettingsManager` class.

### Task 1.2 – Implement the `scrape_skus` Method for Asynchronous Scraping │ Agent_APIClient
- **Objective:** To implement the primary `scrape_skus` method that starts a new scraping job on the Apify platform and waits for its completion.
- **Output:** A fully functional `async def scrape_skus` method within the `ApifyScraperClient` class.
- **Guidance:** Depends on: Task 1.1 Output. This method is the core of the client. It must handle the entire lifecycle of an Apify actor run. Pay attention to Apify API specifics for starting a run and fetching results. Consider potential race conditions or delays in a distributed system.

1. **Implement Method Signature:** Define the method as `async def scrape_skus(self, site: str, skus: list[str], progress_callback=None) -> list[dict]:`.
2. **Start Actor Run:** Construct the correct JSON input for the specified `site`'s actor and send a POST request to the Apify "run actor" endpoint to start the job.
3. **Implement Polling Logic:** Create an asynchronous polling loop that periodically calls the Apify "get run" endpoint to check the job's status (e.g., running, succeeded, failed).
4. **Handle Progress and Completion:** Within the loop, invoke the `progress_callback` with the current status if it's provided. Once the job status is "SUCCEEDED", fetch the full dataset from the Apify API and return it.

### Task 1.3 – Implement Job Management Methods (`get_job_status`, `cancel_job`) │ Agent_APIClient
- **Objective:** To provide essential job management utilities by implementing methods to check a job's status and cancel a running job.
- **Output:** Functional `get_job_status` and `cancel_job` async methods in the `ApifyScraperClient` class.
- **Guidance:** Depends on: Task 1.1 Output. These are straightforward helper methods that map directly to specific Apify API endpoints.

- Implement `async def get_job_status(self, job_id: str) -> dict:`. This method should call the Apify "get run" endpoint for the given `job_id` and return the complete, unmodified run record as a dictionary.
- Implement `async def cancel_job(self, job_id: str) -> bool:`. This method should call the Apify "abort run" endpoint for the given `job_id` and return `True` if the call is successful.

### Task 1.4 – Implement Data Transformation and Error Handling │ Agent_APIClient
- **Objective:** To make the client robust and ensure its output matches the application's existing data schema.
- **Output:** A set of custom exception classes and integrated error handling logic. The `scrape_skus` method will be updated to return data in the application's standard product dictionary format.
- **Guidance:** Depends on: Task 1.2 Output. Proper error handling is critical for a distributed system. The custom exceptions should provide clear context for debugging. Data transformation ensures the new client is a drop-in replacement.

1. **Define Custom Exceptions:** In `apify_client.py`, define three custom exception classes: `ApifyAuthError`, `ApifyTimeoutError`, and `ApifyJobError` to represent distinct failure modes.
2. **Implement Error Handling:** Wrap all `httpx` API calls in `try...except` blocks. Catch connection errors, timeouts, and non-2xx status codes, and raise the appropriate custom exception with a descriptive message.
3. **Implement Data Transformation:** In the `scrape_skus` method, after successfully fetching the results dataset from Apify, add logic to iterate through the raw JSON items and transform each one into the standard product dictionary format used elsewhere in the application.

### Task 1.5 – Create Unit Tests for the `ApifyScraperClient` │ Agent_Testing
- **Objective:** To verify the correctness and robustness of the `ApifyScraperClient` through comprehensive unit tests.
- **Output:** A new test file `tests/unit/test_apify_client.py` with a suite of tests covering success cases, failure modes, and job management functions.
- **Guidance:** Depends on: Task 1.4 Output by Agent_APIClient. Use `pytest-mock` to patch all `httpx` calls, ensuring tests run quickly and without actual network requests.

1. **Create Test File:** Create the new file `tests/unit/test_apify_client.py`.
2. **Test Success Path:** Write a test for the `scrape_skus` success case. Use `pytest-mock` to simulate the `httpx.AsyncClient`'s behavior, including starting a job, returning a "SUCCEEDED" status after a few polls, and providing a sample dataset.
3. **Test Failure Paths:** Write tests for various failure scenarios, such as the Apify API returning an error status code or a job timing out. Assert that the correct custom exception is raised in each case.
4. **Test Helper Methods:** Write simple tests for `get_job_status` and `cancel_job`, mocking their respective API calls and verifying the expected return values.

---
## Phase 2: Integration and Refactoring

### Task 2.1 – Refactor `master.py` to Use `ApifyScraperClient` │ Agent_Orchestration
- **Objective:** To replace the core scraping logic in `master.py` with calls to the new, robust `ApifyScraperClient`.
- **Output:** An updated `src/scrapers/master.py` file that no longer calls scrapers locally and instead uses the new client.
- **Guidance:** Depends on: Task 1.5 Output by Agent_Testing. This is the central goal of the overhaul. The refactoring must be a "drop-in" replacement, preserving the existing interface with the UI, especially the `progress_callback` signal.

1. **Import and Instantiate:** In `src/scrapers/master.py`, import the `ApifyScraperClient` and instantiate it within the main scraping workflow.
2. **Replace Scraping Logic:** Locate the code that currently invokes scraper functions directly and replace it with a single `await` call to `client.scrape_skus(...)`.
3. **Connect Progress Callback:** Ensure the existing `progress_callback` function is passed directly to the `scrape_skus` method so that UI updates continue to function as before.
4. **Update Error Handling:** Adapt the existing `try...except` block to catch the new, specific exceptions (e.g., `ApifyJobError`, `ApifyTimeoutError`) and handle them appropriately.

### Task 2.2 – Update Command-Line Scripts to Use `ApifyScraperClient` │ Agent_Orchestration
- **Objective:** To ensure standalone utility scripts also use the new centralized `ApifyScraperClient`, promoting code reuse and consistency.
- **Output:** An updated `src/utils/scraping/run_scraper.py` file that uses the new client.
- **Guidance:** Depends on: Task 1.5 Output by Agent_Testing. This task ensures all parts of the system adhere to the new architecture.

- In `src/utils/scraping/run_scraper.py`, import and instantiate the `ApifyScraperClient`.
- Replace any bespoke scraping logic in the script with a call to `client.scrape_skus(...)`, ensuring the script's command-line arguments are correctly passed to the client and its output is handled correctly.

---
## Phase 3: Testing and Validation

### Task 3.1 – Create Integration Tests for the End-to-End Scraping Workflow │ Agent_Testing
- **Objective:** To validate that the entire refactored workflow—from the orchestration logic in `master.py` to the (mocked) client—functions correctly and preserves the full data flow.
- **Output:** A new integration test file `tests/integration/test_apify_integration.py`.
- **Guidance:** Depends on: Task 2.1 Output by Agent_Orchestration. This test is critical for verifying that the refactoring was successful without breaking the larger application context.

1. **Create Test File:** Create the new file `tests/integration/test_apify_integration.py`.
2. **Patch the Client:** In a new test function, use `pytest-mock` to patch `ApifyScraperClient` where it's instantiated in `master.py`. Configure the mock instance to return a predefined sample product dictionary when `scrape_skus` is called.
3. **Execute Workflow:** Set up and run the `MasterScraper`'s main scraping method, just as the UI would.
4. **Assert Correctness:** Assert that the data returned by the method matches the sample data from the mock. Crucially, also assert that the `progress_callback` was called with expected values, confirming the UI hook remains intact.

### Task 3.2 – Run Full Test Suite and Fix Any Regressions │ Agent_Testing
- **Objective:** To perform a final quality check, ensuring the recent overhaul has not introduced any regressions in other parts of the application.
- **Output:** A successful `pytest` run with all existing and new tests passing.
- **Guidance:** Depends on: Task 3.1 Output. This is the final sign-off before the work can be considered complete.

1. **Execute Test Suite:** Run the full test suite via the command `python -m pytest tests/`.
2. **Diagnose Failures:** If any tests fail, carefully analyze the `pytest` error output to identify the failing test and the nature of the regression. Read the relevant application and test code to find the root cause.
3. **Fix and Repeat:** Apply code changes to fix the identified regressions. Re-run the full test suite and repeat the process until all tests pass.
