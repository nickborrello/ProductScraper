"""
ProductScraper Core Module
Provides core functionality for scraping, data processing, and platform integration.
"""

from .failure_classifier import FailureClassifier, FailureContext, FailureType
from .scraper_testing_client import ScraperTestingClient, TestingMode
from .scraper_testing_integration import ScraperIntegrationTester

__all__ = [
    "FailureClassifier",
    "FailureContext",
    "FailureType",
    "ScraperIntegrationTester",
    "ScraperTestingClient",
    "TestingMode",
]
