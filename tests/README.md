# Testing

This directory contains the test suite for the ProductScraper project, organized using pytest.

## Setup

Install development dependencies:

```bash
pip install -r tests/requirements-dev.txt
```

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration and fixtures
├── requirements-dev.txt           # Development dependencies
├── fixtures/
│   └── scraper_validator.py       # Test fixtures and validation utilities
├── integration/                   # End-to-end and integration tests
│   ├── __init__.py
│   ├── classification_e2e.py
│   ├── test_data_quality.py
│   ├── test_local_llm_integration.py
│   ├── test_scraper_integration.py
│   └── test_scraper_validation.py
└── unit/                         # Unit tests
    ├── __init__.py
    ├── README.md
    ├── test_classification.py
    ├── test_core_logic.py
    ├── test_data_quality_scorer.py
    ├── test_local_llm_classifier.py
    ├── test_local_storage.py
    ├── test_performance.py
    ├── test_scraper_fields_clean.py
    ├── test_scraper_fields.py
    ├── test_selector_storage.py
    └── test_workflow_executor.py
```

## Running Tests

Run all tests:

```bash
pytest
```

Run unit tests only:

```bash
pytest tests/unit/
```

Run integration tests only:

```bash
pytest tests/integration/
```

Run a specific test file:

```bash
pytest tests/unit/test_classification.py
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with coverage:

```bash
pytest --cov=src
```

## Test Categories

### Unit Tests

Located in `tests/unit/`, these test individual components and functions in isolation.

### Integration Tests

Located in `tests/integration/`, these test interactions between components and end-to-end workflows.

### Fixtures

Located in `tests/fixtures/`, these provide reusable test data and utilities.

## Contributing

When adding new tests:

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Use fixtures from `tests/fixtures/` when possible
4. Follow pytest conventions
5. Update this README if the structure changes