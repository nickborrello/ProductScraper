"""
Product Classification & Editor Package

This package provides product classification and interactive editing functionality.

Classifier Functions (Data Only - NO UI):
- classify_products_batch: Batch classify products, returns data with facets added
- classify_single_product: Classify single product, returns data with facets added
- find_matching_products_and_recommendations: Fuzzy matching logic
- load_classified_dataframe: Load the product database

Cross-Sell Functions (Data Only - NO UI):
- assign_cross_sells_batch: Assign cross-sells to multiple products
- assign_cross_sells_single: Assign cross-sells to single product

Editor Functions (UI Only - NO Classification):
- product_editor_interactive: Edit single product with UI (accepts SKU string or product data dict)
- edit_products_in_batch: Edit multiple products with UI (accepts list of SKUs or product data dicts)

Usage in master.py:
    from UI import classify_products_batch, assign_cross_sells_batch
    from UI.product_editor import edit_products_in_batch

    # Step 1: Auto-classify (adds Category, Product Type, Product On Pages)
    classified_products = classify_products_batch(products)

    # Step 2: User reviews/edits in UI (now accepts product data directly)
    reviewed_products = edit_products_in_batch(classified_products)

    # Step 3: Assign cross-sells (adds Product Field 32)
    final_products = assign_cross_sells_batch(reviewed_products)
"""

from src.core.classification.manager import (
    classify_products_batch,
    classify_single_product,
    RECOMMEND_COLS,
)

from src.core.cross_sell.ui import (
    assign_cross_sells_batch,
    assign_cross_sells_single,
    CROSS_SELL_FIELD,
    MAX_CROSS_SELLS,
)

from .product_editor import product_editor_interactive, edit_products_in_batch

__all__ = [
    "classify_products_batch",
    "classify_single_product",
    "assign_cross_sells_batch",
    "assign_cross_sells_single",
    "product_editor_interactive",
    "edit_products_in_batch",
    "RECOMMEND_COLS",
    "CROSS_SELL_FIELD",
    "MAX_CROSS_SELLS",
]
