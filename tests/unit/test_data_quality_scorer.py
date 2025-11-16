"""
Unit tests for DataQualityScorer
"""

import pytest
from src.core.data_quality_scorer import DataQualityScorer, score_product_data, is_product_high_quality

@pytest.fixture
def valid_record():
    """Fixture for a high-quality product record."""
    return {
        'SKU': 'TEST123',
        'Name': 'Test Product Name',
        'Price': '29.99',
        'Images': 'https://example.com/image1.jpg,https://example.com/image2.jpg',
        'Weight': '5 lb',
        'Product_Field_16': 'Test Brand',
        'Product_Field_24': 'Test Category',
        'Product_Field_25': 'Test Product Type',
        'Product_Field_32': 'SKU1|SKU2|SKU3'
    }

@pytest.fixture
def invalid_record():
    """Fixture for a low-quality product record."""
    return {
        'SKU': '',
        'Name': 'N/A',
        'Price': '',
        'Images': '',
        'Weight': '',
        'Product_Field_16': None,
        'Product_Field_24': '',
        'Product_Field_25': 'N/A'
    }


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
            'SKU': 'TEST123',
            'Name': 'Test Product Name',
            'Price': '29.99',
            'Images': 'https://example.com/image1.jpg,https://example.com/image2.jpg',
            'Weight': '5 lb',
            'Product_Field_16': 'Test Brand',
            'Product_Field_24': 'Test Category',
            'Product_Field_25': 'Test Product Type',
            'Product_Field_32': 'SKU1|SKU2|SKU3'
        }

    @pytest.fixture
    def invalid_record(self):
        """Fixture for a low-quality product record."""
        return {
            'SKU': '',
            'Name': 'N/A',
            'Price': '',
            'Images': '',
            'Weight': '',
            'Product_Field_16': None,
            'Product_Field_24': '',
            'Product_Field_25': 'N/A'
        }

    def test_score_record_valid(self, scorer, valid_record):
        """Test scoring a valid record."""
        score, details = scorer.score_record(valid_record)

        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score >= 85  # Should be high quality
        assert 'completeness' in details
        assert 'accuracy' in details
        assert 'consistency' in details
        assert details['overall'] == score

    def test_score_record_invalid(self, scorer, invalid_record):
        """Test scoring an invalid record."""
        score, details = scorer.score_record(invalid_record)

        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score < 85  # Should be low quality

    def test_completeness_scoring(self, scorer, valid_record, invalid_record):
        """Test completeness scoring."""
        _, valid_details = scorer.score_record(valid_record)
        _, invalid_details = scorer.score_record(invalid_record)

        assert valid_details['completeness']['score'] == 100.0
        assert invalid_details['completeness']['score'] == 0.0

    def test_accuracy_scoring(self, scorer):
        """Test accuracy scoring components."""
        # Test weight normalization
        record = {'Weight': '10 oz'}
        score, details = scorer._score_accuracy(record)
        assert details['weight']['normalized'] == '0.62 lb'

        # Test image URLs
        record = {'Images': 'https://valid.com/img.jpg,invalid-url'}
        score, details = scorer._score_accuracy(record)
        assert details['images']['valid_urls'] == 1
        assert details['images']['total_urls'] == 2

        # Test cross-sell
        record = {'Product_Field_32': 'SKU1|SKU2'}
        score, details = scorer._score_accuracy(record)
        assert details['cross_sell']['format_valid'] is True

    def test_consistency_scoring(self, scorer):
        """Test consistency scoring."""
        # Valid formats
        record = {
            'SKU': 'ABC123',
            'Name': 'Valid Product Name',
            'Product_Field_16': 'Brand',
            'Product_Field_24': 'Category',
            'Product_Field_25': 'Type'
        }
        score, details = scorer._score_consistency(record)
        assert score == 100.0

        # Invalid formats
        record = {
            'SKU': 'invalid sku with spaces and special chars!',
            'Name': '123',  # Just numbers
            'Product_Field_16': '',
            'Product_Field_24': 'N/A',
            'Product_Field_25': None
        }
        score, details = scorer._score_consistency(record)
        assert score == 0.0

    def test_is_high_quality(self, scorer, valid_record, invalid_record):
        """Test high quality threshold check."""
        assert scorer.is_high_quality(90) is True
        assert scorer.is_high_quality(80) is False
        assert scorer.is_high_quality(85) is True  # Boundary

    def test_weight_normalization(self, scorer):
        """Test weight normalization to LB."""
        assert scorer._normalize_weight_to_lb('5 lb') == 5.0
        assert scorer._normalize_weight_to_lb('16 oz') == 1.0
        assert scorer._normalize_weight_to_lb('2.2 kg') == pytest.approx(4.8508, rel=1e-3)
        assert scorer._normalize_weight_to_lb('1000 g') == 2.20462
        assert scorer._normalize_weight_to_lb('invalid') is None
        assert scorer._normalize_weight_to_lb('') is None

    def test_url_validation(self, scorer):
        """Test URL validation."""
        assert scorer._is_valid_url('https://example.com/image.jpg') is True
        assert scorer._is_valid_url('http://example.com/image.jpg') is True
        assert scorer._is_valid_url('ftp://example.com/image.jpg') is False
        assert scorer._is_valid_url('not-a-url') is False
        assert scorer._is_valid_url('') is False

    def test_price_accuracy(self, scorer):
        """Test price parsing."""
        score, details = scorer._score_price_accuracy('$29.99')
        assert score == 100
        assert details['value'] == 29.99

        score, details = scorer._score_price_accuracy('invalid price')
        assert score == 0
        assert details['numeric'] is False


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_score_product_data(self, valid_record):
        """Test score_product_data function."""
        score, details = score_product_data(valid_record)
        assert isinstance(score, float)
        assert isinstance(details, dict)

    def test_is_product_high_quality(self, valid_record, invalid_record):
        """Test is_product_high_quality function."""
        assert is_product_high_quality(valid_record) is True
        assert is_product_high_quality(invalid_record) is False
        assert is_product_high_quality(valid_record, threshold=95) is False  # Custom threshold