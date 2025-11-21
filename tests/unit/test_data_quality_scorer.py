"""
Unit tests for DataQualityScorer
"""

import unittest
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.data_quality_scorer import (
    DataQualityScorer,
    is_product_high_quality,
    score_product_data,
)


class TestDataQualityScorer:
    """Test DataQualityScorer class functionality."""

    @pytest.fixture
    def scorer(self):
        """Fixture for DataQualityScorer instance."""
        return DataQualityScorer()

    @pytest.fixture
    def valid_record(self):
        """Fixture for a high-quality product record."""
        return {
            "SKU": "TEST123",
            "Name": "Test Product Name",
            "Price": "29.99",
            "Images": "https://example.com/image1.jpg,https://example.com/image2.jpg",
            "Weight": "5 lb",
            "Product_Field_16": "Test Brand",
            "Product_Field_24": "Test Category",
            "Product_Field_25": "Test Product Type",
        }

    @pytest.fixture
    def invalid_record(self):
        """Fixture for a low-quality product record."""
        return {
            "SKU": "",
            "Name": "N/A",
            "Price": "invalid",
            "Images": "not-a-url",
            "Weight": "",
            "Product_Field_16": None,
            "Product_Field_24": "",
            "Product_Field_25": "N/A",
        }

    def test_score_record_valid(self, scorer, valid_record):
        """Test scoring a valid record."""
        score, details = scorer.score_record(valid_record)
        max_score = 100
        high_quality_threshold = 85
        assert isinstance(score, float)
        assert 0 <= score <= max_score
        assert score >= high_quality_threshold  # Should be high quality
        assert "completeness" in details
        assert "accuracy" in details
        assert "consistency" in details
        assert details["overall"] == score

    def test_score_record_invalid(self, scorer, invalid_record):
        """Test scoring an invalid record."""
        score, _details = scorer.score_record(invalid_record)
        max_score = 100
        high_quality_threshold = 85
        assert isinstance(score, float)
        assert 0 <= score <= max_score
        assert score < high_quality_threshold  # Should be low quality

    def test_completeness_scoring(self, scorer, valid_record, invalid_record):
        """Test completeness scoring."""
        _, valid_details = scorer.score_record(valid_record)
        _, invalid_details = scorer.score_record(invalid_record)
        max_score = 100.0
        min_score = 0.0
        assert valid_details["completeness"]["score"] == max_score
        assert invalid_details["completeness"]["score"] == min_score

    def test_accuracy_scoring(self, scorer):
        """Test accuracy scoring components."""
        # Test weight normalization
        record = {"Weight": "10 oz"}
        _, details = scorer._score_accuracy(record)
        assert details["weight"]["normalized"] == "0.62 lb"

        # Test image URLs
        record = {"Images": "https://valid.com/img.jpg,invalid-url"}
        _score, details = scorer._score_accuracy(record)
        valid_urls = 1
        total_urls = 2
        assert details["images"]["valid_urls"] == valid_urls
        assert details["images"]["total_urls"] == total_urls

    def test_consistency_scoring(self, scorer):
        """Test consistency scoring."""
        # Valid formats
        record = {
            "SKU": "ABC123",
            "Name": "Valid Product Name",
            "Product_Field_16": "Brand",
            "Product_Field_24": "Category",
            "Product_Field_25": "Type",
        }
        score, _ = scorer._score_consistency(record)
        max_score = 100.0
        assert score == max_score

        # Invalid formats
        invalid_record: dict[str, Any] = {
            "SKU": "invalid sku with spaces and special chars!",
            "Name": "123",  # Just numbers
            "Product_Field_16": "",
            "Product_Field_24": "N/A",
            "Product_Field_25": None,
        }
        score, _ = scorer._score_consistency(invalid_record)
        min_score = 0.0
        assert score == min_score

    def test_is_high_quality(self, scorer, valid_record, invalid_record):
        """Test high quality threshold check."""
        high_score = 90
        low_score = 80
        boundary_score = 85
        assert scorer.is_high_quality(high_score) is True
        assert scorer.is_high_quality(low_score) is False
        assert scorer.is_high_quality(boundary_score) is True  # Boundary

    def test_weight_normalization(self, scorer):
        """Test weight normalization to LB."""
        five_lbs = 5.0
        one_lb = 1.0
        two_point_two_kg = 4.8508
        one_thousand_g = 2.20462
        rel_tolerance = 1e-3
        assert scorer._normalize_weight_to_lb("5 lb") == five_lbs
        assert scorer._normalize_weight_to_lb("16 oz") == one_lb
        assert scorer._normalize_weight_to_lb("2.2 kg") == pytest.approx(
            two_point_two_kg, rel=rel_tolerance
        )
        assert scorer._normalize_weight_to_lb("1000 g") == one_thousand_g
        assert scorer._normalize_weight_to_lb("invalid") is None
        assert scorer._normalize_weight_to_lb("") is None

    def test_url_validation(self, scorer):
        """Test URL validation."""
        assert scorer._is_valid_url("https://example.com/image.jpg") is True
        assert scorer._is_valid_url("http://example.com/image.jpg") is True
        assert scorer._is_valid_url("ftp://example.com/image.jpg") is False
        assert scorer._is_valid_url("not-a-url") is False
        assert scorer._is_valid_url("") is False

    def test_price_accuracy(self, scorer):
        """Test price parsing."""
        max_score = 100
        min_score = 0
        price = 29.99
        score, details = scorer._score_price_accuracy(f"${price}")
        assert score == max_score
        assert details["value"] == price

        score, details = scorer._score_price_accuracy("invalid price")
        assert score == min_score
        assert details["numeric"] is False


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_score_product_data(self, sample_high_quality_record):
        """Test score_product_data function."""
        score, details = score_product_data(sample_high_quality_record)
        assert isinstance(score, float)
        assert isinstance(details, dict)

    def test_is_product_high_quality(self, sample_high_quality_record, sample_low_quality_record):
        """Test is_product_high_quality function."""
        high_quality_threshold = 95
        assert is_product_high_quality(sample_high_quality_record) is True
        assert is_product_high_quality(sample_low_quality_record) is False
        assert (
            is_product_high_quality(sample_high_quality_record, threshold=high_quality_threshold)
            is True
        )  # Custom threshold
