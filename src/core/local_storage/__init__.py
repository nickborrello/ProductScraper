"""
Local storage simulation for Apify SDK operations during development and testing.
Provides in-memory and file-based implementations of Apify platform storage APIs.
"""

from .dataset import LocalDataset
from .key_value_store import LocalKeyValueStore
from .request_queue import LocalRequestQueue
from .actor import LocalActor

__all__ = [
    'LocalDataset',
    'LocalKeyValueStore',
    'LocalRequestQueue',
    'LocalActor'
]