"""
ProductScraper Core Module
Provides core functionality for scraping, data processing, and platform integration.
"""

from .scraper_testing_client import ScraperTestingClient, TestingMode
from .scraper_testing_integration import ScraperIntegrationTester
from .failure_classifier import FailureClassifier, FailureType, FailureContext

__all__ = [
    "ScraperTestingClient",
    "TestingMode",
    "ScraperIntegrationTester",
    "FailureClassifier",
    "FailureType",
    "FailureContext",
]
