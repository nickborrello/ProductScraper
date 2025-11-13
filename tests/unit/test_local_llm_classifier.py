import pytest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the local LLM classifier
from src.core.classification.local_llm_classifier import (
    LocalLLMProductClassifier,
    get_local_llm_classifier,
    classify_product_local_llm,
    GENERAL_PRODUCT_TAXONOMY,
    PRODUCT_PAGES,
)


class TestLocalLLMClassifier:
    """Test suite for LocalLLMProductClassifier using Ollama."""

    @pytest.fixture
    def sample_products(self):
        """Sample product data for testing."""
        return [
            {
                "Name": "Purina Pro Plan Adult Dog Food Chicken & Rice Formula",
                "Brand": "Purina",
            },
            {
                "Name": "Royal Canin Indoor Adult Cat Food Hairball Care",
                "Brand": "Royal Canin",
            },
            {
                "Name": "Kaytee Forti-Diet Pro Health Cockatiel Food",
                "Brand": "Kaytee",
            },
        ]

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock Ollama API response."""
        return {
            "message": {
                "content": '{"category": "Dog Food", "product_type": "Dry Dog Food", "product_on_pages": "Dog Food Shop All"}'
            }
        }

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create a temporary directory for cache testing."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def unique_cache_file(self, tmp_path):
        """Create a unique cache file for each test."""
        import uuid
        cache_file = tmp_path / f"test_cache_{uuid.uuid4().hex}.json"
        return cache_file

    def test_taxonomy_structure(self):
        """Test that the product taxonomy is properly structured."""
        assert isinstance(GENERAL_PRODUCT_TAXONOMY, dict)
        assert len(GENERAL_PRODUCT_TAXONOMY) > 0

        # Check that we have expected categories
        expected_categories = ["Dog Food", "Cat Food", "Bird Supplies"]
        category_names = list(GENERAL_PRODUCT_TAXONOMY.keys())

        for expected in expected_categories:
            assert expected in category_names, f"Missing category: {expected}"

        # Check that categories have product types
        for category, product_types in GENERAL_PRODUCT_TAXONOMY.items():
            assert isinstance(product_types, list)
            assert len(product_types) > 0
            assert all(isinstance(pt, str) for pt in product_types)

    def test_product_pages_structure(self):
        """Test that product pages list is properly structured."""
        assert isinstance(PRODUCT_PAGES, list)
        assert len(PRODUCT_PAGES) > 0
        assert all(isinstance(page, str) for page in PRODUCT_PAGES)

    @patch('ollama.list')
    def test_initialization_success(self, mock_ollama_list, unique_cache_file):
        """Test successful initialization when Ollama is available."""
        mock_ollama_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

        assert classifier.model_name == "llama3.2"
        assert hasattr(classifier, 'conversation_history')
        assert hasattr(classifier, 'classification_cache')
        assert hasattr(classifier, 'cache_file')

    @patch('ollama.list')
    def test_initialization_ollama_unavailable(self, mock_ollama_list, unique_cache_file):
        """Test initialization failure when Ollama is not available."""
        mock_ollama_list.side_effect = Exception("Ollama not running")

        with pytest.raises(ValueError, match="Ollama not available"):
            LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

    @patch('ollama.list')
    @patch('builtins.open', new_callable=mock_open, read_data='{"ollama_model": "gemma3"}')
    @patch('pathlib.Path.exists', return_value=True)
    def test_model_name_from_settings(self, mock_exists, mock_file, mock_ollama_list, unique_cache_file):
        """Test that model name is read from settings.json."""
        mock_ollama_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier(cache_file=unique_cache_file)
        assert classifier.model_name == "gemma3"

    @patch('ollama.list')
    def test_model_name_from_env_var(self, mock_ollama_list, unique_cache_file):
        """Test that model name is read from environment variable."""
        mock_ollama_list.return_value = {"models": []}

        with patch.dict(os.environ, {'OLLAMA_MODEL': 'phi4'}):
            classifier = LocalLLMProductClassifier(cache_file=unique_cache_file)
            assert classifier.model_name == "phi4"

    @patch('ollama.list')
    def test_model_name_parameter_override(self, mock_ollama_list, unique_cache_file):
        """Test that model name parameter overrides other sources."""
        mock_ollama_list.return_value = {"models": []}

        with patch.dict(os.environ, {'OLLAMA_MODEL': 'phi4'}):
            classifier = LocalLLMProductClassifier("custom-model", cache_file=unique_cache_file)
            assert classifier.model_name == "custom-model"

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_classify_product_success(self, mock_chat, mock_list, sample_products, mock_ollama_response, unique_cache_file):
        """Test successful product classification."""
        mock_list.return_value = {"models": []}
        mock_chat.return_value = mock_ollama_response

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        result = classifier.classify_product(
            sample_products[0]["Name"],
            sample_products[0]["Brand"]
        )

        assert isinstance(result, dict)
        assert "category" in result
        assert "product_type" in result
        assert "product_on_pages" in result
        assert result["category"] == "Dog Food"

        # Verify Ollama was called
        mock_chat.assert_called_once()
        call_args = mock_chat.call_args
        assert call_args[1]["model"] == "llama3.2"
        assert "messages" in call_args[1]

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_classify_product_with_caching(self, mock_chat, mock_list, sample_products, mock_ollama_response, unique_cache_file):
        """Test that classification results are cached."""
        mock_list.return_value = {"models": []}
        mock_chat.return_value = mock_ollama_response

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        # Ensure cache starts empty
        classifier.classification_cache = {}

        # First call should use Ollama
        result1 = classifier.classify_product(
            sample_products[0]["Name"],
            sample_products[0]["Brand"]
        )

        # Second call should use cache
        result2 = classifier.classify_product(
            sample_products[0]["Name"],
            sample_products[0]["Brand"]
        )

        assert result1 == result2
        assert mock_chat.call_count == 1  # Should only be called once

        # Verify cache file was created
        assert classifier.cache_file.exists()

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_classify_product_ollama_error(self, mock_chat, mock_list, sample_products, unique_cache_file):
        """Test error handling when Ollama API fails."""
        mock_list.return_value = {"models": []}
        mock_chat.side_effect = Exception("API Error")

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        # Ensure cache starts empty
        classifier.classification_cache = {}

        result = classifier.classify_product(
            sample_products[0]["Name"],
            sample_products[0]["Brand"]
        )

        # Should return empty results on error
        assert result == {"category": "", "product_type": "", "product_on_pages": ""}

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_classify_products_batch(self, mock_chat, mock_list, sample_products, mock_ollama_response, unique_cache_file):
        """Test batch product classification."""
        mock_list.return_value = {"models": []}
        mock_chat.return_value = mock_ollama_response

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        results = classifier.classify_products_batch(sample_products)

        assert isinstance(results, list)
        assert len(results) == len(sample_products)
        assert all(isinstance(result, dict) for result in results)
        assert all("category" in result for result in results)

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_batch_processing_filters_empty_names(self, mock_chat, mock_list, unique_cache_file):
        """Test that batch processing filters out products without names."""
        mock_list.return_value = {"models": []}
        mock_chat.return_value = {"message": {"content": '{"classifications": [{"product_index": 1, "category": "Test", "product_type": "Test", "product_on_pages": "Test"}]}'}}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        # Ensure cache starts empty
        classifier.classification_cache = {}

        products_with_empty_names = [
            {"Name": "Valid Product", "Brand": "Brand"},
            {"Name": "", "Brand": "Brand"},  # Empty name
            {"Name": "   ", "Brand": "Brand"},  # Whitespace only
            {"Brand": "Brand"},  # No name field
        ]

        results = classifier.classify_products_batch(products_with_empty_names)

        # Should return results for all products, with empty results for invalid ones
        assert len(results) == len(products_with_empty_names)
        # Valid product should have results
        assert results[0]["category"] == "Test"
        # Invalid products should have empty results
        assert results[1] == {"category": "", "product_type": "", "product_on_pages": ""}
        assert results[2] == {"category": "", "product_type": "", "product_on_pages": ""}
        assert results[3] == {"category": "", "product_type": "", "product_on_pages": ""}

    @patch('ollama.list')
    def test_conversation_initialization(self, mock_list, unique_cache_file):
        """Test that conversation is properly initialized."""
        mock_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

        assert len(classifier.conversation_history) == 1
        assert classifier.conversation_history[0]["role"] == "system"
        assert "PRODUCT TAXONOMY" in classifier.conversation_history[0]["content"]
        assert "COMMON PRODUCT PAGES" in classifier.conversation_history[0]["content"]

    @patch('ollama.list')
    def test_cache_operations(self, mock_list, unique_cache_file):
        """Test cache loading and saving operations."""
        mock_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        # Ensure cache starts empty
        classifier.classification_cache = {}

        # Initially empty cache
        assert classifier.classification_cache == {}

        # Add something to cache
        test_key = "test|product"
        test_value = {"category": "Test", "product_type": "Test", "product_on_pages": "Test"}
        classifier.classification_cache[test_key] = test_value

        # Save cache
        classifier._save_cache()

        # Create new classifier and load cache
        classifier2 = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

        # Should load the cached data
        assert test_key in classifier2.classification_cache
        assert classifier2.classification_cache[test_key] == test_value

    @patch('ollama.list')
    def test_cache_key_generation(self, mock_list, unique_cache_file):
        """Test cache key generation."""
        mock_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

        # Test various combinations
        assert classifier._get_cache_key("Product Name", "Brand") == "Brand|Product Name"
        assert classifier._get_cache_key("Product Name", "") == "Product Name"
        assert classifier._get_cache_key("Product Name") == "Product Name"

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_json_parsing_error_handling(self, mock_chat, mock_list, unique_cache_file):
        """Test handling of malformed JSON responses."""
        mock_list.return_value = {"models": []}

        # Mock invalid JSON response
        mock_chat.return_value = {"message": {"content": "Invalid JSON response"}}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        result = classifier.classify_product("Test Product")

        # Should return empty results for parsing errors
        assert result == {"category": "", "product_type": "", "product_on_pages": ""}

    @patch('ollama.list')
    @patch('ollama.chat')
    def test_json_parsing_with_extra_text(self, mock_chat, mock_list, unique_cache_file):
        """Test JSON parsing when response contains extra text."""
        mock_list.return_value = {"models": []}

        # Mock response with extra text around JSON
        mock_chat.return_value = {
            "message": {
                "content": 'Here is the classification: {"category": "Dog Food", "product_type": "Dry Dog Food", "product_on_pages": "Dog Food Shop All"} Hope this helps!'
            }
        }

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)
        # Ensure cache starts empty
        classifier.classification_cache = {}

        result = classifier.classify_product("Test Product")

        # Should extract JSON from the middle
        assert result["category"] == "Dog Food"
        assert result["product_type"] == "Dry Dog Food"
        assert result["product_on_pages"] == "Dog Food Shop All"

    @patch('ollama.list')
    def test_reset_conversation(self, mock_list, unique_cache_file):
        """Test conversation reset functionality."""
        mock_list.return_value = {"models": []}

        classifier = LocalLLMProductClassifier("llama3.2", cache_file=unique_cache_file)

        # Add some conversation history
        classifier.conversation_history.append({"role": "user", "content": "test"})
        classifier.conversation_history.append({"role": "assistant", "content": "response"})

        assert len(classifier.conversation_history) > 1

        # Reset conversation
        classifier.reset_conversation()

        # Should be back to initial state
        assert len(classifier.conversation_history) == 1
        assert classifier.conversation_history[0]["role"] == "system"

    @patch('ollama.list')
    def test_global_classifier_instance(self, mock_list):
        """Test the global classifier instance management."""
        mock_list.return_value = {"models": []}

        # Reset global instance
        import src.core.classification.local_llm_classifier as llm_module
        llm_module._local_llm_classifier = None

        # First call should create instance
        classifier1 = get_local_llm_classifier()
        assert classifier1 is not None

        # Second call should return same instance
        classifier2 = get_local_llm_classifier()
        assert classifier1 is classifier2

    @patch('ollama.list')
    def test_global_classifier_initialization_failure(self, mock_list):
        """Test global classifier when Ollama is not available."""
        mock_list.side_effect = Exception("Ollama not running")

        # Reset global instance
        import src.core.classification.local_llm_classifier as llm_module
        llm_module._local_llm_classifier = None

        classifier = get_local_llm_classifier()
        assert classifier is None

    @patch('src.core.classification.local_llm_classifier.get_local_llm_classifier')
    def test_classify_product_local_llm_integration(self, mock_get_classifier):
        """Test the integration function for local LLM classification."""
        mock_classifier = MagicMock()
        mock_classifier.classify_product.return_value = {
            "category": "Dog Food",
            "product_type": "Dry Dog Food",
            "product_on_pages": "Dog Food Shop All"
        }
        mock_get_classifier.return_value = mock_classifier

        product_info = {"Name": "Test Dog Food", "Brand": "Test Brand"}
        result = classify_product_local_llm(product_info)

        assert result["Category"] == "Dog Food"
        assert result["Product Type"] == "Dry Dog Food"
        assert result["Product On Pages"] == "Dog Food Shop All"
        mock_classifier.classify_product.assert_called_once_with("Test Dog Food", "Test Brand")

    @patch('src.core.classification.local_llm_classifier.get_local_llm_classifier')
    def test_classify_product_local_llm_no_classifier(self, mock_get_classifier):
        """Test local LLM classification when classifier is not available."""
        mock_get_classifier.return_value = None

        product_info = {"Name": "Test Product"}
        result = classify_product_local_llm(product_info)

        assert result == {"Category": "", "Product Type": "", "Product On Pages": ""}

    @patch('src.core.classification.local_llm_classifier.get_local_llm_classifier')
    def test_classify_product_local_llm_empty_name(self, mock_get_classifier):
        """Test local LLM classification with empty product name."""
        mock_get_classifier.return_value = None  # Should not reach classifier

        product_info = {"Name": "", "Brand": "Test Brand"}
        result = classify_product_local_llm(product_info)

        assert result == {"Category": "", "Product Type": "", "Product On Pages": ""}

    @patch('src.core.classification.local_llm_classifier.get_local_llm_classifier')
    def test_classify_product_local_llm_exception_handling(self, mock_get_classifier):
        """Test exception handling in local LLM classification."""
        mock_classifier = MagicMock()
        mock_classifier.classify_product.side_effect = Exception("Classification error")
        mock_get_classifier.return_value = mock_classifier

        product_info = {"Name": "Test Product"}
        result = classify_product_local_llm(product_info)

        assert result == {"Category": "", "Product Type": "", "Product On Pages": ""}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])