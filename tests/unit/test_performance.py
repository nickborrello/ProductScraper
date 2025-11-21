"""
Performance tests for validation framework
"""

import os
import threading
import time

import psutil
import pytest

from src.core.data_quality_scorer import DataQualityScorer


@pytest.mark.performance
@pytest.mark.slow
class TestValidationPerformance:
    """Performance tests ensuring <5 min execution and <500MB memory usage."""

    @pytest.fixture
    def large_dataset(self):
        """Generate large dataset for performance testing."""
        records = []
        base_record = {
            "SKU": "PERF001",
            "Name": "Performance Test Product",
            "Price": "29.99",
            "Images": "https://example.com/img1.jpg,https://example.com/img2.jpg",
            "Weight": "5 lb",
            "Product_Field_16": "Test Brand",
            "Product_Field_24": "Test Category",
            "Product_Field_25": "Test Type",
            "Product_Field_32": "SKU1|SKU2",
        }

        for i in range(5000):  # Large dataset
            record = base_record.copy()
            record["SKU"] = f"PERF{i:04d}"
            record["Name"] = f"Performance Test Product {i}"
            records.append(record)

        return records

    def test_large_scale_scoring_performance(self, large_dataset):
        """Test scoring performance on large dataset."""
        scorer = DataQualityScorer()

        # Memory monitoring
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Time monitoring
        start_time = time.time()

        results = []
        for record in large_dataset:
            score, _ = scorer.score_record(record)
            results.append(score)

        elapsed_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # Performance assertions
        max_processing_time = 300.0  # 5 minutes
        max_memory_increase = 500.0  # 500MB
        assert elapsed_time < max_processing_time, (
            f"Processing 5000 records took {elapsed_time:.2f}s (>5 min)"
        )
        assert memory_delta < max_memory_increase, (
            f"Memory usage increased by {memory_delta:.2f}MB (>500MB)"
        )

        # Quality assertions
        avg_score = sum(results) / len(results)
        quality_threshold = 85.0
        high_quality_count = sum(1 for score in results if score >= quality_threshold)

        assert avg_score >= quality_threshold, f"Average quality score too low: {avg_score:.2f}"
        assert high_quality_count == len(results), (
            f"Only {high_quality_count}/{len(results)} records are high quality"
        )

        print(
            f"Performance results: {elapsed_time:.2f}s, {memory_delta:.2f}MB memory, avg score:"
            f" {avg_score:.2f}"
        )

    def test_memory_efficiency_under_load(self):
        """Test memory efficiency during sustained load."""
        scorer = DataQualityScorer()
        process = psutil.Process(os.getpid())

        memory_readings = []

        # Simulate sustained scoring load
        for batch in range(10):
            batch_records = []
            for i in range(500):  # 500 records per batch
                record = {
                    "SKU": f"BATCH{batch}REC{i:03d}",
                    "Name": f"Batch {batch} Record {i}",
                    "Price": "19.99",
                    "Images": "https://example.com/img.jpg",
                    "Weight": "2 lb",
                    "Product_Field_16": "Brand",
                    "Product_Field_24": "Category",
                    "Product_Field_25": "Type",
                }
                batch_records.append(record)

            # Score batch
            for record in batch_records:
                scorer.score_record(record)

            # Record memory
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_readings.append(memory_mb)

            # Small delay to simulate real usage
            time.sleep(0.01)

        # Check memory stability (should not grow excessively)
        initial_memory = memory_readings[0]
        final_memory = memory_readings[-1]
        max_memory = max(memory_readings)

        memory_growth = final_memory - initial_memory
        peak_growth = max_memory - initial_memory

        max_memory_growth = 50.0  # MB
        max_peak_growth = 100.0  # MB
        assert memory_growth < max_memory_growth, (
            f"Memory grew by {memory_growth:.2f}MB during test (>50MB)"
        )
        assert peak_growth < max_peak_growth, f"Peak memory growth {peak_growth:.2f}MB (>100MB)"

        print(f"Memory stability: growth {memory_growth:.2f}MB, peak {peak_growth:.2f}MB")

    def test_concurrent_performance_simulation(self):
        """Simulate concurrent validation scenarios."""
        scorer = DataQualityScorer()
        results = {}
        errors = []

        def score_worker(worker_id, records):
            """Worker function for scoring records."""
            try:
                worker_results = []
                for record in records:
                    score, _ = scorer.score_record(record)
                    worker_results.append(score)
                results[worker_id] = worker_results
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Create test data
        num_workers = 4
        records_per_worker = 250
        threads = []

        start_time = time.time()

        for worker_id in range(num_workers):
            records = []
            for i in range(records_per_worker):
                record = {
                    "SKU": f"CONC{worker_id}{i:03d}",
                    "Name": f"Concurrent Test Product {worker_id}-{i}",
                    "Price": "24.99",
                    "Images": "https://example.com/img.jpg",
                    "Weight": "3 lb",
                    "Product_Field_16": "Brand",
                    "Product_Field_24": "Category",
                    "Product_Field_25": "Type",
                }
                records.append(record)

            thread = threading.Thread(target=score_worker, args=(worker_id, records))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        elapsed_time = time.time() - start_time

        # Assertions
        assert len(errors) == 0, f"Threading errors occurred: {errors}"
        assert len(results) == num_workers, "Not all workers completed"

        total_scores = sum(len(scores) for scores in results.values())
        assert total_scores == num_workers * records_per_worker, "Not all records were scored"

        # Performance check
        max_concurrent_time = 60.0  # 1 minute
        assert elapsed_time < max_concurrent_time, (
            f"Concurrent processing took {elapsed_time:.2f}s (>1 min)"
        )

        print(f"Concurrent performance: {elapsed_time:.2f}s for {total_scores} records")


@pytest.mark.performance
def test_individual_scoring_speed():
    """Test that individual record scoring is fast."""
    scorer = DataQualityScorer()
    record = {
        "SKU": "SPEED001",
        "Name": "Speed Test Product",
        "Price": "39.99",
        "Images": "https://example.com/img1.jpg,https://example.com/img2.jpg",
        "Weight": "10 lb",
        "Product_Field_16": "Speed Brand",
        "Product_Field_24": "Speed Category",
        "Product_Field_25": "Speed Type",
        "Product_Field_32": "SPEED002|SPEED003",
    }

    # Warm up
    for _ in range(10):
        scorer.score_record(record)

    # Timed runs
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        scorer.score_record(record)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms

    avg_time = sum(times) / len(times)
    max_time = max(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    # Performance thresholds
    max_avg_time = 5.0  # ms
    max_max_time = 20.0  # ms
    max_p95_time = 10.0  # ms
    assert avg_time < max_avg_time, f"Average scoring time {avg_time:.2f}ms (>5ms)"
    assert max_time < max_max_time, f"Max scoring time {max_time:.2f}ms (>20ms)"
    assert p95_time < max_p95_time, f"95th percentile {p95_time:.2f}ms (>10ms)"

    print(f"Speed test: avg {avg_time:.2f}ms, max {max_time:.2f}ms, p95 {p95_time:.2f}ms")
