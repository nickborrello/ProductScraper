"""
Local Testing Client
Provides interface for local testing only.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestingMode(Enum):
    """Testing mode enumeration."""

    LOCAL = "local"


class PlatformTestingError(Exception):
    """Base exception for platform testing errors."""

    pass


class PlatformTestingAuthError(PlatformTestingError):
    """Authentication error."""

    pass


class PlatformTestingTimeoutError(PlatformTestingError):
    """Timeout error."""

    pass


class PlatformTestingJobError(PlatformTestingError):
    """Job execution error."""

    pass


class PlatformTestingClient:
    """
    Local testing client.
    Provides interface for local testing only.
    """

    def __init__(self, mode: TestingMode = TestingMode.LOCAL, **kwargs):
        """
        Initialize the testing client.

        Args:
            mode: Testing mode (only LOCAL supported)
            **kwargs: Additional arguments (ignored)
        """
        if mode != TestingMode.LOCAL:
            raise ValueError("Only LOCAL testing mode is supported")

        self.mode = mode

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

    async def run_scraper(
        self, scraper_name: str, skus: List[str], **kwargs
    ) -> Dict[str, Any]:
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
        self, scraper_name: str, skus: List[str], **kwargs
    ) -> Dict[str, Any]:
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
        from tests.integration.test_scraper_integration import \
            ScraperIntegrationTester

        tester = ScraperIntegrationTester()
        local_results = tester.run_scraper_locally(scraper_name, skus)

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

    def is_platform_mode(self) -> bool:
        """Check if running in platform mode."""
        return False

    def is_local_mode(self) -> bool:
        """Check if running in local mode."""
        return True
