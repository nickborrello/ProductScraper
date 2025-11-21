"""
Scraper Testing Client
Provides interface for local scraper testing only.
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TestingMode(Enum):
    """Testing mode enumeration."""

    LOCAL = "local"


class ScraperTestingError(Exception):
    """Base exception for scraper testing errors."""

    pass


class ScraperTestingAuthError(ScraperTestingError):
    """Authentication error."""

    pass


class ScraperTestingTimeoutError(ScraperTestingError):
    """Timeout error."""

    pass


class ScraperTestingJobError(ScraperTestingError):
    """Job execution error."""

    pass


class ScraperTestingClient:
    """
    Local scraper testing client.
    Provides interface for local scraper testing only.
    """

    def __init__(self, mode: TestingMode = TestingMode.LOCAL, headless: bool = True, **kwargs):
        """
        Initialize the testing client.

        Args:
            mode: Testing mode (only LOCAL supported)
            headless: Whether to run browser in headless mode
            **kwargs: Additional arguments (ignored)
        """
        if mode != TestingMode.LOCAL:
            raise ValueError("Only LOCAL testing mode is supported")

        self.mode = mode
        self.headless = headless

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

    async def run_scraper(self, scraper_name: str, skus: list[str], **kwargs) -> dict[str, Any]:
        """
        Run a scraper locally with the specified SKUs.

        Args:
            scraper_name: Name of the scraper to run
            skus: List of SKUs to scrape
            **kwargs: Additional arguments

        Returns:
            Dict with run results
        """
        return await self._run_local_scraper(scraper_name, skus, **kwargs)

    async def _run_local_scraper(
        self, scraper_name: str, skus: list[str], **kwargs
    ) -> dict[str, Any]:
        """
        Run scraper locally.

        Args:
            scraper_name: Name of the scraper
            skus: List of SKUs
            **kwargs: Additional arguments

        Returns:
            Dict with run results
        """
        # Import the integration tester for local runs
        from tests.integration.test_scraper_integration import ScraperIntegrationTester

        tester = ScraperIntegrationTester()
        local_results = tester.run_scraper_locally(scraper_name, skus, headless=self.headless)

        # Convert to unified format
        results = {
            "scraper": scraper_name,
            "skus": skus,
            "mode": "local",
            "success": local_results.get("success", False),
            "products": local_results.get("products", []),
            "run_id": None,
            "dataset_id": None,
            "execution_time": local_results.get("execution_time", 0),
            "errors": local_results.get("errors", []),
        }

        return results

    @property
    def testing_mode(self) -> TestingMode:
        """Get current testing mode."""
        return self.mode

    def is_local_mode(self) -> bool:
        """Check if running in local mode."""
        return True
