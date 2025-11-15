"""
Local Apify SDK implementation for development and testing.
Provides the same interface as the Apify SDK but uses local storage.
"""

from src.core.local_storage.actor import Actor

# Re-export for convenience
__all__ = ['Actor']