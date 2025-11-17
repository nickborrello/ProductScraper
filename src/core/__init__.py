"""
ProductScraper Core Module
Provides core functionality for scraping, data processing, and platform integration.
"""

from .platform_testing_client import PlatformTestingClient, TestingMode
from .platform_testing_integration import PlatformScraperIntegrationTester

__all__ = [
    'PlatformTestingClient',
    'TestingMode',
    'PlatformScraperIntegrationTester'
]