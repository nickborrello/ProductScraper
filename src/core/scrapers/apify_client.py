import httpx
import typing
import logging
import asyncio
from src.core.settings_manager import SettingsManager


class ApifyAuthError(Exception):
    pass


class ApifyTimeoutError(Exception):
    pass


class ApifyJobError(Exception):
    pass


class ApifyScraperClient:
    def __init__(self):
        self._client: httpx.AsyncClient = httpx.AsyncClient()
        self._settings_manager = SettingsManager()
        self._api_token: str = self._settings_manager.get("apify_api_token")
        self._base_url: str = self._settings_manager.get("apify_base_url")

    async def scrape_skus(self, site: str, skus: list[str], progress_callback=None) -> list[dict]:
        actor_id = f"{site}-scraper"
        headers = {"Authorization": f"Bearer {self._api_token}"}
        
        # Start actor run
        run_url = f"{self._base_url}/acts/{actor_id}/runs"
        try:
            run_response = await self._client.post(run_url, headers=headers, json={"skus": skus})
        except httpx.TimeoutException:
            raise ApifyTimeoutError("Timeout during actor run start")
        
        if not run_response.is_success:
            if run_response.status_code in (401, 403):
                raise ApifyAuthError(f"Authentication failed: {run_response.status_code} - {run_response.text}")
            else:
                raise ApifyJobError(f"Failed to start actor run: {run_response.status_code} - {run_response.text}")
        
        run_data = run_response.json()
        run_id = run_data["data"]["id"]
        
        # Polling loop
        while True:
            status_url = f"{self._base_url}/actor-runs/{run_id}"
            try:
                status_response = await self._client.get(status_url, headers=headers)
            except httpx.TimeoutException:
                raise ApifyTimeoutError("Timeout during job status check")
            
            if not status_response.is_success:
                if status_response.status_code in (401, 403):
                    raise ApifyAuthError(f"Authentication failed: {status_response.status_code} - {status_response.text}")
                else:
                    raise ApifyJobError(f"Failed to get job status: {status_response.status_code} - {status_response.text}")
            
            status_data = status_response.json()
            status = status_data["data"]["status"]
            
            if progress_callback:
                progress_callback(status)
            
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "TIMED-OUT", "ABORTED"]:
                raise ApifyJobError(f"Scraping job failed with status: {status}")
            
            await asyncio.sleep(5)
        
        # Fetch dataset
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{self._base_url}/datasets/{dataset_id}/items"
        try:
            dataset_response = await self._client.get(dataset_url, headers=headers)
        except httpx.TimeoutException:
            raise ApifyTimeoutError("Timeout during dataset fetch")
        
        if not dataset_response.is_success:
            if dataset_response.status_code in (401, 403):
                raise ApifyAuthError(f"Authentication failed: {dataset_response.status_code} - {dataset_response.text}")
            else:
                raise ApifyJobError(f"Failed to fetch dataset: {dataset_response.status_code} - {dataset_response.text}")
        
        dataset_items = dataset_response.json()
        
        # Data transformation
        field_mapping = {
            'sku': 'SKU',
            'product_name': 'Name',
            'price': 'Price',
            'images': 'Images',
            'weight': 'Weight',
            'brand': 'Brand',
        }
        transformed_items = []
        for item in dataset_items:
            transformed_item = {}
            for scraper_field, app_field in field_mapping.items():
                if scraper_field in item:
                    transformed_item[app_field] = item[scraper_field]
            transformed_items.append(transformed_item)
        
        return transformed_items

    async def get_job_status(self, job_id: str) -> dict:
        headers = {"Authorization": f"Bearer {self._api_token}"}
        status_url = f"{self._base_url}/actor-runs/{job_id}"
        try:
            status_response = await self._client.get(status_url, headers=headers)
        except httpx.TimeoutException:
            raise ApifyTimeoutError("Timeout during job status check")
        
        if not status_response.is_success:
            if status_response.status_code in (401, 403):
                raise ApifyAuthError(f"Authentication failed: {status_response.status_code} - {status_response.text}")
            else:
                raise ApifyJobError(f"Failed to get job status: {status_response.status_code} - {status_response.text}")
        
        status_data = status_response.json()
        return status_data

    async def cancel_job(self, job_id: str) -> bool:
        headers = {"Authorization": f"Bearer {self._api_token}"}
        abort_url = f"{self._base_url}/actor-runs/{job_id}/abort"
        try:
            abort_response = await self._client.post(abort_url, headers=headers)
        except httpx.TimeoutException:
            raise ApifyTimeoutError("Timeout during job cancellation")
        
        if not abort_response.is_success:
            if abort_response.status_code in (401, 403):
                raise ApifyAuthError(f"Authentication failed: {abort_response.status_code} - {abort_response.text}")
            else:
                raise ApifyJobError(f"Failed to cancel job: {abort_response.status_code} - {abort_response.text}")
        
        abort_data = abort_response.json()
        status = abort_data["data"]["status"]
        if status in ["ABORTING", "ABORTED"]:
            return True
        return False