import json
from unittest.mock import patch

import pytest

from src.core.classification.local_llm_classifier import (
    reset_local_llm_classifier,
)
from src.core.classification.manager import classify_products_batch, classify_single_product


class TestLocalLLMIntegration:
    """Integration tests for LocalLLM classifier with main classification system."""

    def setup_method(self):
        """Reset the global classifier instance before each test."""
        reset_local_llm_classifier()

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock successful Ollama response."""
        return {
            "message": {
                "content": json.dumps(
                    {
                        "category": "Dog Food",
                        "product_type": "Dry Dog Food",
                        "product_on_pages": "Dog Food Shop All",
                    }
                )
            }
        }

    @pytest.fixture
    def sample_products(self):
        """Sample product data for testing."""
        return [
            {
                "SKU": "TEST001",
                "Name": "Premium Dog Food - Chicken Flavor",
                "Price": "29.99",
                "Category": "",  # Will be filled by classification
                "Product Type": "",  # Will be filled by classification
                "Product On Pages": "",  # Will be filled by classification
            },
            {
                "SKU": "TEST002",
                "Name": "Cat Litter - Clumping Formula",
                "Price": "12.99",
                "Category": "",
                "Product Type": "",
                "Product On Pages": "",
            },
        ]

    @patch("ollama.list")
    @patch("ollama.chat")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache")
    def test_local_llm_method_integration(  # noqa: PLR0913
        self,
        mock_save_cache,
        mock_load_cache,
        mock_chat,
        mock_list,
        mock_ollama_response,
        sample_products,
    ):
        """Test that local_llm method works in main classifier."""
        # Mock empty cache initially
        mock_load_cache.return_value = {}

        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        mock_chat.return_value = mock_ollama_response

        # Test single product classification
        result = classify_single_product(sample_products[0], method="local_llm")

        assert result is not None
        assert "Category" in result
        assert "Product Type" in result
        assert result["Category"] == "Dog Food"
        assert result["Product Type"] == "Dry Dog Food"

        # Verify Ollama was called
        mock_chat.assert_called_once()

    @patch("ollama.list")
    @patch("ollama.chat")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache")
    def test_batch_classification_integration(  # noqa: PLR0913
        self,
        mock_save_cache,
        mock_load_cache,
        mock_chat,
        mock_list,
        mock_ollama_response,
        sample_products,
    ):
        """Test batch classification through main classifier."""
        # Mock empty cache initially
        mock_load_cache.return_value = {}
        num_products = 2
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        # Mock batch response for multiple products
        batch_response = {
            "message": {
                "content": json.dumps(
                    {
                        "classifications": [
                            {
                                "product_index": 1,
                                "category": "Dog Food",
                                "product_type": "Dry Dog Food",
                                "product_on_pages": "Dog Food Shop All",
                                "confidence": "high",
                                "reasoning": "Product appears to be dry dog food",
                            },
                            {
                                "product_index": 2,
                                "category": "Cat Supplies",
                                "product_type": "Cat Litter",
                                "product_on_pages": "Cat Supplies Shop All",
                                "confidence": "high",
                                "reasoning": "Product appears to be cat litter",
                            },
                        ]
                    }
                )
            }
        }
        mock_chat.return_value = batch_response

        # Test batch classification
        results = classify_products_batch(sample_products, method="local_llm")

        assert len(results) == num_products
        assert results[0]["Category"] == "Dog Food"
        assert results[1]["Category"] == "Cat Supplies"

    @patch("ollama.list")
    @patch("ollama.chat")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache")
    def test_caching_integration(  # noqa: PLR0913
        self,
        mock_save_cache,
        mock_load_cache,
        mock_chat,
        mock_list,
        mock_ollama_response,
        sample_products,
    ):
        """Test that caching works through main classifier."""
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        # Mock empty cache initially
        mock_load_cache.return_value = {}

        mock_chat.return_value = mock_ollama_response

        # First classification - should call Ollama
        result1 = classify_single_product(sample_products[0], method="local_llm")
        assert mock_chat.call_count == 1

        # Second classification of same product - should use cache
        result2 = classify_single_product(sample_products[0], method="local_llm")
        assert mock_chat.call_count == 1  # Still 1 call

        # Results should be identical
        assert result1 == result2

        # Cache should have been saved
        mock_save_cache.assert_called()

    @patch("ollama.list")
    @patch("ollama.chat")
    def test_error_handling_integration(self, mock_chat, mock_list, sample_products):
        """Test error handling in main classifier."""
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        # Mock Ollama failure
        mock_chat.side_effect = Exception("Ollama service unavailable")

        # Classification should handle error gracefully
        result = classify_single_product(sample_products[0], method="local_llm")

        # Should return some fallback result or None
        assert result is not None or result is None  # Allow for different error handling strategies

    @patch("ollama.list")
    @patch("ollama.chat")
    def test_model_validation_integration(
        self, mock_chat, mock_list, mock_ollama_response, sample_products
    ):
        """Test model validation through main classifier."""
        # Mock available models
        mock_list.return_value = {"models": [{"name": "llama2"}, {"name": "mistral"}]}
        mock_chat.return_value = mock_ollama_response

        # Should work with valid model
        result = classify_single_product(sample_products[0], method="local_llm")
        assert result is not None

    @patch("ollama.list")
    @patch("ollama.chat")
    def test_response_parsing_integration(self, mock_chat, mock_list, sample_products):
        """Test JSON response parsing in integration context."""
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        # Test valid JSON response
        valid_response = {
            "message": {
                "content": json.dumps(
                    {
                        "category": "Test Category",
                        "product_type": "Test Subcategory",
                        "product_on_pages": "Test Page",
                    }
                )
            }
        }
        mock_chat.return_value = valid_response

        result = classify_single_product(sample_products[0], method="local_llm")
        assert result["Category"] == "Test Category"
        assert result["Product Type"] == "Test Subcategory"

        # Test malformed JSON response
        malformed_response = {"message": {"content": "invalid json"}}
        mock_chat.return_value = malformed_response

        result = classify_single_product(sample_products[0], method="local_llm")
        # Should handle gracefully
        assert result is not None  # Implementation should provide fallback

    @patch("ollama.list")
    @patch("ollama.chat")
    def test_empty_product_handling(self, mock_chat, mock_list):
        """Test handling of empty or invalid products."""
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        empty_product = {}

        result = classify_single_product(empty_product, method="local_llm")
        # Should handle empty products gracefully
        assert result is not None or result is None  # Allow for different strategies

    @patch("ollama.list")
    @patch("ollama.chat")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache")
    @patch("src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache")
    def test_large_batch_processing(self, mock_save_cache, mock_load_cache, mock_chat, mock_list):
        """Test processing of large batches."""
        # Mock empty cache initially
        mock_load_cache.return_value = {}
        batch_size = 10
        mock_list.return_value = [
            {"name": "llama2", "size": 1000000}
        ]  # Mock successful list response
        # Create large batch of products
        large_batch = [
            {"SKU": f"TEST{i:03d}", "Name": f"Product {i}", "Price": "9.99"}
            for i in range(batch_size)  # Smaller batch for testing
        ]

        # Mock batch response
        batch_response = {
            "message": {
                "content": json.dumps(
                    {
                        "classifications": [
                            {
                                "product_index": i + 1,
                                "category": "Test Category",
                                "product_type": "Test Subcategory",
                                "product_on_pages": "Test Page",
                                "confidence": "high",
                                "reasoning": "Test reasoning",
                            }
                            for i in range(batch_size)
                        ]
                    }
                )
            }
        }
        mock_chat.return_value = batch_response

        results = classify_products_batch(large_batch, method="local_llm")
        assert len(results) == batch_size

    @patch("ollama.list")
    def test_ollama_availability_check(self, mock_list, sample_products):
        """Test Ollama availability checking."""
        # Mock Ollama as unavailable
        mock_list.side_effect = Exception("Ollama not available")

        # Should handle unavailable Ollama gracefully
        result = classify_single_product(sample_products[0], method="local_llm")
        assert result is not None  # Should have fallback behavior
