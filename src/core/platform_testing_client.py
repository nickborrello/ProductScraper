"""
Platform Testing Integration Layer
Provides unified interface for local and platform testing modes.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from .apify_platform_client import (
    ApifyPlatformClient,
    ApifyPlatformError,
    ApifyPlatformAuthError,
    ApifyPlatformTimeoutError,
    ApifyPlatformJobError
)
from .local_apify import Actor as LocalActor


logger = logging.getLogger(__name__)


class TestingMode(Enum):
    """Testing mode enumeration."""
    LOCAL = "local"
    PLATFORM = "platform"


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
    Unified client for platform and local testing.
    Provides the same interface regardless of testing mode.
    """

    def __init__(self, mode: TestingMode = TestingMode.LOCAL, **kwargs):
        """
        Initialize the testing client.

        Args:
            mode: Testing mode (LOCAL or PLATFORM)
            **kwargs: Additional arguments for platform client
        """
        self.mode = mode
        self._platform_client: Optional[ApifyPlatformClient] = None
        self._local_client = None

        if mode == TestingMode.PLATFORM:
            self._platform_client = ApifyPlatformClient(**kwargs)
        elif mode == TestingMode.LOCAL:
            # Local client is initialized per run
            pass
        else:
            raise ValueError(f"Invalid testing mode: {mode}")

    async def __aenter__(self):
        """Enter async context."""
        if self._platform_client:
            await self._platform_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._platform_client:
            await self._platform_client.__aexit__(exc_type, exc_val, exc_tb)

    async def run_scraper(self, scraper_name: str, skus: List[str], **kwargs) -> Dict[str, Any]:
        """
        Run a scraper with the specified SKUs.

        Args:
            scraper_name: Name of the scraper to run
            skus: List of SKUs to scrape
            **kwargs: Additional arguments

        Returns:
            Dict with run results
        """
        if self.mode == TestingMode.PLATFORM:
            return await self._run_platform_scraper(scraper_name, skus, **kwargs)
        else:
            return await self._run_local_scraper(scraper_name, skus, **kwargs)

    async def _run_platform_scraper(self, scraper_name: str, skus: List[str], **kwargs) -> Dict[str, Any]:
        """
        Run scraper on Apify platform.

        Args:
            scraper_name: Name of the scraper
            skus: List of SKUs
            **kwargs: Additional arguments

        Returns:
            Dict with run results
        """
        if not self._platform_client:
            raise RuntimeError("Platform client not initialized")

        results = {
            "scraper": scraper_name,
            "skus": skus,
            "mode": "platform",
            "success": False,
            "products": [],
            "run_id": None,
            "dataset_id": None,
            "execution_time": 0,
            "errors": []
        }

        try:
            # Prepare input data
            input_data = {"skus": skus}

            # Start actor run
            actor_id = f"{scraper_name}-scraper"
            run_id = await self._platform_client.run_actor(actor_id, input_data)
            results["run_id"] = run_id

            # Wait for completion
            import time
            start_time = time.time()
            run_data = await self._platform_client.wait_for_run_completion(run_id)
            results["execution_time"] = time.time() - start_time

            # Get results
            dataset_id = run_data.get("defaultDatasetId")
            if dataset_id:
                results["dataset_id"] = dataset_id
                products = await self._platform_client.get_run_dataset(run_id)
                results["products"] = products
                results["success"] = True
            else:
                results["errors"].append("No dataset found in run results")

        except ApifyPlatformAuthError as e:
            results["errors"].append(f"Authentication failed: {e}")
            raise PlatformTestingAuthError(str(e)) from e
        except ApifyPlatformTimeoutError as e:
            results["errors"].append(f"Timeout: {e}")
            raise PlatformTestingTimeoutError(str(e)) from e
        except ApifyPlatformJobError as e:
            results["errors"].append(f"Job failed: {e}")
            raise PlatformTestingJobError(str(e)) from e
        except ApifyPlatformError as e:
            results["errors"].append(f"Platform error: {e}")
            raise PlatformTestingError(str(e)) from e
        except Exception as e:
            results["errors"].append(f"Unexpected error: {e}")
            raise PlatformTestingError(f"Unexpected error: {e}") from e

        return results

    async def _run_local_scraper(self, scraper_name: str, skus: List[str], **kwargs) -> Dict[str, Any]:
        """
        Run scraper locally using local Apify simulation.

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
            "errors": local_results.get("errors", [])
        }

        return results

    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get status of a platform run.

        Args:
            run_id: Run ID

        Returns:
            Status data
        """
        if self.mode != TestingMode.PLATFORM or not self._platform_client:
            raise RuntimeError("Status checking only available in platform mode")

        return await self._platform_client.get_run_status(run_id)

    async def abort_run(self, run_id: str) -> bool:
        """
        Abort a platform run.

        Args:
            run_id: Run ID to abort

        Returns:
            True if aborted successfully
        """
        if self.mode != TestingMode.PLATFORM or not self._platform_client:
            raise RuntimeError("Run abortion only available in platform mode")

        return await self._platform_client.abort_run(run_id)

    async def upload_dataset(self, name: str, data: List[Dict[str, Any]]) -> str:
        """
        Upload data to a platform dataset.

        Args:
            name: Dataset name
            data: Data to upload

        Returns:
            Dataset ID
        """
        if self.mode != TestingMode.PLATFORM or not self._platform_client:
            raise RuntimeError("Dataset upload only available in platform mode")

        return await self._platform_client.upload_dataset(name, data)

    async def list_datasets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List platform datasets.

        Args:
            limit: Maximum number of datasets

        Returns:
            List of datasets
        """
        if self.mode != TestingMode.PLATFORM or not self._platform_client:
            raise RuntimeError("Dataset listing only available in platform mode")

        return await self._platform_client.list_datasets(limit)

    @property
    def testing_mode(self) -> TestingMode:
        """Get current testing mode."""
        return self.mode

    def is_platform_mode(self) -> bool:
        """Check if running in platform mode."""
        return self.mode == TestingMode.PLATFORM

    def is_local_mode(self) -> bool:
        """Check if running in local mode."""
        return self.mode == TestingMode.LOCAL