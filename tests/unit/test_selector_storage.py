import json
import os
import shutil
import tempfile

import pytest

from src.scrapers.selector_storage import SelectorData, SelectorManager, SelectorStorage


@pytest.fixture
def temp_storage_path():
    """Create a temporary file path for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_selector_data():
    """Create sample selector data for testing."""
    confidence = 0.8
    return SelectorData(
        selector=".product-title",
        confidence=confidence,
        last_updated="2023-01-01T00:00:00Z",
        fallbacks=[".title", ".name"],
    )


class TestSelectorData:
    """Test cases for SelectorData class."""

    def test_init_default_values(self):
        """Test SelectorData initialization with default values."""
        data = SelectorData(selector=".test")

        assert data.selector == ".test"
        initial_confidence = 0.5
        assert data.confidence == initial_confidence
        assert data.fallbacks == []
        assert data.last_updated is not None

    def test_init_custom_values(self):
        """Test SelectorData initialization with custom values."""
        high_confidence = 0.9
        data = SelectorData(
            selector=".custom",
            confidence=high_confidence,
            last_updated="2023-01-01T00:00:00Z",
            fallbacks=[".alt1", ".alt2"],
        )

        assert data.selector == ".custom"
        assert data.confidence == high_confidence
        assert data.last_updated == "2023-01-01T00:00:00Z"
        assert data.fallbacks == [".alt1", ".alt2"]

    def test_to_dict(self, sample_selector_data):
        """Test converting SelectorData to dictionary."""
        confidence = 0.8
        data_dict = sample_selector_data.to_dict()

        expected = {
            "selector": ".product-title",
            "confidence": confidence,
            "last_updated": "2023-01-01T00:00:00Z",
            "fallbacks": [".title", ".name"],
        }
        assert data_dict == expected

    def test_from_dict(self):
        """Test creating SelectorData from dictionary."""
        confidence = 0.8
        data_dict = {
            "selector": ".product-title",
            "confidence": confidence,
            "last_updated": "2023-01-01T00:00:00Z",
            "fallbacks": [".title", ".name"],
        }

        data = SelectorData.from_dict(data_dict)

        assert data.selector == ".product-title"
        good_confidence = 0.8
        assert data.confidence == good_confidence
        assert data.last_updated == "2023-01-01T00:00:00Z"
        assert data.fallbacks == [".title", ".name"]

    def test_from_dict_defaults(self):
        """Test creating SelectorData from dictionary with missing fields."""
        data_dict = {"selector": ".test"}

        data = SelectorData.from_dict(data_dict)

        assert data.selector == ".test"
        default_confidence = 0.5
        assert data.confidence == default_confidence
        assert data.fallbacks == []

    def test_update_confidence_success(self):
        """Test confidence update on successful extraction."""
        initial_confidence = 0.5
        expected_confidence = 0.6  # 0.5 + 0.1
        data = SelectorData(selector=".test", confidence=initial_confidence)

        data.update_confidence(success=True)

        assert data.confidence == expected_confidence

    def test_update_confidence_failure(self):
        """Test confidence update on failed extraction."""
        initial_confidence = 0.5
        expected_confidence_after_failure = 0.4  # 0.5 - 0.1
        data = SelectorData(selector=".test", confidence=initial_confidence)

        data.update_confidence(success=False)

        assert data.confidence == expected_confidence_after_failure

    def test_update_confidence_max_min_bounds(self):
        """Test confidence stays within 0.0-1.0 bounds."""
        # Test upper bound
        initial_confidence = 0.95
        max_confidence = 1.0
        data = SelectorData(selector=".test", confidence=initial_confidence)
        data.update_confidence(success=True)
        assert data.confidence == max_confidence

        # Test lower bound
        initial_confidence = 0.05
        min_confidence = 0.0
        data = SelectorData(selector=".test", confidence=initial_confidence)
        data.update_confidence(success=False)
        assert data.confidence == min_confidence

    def test_update_confidence_custom_learning_rate(self):
        """Test confidence update with custom learning rate."""
        initial_confidence = 0.5
        learning_rate = 0.2
        expected_confidence_with_learning_rate = 0.7  # 0.5 + 0.2
        data = SelectorData(selector=".test", confidence=initial_confidence)

        data.update_confidence(success=True, learning_rate=learning_rate)

        assert data.confidence == expected_confidence_with_learning_rate


class TestSelectorStorage:
    """Test cases for SelectorStorage class."""

    def test_init_creates_storage_directory(self, tmp_path):
        """Test that storage directory is created if it doesn't exist."""
        # Create a unique subdirectory for this test
        test_dir = tmp_path / "test_selector_storage"
        storage_file = test_dir / "selectors.json"

        # Ensure the directory doesn't exist
        if test_dir.exists():
            shutil.rmtree(test_dir)

        SelectorStorage(str(storage_file))

        assert test_dir.exists()

    def test_load_empty_file(self, temp_storage_path):
        """Test loading from an empty/nonexistent file."""
        storage = SelectorStorage(temp_storage_path)

        assert storage.data == {}
        assert storage.metadata["version"] == "1.0"

    def test_load_valid_data(self, temp_storage_path):
        """Test loading valid selector data from file."""
        confidence = 0.8
        test_data = {
            "metadata": {
                "version": "1.0",
                "created_at": "2023-01-01T00:00:00Z",
                "last_modified": "2023-01-01T00:00:00Z",
            },
            "selectors": {
                "example.com": {
                    "product_name": {
                        "selector": ".product-title",
                        "confidence": confidence,
                        "last_updated": "2023-01-01T00:00:00Z",
                        "fallbacks": [".title"],
                    }
                }
            },
        }

        with open(temp_storage_path, "w") as f:
            json.dump(test_data, f)

        storage = SelectorStorage(temp_storage_path)

        assert "example.com" in storage.data
        assert "product_name" in storage.data["example.com"]
        selector_data = storage.data["example.com"]["product_name"]
        assert selector_data.selector == ".product-title"
        assert selector_data.confidence == confidence

    def test_load_corrupted_file(self, temp_storage_path):
        """Test loading from a corrupted JSON file."""
        with open(temp_storage_path, "w") as f:
            f.write("invalid json")

        storage = SelectorStorage(temp_storage_path)

        # Should initialize with empty data
        assert storage.data == {}

    def test_save_and_load_roundtrip(self, temp_storage_path):
        """Test saving and loading data preserves information."""
        confidence = 0.9
        storage = SelectorStorage(temp_storage_path)

        # Add some data
        storage.set_selector("example.com", "price", ".price", confidence, [".cost"])

        # Save and reload
        storage.save()
        new_storage = SelectorStorage(temp_storage_path)

        selector_data = new_storage.get_selector("example.com", "price")
        assert selector_data is not None
        assert selector_data.selector == ".price"
        assert selector_data.confidence == confidence
        assert selector_data.fallbacks == [".cost"]

    def test_get_selector_exists(self, temp_storage_path):
        """Test getting an existing selector."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title")

        selector_data = storage.get_selector("example.com", "title")

        assert selector_data is not None
        assert selector_data.selector == ".title"

    def test_get_selector_not_exists(self, temp_storage_path):
        """Test getting a non-existing selector."""
        storage = SelectorStorage(temp_storage_path)

        selector_data = storage.get_selector("example.com", "missing")

        assert selector_data is None

    def test_set_selector_new(self, temp_storage_path):
        """Test setting a new selector."""
        confidence = 0.7
        storage = SelectorStorage(temp_storage_path)

        storage.set_selector("example.com", "name", ".name", confidence, [".title"])

        selector_data = storage.get_selector("example.com", "name")
        assert selector_data is not None
        assert selector_data.selector == ".name"
        assert selector_data.confidence == confidence
        assert selector_data.fallbacks == [".title"]

    def test_set_selector_update(self, temp_storage_path):
        """Test updating an existing selector."""
        initial_confidence = 0.5
        updated_confidence = 0.8
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "name", ".name", initial_confidence)

        storage.set_selector("example.com", "name", ".new-name", updated_confidence, [".alt"])

        selector_data = storage.get_selector("example.com", "name")
        assert selector_data is not None
        assert selector_data.selector == ".new-name"
        assert selector_data.confidence == updated_confidence
        assert selector_data.fallbacks == [".alt"]

    def test_update_selector_confidence(self, temp_storage_path):
        """Test updating selector confidence."""
        initial_confidence = 0.5
        updated_confidence = 0.6
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "price", ".price", initial_confidence)

        storage.update_selector_confidence("example.com", "price", True)

        selector_data = storage.get_selector("example.com", "price")
        assert selector_data is not None
        assert selector_data.confidence == updated_confidence

    def test_get_fallback_chain(self, temp_storage_path):
        """Test getting fallback chain."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title", fallbacks=[".name", ".header"])

        chain = storage.get_fallback_chain("example.com", "title")

        assert chain == [".title", ".name", ".header"]

    def test_get_fallback_chain_no_selector(self, temp_storage_path):
        """Test getting fallback chain for non-existing selector."""
        storage = SelectorStorage(temp_storage_path)

        chain = storage.get_fallback_chain("example.com", "missing")

        assert chain == []

    def test_add_fallback(self, temp_storage_path):
        """Test adding a fallback selector."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title")

        storage.add_fallback("example.com", "title", ".alt-title")

        selector_data = storage.get_selector("example.com", "title")
        assert selector_data is not None
        assert ".alt-title" in selector_data.fallbacks

    def test_add_fallback_duplicate(self, temp_storage_path):
        """Test adding a duplicate fallback selector."""
        num_fallbacks = 1
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title", fallbacks=[".alt"])

        storage.add_fallback("example.com", "title", ".alt")

        selector_data = storage.get_selector("example.com", "title")
        assert selector_data is not None
        assert selector_data.fallbacks.count(".alt") == num_fallbacks  # Should not duplicate

    def test_get_all_domains(self, temp_storage_path):
        """Test getting all stored domains."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("site1.com", "field1", ".selector1")
        storage.set_selector("site2.com", "field2", ".selector2")

        domains = storage.get_all_domains()

        assert set(domains) == {"site1.com", "site2.com"}

    def test_get_domain_fields(self, temp_storage_path):
        """Test getting all fields for a domain."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title")
        storage.set_selector("example.com", "price", ".price")
        storage.set_selector("other.com", "name", ".name")

        fields = storage.get_domain_fields("example.com")

        assert set(fields) == {"title", "price"}

    def test_remove_selector(self, temp_storage_path):
        """Test removing a selector."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title")
        storage.set_selector("example.com", "price", ".price")

        storage.remove_selector("example.com", "title")

        assert storage.get_selector("example.com", "title") is None
        assert storage.get_selector("example.com", "price") is not None

    def test_clear_domain(self, temp_storage_path):
        """Test clearing all selectors for a domain."""
        storage = SelectorStorage(temp_storage_path)
        storage.set_selector("example.com", "title", ".title")
        storage.set_selector("example.com", "price", ".price")
        storage.set_selector("other.com", "name", ".name")

        storage.clear_domain("example.com")

        assert storage.get_selector("example.com", "title") is None
        assert storage.get_selector("example.com", "price") is None
        assert storage.get_selector("other.com", "name") is not None


class TestSelectorManager:
    """Test cases for SelectorManager class."""

    def test_init(self, temp_storage_path):
        """Test SelectorManager initialization."""
        manager = SelectorManager(temp_storage_path)

        assert isinstance(manager.storage, SelectorStorage)

    def test_learn_selector_new(self, temp_storage_path):
        """Test learning a new selector."""
        manager = SelectorManager(temp_storage_path)

        manager.learn_selector("example.com", "title", ".new-title", success=True)

        selector = manager.get_best_selector("example.com", "title")
        assert selector == ".new-title"

    def test_learn_selector_existing_same(self, temp_storage_path):
        """Test learning with existing selector (same selector)."""
        manager = SelectorManager(temp_storage_path)
        manager.learn_selector("example.com", "title", ".title", success=True)
        expected_confidence = 0.6  # 0.5 + 0.1

        # Learn again with same selector
        manager.learn_selector("example.com", "title", ".title", success=True)

        selector_data = manager.storage.get_selector("example.com", "title")
        assert selector_data is not None
        assert selector_data.confidence == expected_confidence

    def test_learn_selector_promote_new(self, temp_storage_path):
        """Test promoting a new selector when confidence is low."""
        manager = SelectorManager(temp_storage_path)
        manager.learn_selector("example.com", "title", ".old-title", success=False)
        # Confidence should be 0.4

        # Learn new selector with success
        manager.learn_selector("example.com", "title", ".new-title", success=True)

        selector_data = manager.storage.get_selector("example.com", "title")
        assert selector_data is not None
        assert selector_data.selector == ".new-title"
        assert ".old-title" in selector_data.fallbacks

    def test_get_best_selector(self, temp_storage_path):
        """Test getting the best selector."""
        manager = SelectorManager(temp_storage_path)
        manager.learn_selector("example.com", "title", ".title")

        best = manager.get_best_selector("example.com", "title")

        assert best == ".title"

    def test_get_best_selector_none(self, temp_storage_path):
        """Test getting best selector when none exists."""
        manager = SelectorManager(temp_storage_path)

        best = manager.get_best_selector("example.com", "missing")

        assert best is None

    def test_get_selector_with_fallbacks(self, temp_storage_path):
        """Test getting selector with fallbacks."""
        manager = SelectorManager(temp_storage_path)
        manager.storage.set_selector("example.com", "title", ".title", fallbacks=[".alt"])

        chain = manager.get_selector_with_fallbacks("example.com", "title")

        assert chain == [".title", ".alt"]

    def test_validate_selector_exists(self, temp_storage_path):
        """Test validating selector existence."""
        manager = SelectorManager(temp_storage_path)
        manager.learn_selector("example.com", "title", ".title")

        assert manager.validate_selector_exists("example.com", "title") is True
        assert manager.validate_selector_exists("example.com", "missing") is False

    def test_get_selector_stats(self, temp_storage_path):
        """Test getting selector statistics."""
        confidence = 0.8
        fallback_count = 2
        total_selectors = 3
        manager = SelectorManager(temp_storage_path)
        manager.storage.set_selector(
            "example.com",
            "title",
            ".title",
            confidence=confidence,
            fallbacks=[".alt1", ".alt2"],
        )

        stats = manager.get_selector_stats("example.com", "title")

        assert stats is not None
        assert stats["selector"] == ".title"
        assert stats["confidence"] == confidence
        assert stats["fallback_count"] == fallback_count
        assert stats["total_selectors"] == total_selectors

    def test_get_selector_stats_none(self, temp_storage_path):
        """Test getting stats for non-existing selector."""
        manager = SelectorManager(temp_storage_path)

        stats = manager.get_selector_stats("example.com", "missing")

        assert stats is None

    def test_cleanup_low_confidence_selectors(self, temp_storage_path):
        """Test cleaning up low confidence selectors."""
        good_confidence = 0.9
        bad_confidence1 = 0.1
        bad_confidence2 = 0.2
        cleanup_threshold = 0.3
        manager = SelectorManager(temp_storage_path)
        manager.storage.set_selector("example.com", "good", ".good", confidence=good_confidence)
        manager.storage.set_selector("example.com", "bad", ".bad", confidence=bad_confidence1)
        manager.storage.set_selector(
            "other.com", "also_bad", ".also-bad", confidence=bad_confidence2
        )

        manager.cleanup_low_confidence_selectors(threshold=cleanup_threshold)

        assert manager.storage.get_selector("example.com", "good") is not None
        assert manager.storage.get_selector("example.com", "bad") is None
        assert manager.storage.get_selector("other.com", "also_bad") is None
