"""
Local mock implementation of Apify SDK for testing purposes.
This provides minimal functionality needed for scraper testing.
"""

class Actor:
    """Mock Actor class."""

    @staticmethod
    def init():
        """Initialize the actor."""
        pass

    @staticmethod
    def get_input():
        """Get input data."""
        return {}

    @staticmethod
    def push_data(data):
        """Push data to dataset."""
        pass

    @staticmethod
    def get_value(key):
        """Get a value from key-value store."""
        return None

    @staticmethod
    def set_value(key, value):
        """Set a value in key-value store."""
        pass

class Dataset:
    """Mock Dataset class."""

    def __init__(self, dataset_id=None):
        self.dataset_id = dataset_id
        self.data = []

    def push_data(self, data):
        """Push data to dataset."""
        if isinstance(data, list):
            self.data.extend(data)
        else:
            self.data.append(data)

    def get_data(self):
        """Get all data from dataset."""
        return self.data

class KeyValueStore:
    """Mock KeyValueStore class."""

    def __init__(self, store_id=None):
        self.store_id = store_id
        self.data = {}

    def get_value(self, key):
        """Get value by key."""
        return self.data.get(key)

    def set_value(self, key, value):
        """Set value by key."""
        self.data[key] = value

# Mock the main apify module
import sys
sys.modules['apify'] = sys.modules[__name__]