"""
Product Classification Module
Handles fuzzy matching, recommendations, and batch classification coordination.
Separates business logic from UI (product_editor.py).
"""

import os
import pandas as pd
from rapidfuzz import fuzz
import re
import sqlite3
from pathlib import Path

# Database path instead of Excel
DB_PATH = Path(__file__).parent.parent.parent / "data" / "databases" / "products.db"

RECOMMEND_COLS = [
    ("Category", "Category"),
    ("Product_Type", "Product Type"),
    ("Product_On_Pages", "Product On Pages")
]


def clean_text(text):
    """Clean text for fuzzy matching by removing punctuation and stopwords."""
    text = str(text).lower().strip()
    text = re.sub(r'[^a-z0-9 ]', '', text)
    stopwords = {'the', 'and', 'of', 'with', 'for', 'to', 'in'}
    tokens = [w for w in text.split() if w not in stopwords]
    return ' '.join(tokens)


def product_similarity(name1, brand1, name2, brand2):
    """Calculate similarity score between two products based on name and brand.
    Pet-related keywords get significantly higher weight for better matching.
    """
    name1_clean = clean_text(name1)
    name2_clean = clean_text(name2)
    brand1_clean = clean_text(brand1)
    brand2_clean = clean_text(brand2)

    # Pet-related keywords that should have high matching weight
    pet_keywords = {
        'dog', 'cat', 'puppy', 'kitten', 'canine', 'feline',
        'bird', 'avian', 'parrot', 'cockatiel', 'budgie',
        'fish', 'aquatic', 'tropical', 'goldfish',
        'small animal', 'rabbit', 'guinea pig', 'hamster', 'gerbil',
        'reptile', 'snake', 'lizard', 'turtle', 'tortoise',
        'horse', 'equine', 'pony'
    }

    # Calculate base scores
    brand_score = fuzz.ratio(brand1_clean, brand2_clean)
    name_score = fuzz.token_set_ratio(name1_clean, name2_clean)

    # Extract pet keywords from both names
    name1_words = set(name1_clean.split())
    name2_words = set(name2_clean.split())
    name1_pet_words = name1_words & pet_keywords
    name2_pet_words = name2_words & pet_keywords

    # Calculate pet keyword matching bonus
    pet_match_bonus = 0
    if name1_pet_words and name2_pet_words:
        # Perfect match if they share any pet keywords
        if name1_pet_words & name2_pet_words:
            pet_match_bonus = 100  # Maximum bonus for matching pet types
        else:
            # Partial bonus if they have different pet keywords (less relevant)
            pet_match_bonus = 20

    # Enhanced scoring: pet keywords get much higher weight
    # Base weights: brand 60%, name 40%
    # But pet matching can boost the score significantly
    base_score = 0.6 * brand_score + 0.4 * name_score

    # Apply pet matching bonus (weighted heavily)
    final_score = base_score + (pet_match_bonus * 0.3)  # 30% weight for pet matching

    # Cap at 100
    return min(final_score, 100.0)


def find_matching_products_and_recommendations(product_info, classified_df):
    """
    Find matching products and get recommendations WITHOUT opening UI.
    Returns tuple of (matches, matched_rows, top_options, recommended_items).
    
    Args:
        product_info: Dict with product details (Name, Brand, etc.)
        classified_df: DataFrame with previously classified products
    
    Returns:
        tuple: (matches, matched_rows, top_options, recommended_items)
            - matches: List of top 5 matching product names
            - matched_rows: DataFrame rows for matched products
            - top_options: Dict of top values for each facet column
            - recommended_items: Dict of recommended facet selections from best match
    """
    product_name = product_info.get("Name", "")
    product_brand = product_info.get("Brand", "")
    
    # Build tuples of (brand, name) from DataFrame rows
    classified_pairs = []
    for idx, row in classified_df.iterrows():
        name = row.get("Name", "")
        brand = row.get("Brand", "")
        if pd.notna(name):
            classified_pairs.append((brand, name))

    # Score all pairs based on both brand AND name similarity
    scored = []
    seen_names = set()
    for b, n in classified_pairs:
        if n in seen_names:
            continue
        seen_names.add(n)
        score = product_similarity(product_name, product_brand, n, b)
        scored.append((score, n))
    
    # Get top 5 matches above threshold (75 - more strict to avoid false matches)
    scored.sort(reverse=True)
    matches = [n for score, n in scored[:5] if score > 75]
    matched_rows = classified_df[classified_df["Name"].isin(matches)] if matches else pd.DataFrame()
    
    # Get top options for each facet
    def get_top_values(matched_rows, col, top_n=5):
        if col in matched_rows.columns:
            values = matched_rows[col].dropna().value_counts().index.tolist()
            return values[:top_n]
        return []
    
    top_options = {label: get_top_values(matched_rows, col) for col, label in RECOMMEND_COLS}
    
    # Get recommended items from TOP MATCHES - select most common values
    recommended_items = {}
    if matches and not matched_rows.empty:
        # Use top 3 matches to find most common values
        top_matches = matches[:3]  # Use top 3 for better consensus
        
        # Collect all values from top matches
        field_values = {label: [] for _, label in RECOMMEND_COLS}
        
        for match_name in top_matches:
            match_row = matched_rows[matched_rows["Name"] == match_name]
            if not match_row.empty:
                match_data = match_row.iloc[0]
                
                for field, label in RECOMMEND_COLS:
                    if field in match_data.index:
                        value = match_data[field]
                        if pd.notna(value) and str(value).strip():
                            # Split on pipe first, then split each part on comma to get individual items
                            all_items = []
                            pipe_parts = str(value).split('|')
                            for part in pipe_parts:
                                # Split each pipe part on comma to handle comma-separated values
                                comma_parts = [item.strip() for item in part.split(',') if item.strip()]
                                all_items.extend(comma_parts)
                            field_values[label].extend(all_items)
        
        # For each field, find the most common value
        for label, values in field_values.items():
            if values:
                # Count frequency of each value
                from collections import Counter
                value_counts = Counter(values)
                # Get the most common value (if tie, takes first one)
                most_common_value = value_counts.most_common(1)[0][0]
                # Normalize case for consistency
                if label == "Product Type":
                    most_common_value = most_common_value.title()  # Capitalize first letter
                recommended_items[label] = [most_common_value]
    
    return matches, matched_rows, top_options, recommended_items


def load_classified_dataframe():
    """
    Load the classified products from the database.
    
    Returns:
        pandas.DataFrame: Classified products data with columns matching Excel format
    """
    if not DB_PATH.exists():
        print(f"❌ Database file not found: {DB_PATH}")
        print("Creating empty DataFrame for classification...")
        return pd.DataFrame(columns=["Name", "Product Field 16", "Product Field 24", "Product Field 25", "Product On Pages"])
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Ensure UTF-8 handling
        conn.text_factory = str
        
        # Query products that have classification data (Category and/or Product Type filled)
        cursor = conn.execute("""
            SELECT Name, Brand, Category, Product_Type, Product_On_Pages
            FROM products
            WHERE (Category IS NOT NULL AND Category != '')
               OR (Product_Type IS NOT NULL AND Product_Type != '')
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ No classified products found in database")
            return pd.DataFrame(columns=["Name", "Product Field 16", "Product Field 24", "Product Field 25", "Product On Pages"])
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=["Name", "Brand", "Category", "Product_Type", "Product_On_Pages"])
        
        print(f"✅ Loaded {len(df)} classified products from database")
        return df
    
    finally:
        conn.close()


def get_default_pet_food_classifications(product_info):
    """
    Provide default classifications based on similar products found in database.
    Strictly database-driven - no hardcoded categories or product types.

    Args:
        product_info: Dict with product details (Name, Brand, etc.)

    Returns:
        Dict of classifications from similar database products, or None if no similar products found
    """
    product_name = product_info.get('Name', '').strip()
    product_brand = product_info.get('Brand', '').strip()

    if not product_name:
        return None

    # Load classified products from database
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    try:
        # Get all classified products
        cursor = conn.execute("""
            SELECT Name, Brand, Category, Product_Type, Product_On_Pages
            FROM products
            WHERE Category IS NOT NULL AND Category != ''
            ORDER BY Name
        """)

        classified_products = cursor.fetchall()
        if not classified_products:
            return None

        # Find products with similar names or brands
        similar_products = []
        
        # Extract pet types dynamically from database products (no hardcoded defaults)
        db_pet_types = set()
        for db_name, db_brand, db_category, db_type, db_pages in classified_products:
            if db_name:
                db_name_lower = str(db_name).lower()
                db_category_lower = str(db_category or '').lower()
                
                # Extract pet types from product names and categories
                for potential_pet in ['dog', 'cat', 'bird', 'fish', 'small animal', 'reptile', 'horse']:
                    if potential_pet in db_name_lower or potential_pet in db_category_lower:
                        db_pet_types.add(potential_pet)
        
        # Determine the pet type of the input product by matching against database pet types
        input_pet_type = None
        input_name_lower = product_name.lower()
        for pet_type in db_pet_types:
            if pet_type in input_name_lower:
                input_pet_type = pet_type
                break

        for db_name, db_brand, db_category, db_type, db_pages in classified_products:
            if not db_name:
                continue

            # Filter to only include products with the same pet type (dynamically determined)
            if input_pet_type:
                db_name_lower = str(db_name).lower()
                db_category_lower = str(db_category or '').lower()
                if input_pet_type not in db_name_lower and input_pet_type not in db_category_lower:
                    continue  # Skip products that don't match the pet type

            # Calculate similarity scores
            name_similarity = product_similarity(product_name, product_brand, str(db_name), str(db_brand or ''))

            # Consider products with similarity > 85 as similar (more restrictive for defaults)
            if 85 <= name_similarity < 95:  # Higher threshold, exclude exact matches
                similar_products.append((name_similarity, db_category, db_type, db_pages))

        if not similar_products:
            return None

        # Sort by similarity (highest first) and take top matches
        similar_products.sort(reverse=True)
        top_similar = similar_products[:5]  # Use top 5 most similar products

        # Aggregate classifications from similar products
        categories = set()
        product_types = set()
        pages = set()

        for _, db_category, db_type, db_pages in top_similar:
            if db_category:
                categories.update(str(db_category).split('|'))
            if db_type:
                product_types.update(str(db_type).split('|'))
            if db_pages:
                pages.update(str(db_pages).split('|'))

        # Only return classifications if we found meaningful data
        if categories or product_types or pages:
            from collections import Counter
            
            classifications = {}
            if categories:
                # Select most common category
                category_counts = Counter(categories)
                classifications['Category'] = [category_counts.most_common(1)[0][0]]
            if product_types:
                # Select most common product type
                type_counts = Counter(product_types)
                most_common_type = type_counts.most_common(1)[0][0]
                classifications['Product Type'] = [most_common_type.title()]  # Normalize case
            if pages:
                # Flatten all page groups into individual pages, then select most common
                all_individual_pages = []
                for page_group in pages:
                    # Split each group on comma to get individual pages
                    individual_pages = [page.strip() for page in str(page_group).split(',') if page.strip()]
                    all_individual_pages.extend(individual_pages)
                
                # Count individual pages and select top 3 most common
                page_counts = Counter(all_individual_pages)
                top_individual_pages = [page for page, _ in page_counts.most_common(3)]
                classifications['Product On Pages'] = top_individual_pages
            return classifications

    finally:
        conn.close()

    return None


def classify_products_batch(products_list):
    """
    Classify multiple products using hybrid AI + Fuzzy matching approach.
    Uses AI for primary classification, falls back to fuzzy matching for edge cases.
    
    Args:
        products_list: List of product_info dictionaries to classify
    
    Returns:
        List of product_info dictionaries with recommended facets added
    """
    print(f"🤖 Batch Classification: Using AI + Fuzzy hybrid approach for {len(products_list)} products...")
    
    classified_products = []
    
    for idx, product_info in enumerate(products_list, 1):
        product_name = product_info.get('Name', 'Unknown')
        print(f"  Analyzing {idx}/{len(products_list)}: {product_name[:50]}...")
        
        # Use hybrid classification (AI first, fuzzy fallback)
        classified_product = classify_single_product(product_info.copy())
        classified_products.append(classified_product)
    
    print(f"\033[92m✅ Hybrid batch classification complete! Processed {len(classified_products)} products\033[0m\n")
    return classified_products


def classify_single_product(product_info):
    """
    Classify a single product using hybrid AI + Fuzzy matching approach.
    Uses AI for primary classification, falls back to fuzzy matching for edge cases.
    
    Args:
        product_info: Dict with product details
    
    Returns:
        Dict: Product_info with recommended facets added
    """
    product_name = product_info.get('Name', '').strip()
    
    # First try AI classification (fast and accurate)
    ai_confidence = 0
    try:
        from .ai_classifier import classify_product_ai
        ai_result = classify_product_ai(product_info)
        
        # Check AI confidence - if AI gives results but they seem wrong, reduce confidence
        if ai_result and any(ai_result.values()):
            # Simple heuristic: check if product name keywords match predicted category
            product_lower = product_name.lower()
            category = ai_result.get('Category', '').lower()
            
            # If product mentions "reptile" but AI says "dog", very low confidence
            pet_keywords = {
                'dog': ['dog', 'puppy', 'canine'],
                'cat': ['cat', 'kitten', 'feline'], 
                'bird': ['bird', 'avian', 'parrot'],
                'fish': ['fish', 'aquatic'],
                'reptile': ['reptile', 'snake', 'lizard', 'turtle', 'bearded dragon'],
                'small animal': ['rabbit', 'guinea pig', 'hamster']
            }
            
            # Check if product keywords contradict AI prediction
            product_pet_type = None
            for pet_type, keywords in pet_keywords.items():
                if any(keyword in product_lower for keyword in keywords):
                    product_pet_type = pet_type
                    break
            
            if product_pet_type and product_pet_type not in category:
                ai_confidence = 0.2  # Very low confidence if pet types don't match
            else:
                ai_confidence = 0.8  # Good confidence if pet types match
            
            # Use AI results if confidence is high enough
            if ai_confidence >= 0.5:
                for label in ['Category', 'Product Type', 'Product On Pages']:
                    if label in ai_result and ai_result[label]:
                        product_info[label] = ai_result[label]
                    else:
                        product_info[label] = ""
                return product_info
        
    except Exception as e:
        print(f"⚠️ AI classification failed (confidence: {ai_confidence}), falling back to fuzzy matching: {e}")
    
    # Fallback to fuzzy matching (either AI failed or low confidence)
    print(f"🔄 Using fuzzy matching fallback (AI confidence: {ai_confidence})")
    classified_df = load_classified_dataframe()
    
    # Find matches and get recommendations
    matches, matched_rows, top_options, recommended_items = \
        find_matching_products_and_recommendations(product_info, classified_df)
    
    # Apply recommendations to the product (automatically use most common from top matches)
    if recommended_items:
        # Use pipe-separated values for multi-select fields
        for label, items in recommended_items.items():
            if items:
                product_info[label] = "|".join(items)
            else:
                product_info[label] = ""
    else:
        # No matches found - try to provide default classifications for pet food
        default_classifications = get_default_pet_food_classifications(product_info)
        if default_classifications:
            for label, items in default_classifications.items():
                product_info[label] = "|".join(items) if items else ""
        else:
            # No matches and no defaults - leave facets empty
            for _, label in RECOMMEND_COLS:
                product_info[label] = ""

        # Fill any missing fields with default classifications
        missing_labels = [label for _, label in RECOMMEND_COLS if not product_info.get(label, '').strip()]
        if missing_labels:
            default_classifications = get_default_pet_food_classifications(product_info)
            if default_classifications:
                for label in missing_labels:
                    if label in default_classifications and default_classifications[label]:
                        # Default classifications already return most common values
                        product_info[label] = "|".join(default_classifications[label])
    
    return product_info


# Test section - run this file directly to test classification
if __name__ == "__main__":
    print("🧪 Testing Product Classification System")
    print("=" * 50)

    # Create a test product
    test_product = {
        'Name': 'Purina Pro Plan Adult Dog Food Chicken & Rice Formula',
        'Brand': 'Purina',
        'SKU': 'TEST001',
        'Price': '$29.99',
        'Weight': '30 LB',
        'Images': 'https://example.com/image1.jpg',
        'Special Order': '',
        'Category': '',  # Will be filled by classification
        'Product Type': '',  # Will be filled by classification
        'Product On Pages': ''  # Will be filled by classification
    }

    print("📦 Test Product:")
    print(f"   Name: {test_product['Name']}")
    print(f"   Brand: {test_product['Brand']}")
    print()

    # Test single product classification
    print("🔍 Classifying single product...")
    classified_product = classify_single_product(test_product.copy())

    print("📊 Classification Results:")
    print(f"   Category: {classified_product.get('Category', 'None')}")
    print(f"   Product Type: {classified_product.get('Product Type', 'None')}")
    print(f"   Product On Pages: {classified_product.get('Product On Pages', 'None')}")
    print()

    # Test batch classification
    print("📋 Testing batch classification...")
    test_products = [
        test_product.copy(),
        {
            'Name': 'Royal Canin Indoor Adult Cat Food',
            'Brand': 'Royal Canin',
            'SKU': 'TEST002',
            'Price': '$24.99',
            'Weight': '15 LB',
            'Images': 'https://example.com/image2.jpg',
            'Special Order': '',
            'Category': '',
            'Product Type': '',
            'Product On Pages': ''
        }
    ]

    classified_batch = classify_products_batch(test_products)

    print("📊 Batch Classification Results:")
    for i, product in enumerate(classified_batch, 1):
        print(f"   Product {i}: {product['Name'][:40]}...")
        print(f"      Category: {product.get('Category', 'None')}")
        print(f"      Product Type: {product.get('Product Type', 'None')}")
        print(f"      Product On Pages: {product.get('Product On Pages', 'None')}")
        print()

    print("✅ Test completed!")
