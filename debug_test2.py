from unittest.mock import patch
from src.core.classification.manager import classify_single_product
from src.core.classification.local_llm_classifier import get_local_llm_classifier, reset_local_llm_classifier

# Reset classifier first
reset_local_llm_classifier()

# Test with manual mock
with patch('src.core.classification.local_llm_classifier.ollama.chat') as mock_chat, \
     patch('src.core.classification.local_llm_classifier.ollama.list') as mock_list, \
     patch('src.core.classification.local_llm_classifier.LocalLLMProductClassifier._load_cache') as mock_load, \
     patch('src.core.classification.local_llm_classifier.LocalLLMProductClassifier._save_cache') as mock_save:

    mock_load.return_value = {}
    mock_list.return_value = [{'name': 'llama3.2', 'size': 1000000}]
    mock_chat.return_value = {'message': {'content': '{"category": "Dog Food", "product_type": "Dry Dog Food", "product_on_pages": "Dog Food Shop All"}'}}

    product = {'Name': 'Premium Dog Food - Chicken Flavor', 'Price': '29.99', 'Category': '', 'Product Type': '', 'Product On Pages': ''}
    result = classify_single_product(product, method='local_llm')

    print('Mock called:', mock_chat.called)
    print('Call count:', mock_chat.call_count)
    print('Result:', result)

    # Also test the classifier directly
    classifier = get_local_llm_classifier()
    if classifier:
        direct_result = classifier.classify_product('Test Product')
        print('Direct classifier result:', direct_result)