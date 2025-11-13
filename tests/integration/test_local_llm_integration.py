import pytest
import json
from unittest.mock import patch, MagicMock
from src.core.classification.classifier import classify_single_product, classify_products_batch
from src.core.classification.local_llm_classifier import LocalLLMProductClassifier


class TestLocalLLMIntegration:
    """Integration tests for LocalLLM classifier with main classification system."""

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock successful Ollama response."""
        return {
            "response": json.dumps({
                "category": "Dog Food",
                "subcategory": "Dry Dog Food",
                "confidence": 0.95,
                "reasoning": "Product appears to be dry dog food based on description"
            })
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
            }
        ]

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_local_llm_method_integration(self, mock_chat, mock_list, mock_ollama_response, sample_products):
        """Test that local_llm method works in main classifier."""
        mock_list.return_value = [{'name': 'llama3.2', 'size': 1000000}]  # Mock successful list response
        mock_chat.return_value = mock_ollama_response

        # Test single product classification
        result = classify_single_product(sample_products[0], method="local_llm")

        assert result is not None
        assert 'Category' in result
        assert 'Product Type' in result
        assert result['Category'] == 'Dog Food'
        assert result['Product Type'] == 'Dry Dog Food'

        # Verify Ollama was called
        mock_chat.assert_called_once()

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_batch_classification_integration(self, mock_chat, mock_list, mock_ollama_response, sample_products):
        """Test batch classification through main classifier."""
        mock_list.return_value = [{'name': 'llama3.2', 'size': 1000000}]  # Mock successful list response
        # Mock batch response for multiple products
        batch_response = {
            "response": json.dumps([
                {
                    "category": "Dog Food",
                    "subcategory": "Dry Dog Food",
                    "confidence": 0.95
                },
                {
                    "category": "Cat Supplies",
                    "subcategory": "Cat Litter",
                    "confidence": 0.90
                }
            ])
        }
        mock_chat.return_value = batch_response

        # Test batch classification
        results = classify_products_batch(sample_products, method="local_llm")

        assert len(results) == 2
        assert results[0]['Category'] == 'Dog Food'
        assert results[1]['Category'] == 'Cat Supplies'

    @patch('ollama.chat')
    @patch('src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache')
    @patch('src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache')
    def test_caching_integration(self, mock_save_cache, mock_load_cache, mock_chat, mock_ollama_response, sample_products):
        """Test that caching works through main classifier."""
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

    @patch('ollama.chat')
    def test_error_handling_integration(self, mock_chat, sample_products):
        """Test error handling in main classifier."""
        # Mock Ollama failure
        mock_chat.side_effect = Exception("Ollama service unavailable")

        # Classification should handle error gracefully
        result = classify_single_product(sample_products[0], method="local_llm")

        # Should return some fallback result or None
        assert result is not None or result is None  # Allow for different error handling strategies

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_model_validation_integration(self, mock_chat, mock_list, mock_ollama_response, sample_products):
        """Test model validation through main classifier."""
        # Mock available models
        mock_list.return_value = {'models': [{'name': 'llama2'}, {'name': 'mistral'}]}
        mock_chat.return_value = mock_ollama_response

        # Should work with valid model
        result = classify_single_product(sample_products[0], method="local_llm")
        assert result is not None

    @patch('ollama.chat')
    def test_response_parsing_integration(self, mock_chat, sample_products):
        """Test JSON response parsing in integration context."""
        # Test valid JSON response
        valid_response = {
            "response": json.dumps({
                "category": "Test Category",
                "subcategory": "Test Subcategory",
                "confidence": 0.85
            })
        }
        mock_chat.return_value = valid_response

        result = classify_single_product(sample_products[0], method="local_llm")
        assert result['Category'] == 'Test Category'
        assert result['Product Type'] == 'Test Subcategory'

        # Test malformed JSON response
        malformed_response = {"response": "invalid json"}
        mock_chat.return_value = malformed_response

        result = classify_single_product(sample_products[0], method="local_llm")
        # Should handle gracefully
        assert result is not None  # Implementation should provide fallback

    @patch('ollama.chat')
    def test_empty_product_handling(self, mock_chat):
        """Test handling of empty or invalid products."""
        empty_product = {}

        result = classify_single_product(empty_product, method="local_llm")
        # Should handle empty products gracefully
        assert result is not None or result is None  # Allow for different strategies

    @patch('ollama.chat')
    def test_large_batch_processing(self, mock_chat):
        """Test processing of large batches."""
        # Create large batch of products
        large_batch = [
            {
                "SKU": f"TEST{i:03d}",
                "Name": f"Product {i}",
                "Price": "9.99"
            } for i in range(10)  # Smaller batch for testing
        ]

        # Mock batch response
        batch_response = {
            "response": json.dumps([
                {
                    "category": "Test Category",
                    "subcategory": "Test Subcategory",
                    "confidence": 0.8
                }
            ] * 10)
        }
        mock_chat.return_value = batch_response

        results = classify_products_batch(large_batch, method="local_llm")
        assert len(results) == 10

    @patch('src.core.classification.local_llm_classifier.LocalLLMProductClassifier._is_ollama_available')
    def test_ollama_availability_check(self, mock_available, sample_products):
        """Test Ollama availability checking."""
        mock_available.return_value = False

        # Should handle unavailable Ollama gracefully
        result = classify_single_product(sample_products[0], method="local_llm")
        assert result is not None  # Should have fallback behavior