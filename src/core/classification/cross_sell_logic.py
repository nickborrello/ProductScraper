"""
Product Cross-Sell Logic Module
Handles cross-sell recommendations using database filtering.
Contains non-UI business logic for cross-selling.
"""

import os
import sqlite3
from pathlib import Path

# Database path
# Adjusted DB_PATH for the new location: inventory/classification/cross_sell_logic.py
# It needs to go up three levels (classification, inventory, ProductScraper) and then into data
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "databases" / "products.db"

def get_facet_options_from_db():
    """
    Get all available categories, product types, and pages from the database.
    
    Returns:
        Tuple of (categories_list, product_types_list, pages_list)
    """
    if not DB_PATH.exists():
        return [], [], []
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Get categories
        cursor = conn.execute("""
            SELECT DISTINCT Category FROM products 
            WHERE Category IS NOT NULL AND Category != ''
        """)
        categories = []
        for row in cursor.fetchall():
            if row[0]:
                categories.extend([cat.strip() for cat in str(row[0]).split('|') if cat.strip()])
        categories = sorted(list(set(categories)), key=str.lower)
        
        # Get product types
        cursor = conn.execute("""
            SELECT DISTINCT Product_Type FROM products 
            WHERE Product_Type IS NOT NULL AND Product_Type != ''
        """)
        product_types = []
        for row in cursor.fetchall():
            if row[0]:
                product_types.extend([pt.strip() for pt in str(row[0]).split('|') if pt.strip()])
        product_types = sorted(list(set(product_types)), key=str.lower)
        
        # Get pages
        cursor = conn.execute("""
            SELECT DISTINCT Product_On_Pages FROM products 
            WHERE Product_On_Pages IS NOT NULL AND Product_On_Pages != ''
        """)
        pages = []
        for row in cursor.fetchall():
            if row[0]:
                pages.extend([page.strip() for page in str(row[0]).split('|') if page.strip()])
        pages = sorted(list(set(pages)), key=str.lower)
        
        return categories, product_types, pages
        
    finally:
        conn.close()


def query_cross_sell_candidates(category_filters, product_type_filters, page_filters, exclude_sku=None, limit=50):
    """
    Query database for cross-sell candidates based on filters.
    
    Args:
        category_filters: List of category strings to filter by
        product_type_filters: List of product type strings to filter by  
        page_filters: List of page strings to filter by
        exclude_sku: SKU to exclude from results (current product)
        limit: Maximum number of results to return
    
    Returns:
        List of dicts with product info (SKU, Name, Images, etc.)
    """
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Build WHERE clause based on filters
        where_conditions = []
        params = []
        
        # Exclude disabled products
        where_conditions.append("(ProductDisabled IS NULL OR ProductDisabled != 'checked')")
        
        # Exclude current product
        if exclude_sku:
            where_conditions.append("SKU != ?")
            params.append(exclude_sku)
        
        # Category filter - match ALL of the selected categories
        if category_filters:
            category_conditions = []
            for cat in category_filters:
                category_conditions.append("Category LIKE ?")
                params.append(f"%{cat}%")
            where_conditions.append(f"({' AND '.join(category_conditions)})")
        
        # Product Type filter - match ALL of the selected types
        if product_type_filters:
            type_conditions = []
            for pt in product_type_filters:
                type_conditions.append("Product_Type LIKE ?")
                params.append(f"%{pt}%")
            where_conditions.append(f"({' AND '.join(type_conditions)})")
        
        # Pages filter - match ALL of the selected pages
        if page_filters:
            page_conditions = []
            for page in page_filters:
                page_conditions.append("Product_On_Pages LIKE ?")
                params.append(f"%{page}%")
            where_conditions.append(f"({' AND '.join(page_conditions)})")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"""
            SELECT SKU, Name, Images, Category, Product_Type, Brand, Product_On_Pages
            FROM products 
            WHERE {where_clause}
            ORDER BY Name
            LIMIT ?
        """
        params.append(limit)
        
        cursor = conn.execute(query, params)
        results = []
        for row in cursor.fetchall():
            sku, name, images, category, product_type, brand, pages = row
            results.append({
                'SKU': sku or '',
                'Name': name or '',
                'Images': images or '',
                'Category': category or '',
                'Product_Type': product_type or '',
                'Brand': brand or '',
                'Product_On_Pages': pages or ''
            })
        
        return results
        
    finally:
        conn.close()


def get_first_image_url(images_field: str) -> str:
    """Return a usable image URL based on the Images field from the DB.

    - If images_field is a comma-separated list, take the first non-empty entry.
    - If the entry already starts with http(s) return as-is.
    - Otherwise prepend the site's media path.
    """
    if not images_field:
        return ""
    # Take first image from comma-separated list
    first = str(images_field).split(",")[0].strip()
    if not first:
        return ""
    if first.startswith(("http://", "https://")):
        return first
    # Otherwise assume it's a media path stored in DB and prepend base
    return f"https://www.baystatepet.com/media/{first}"
