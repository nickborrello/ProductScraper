import os
import sqlite3
from pathlib import Path

# Get the project root (parent of scripts directory)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "databases" / "products.db"

if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check classification completeness
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN Category IS NOT NULL AND Category != "" THEN 1 ELSE 0 END) as has_category,
                SUM(CASE WHEN Product_Type IS NOT NULL AND Product_Type != "" THEN 1 ELSE 0 END) as has_type,
                SUM(CASE WHEN Product_On_Pages IS NOT NULL AND Product_On_Pages != "" THEN 1 ELSE 0 END) as has_pages
            FROM products
        """
        )
        stats = cursor.fetchone()

        total = stats[0] or 0
        has_category = stats[1] or 0
        has_type = stats[2] or 0
        has_pages = stats[3] or 0

        print(f"Total products: {total}")
        if total > 0:
            print(f"With Category: {has_category} ({has_category/total*100:.1f}%)")
            print(f"With Product Type: {has_type} ({has_type/total*100:.1f}%)")
            print(f"With Product On Pages: {has_pages} ({has_pages/total*100:.1f}%)")
        else:
            print("With Category: 0 (0.0%)")
            print("With Product Type: 0 (0.0%)")
            print("With Product On Pages: 0 (0.0%)")

        # Check unique categories and types
        cursor = conn.execute(
            'SELECT Category FROM products WHERE Category IS NOT NULL AND Category != ""'
        )
        categories = set(row[0] for row in cursor.fetchall())

        cursor = conn.execute(
            'SELECT Product_Type FROM products WHERE Product_Type IS NOT NULL AND Product_Type != ""'
        )
        types = set(row[0] for row in cursor.fetchall())

        print(f"Unique Categories: {len(categories)}")
        print(f"Unique Product Types: {len(types)}")

    finally:
        conn.close()
else:
    print("Database not found")
