"""
Integration tests for scraper validation using data quality scoring
"""

import pytest

from src.core.data_quality_scorer import is_product_high_quality

HIGH_QUALITY_SCORE = 85.0
MEDIUM_QUALITY_SCORE = 70.0
LOW_QUALITY_SCORE = 0.0
FULL_COVERAGE = 100.0
HIGH_ACCURACY_SCORE = 80.0
VALID_URLS = 3
TOTAL_URLS_PERCENTAGE = 100.0
HIGH_QUALITY_RECORDS = 1
MAX_PROCESSING_TIME = 300.0
MAX_MEMORY_INCREASE = 500.0
MAX_AVG_TIME_MS = 10.0
MAX_MAX_TIME_MS = 50.0


@pytest.mark.integration
class TestScraperValidation:
    """Integration tests for validating scraper outputs with quality scoring."""

    @pytest.mark.parametrize(
        "quality_level,expected_score_min,expected_high_quality",
        [
            ("high", HIGH_QUALITY_SCORE, True),
            ("medium", MEDIUM_QUALITY_SCORE, False),
            ("low", LOW_QUALITY_SCORE, False),
        ],
    )
    def test_record_quality_validation_parametrized(
        self,
        data_quality_scorer,
        quality_level,
        expected_score_min,
        expected_high_quality,
        sample_high_quality_record,
        sample_medium_quality_record,
        sample_low_quality_record,
    ):
        """Test record validation across different quality levels."""
        # Select the appropriate sample record
        if quality_level == "high":
            record = sample_high_quality_record
        elif quality_level == "medium":
            record = sample_medium_quality_record
        else:  # low
            record = sample_low_quality_record

        score, _details = data_quality_scorer.score_record(record)

        assert score >= expected_score_min, f"{quality_level}-quality record scored too low: {score}"
        assert (
            is_product_high_quality(record) == expected_high_quality
        ), f"{quality_level}-quality record high-quality detection incorrect"

    def test_high_quality_record_validation(self, data_quality_scorer, sample_high_quality_record):
        """Test that high-quality records pass validation."""
        score, details = data_quality_scorer.score_record(sample_high_quality_record)

        assert score >= HIGH_QUALITY_SCORE, f"High-quality record scored too low: {score}"
        assert is_product_high_quality(
            sample_high_quality_record
        ), "High-quality record not recognized"

        # Check all components are high
        assert details["completeness"]["score"] == FULL_COVERAGE
        assert details["accuracy"]["score"] >= HIGH_ACCURACY_SCORE
        assert details["consistency"]["score"] == FULL_COVERAGE

    def test_low_quality_record_validation(self, data_quality_scorer, sample_low_quality_record):
        """Test that low-quality records fail validation."""
        score, _details = data_quality_scorer.score_record(sample_low_quality_record)

        assert score < HIGH_QUALITY_SCORE, f"Low-quality record scored too high: {score}"
        assert not is_product_high_quality(
            sample_low_quality_record
        ), "Low-quality record incorrectly recognized as high quality"

    def test_mixed_quality_batch_validation(
        self, data_quality_scorer, sample_mixed_quality_records
    ):
        """Test batch validation of mixed quality records."""
        results = []
        for record in sample_mixed_quality_records:
            score, _details = data_quality_scorer.score_record(record)
            results.append((score, is_product_high_quality(record)))

        # Should have one high and one low quality
        high_quality_count = sum(1 for _, is_high in results if is_high)
        assert (
            high_quality_count == HIGH_QUALITY_RECORDS
        ), f"Expected 1 high-quality record, got {high_quality_count}"

    def test_weight_normalization_integration(self, data_quality_scorer):
        """Test weight normalization in various units."""
        test_cases = [
            ("5 lb", 5.0),
            ("16 oz", 1.0),
            ("2.2 kg", 4.8508),
            ("1000 g", 2.20462),
        ]
        rel_tolerance = 1e-10
        for weight_str, expected_lb in test_cases:
            record = {"Weight": weight_str}
            _score, details = data_quality_scorer._score_accuracy(record)
            assert pytest.approx(float(details["weight"]["normalized"].split(" ")[0]), rel=rel_tolerance) == expected_lb

    def test_image_url_validation_integration(self, data_quality_scorer):
        """Test image URL validation in records."""
        # Valid URLs
        record = {
            "Images": "https://example.com/img1.jpg,http://example.com/img2.png,https://cdn.example.com/img3.jpeg"
        }
        _score, details = data_quality_scorer._score_accuracy(record)
        assert details["images"]["valid_urls"] == VALID_URLS
        assert details["images"]["percentage"] == TOTAL_URLS_PERCENTAGE

        # Mixed valid/invalid
        record = {"Images": "https://valid.com/img.jpg,invalid-url,ftp://invalid.com/img.jpg"}
        _score, details = data_quality_scorer._score_accuracy(record)
        assert details["images"]["valid_urls"] == 1
        assert details["images"]["percentage"] == pytest.approx(
            33.333333333333336, rel=1e-10
        )  # 1/3


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceValidation:
    """Performance tests for validation framework."""

    def test_large_dataset_performance(
        self, data_quality_scorer, performance_test_data, time_monitor, memory_monitor
    ):
        """Test performance with large dataset (1000 records)."""
        time_monitor.start()

        total_score = 0
        high_quality_count = 0

        for record in performance_test_data:
            score, _ = data_quality_scorer.score_record(record)
            total_score += score
            if score >= HIGH_QUALITY_SCORE:
                high_quality_count += 1

        elapsed_seconds = time_monitor.elapsed_seconds()
        memory_delta_mb = memory_monitor.get_memory_delta_mb()

        # Performance assertions
        assert elapsed_seconds < MAX_PROCESSING_TIME, f"Processing took too long: {elapsed_seconds}s (>5 min)"
        assert memory_delta_mb < MAX_MEMORY_INCREASE, f"Memory usage too high: {memory_delta_mb}MB (>500MB)"

        # Quality assertions
        avg_score = total_score / len(performance_test_data)
        assert avg_score >= HIGH_QUALITY_SCORE, f"Average score too low: {avg_score}"
        assert high_quality_count == len(
            performance_test_data
        ), "Not all records recognized as high quality"

        print(
            f"Performance test results: {elapsed_seconds:.2f}s, {memory_delta_mb:.2f}MB memory delta"
        )

    def test_individual_record_performance(
        self, data_quality_scorer, sample_high_quality_record, time_monitor
    ):
        """Test performance for individual record scoring."""
        times = []

        for _ in range(100):
            time_monitor.start()
            data_quality_scorer.score_record(sample_high_quality_record)
            times.append(time_monitor.elapsed_ms())

        avg_time_ms = sum(times) / len(times)
        max_time_ms = max(times)

        # Should be very fast (< 10ms average)
        assert avg_time_ms < MAX_AVG_TIME_MS, f"Average scoring time too slow: {avg_time_ms}ms"
        assert max_time_ms < MAX_MAX_TIME_MS, f"Max scoring time too slow: {max_time_ms}ms"

        print(
            f"Individual record performance: {avg_time_ms:.2f}ms average, {max_time_ms:.2f}ms max"
        )


@pytest.mark.integration
class TestValidationFrameworkIntegration:
    """Test integration with broader validation framework."""

    def test_validation_pipeline(self, data_quality_scorer, sample_mixed_quality_records):
        """Test complete validation pipeline."""
        validation_results = []

        for i, record in enumerate(sample_mixed_quality_records):
            score, details = data_quality_scorer.score_record(record)
            is_high = data_quality_scorer.is_high_quality(score)

            result = {
                "record_id": i,
                "score": score,
                "is_high_quality": is_high,
                "completeness_score": details["completeness"]["score"],
                "accuracy_score": details["accuracy"]["score"],
                "consistency_score": details["consistency"]["score"],
            }
            validation_results.append(result)

        # Should have different results for different quality records
        scores = [r["score"] for r in validation_results]
        assert len(set(scores)) > 1, "All records scored the same - validation not working"

        high_quality_results = [r for r in validation_results if r["is_high_quality"]]
        assert (
            len(high_quality_results) == HIGH_QUALITY_RECORDS
        ), "Expected exactly 1 high-quality record"

    def test_threshold_configuration(self, data_quality_scorer, sample_high_quality_record):
        """Test configurable quality thresholds."""
        score, _ = data_quality_scorer.score_record(sample_high_quality_record)

        # Default 85%
        assert data_quality_scorer.is_high_quality(score) is True

        # Higher threshold (score should be 100, so >= 95 is True)
        assert data_quality_scorer.is_high_quality(score, 95.0) is True

        # Lower threshold
        assert data_quality_scorer.is_high_quality(score, 75.0) is True
