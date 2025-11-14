"""
Product Classification Module
Handles LLM-based classification and batch processing coordination.
Separates business logic from UI (product_editor.py).
"""

import json
import os
import pandas as pd
import re
import sqlite3
from pathlib import Path
from typing import List

# Import taxonomy manager
try:
    # Try relative import first (when run as part of package)
    from .taxonomy_manager import get_product_taxonomy
except ImportError:
    try:
        # Try absolute import (when run as standalone script)
        from src.core.classification.taxonomy_manager import get_product_taxonomy
    except ImportError:
        # Last resort - try direct import from current directory
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from taxonomy_manager import get_product_taxonomy

# Ensure src directory is in path for standalone execution
import sys
import os
src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import settings manager
try:
    from src.core.settings_manager import settings
    _settings_available = True
except ImportError:
    try:
        # Fallback for when run as standalone
        from ..settings_manager import settings
        _settings_available = True
    except ImportError:
        # Last resort - try to load from settings.json directly
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent.parent / "settings.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                _config = json.load(f)
                _classification_method = _config.get("classification_method", "llm")
        else:
            _classification_method = "llm"
        _settings_available = False

# Database path instead of Excel
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "databases" / "products.db"


# Unified prompts for all LLM classifiers
UNIFIED_SYSTEM_PROMPT = """You are an expert e-commerce product classifier for a retail store.

{taxonomy_text}

{pages_text}

CLASSIFICATION RULES:
1. **Prioritize the existing taxonomy.** If a product fits well into an existing category or product type, you must use it.
2. If no suitable option exists, you may suggest a new one.
3. If you are uncertain, it is better to choose the closest existing match rather than creating a new one.

CRITICAL: You must respond with valid JSON only. No explanations, no markdown, no additional text.
"""

UNIFIED_SINGLE_PRODUCT_JSON_FORMAT = """
Return classifications in this exact JSON format:
{{
    "category": "Main Category Name",
    "product_type": "Product Type 1|Product Type 2",
    "product_on_pages": "Page 1|Page 2|Page 3"
}}

Example valid response: {{"category": "Dog Food", "product_type": "Dry Dog Food|Adult Dog Food", "product_on_pages": "Dog Food|All Pets|Pet Supplies"}}"""

UNIFIED_BATCH_JSON_FORMAT = """Return classifications in this exact JSON format:
{
  "classifications": [
    {
      "product_index": 1,
      "category": "Main Category",
      "product_type": "Type 1|Type 2",
      "product_on_pages": "Page 1|Page 2|Page 3"
    },
    {
      "product_index": 2,
      "category": "Main Category",
      "product_type": "Type 1|Type 2",
      "product_on_pages": "Page 1|Page 2|Page 3"
    }
  ]
}

CRITICAL: Respond with valid JSON only. No explanations, no markdown, no additional text."""


RECOMMEND_COLS = [
    ("Category", "Category"),
    ("Product_Type", "Product Type"),
    ("Product_On_Pages", "Product On Pages"),
]


# Centralized product taxonomy - shared between all classifiers
GENERAL_PRODUCT_TAXONOMY = get_product_taxonomy()

def get_product_pages() -> List[str]:
    """
    Load product pages from JSON file

    Returns:
        List of product page names
    """
    pages_file = Path(__file__).parent.parent.parent.parent / "src" / "data" / "product_pages.json"
    try:
        with open(pages_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARNING] Error loading product pages file: {e}")
        return []

# Product pages from ShopSite
PRODUCT_PAGES = get_product_pages()


def classify_products_batch(products_list, method=None):
    """
    Classify multiple products using specified method.

    Args:
        products_list: List of product_info dictionaries to classify
        method: Classification method - "llm" (OpenRouter API), "local_llm" (Ollama), "mock" (for testing). If None, uses settings.

    Returns:
        List of product_info dictionaries with recommended facets added
    """
    # Use settings if no method specified
    if method is None:
        if _settings_available:
            method = settings.get("classification_method", "llm")
        else:
            method = _classification_method
    
    print(
        f"[CLASSIFY] Batch Classification: Using {method} approach for {len(products_list)} products..."
    )

    # Special handling for llm method - use batch processing
    if method == "llm":
        try:
            from src.core.classification.llm_classifier import get_llm_classifier
        except ImportError:
            try:
                from llm_classifier import get_llm_classifier
            except ImportError:
                print(f"[WARNING] Could not import LLM classifier")
                # Fall through to individual processing

        try:
            classifier = get_llm_classifier(product_taxonomy=GENERAL_PRODUCT_TAXONOMY, product_pages=PRODUCT_PAGES)
            if classifier:
                # Create batches with merging logic for last small batch
                batch_size = 15
                min_batch_size = 10
                batches = [products_list[i:i + batch_size] for i in range(0, len(products_list), batch_size)]
                if len(batches) > 1 and len(batches[-1]) < min_batch_size:
                    batches[-2].extend(batches[-1])
                    batches.pop()

                # Process each batch
                classified_products = []
                for batch in batches:
                    batch_results = classifier.classify_products_batch(batch)
                    classified_products.extend(batch_results)

                print(
                    f"[SUCCESS] LLM batch classification complete! Processed {len(classified_products)} products\n"
                )
                return classified_products
            else:
                print("[WARNING] LLM classifier not available, leaving products unclassified")
        except Exception as e:
            print(f"[WARNING] LLM batch classification failed: {e}, leaving products unclassified")

    # Special handling for local_llm method - use batch processing
    if method == "local_llm":
        try:
            from src.core.classification.local_llm_classifier import get_local_llm_classifier
        except ImportError:
            try:
                from local_llm_classifier import get_local_llm_classifier
            except ImportError:
                print(f"[WARNING] Could not import local LLM classifier")
                # Fall through to individual processing

        try:
            classifier = get_local_llm_classifier(product_taxonomy=GENERAL_PRODUCT_TAXONOMY, product_pages=PRODUCT_PAGES)
            if classifier:
                # Create batches with merging logic for last small batch
                batch_size = 15
                min_batch_size = 10
                batches = [products_list[i:i + batch_size] for i in range(0, len(products_list), batch_size)]
                if len(batches) > 1 and len(batches[-1]) < min_batch_size:
                    batches[-2].extend(batches[-1])
                    batches.pop()

                # Process each batch
                classified_products = []
                for batch in batches:
                    # Convert to format expected by batch classifier
                    batch_products = []
                    for product in batch:
                        batch_products.append({
                            "Name": product.get("Name", ""),
                            "Brand": product.get("Brand", "")
                        })

                    # Use batch classification
                    batch_results = classifier.classify_products_batch(batch_products)

                    # Convert results back to expected format
                    for product_info, result in zip(batch, batch_results):
                        product_copy = product_info.copy()
                        product_copy["Category"] = result.get("category", "")
                        product_copy["Product Type"] = result.get("product_type", "")
                        product_copy["Product On Pages"] = result.get("product_on_pages", "")
                        classified_products.append(product_copy)

                print(
                    f"[SUCCESS] Local_Llm batch classification complete! Processed {len(classified_products)} products\n"
                )
                return classified_products
            else:
                print("[WARNING] Local LLM classifier not available, leaving products unclassified")
        except Exception as e:
            print(f"[WARNING] Local LLM batch classification failed: {e}, leaving products unclassified")

    # Default: process each product individually
    classified_products = []

    for idx, product_info in enumerate(products_list, 1):
        product_name = product_info.get("Name", "Unknown")
        print(f"  Analyzing {idx}/{len(products_list)}: {product_name[:50]}...")

        # Use specified classification method
        classified_product = classify_single_product(product_info.copy(), method=method)
        classified_products.append(classified_product)

    print(
        f"[SUCCESS] {method.title()} batch classification complete! Processed {len(classified_products)} products\n"
    )
    return classified_products


def classify_single_product(product_info, method=None):
    """
    Classify a single product using LLM classification.

    Args:
        product_info: Dict with product details
        method: Classification method - "llm" (OpenRouter API), "local_llm" (Ollama), "mock" (for testing). If None, uses settings.

    Returns:
        Dict: Product_info with recommended facets added
    """
    # Use settings if no method specified
    if method is None:
        if _settings_available:
            method = settings.get("classification_method", "llm")
        else:
            method = _classification_method
    
    product_name = product_info.get("Name", "").strip()

    # LLM-based classification (most accurate)
    if method == "llm":
        try:
            from src.core.classification.llm_classifier import classify_product_llm
        except ImportError:
            try:
                from llm_classifier import classify_product_llm
            except ImportError:
                print(f"[WARNING] Could not import LLM classifier")
                return product_info

        try:
            llm_result = classify_product_llm(product_info)

            # Apply LLM results
            for label in ["Category", "Product Type", "Product On Pages"]:
                if label in llm_result and llm_result[label]:
                    product_info[label] = llm_result[label]
                else:
                    product_info[label] = ""

            print(
                f"[LLM] LLM classification: {product_name[:40]}... -> {product_info.get('Category', 'N/A')}"
            )
            return product_info
        except Exception as e:
            print(f"[WARNING] LLM classification failed: {e}")
            # Leave product unclassified instead of falling back to fuzzy matching

    # Local LLM-based classification (Ollama - no API key required)
    elif method == "local_llm":
        try:
            from src.core.classification.local_llm_classifier import classify_product_local_llm
        except ImportError:
            try:
                from local_llm_classifier import classify_product_local_llm
            except ImportError:
                print(f"[WARNING] Could not import local LLM classifier")
                return product_info

        try:
            llm_result = classify_product_local_llm(product_info, product_taxonomy=GENERAL_PRODUCT_TAXONOMY, product_pages=PRODUCT_PAGES)

            # Apply LLM results
            product_info["Category"] = llm_result.get("Category", "")
            product_info["Product Type"] = llm_result.get("Product Type", "")
            product_info["Product On Pages"] = llm_result.get("Product On Pages", "")

            print(
                f"[LOCAL] Local LLM classification: {product_name[:40]}... -> {product_info.get('Category', 'N/A')}"
            )
            return product_info
        except Exception as e:
            print(f"[WARNING] Local LLM classification failed: {e}")
            # Leave product unclassified instead of falling back to fuzzy matching

    # Mock classification (for testing without API keys)
    elif method == "mock":
        # Return mock classification data for testing
        product_info["Category"] = "Dog Food|Pet Food"
        product_info["Product Type"] = "Dry Dog Food"
        product_info["Product On Pages"] = "Dog Food|All Pets"

        print(
            f"[MOCK] Mock classification: {product_name[:40]}... -> {product_info.get('Category', 'N/A')}"
        )
        return product_info

    return product_info


# Test section - run this file directly to test classification
if __name__ == "__main__":
    print("TEST: Testing Product Classification System")
    print("=" * 50)

    # Test 1: Verify manager doesn't open UI (pure business logic)
    print("TEST 1: Verifying manager is pure business logic (no UI)...")
    try:
        # Import check - manager should not import any UI components
        import sys
        ui_modules = [name for name in sys.modules.keys() if 'ui' in name.lower() or 'qt' in name.lower() or 'tkinter' in name.lower()]
        if ui_modules:
            print(f"WARNING: Manager imported UI modules: {ui_modules}")
        else:
            print("PASS: Manager correctly imports no UI components")

        # Function signature check - should return data, not show dialogs
        result = classify_single_product({"Name": "Test Product"}, method="mock")
        if isinstance(result, dict) and "Category" in result:
            print("PASS: Manager returns classification data (not UI)")
        else:
            print("WARNING: Manager returned unexpected format")

    except Exception as e:
        print(f"FAIL: UI isolation test failed: {e}")

    print()

    # Create a test product
    test_product = {
        "Name": "Purina Pro Plan Adult Dog Food Chicken & Rice Formula",
        "Brand": "Purina",
        "SKU": "TEST001",
        "Price": "$29.99",
        "Weight": "30 LB",
        "Images": "https://example.com/image1.jpg",
        "Special Order": "",
        "Category": "",  # Will be filled by classification
        "Product Type": "",  # Will be filled by classification
        "Product On Pages": "",  # Will be filled by classification
    }

    print("PRODUCT: Test Product:")
    print(f"   Name: {test_product['Name']}")
    print(f"   Brand: {test_product['Brand']}")
    print()

    # Test 2: Single product classification (using settings method)
    print("TEST 2: Testing classification with settings method...")
    try:
        classified_product = classify_single_product(test_product.copy())

        print("RESULTS: Classification Results:")
        print(f"   Category: {classified_product.get('Category', 'None')}")
        print(f"   Product Type: {classified_product.get('Product Type', 'None')}")
        print(f"   Product On Pages: {classified_product.get('Product On Pages', 'None')}")

        # Verify classification added expected fields
        expected_fields = ["Category", "Product Type", "Product On Pages"]
        missing_fields = [field for field in expected_fields if not classified_product.get(field)]
        if missing_fields:
            print(f"WARNING: Missing classification fields: {missing_fields}")
        else:
            print("PASS: All expected classification fields present")

    except Exception as e:
        print(f"FAIL: Auto classification test failed: {e}")

    print()

    # Test 3: Batch classification
    print("TEST 3: Testing batch classification...")
    try:
        test_products = [
            test_product.copy(),
            {
                "Name": "Royal Canin Indoor Adult Cat Food",
                "Brand": "Royal Canin",
                "SKU": "TEST002",
                "Price": "$24.99",
                "Weight": "15 LB",
                "Images": "https://example.com/image2.jpg",
                "Special Order": "",
                "Category": "",
                "Product Type": "",
                "Product On Pages": "",
            },
        ]

        classified_batch = classify_products_batch(test_products)

        print("RESULTS: Batch Classification Results:")
        for i, product in enumerate(classified_batch, 1):
            print(f"   Product {i}: {product['Name'][:40]}...")
            print(f"      Category: {product.get('Category', 'None')}")
            print(f"      Product Type: {product.get('Product Type', 'None')}")
            print(f"      Product On Pages: {product.get('Product On Pages', 'None')}")

        # Verify batch processing
        if len(classified_batch) == len(test_products):
            print("PASS: Batch processing returned correct number of products")
        else:
            print(f"FAIL: Batch processing failed: expected {len(test_products)}, got {len(classified_batch)}")

        # Verify all products have classification
        unclassified = [i for i, p in enumerate(classified_batch) if not any(p.get(field) for field in expected_fields)]
        if unclassified:
            print(f"WARNING: Products {unclassified} appear unclassified")
        else:
            print("PASS: All products in batch have classification data")

    except Exception as e:
        print(f"FAIL: Batch classification test failed: {e}")

    print()

    # Test 4: Error handling
    print("TEST 4: Testing error handling...")
    try:
        # Test with invalid method
        result = classify_single_product(test_product.copy(), method="invalid_method")
        if result.get("Category") == "":  # Should be empty/unclassified
            print("PASS: Invalid method handled gracefully")
        else:
            print("WARNING: Invalid method should leave product unclassified")

        # Test with empty product
        result = classify_single_product({})
        if result.get("Category") == "":
            print("PASS: Empty product handled gracefully")
        else:
            print("WARNING: Empty product should be unclassified")

    except Exception as e:
        print(f"FAIL: Error handling test failed: {e}")

    print()
    print("PASS: All tests completed!")
