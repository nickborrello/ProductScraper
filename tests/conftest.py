"""
Pytest configuration and fixtures for ProductScraper tests
"""

import pytest

from src.core.data_quality_scorer import DataQualityScorer


@pytest.fixture(scope="session")
def data_quality_scorer():
    """Session-scoped DataQualityScorer instance."""
    return DataQualityScorer()


@pytest.fixture
def sample_high_quality_record():
    """Sample high-quality product record for testing."""
    return {
        "SKU": "SAMPLE001",
        "Name": "Premium Dog Food - Chicken Flavor",
        "Price": "49.99",
        "Images": "https://example.com/image1.jpg,https://example.com/image2.jpg,https://example.com/image3.jpg",
        "Weight": "25 lb",
        "Product_Field_16": "Premium Pet Foods",
        "Product_Field_24": "Dog Food",
        "Product_Field_25": "Dry Dog Food",
        "Product_Field_32": "RELATED001|RELATED002",
        "Product_On_Pages": "page1|page2",
        "last_updated": "2025-11-15 12:00:00",
        "ProductDisabled": "checked",
    }


@pytest.fixture
def sample_low_quality_record():
    """Sample low-quality product record for testing."""
    return {
        "SKU": "",
        "Name": "N/A",
        "Price": "invalid",
        "Images": "not-a-url,another-invalid",
        "Weight": "",
        "Product_Field_16": None,
        "Product_Field_24": "",
        "Product_Field_25": "N/A",
        "Product_Field_32": "invalid sku format!",
    }


@pytest.fixture
def sample_mixed_quality_records(sample_high_quality_record, sample_low_quality_record):
    """List of mixed quality records."""
    return [sample_high_quality_record, sample_low_quality_record]


@pytest.fixture
def performance_test_data(sample_high_quality_record):
    """Large dataset for performance testing."""
    records = []
    for i in range(1000):
        record = sample_high_quality_record.copy()
        record["SKU"] = f"TEST{i:04d}"
        record["Name"] = f"Test Product {i}"
        records.append(record)
    return records


# Performance monitoring fixtures
@pytest.fixture
def memory_monitor():
    """Fixture to monitor memory usage during tests."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    class MemoryMonitor:
        def get_current_memory_mb(self):
            return process.memory_info().rss / 1024 / 1024

        def get_memory_delta_mb(self):
            return self.get_current_memory_mb() - initial_memory

    return MemoryMonitor()


@pytest.fixture
def time_monitor():
    """Fixture to monitor execution time."""
    import time

    class TimeMonitor:
        def __init__(self):
            self.start_time = None

        def start(self):
            self.start_time = time.time()

        def elapsed_seconds(self):
            if self.start_time is None:
                return 0
            return time.time() - self.start_time

        def elapsed_ms(self):
            return self.elapsed_seconds() * 1000

    return TimeMonitor()
