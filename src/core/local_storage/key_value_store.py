"""
Local key-value store implementation for Apify SDK.
Provides file-based storage that mimics platform key-value store operations.
"""

import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class LocalKeyValueStore:
    """
    Local key-value store implementation that stores data to files.
    Mimics Apify key-value store API for local development and testing.
    """

    def __init__(self, store_id: str = "default", storage_dir: Optional[str] = None):
        """
        Initialize local key-value store.

        Args:
            store_id: Store identifier (used as directory name)
            storage_dir: Base storage directory (defaults to ./storage/key_value_stores)
        """
        if storage_dir is None:
            # Default to storage/key_value_stores relative to current working directory
            storage_dir = os.path.join(os.getcwd(), "storage", "key_value_stores")

        self.store_id = store_id
        self.storage_dir = Path(storage_dir) / store_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get file path for a given key."""
        # Sanitize key for filename
        safe_key = "".join(c for c in key if c.isalnum() or c in "._-").strip()
        if not safe_key:
            safe_key = "default"
        return self.storage_dir / f"{safe_key}.json"

    def set_value(self, key: str, value: Any) -> None:
        """
        Set a value in the key-value store.

        Args:
            key: Key to set
            value: Value to store (must be JSON serializable)
        """
        filepath = self._get_file_path(key)

        # Try JSON serialization first
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            # Fall back to pickle for non-JSON serializable objects
            pickle_path = filepath.with_suffix('.pkl')
            with open(pickle_path, 'wb') as f:
                pickle.dump(value, f)

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the key-value store.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        filepath = self._get_file_path(key)

        # Try JSON first
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Try pickle
        pickle_path = filepath.with_suffix('.pkl')
        if pickle_path.exists():
            try:
                with open(pickle_path, 'rb') as f:
                    return pickle.load(f)
            except (pickle.UnpicklingError, FileNotFoundError):
                pass

        return default

    def delete_value(self, key: str) -> bool:
        """
        Delete a value from the key-value store.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted, False if not found
        """
        filepath = self._get_file_path(key)
        deleted = False

        if filepath.exists():
            filepath.unlink()
            deleted = True

        pickle_path = filepath.with_suffix('.pkl')
        if pickle_path.exists():
            pickle_path.unlink()
            deleted = True

        return deleted

    def get_info(self) -> Dict[str, Any]:
        """
        Get key-value store information.

        Returns:
            Store metadata
        """
        files = list(self.storage_dir.glob("*"))
        return {
            "id": self.store_id,
            "name": self.store_id,
            "keyCount": len(files),
            "storageDir": str(self.storage_dir)
        }

    def list_keys(self) -> List[str]:
        """
        List all keys in the store.

        Returns:
            List of keys
        """
        keys = []
        for filepath in self.storage_dir.glob("*"):
            if filepath.suffix in ['.json', '.pkl']:
                key = filepath.stem
                keys.append(key)
        return keys

    def drop(self) -> None:
        """Delete all data in the key-value store."""
        import shutil
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)