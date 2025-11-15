"""
Local dataset implementation for Apify SDK.
Provides file-based storage that mimics platform dataset operations.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class LocalDataset:
    """
    Local dataset implementation that stores data to files.
    Mimics Apify dataset API for local development and testing.
    """

    def __init__(self, dataset_id: str = "default", storage_dir: Optional[str] = None):
        """
        Initialize local dataset.

        Args:
            dataset_id: Dataset identifier (used as directory name)
            storage_dir: Base storage directory (defaults to ./storage/datasets)
        """
        if storage_dir is None:
            # Default to storage/datasets relative to current working directory
            storage_dir = os.path.join(os.getcwd(), "storage", "datasets")

        self.dataset_id = dataset_id
        self.storage_dir = Path(storage_dir) / dataset_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for faster access
        self._cache: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Load existing data from files into memory cache."""
        self._cache = []
        if self.storage_dir.exists():
            for json_file in self.storage_dir.glob("*.json"):
                if json_file.name.startswith("__"):  # Skip metadata files
                    continue
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._cache.extend(data)
                        else:
                            self._cache.append(data)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue

    def _save_item(self, item: Dict[str, Any]) -> None:
        """Save a single item to a JSON file."""
        item_id = str(uuid.uuid4())
        filename = f"{item_id}.json"
        filepath = self.storage_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)

    def push_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """
        Push data to the dataset.
        Mimics Apify Actor.push_data() method.

        Args:
            data: Single item or list of items to push
        """
        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise ValueError("Data must be a dict or list of dicts")

        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Each item must be a dict")
            self._cache.append(item)
            self._save_item(item)

    def get_data(self, offset: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get data from the dataset.

        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of dataset items
        """
        if limit is None:
            return self._cache[offset:]
        return self._cache[offset:offset + limit]

    def get_info(self) -> Dict[str, Any]:
        """
        Get dataset information.

        Returns:
            Dataset metadata
        """
        return {
            "id": self.dataset_id,
            "name": self.dataset_id,
            "itemCount": len(self._cache),
            "cleanItemCount": len(self._cache),
            "storageDir": str(self.storage_dir)
        }

    def drop(self) -> None:
        """Delete all data in the dataset."""
        import shutil
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache = []

    def __len__(self) -> int:
        """Return the number of items in the dataset."""
        return len(self._cache)

    def __iter__(self):
        """Iterate over dataset items."""
        return iter(self._cache)