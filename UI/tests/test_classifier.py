#!/usr/bin/env python3
"""
Test script for the product classifier module.
Tests the classification functionality with mock data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import classify_products_batch, classify_single_product, load_classified_dataframe, find_matching_products_and_recommendations

def test_load_classified_dataframe():
    """Test loading classified products from database."""
    df = load_classified_dataframe()
    assert len(df) > 0, "Should load classified products from database"
    assert 'Name' in df.columns, "Should have Name column"
    assert 'Product Field 24' in df.columns, "Should have Category column"
    assert 'Product Field 25' in df.columns, "Should have Product Type column"
    print(f"✅ Loaded {len(df)} classified products from database")

def test_classify_single_product():
    """Test classifying a single product."""
    test_product = {
        'SKU': 'TEST001',
        'Name': 'Blue Buffalo Dog Food Chicken',
        'Brand': 'Blue Buffalo',
        'Weight': '30 lb',
        'Image URLs': ['https://example.com/image1.jpg'],
        'Category': '',
        'Product Type': '',
        'Product On Pages': '',
        'Special Order': '',
        'Product Disabled': 'uncheck'
    }

    # Should start with empty categories
    assert test_product['Category'] == ''
    assert test_product['Product Type'] == ''

    classified_product = classify_single_product(test_product)

    # Should now have categories filled in
    assert classified_product['Category'] != '', "Should have category assigned"
    assert classified_product['Product Type'] != '', "Should have product type assigned"
    print(f"✅ Classified single product: {classified_product['Name']}")

def test_classify_products_batch():
    """Test classifying multiple products in batch."""
    mock_products = [
        {
            'SKU': 'TEST001',
            'Name': 'Blue Buffalo Dog Food Chicken',
            'Brand': 'Blue Buffalo',
            'Weight': '30 lb',
            'Image URLs': ['https://example.com/image1.jpg'],
            'Category': '',
            'Product Type': '',
            'Product On Pages': '',
            'Special Order': '',
            'Product Disabled': 'uncheck'
        },
        {
            'SKU': 'TEST002',
            'Name': 'Purina Pro Plan Cat Food Salmon',
            'Brand': 'Purina',
            'Weight': '15 lb',
            'Image URLs': ['https://example.com/image2.jpg'],
            'Category': '',
            'Product Type': '',
            'Product On Pages': '',
            'Special Order': '',
            'Product Disabled': 'uncheck'
        },
        {
            'SKU': 'TEST003',
            'Name': 'Unknown Brand Rabbit Food',
            'Brand': 'Unknown Brand',
            'Weight': '5 lb',
            'Image URLs': ['https://example.com/image3.jpg'],
            'Category': '',
            'Product Type': '',
            'Product On Pages': '',
            'Special Order': '',
            'Product Disabled': 'uncheck'
        }
    ]

    classified_batch = classify_products_batch(mock_products)

    assert len(classified_batch) == 3, "Should return same number of products"

    # First two should be classified
    assert classified_batch[0]['Category'] != '', "First product should have category"
    assert classified_batch[1]['Category'] != '', "Second product should have category"

    # Third should not be classified (unknown brand)
    assert classified_batch[2]['Category'] == '', "Third product should not be classified"
    print(f"✅ Batch classified {len(classified_batch)} products")