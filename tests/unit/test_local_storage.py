"""
Unit tests for local storage simulation classes.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.core.local_storage.dataset import LocalDataset
from src.core.local_storage.key_value_store import LocalKeyValueStore
from src.core.local_storage.request_queue import LocalRequestQueue


class TestLocalDataset:
    """Test LocalDataset functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.dataset = LocalDataset("test_dataset", str(self.temp_dir))

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_push_data_single_item(self):
        """Test pushing a single data item."""
        data = {"name": "Test Product", "price": 10.99}
        self.dataset.push_data(data)

        # Check that data was saved
        assert len(self.dataset) == 1
        assert self.dataset._cache[0] == data

        # Check file was created
        files = list(self.dataset.storage_dir.glob("*.json"))
        assert len(files) == 1

        # Check file contents
        with open(files[0]) as f:
            saved_data = json.load(f)
            assert saved_data == data

    def test_push_data_multiple_items(self):
        """Test pushing multiple data items."""
        data_list = [
            {"name": "Product 1", "price": 10.99},
            {"name": "Product 2", "price": 20.99},
        ]
        self.dataset.push_data(data_list)

        expected_item_count = 2
        assert len(self.dataset) == expected_item_count
        assert self.dataset._cache == data_list

        # Check files were created
        files = list(self.dataset.storage_dir.glob("*.json"))
        expected_file_count = 2
        assert len(files) == expected_file_count

    def test_get_data(self):
        """Test getting data from dataset."""
        data = [{"name": "Product 1"}, {"name": "Product 2"}, {"name": "Product 3"}]
        self.dataset.push_data(data)

        # Get all data
        all_data = self.dataset.get_data()
        assert all_data == data

        # Get with limit
        limited_data = self.dataset.get_data(limit=2)
        assert limited_data == data[:2]

        # Get with offset
        offset_data = self.dataset.get_data(offset=1, limit=2)
        assert offset_data == data[1:3]

    def test_get_info(self):
        """Test getting dataset info."""
        data = [{"name": "Product 1"}, {"name": "Product 2"}]
        self.dataset.push_data(data)

        info = self.dataset.get_info()
        assert info["id"] == "test_dataset"
        expected_item_count = 2
        assert info["itemCount"] == expected_item_count
        assert str(self.temp_dir / "test_dataset") in info["storageDir"]

    def test_drop(self):
        """Test dropping dataset."""
        self.dataset.push_data({"name": "Test"})
        assert len(self.dataset) == 1

        self.dataset.drop()
        assert len(self.dataset) == 0
        assert len(list(self.dataset.storage_dir.glob("*.json"))) == 0


class TestLocalKeyValueStore:
    """Test LocalKeyValueStore functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = LocalKeyValueStore("test_store", str(self.temp_dir))

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_set_get_value(self):
        """Test setting and getting values."""
        self.store.set_value("key1", "value1")
        self.store.set_value("key2", {"nested": "data"})

        assert self.store.get_value("key1") == "value1"
        assert self.store.get_value("key2") == {"nested": "data"}
        assert self.store.get_value("nonexistent") is None
        assert self.store.get_value("nonexistent", "default") == "default"

    def test_delete_value(self):
        """Test deleting values."""
        self.store.set_value("key1", "value1")
        assert self.store.get_value("key1") == "value1"

        assert self.store.delete_value("key1") is True
        assert self.store.get_value("key1") is None

        assert self.store.delete_value("nonexistent") is False

    def test_list_keys(self):
        """Test listing keys."""
        self.store.set_value("key1", "value1")
        self.store.set_value("key2", "value2")

        keys = self.store.list_keys()
        expected_key_count = 2
        assert len(keys) == expected_key_count
        assert "key1" in keys
        assert "key2" in keys

    def test_get_info(self):
        """Test getting store info."""
        self.store.set_value("key1", "value1")

        info = self.store.get_info()
        assert info["id"] == "test_store"
        assert info["keyCount"] == 1
        assert str(self.temp_dir / "test_store") in info["storageDir"]

    def test_drop(self):
        """Test dropping store."""
        self.store.set_value("key1", "value1")
        assert len(self.store.list_keys()) == 1

        self.store.drop()
        assert len(self.store.list_keys()) == 0


class TestLocalRequestQueue:
    """Test LocalRequestQueue functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.queue = LocalRequestQueue("test_queue", str(self.temp_dir))

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_add_request(self):
        """Test adding requests to queue."""
        request = {"url": "https://example.com", "method": "GET"}
        request_id = self.queue.add_request(request)

        assert request_id.startswith("req_")
        assert len(self.queue) == 1

    def test_fetch_next_request(self):
        """Test fetching next request."""
        request1 = {"url": "https://example1.com"}
        request2 = {"url": "https://example2.com"}

        self.queue.add_request(request1)
        self.queue.add_request(request2)

        fetched1 = self.queue.fetch_next_request()
        assert fetched1 is not None
        assert fetched1["url"] == "https://example1.com"
        assert len(self.queue) == 1

        fetched2 = self.queue.fetch_next_request()
        assert fetched2 is not None
        assert fetched2["url"] == "https://example2.com"
        assert len(self.queue) == 0

        # Queue should be empty
        assert self.queue.fetch_next_request() is None

    def test_mark_request_handled(self):
        """Test marking requests as handled."""
        request = {"url": "https://example.com"}
        self.queue.add_request(request)

        fetched = self.queue.fetch_next_request()
        assert fetched is not None
        assert len(self.queue) == 0

        self.queue.mark_request_as_handled(fetched)

        # Check that request was moved to handled
        info = self.queue.get_info()
        assert info["handledRequestCount"] == 1
        assert info["pendingRequestCount"] == 0

    def test_reclaim_request(self):
        """Test reclaiming requests."""
        request = {"url": "https://example.com"}
        self.queue.add_request(request)

        fetched = self.queue.fetch_next_request()
        assert fetched is not None
        self.queue.mark_request_as_handled(fetched)

        # Reclaim the request
        self.queue.reclaim_request(fetched)
        assert len(self.queue) == 1

        # Should be able to fetch it again
        refetched = self.queue.fetch_next_request()
        assert refetched is not None
        assert refetched["url"] == "https://example.com"

    def test_get_info(self):
        """Test getting queue info."""
        request = {"url": "https://example.com"}
        self.queue.add_request(request)

        info = self.queue.get_info()
        assert info["id"] == "test_queue"
        assert info["pendingRequestCount"] == 1
        assert info["handledRequestCount"] == 0
        assert info["totalRequestCount"] == 1

    def test_drop(self):
        """Test dropping queue."""
        self.queue.add_request({"url": "https://example.com"})
        assert len(self.queue) == 1

        self.queue.drop()
        assert len(self.queue) == 0
        assert self.queue.is_empty()


if __name__ == "__main__":
    pytest.main([__file__])
