"""
Local Actor implementation for Apify SDK.
Provides a context manager that mimics Apify Actor for local development and testing.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from .dataset import LocalDataset
from .key_value_store import LocalKeyValueStore
from .request_queue import LocalRequestQueue


class LocalActor:
    """
    Local Actor implementation that mimics Apify Actor for local testing.
    Provides the same interface as Apify Actor but uses local storage.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize local actor.

        Args:
            storage_dir: Base storage directory (defaults to ./storage)
        """
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), "storage")
        self._dataset: Optional[LocalDataset] = None
        self._key_value_store: Optional[LocalKeyValueStore] = None
        self._request_queue: Optional[LocalRequestQueue] = None
        self._input: Optional[Dict[str, Any]] = None

    async def __aenter__(self):
        """Enter the actor context."""
        # Initialize storage components
        self._dataset = LocalDataset(dataset_id="default", storage_dir=self.storage_dir)
        self._key_value_store = LocalKeyValueStore(store_id="default", storage_dir=self.storage_dir)
        self._request_queue = LocalRequestQueue(queue_id="default", storage_dir=self.storage_dir)

        # Load input from environment or file
        await self._load_input()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the actor context."""
        # Cleanup if needed
        pass

    async def _load_input(self) -> None:
        """Load input data for the actor."""
        # Try environment variable first (APIFY_INPUT)
        input_json = os.getenv('APIFY_INPUT')
        if input_json:
            try:
                self._input = json.loads(input_json)
                return
            except json.JSONDecodeError:
                pass

        # Try input.json file
        input_file = os.path.join(os.getcwd(), "input.json")
        if os.path.exists(input_file):
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    self._input = json.load(f)
                return
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Default empty input
        self._input = {}

    async def get_input(self) -> Optional[Dict[str, Any]]:
        """
        Get actor input.
        Mimics Apify Actor.get_input().

        Returns:
            Input data or None
        """
        return self._input

    async def push_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """
        Push data to the default dataset.
        Mimics Apify Actor.push_data().

        Args:
            data: Data to push
        """
        if self._dataset is None:
            raise RuntimeError("Actor context not entered")
        self._dataset.push_data(data)

    def get_dataset(self, dataset_id: str = "default") -> LocalDataset:
        """
        Get a dataset instance.

        Args:
            dataset_id: Dataset identifier

        Returns:
            LocalDataset instance
        """
        return LocalDataset(dataset_id, self.storage_dir)

    def get_key_value_store(self, store_id: str = "default") -> LocalKeyValueStore:
        """
        Get a key-value store instance.

        Args:
            store_id: Store identifier

        Returns:
            LocalKeyValueStore instance
        """
        return LocalKeyValueStore(store_id, self.storage_dir)

    def get_request_queue(self, queue_id: str = "default") -> LocalRequestQueue:
        """
        Get a request queue instance.

        Args:
            queue_id: Queue identifier

        Returns:
            LocalRequestQueue instance
        """
        return LocalRequestQueue(queue_id, self.storage_dir)

    def log(self, message: str, level: str = "info") -> None:
        """
        Log a message.
        Mimics Apify Actor.log.

        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        print(f"[{level.upper()}] {message}")

    @property
    def dataset(self) -> LocalDataset:
        """Get the default dataset."""
        if self._dataset is None:
            raise RuntimeError("Actor context not entered")
        return self._dataset

    @property
    def key_value_store(self) -> LocalKeyValueStore:
        """Get the default key-value store."""
        if self._key_value_store is None:
            raise RuntimeError("Actor context not entered")
        return self._key_value_store

    @property
    def request_queue(self) -> LocalRequestQueue:
        """Get the default request queue."""
        if self._request_queue is None:
            raise RuntimeError("Actor context not entered")
        return self._request_queue


# Global instance for convenience (similar to Apify Actor)
_actor_instance: Optional[LocalActor] = None


class _ActorLogger:
    """Simple logger for Actor.log"""

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def warning(self, message: str) -> None:
        print(f"[WARNING] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    def debug(self, message: str) -> None:
        print(f"[DEBUG] {message}")


class _ActorContextManager:
    """Async context manager for Actor usage."""

    def __init__(self):
        self._instance: Optional[LocalActor] = None
        self.log = _ActorLogger()

    async def get_input(self) -> Optional[Dict[str, Any]]:
        """Get actor input. Available even before entering context."""
        # Load input similar to LocalActor
        import os
        import json

        # Try environment variable first (APIFY_INPUT)
        input_json = os.getenv('APIFY_INPUT')
        if input_json:
            try:
                return json.loads(input_json)
            except json.JSONDecodeError:
                pass

        # Try input.json file
        input_file = os.path.join(os.getcwd(), "input.json")
        if os.path.exists(input_file):
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Default empty input
        return {}

    async def push_data(self, data) -> None:
        """Push data to dataset. Delegates to instance if in context."""
        if self._instance is None:
            raise RuntimeError("Actor context not entered")
        await self._instance.push_data(data)

    async def __aenter__(self):
        global _actor_instance
        self._instance = LocalActor()
        _actor_instance = self._instance
        await self._instance.__aenter__()
        return self._instance

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global _actor_instance
        if self._instance:
            await self._instance.__aexit__(exc_type, exc_val, exc_tb)
        _actor_instance = None


# Create a global instance that can be used as "async with Actor:"
Actor = _ActorContextManager()