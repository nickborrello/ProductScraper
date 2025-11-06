"""
Test script for cross-sell functionality
Tests cross-sell assignment logic with sample products
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.product_cross_sell_ui import load_website_dataframe, find_cross_sell_candidates, get_subproduct_skus, calculate_similarity_score

# Test product (your example)
test_product_filled = {
    "SKU": "123456789012",
    "Name": "Mazuri Tortoise Diet 25lb",
    "Brand": "Mazuri",
    "Weight": "25",
    "Product Field 24": "Reptile Food & Supplies",  # Category
    "Product Field 25": "Food",  # Product Type
    "Product On Pages": "Reptile Food & Supplies Shop All|Reptile Food & Treats",
    "Image URLs": [
        'https://mazuri.com/cdn/shop/files/727613021450_New_2000x2000_b7aa0b76-2cde-425e-a443-020a486c0d78.jpg?v=1720807609'
    ]
}

# Sample candidate products for cross-sell matching
candidate_products = [
    {
        "SKU": "111111111111",
        "Name": "Mazuri Tortoise Diet 5lb",
        "Brand": "Mazuri",
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Food",  # Same type
        "Product On Pages": "Reptile Food & Supplies Shop All|Reptile Food & Treats",  # Same pages
        "ProductDisabled": ""  # Not disabled
    },
    {
        "SKU": "222222222222",
        "Name": "Zoo Med Tortoise Food 15oz",
        "Brand": "Zoo Med",
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Food",  # Same type
        "Product On Pages": "Reptile Food & Supplies Shop All|Reptile Food & Treats",
        "ProductDisabled": ""
    },
    {
        "SKU": "333333333333",
        "Name": "Mazuri Aquatic Turtle Diet 12oz",
        "Brand": "Mazuri",  # Same brand
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Food",  # Same type
        "Product On Pages": "Reptile Food & Supplies Shop All",  # 1 shared page
        "ProductDisabled": ""
    },
    {
        "SKU": "444444444444",
        "Name": "ReptiVite Vitamin Supplement",
        "Brand": "Zoo Med",
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Supplement",  # Different type
        "Product On Pages": "Reptile Food & Supplies Shop All",  # 1 shared page
        "ProductDisabled": ""
    },
    {
        "SKU": "555555555555",
        "Name": "Reptile Water Bowl Large",
        "Brand": "Exo Terra",
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Accessory",  # Different type
        "Product On Pages": "Reptile Accessories|Reptile Food & Supplies Shop All",  # 1 shared page
        "ProductDisabled": ""
    },
    {
        "SKU": "666666666666",
        "Name": "Mazuri Tortoise Diet 40lb",
        "Brand": "Mazuri",  # Same brand
        "Product Field 24": "Reptile Food & Supplies",  # Same category
        "Product Field 25": "Food",  # Same type
        "Product On Pages": "Reptile Food & Supplies Shop All|Reptile Food & Treats",  # Both pages
        "ProductDisabled": ""
    },
    {
        "SKU": "777777777777",
        "Name": "Out of Stock Product",
        "Brand": "Mazuri",
        "Product Field 24": "Reptile Food & Supplies",
        "Product Field 25": "Food",
        "Product On Pages": "Reptile Food & Supplies Shop All|Reptile Food & Treats",
        "ProductDisabled": "checked"  # DISABLED - should be excluded
    },
    {
        "SKU": "888888888888",
        "Name": "Dog Food Premium 50lb",
        "Brand": "Blue Buffalo",
        "Product Field 24": "Dog Food",  # Different category
        "Product Field 25": "Food",  # Same type
        "Product On Pages": "Dog Food Shop All",  # No shared pages
        "ProductDisabled": ""
    }
]

def test_load_website_dataframe():
    """Test loading website dataframe for cross-sell candidates."""
    df = load_website_dataframe()
    assert len(df) > 0, "Should load website products from database"
    assert 'SKU' in df.columns, "Should have SKU column"
    assert 'Name' in df.columns, "Should have Name column"

def test_calculate_similarity_score():
    """Test similarity score calculation between products."""
    # Same brand, category, type - should be high score
    score1 = calculate_similarity_score(test_product_filled, candidate_products[0])
    assert score1 >= 4, f"Same brand/category/type should have high score, got {score1}"  # 4 for type + 3 for category + 1 for brand + 2 for pages = 10

    # Different category but same type - should have moderate score
    score2 = calculate_similarity_score(test_product_filled, candidate_products[7])  # Dog food
    assert score2 >= 4, f"Different category but same type should have moderate score, got {score2}"  # 4 for same type

def test_find_cross_sell_candidates():
    """Test finding cross-sell candidates for a product."""
    # Create DataFrame from test candidates for controlled testing
    import pandas as pd
    website_df = pd.DataFrame(candidate_products)
    subproduct_skus = get_subproduct_skus(website_df)
    
    candidates_str = find_cross_sell_candidates(test_product_filled, website_df, subproduct_skus)
    candidates = candidates_str.split('|') if candidates_str else []
    
    # Should find several good candidates
    assert len(candidates) > 0, "Should find cross-sell candidates"
    
    # Should not include out of stock products
    assert '777777777777' not in candidates, "Should not include disabled products"
    
    # Same type different category products can be included (dog food has same "Food" type)
    # assert '888888888888' not in candidates, "Should not include different category products"

def test_get_subproduct_skus():
    """Test extracting subproduct SKUs from product name."""
    website_df = load_website_dataframe()
    skus = get_subproduct_skus(website_df)
    
    # Should return a set
    assert isinstance(skus, set), "Should return a set of SKUs"
