"""
Apify Platform API Client
Handles authentication, dataset uploads, actor runs, and result retrieval for platform testing.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
import httpx

from src.core.settings_manager import settings


logger = logging.getLogger(__name__)

# Validate httpx import for debugging
try:
    logger.debug(f"httpx version {httpx.__version__} imported successfully")
except AttributeError:
    logger.debug("httpx imported successfully (version not available)")


class ApifyPlatformError(Exception):
    """Base exception for Apify platform API errors."""
    pass


class ApifyPlatformAuthError(ApifyPlatformError):
    """Authentication error."""
    pass


class ApifyPlatformTimeoutError(ApifyPlatformError):
    """Timeout error."""
    pass


class ApifyPlatformJobError(ApifyPlatformError):
    """Job execution error."""
    pass


class ApifyPlatformClient:
    """
    Client for interacting with the Apify platform API.
    Provides methods for dataset management, actor runs, and result retrieval.
    """

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the platform API client.

        Args:
            api_token: Apify API token (defaults to settings)
            base_url: Apify API base URL (defaults to settings)
        """
        self.api_token = api_token or settings.get("apify_api_token")
        self.base_url = base_url or settings.get("apify_base_url", "https://api.apify.com/v2")

        if not self.api_token:
            raise ApifyPlatformAuthError("Apify API token not configured. Please set 'apify_api_token' in settings.")

        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {"Authorization": f"Bearer {self.api_token}"}

    async def __aenter__(self):
        """Enter async context."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    def _ensure_client(self):
        """Ensure HTTP client is available."""
        if self._client is None:
            raise RuntimeError("Platform client must be used within async context manager")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated request to the Apify API.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional request parameters

        Returns:
            JSON response data

        Raises:
            ApifyPlatformAuthError: On authentication failures
            ApifyPlatformTimeoutError: On timeout
            ApifyPlatformError: On other API errors
        """
        self._ensure_client()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault('headers', {}).update(self._headers)

        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.TimeoutException:
            raise ApifyPlatformTimeoutError(f"Request timeout for {method} {endpoint}")
        except httpx.RequestError as e:
            raise ApifyPlatformError(f"Request failed: {e}")

        if response.status_code in (401, 403):
            raise ApifyPlatformAuthError(f"Authentication failed: {response.status_code} - {response.text}")
        elif not response.is_success:
            raise ApifyPlatformError(f"API request failed: {response.status_code} - {response.text}")

        try:
            return response.json()
        except json.JSONDecodeError:
            raise ApifyPlatformError(f"Invalid JSON response: {response.text}")

    async def upload_dataset(self, dataset_name: str, data: List[Dict[str, Any]]) -> str:
        """
        Upload data to a new dataset on the platform.

        Args:
            dataset_name: Name for the new dataset
            data: List of data items to upload

        Returns:
            Dataset ID of the created dataset
        """
        logger.info(f"Uploading {len(data)} items to dataset '{dataset_name}'")

        # Create dataset
        create_data = {"name": dataset_name}
        create_response = await self._make_request("POST", "datasets", json=create_data)
        dataset_id = create_response["data"]["id"]

        # Upload data in batches
        batch_size = 1000
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            await self._make_request("POST", f"datasets/{dataset_id}/items", json=batch)

        logger.info(f"Successfully uploaded dataset '{dataset_name}' with ID: {dataset_id}")
        return dataset_id

    async def run_actor(self, actor_id: str, input_data: Dict[str, Any]) -> str:
        """
        Start an actor run on the platform.

        Args:
            actor_id: ID of the actor to run
            input_data: Input data for the actor

        Returns:
            Run ID of the started actor run
        """
        logger.info(f"Starting actor run for '{actor_id}'")

        run_data = {"input": input_data}
        run_response = await self._make_request("POST", f"acts/{actor_id}/runs", json=run_data)
        run_id = run_response["data"]["id"]

        logger.info(f"Started actor run with ID: {run_id}")
        return run_id

    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of an actor run.

        Args:
            run_id: ID of the actor run

        Returns:
            Run status data
        """
        status_response = await self._make_request("GET", f"actor-runs/{run_id}")
        return status_response["data"]

    async def wait_for_run_completion(self, run_id: str, poll_interval: int = 5, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for an actor run to complete.

        Args:
            run_id: ID of the actor run
            poll_interval: Seconds between status checks
            timeout: Maximum time to wait in seconds

        Returns:
            Final run status data

        Raises:
            ApifyPlatformTimeoutError: If run doesn't complete within timeout
            ApifyPlatformJobError: If run fails
        """
        logger.info(f"Waiting for run {run_id} to complete (timeout: {timeout}s)")

        start_time = asyncio.get_event_loop().time()
        while True:
            status_data = await self.get_run_status(run_id)
            status = status_data["status"]

            logger.debug(f"Run {run_id} status: {status}")

            if status == "SUCCEEDED":
                logger.info(f"Run {run_id} completed successfully")
                return status_data
            elif status in ["FAILED", "TIMED-OUT", "ABORTED"]:
                raise ApifyPlatformJobError(f"Actor run failed with status: {status}")

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise ApifyPlatformTimeoutError(f"Run {run_id} timed out after {timeout} seconds")

            await asyncio.sleep(poll_interval)

    async def get_run_dataset(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get the dataset items from a completed actor run.

        Args:
            run_id: ID of the completed actor run

        Returns:
            List of dataset items
        """
        # Get run details to find dataset ID
        run_data = await self.get_run_status(run_id)
        dataset_id = run_data.get("defaultDatasetId")

        if not dataset_id:
            raise ApifyPlatformError(f"No dataset found for run {run_id}")

        # Fetch dataset items - Apify returns items directly as a list
        dataset_items = await self._make_request("GET", f"datasets/{dataset_id}/items")
        return dataset_items if isinstance(dataset_items, list) else []

    async def abort_run(self, run_id: str) -> bool:
        """
        Abort a running actor run.

        Args:
            run_id: ID of the actor run to abort

        Returns:
            True if successfully aborted
        """
        try:
            abort_response = await self._make_request("POST", f"actor-runs/{run_id}/abort")
            status = abort_response["data"]["status"]
            return status in ["ABORTING", "ABORTED"]
        except ApifyPlatformError:
            return False

    async def list_datasets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List user's datasets.

        Args:
            limit: Maximum number of datasets to return

        Returns:
            List of dataset information
        """
        params = {"limit": limit}
        response = await self._make_request("GET", "datasets", params=params)
        return response.get("data", {}).get("items", [])

    async def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset.

        Args:
            dataset_id: ID of the dataset to delete

        Returns:
            True if successfully deleted
        """
        try:
            await self._make_request("DELETE", f"datasets/{dataset_id}")
            return True
        except ApifyPlatformError:
            return False