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
from .taxonomy_manager import get_product_taxonomy

# Database path instead of Excel
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "databases" / "products.db"


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
        print(f"⚠️ Error loading product pages file: {e}")
        return []

# Product pages from ShopSite
PRODUCT_PAGES = get_product_pages()


def classify_products_batch(products_list, method="llm"):
    """
    Classify multiple products using specified method.

    Args:
        products_list: List of product_info dictionaries to classify
        method: Classification method - "llm" (OpenRouter API) or "local_llm" (Ollama)

    Returns:
        List of product_info dictionaries with recommended facets added
    """
    print(
        f"🤖 Batch Classification: Using {method} approach for {len(products_list)} products..."
    )

    # Special handling for local_llm method - use batch processing
    if method == "local_llm":
        try:
            from .local_llm_classifier import get_local_llm_classifier

            classifier = get_local_llm_classifier(product_taxonomy=GENERAL_PRODUCT_TAXONOMY, product_pages=PRODUCT_PAGES)
            if classifier:
                # Convert products to format expected by batch classifier
                batch_products = []
                for product in products_list:
                    batch_products.append({
                        "Name": product.get("Name", ""),
                        "Brand": product.get("Brand", "")
                    })

                # Use batch classification
                batch_results = classifier.classify_products_batch(batch_products)

                # Convert results back to expected format
                classified_products = []
                for product_info, result in zip(products_list, batch_results):
                    product_copy = product_info.copy()
                    product_copy["Category"] = result.get("category", "")
                    product_copy["Product Type"] = result.get("product_type", "")
                    product_copy["Product On Pages"] = result.get("product_on_pages", "")
                    classified_products.append(product_copy)

                print(
                    f"\033[92m✅ Local_Llm batch classification complete! Processed {len(classified_products)} products\033[0m\n"
                )
                return classified_products
            else:
                print("⚠️ Local LLM classifier not available, leaving products unclassified")
        except Exception as e:
            print(f"⚠️ Local LLM batch classification failed: {e}, leaving products unclassified")

    # Default: process each product individually
    classified_products = []

    for idx, product_info in enumerate(products_list, 1):
        product_name = product_info.get("Name", "Unknown")
        print(f"  Analyzing {idx}/{len(products_list)}: {product_name[:50]}...")

        # Use specified classification method
        classified_product = classify_single_product(product_info.copy(), method=method)
        classified_products.append(classified_product)

    print(
        f"\033[92m✅ {method.title()} batch classification complete! Processed {len(classified_products)} products\033[0m\n"
    )
    return classified_products


def classify_single_product(product_info, method="llm"):
    """
    Classify a single product using LLM classification.

    Args:
        product_info: Dict with product details
        method: Classification method - "llm" (OpenRouter API) or "local_llm" (Ollama)

    Returns:
        Dict: Product_info with recommended facets added
    """
    product_name = product_info.get("Name", "").strip()

    # LLM-based classification (most accurate)
    if method == "llm":
        try:
            from .llm_classifier import classify_product_llm

            llm_result = classify_product_llm(product_info)

            # Apply LLM results
            for label in ["Category", "Product Type", "Product On Pages"]:
                if label in llm_result and llm_result[label]:
                    product_info[label] = llm_result[label]
                else:
                    product_info[label] = ""

            print(
                f"🧠 LLM classification: {product_name[:40]}... → {product_info.get('Category', 'N/A')}"
            )
            return product_info

        except Exception as e:
            print(f"⚠️ LLM classification failed: {e}")
            # Leave product unclassified instead of falling back to fuzzy matching

    # Local LLM-based classification (Ollama - no API key required)
    elif method == "local_llm":
        try:
            from .local_llm_classifier import classify_product_local_llm

            llm_result = classify_product_local_llm(product_info, product_taxonomy=GENERAL_PRODUCT_TAXONOMY, product_pages=PRODUCT_PAGES)

            # Apply LLM results
            for label in ["Category", "Product Type", "Product On Pages"]:
                if label in llm_result and llm_result[label]:
                    product_info[label] = llm_result[label]
                else:
                    product_info[label] = ""

            print(
                f"🏠 Local LLM classification: {product_name[:40]}... → {product_info.get('Category', 'N/A')}"
            )
            return product_info

        except Exception as e:
            print(f"⚠️ Local LLM classification failed: {e}")
            # Leave product unclassified instead of falling back to fuzzy matching

    # No fallback - leave product unclassified
    print(f"⚠️ No classification method available for: {product_name[:40]}...")
    return product_info


# Test section - run this file directly to test classification
if __name__ == "__main__":
    print("🧪 Testing Product Classification System")
    print("=" * 50)

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

    print("📦 Test Product:")
    print(f"   Name: {test_product['Name']}")
    print(f"   Brand: {test_product['Brand']}")
    print()

    # Test single product classification (LLM method)
    print("🔍 Testing LLM classification...")
    classified_product = classify_single_product(test_product.copy(), method="llm")

    print("📊 LLM Classification Results:")
    print(f"   Category: {classified_product.get('Category', 'None')}")
    print(f"   Product Type: {classified_product.get('Product Type', 'None')}")
    print(f"   Product On Pages: {classified_product.get('Product On Pages', 'None')}")
    print()

    # Test batch classification
    print("📋 Testing batch classification...")
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

    classified_batch = classify_products_batch(test_products, method="llm")

    print("📊 Batch Classification Results:")
    for i, product in enumerate(classified_batch, 1):
        print(f"   Product {i}: {product['Name'][:40]}...")
        print(f"      Category: {product.get('Category', 'None')}")
        print(f"      Product Type: {product.get('Product Type', 'None')}")
        print(f"      Product On Pages: {product.get('Product On Pages', 'None')}")
        print()

    print("✅ Test completed!")
