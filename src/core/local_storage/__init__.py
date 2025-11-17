"""
Local storage implementations for testing purposes.

This module provides local file-based implementations of storage services
that mimic cloud storage APIs for testing.
"""

from .dataset import LocalDataset
from .key_value_store import LocalKeyValueStore
from .request_queue import LocalRequestQueue

__all__ = [
    "LocalDataset",
    "LocalKeyValueStore",
    "LocalRequestQueue"
]