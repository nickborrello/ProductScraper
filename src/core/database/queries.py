#!/usr/bin/env python3
"""
SQLite Query Interface for ShopSite Products Database
"""

import os
import sqlite3
from typing import Any


class ProductDatabase:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels from src/core/ to project root, then into src/data/databases/
            project_root = os.path.dirname(os.path.dirname(script_dir))
            db_path = os.path.join(project_root, "src", "data", "databases", "products.db")

        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self):
        """Connect to the database"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_product_count(self) -> int:
        """Get total number of products"""
        assert self.conn is not None
        cursor = self.conn.execute("SELECT COUNT(*) FROM products")
        result = cursor.fetchone()
        return int(result[0]) if result else 0

    def get_sample_fields(self) -> list[str]:
        """Get list of available fields from database schema"""
        assert self.conn is not None
        # Get column names from the database schema
        cursor = self.conn.execute("PRAGMA table_info(products)")
        columns_info = cursor.fetchall()
        # Return column names, excluding 'id' and 'last_updated'
        return [row[1] for row in columns_info if row[1] not in ["id", "last_updated"]]

    def query_products(self, sql_query: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Execute a custom SQL query on the products table
        Returns list of dictionaries with product data
        """
        assert self.conn is not None
        try:
            # Add LIMIT if not present
            if "LIMIT" not in sql_query.upper():
                sql_query += f" LIMIT {limit}"

            cursor = self.conn.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                product = dict(zip(columns, row, strict=False))

                # No extra_data JSON parsing needed for current schema
                results.append(product)

            return results

        except sqlite3.Error as e:
            raise Exception(f"SQL Error: {e}")

    def search_products(self, field: str, value: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        Search for products where a specific field contains a value
        """
        assert self.conn is not None
        # For the current schema, search in the appropriate column
        # Map common field names to database column names
        column_mapping = {
            "SKU": "SKU",
            "Name": "Name",
            "Price": "Price",
            "Images": "Images",
            "Weight": "Weight",
            "Brand": "Brand",
            "Special_Order": "Special_Order",
            "Category": "Category",
            "Product_Type": "Product_Type",
            "Product_On_Pages": "Product_On_Pages",
            "ProductDisabled": "ProductDisabled",
        }

        # Use the mapped column name, or the field name directly if not mapped
        column_name = column_mapping.get(field, field)

        # Build query for the specific column
        query = f"SELECT * FROM products WHERE {column_name} LIKE ? LIMIT {limit}"
        cursor = self.conn.execute(query, (f"%{value}%",))

        columns = [desc[0] for desc in cursor.description]
        results = []

        for row in cursor.fetchall():
            product = dict(zip(columns, row, strict=False))
            results.append(product)

        return results


def main():
    db = ProductDatabase()

    try:
        db.connect()
        print("🗄️  ShopSite Products Database Query Interface")
        print("=" * 50)
        print(f"📊 Total products: {db.get_product_count():,}")

        fields = db.get_sample_fields()
        print(f"📋 Available fields: {len(fields)} total")
        DISPLAY_LIMIT = 10
        print("Common fields:", ", ".join(fields[:DISPLAY_LIMIT]))
        if len(fields) > DISPLAY_LIMIT:
            print(f"... and {len(fields) - DISPLAY_LIMIT} more")

        print("\n" + "=" * 50)
        print("Query Examples:")
        print("1. Search by name: 'Name' contains 'dog'")
        print("2. Custom SQL: SELECT * FROM products WHERE SKU LIKE '2028%'")
        print(
            "3. Count by category: SELECT Category, COUNT(*) FROM products WHERE Category IS NOT NULL GROUP BY Category"
        )
        print("=" * 50)

        while True:
            print("\nOptions:")
            print("1. Search products by field/value")
            print("2. Run custom SQL query")
            print("3. Show field examples")
            print("4. Exit")

            choice = input("\nEnter choice (1-4): ").strip()

            if choice == "1":
                field = input("Field to search: ").strip()
                value = input("Value to find: ").strip()
                try:
                    results = db.search_products(field, value)
                    print(f"\n🔍 Found {len(results)} products:")
                    for i, product in enumerate(results[:5], 1):  # Show first 5
                        sku = product.get("sku", "No SKU")
                        name = product.get("extra_data", {}).get("Name", "No Name")
                        print(f"  {i}. {sku}: {name}")
                    RESULT_DISPLAY_LIMIT = 5
                    if len(results) > RESULT_DISPLAY_LIMIT:
                        print(f"     ... and {len(results) - RESULT_DISPLAY_LIMIT} more")
                except Exception as e:
                    print(f"❌ Error: {e}")

            elif choice == "2":
                print(
                    "Enter SQL query (products table has: id, SKU, Name, Price, Images, Weight, Brand, Special_Order, Category, Product_Type, Product_On_Pages, ProductDisabled, last_updated)"
                )
                query = input("SQL> ").strip()
                if query:
                    try:
                        results = db.query_products(query)
                        print(f"\n📊 Query returned {len(results)} results:")
                        QUERY_DISPLAY_LIMIT = 10
                        for i, product in enumerate(
                            results[:QUERY_DISPLAY_LIMIT], 1
                        ):  # Show first 10
                            print(f"  {i}. {product}")
                        if len(results) > QUERY_DISPLAY_LIMIT:
                            print(f"     ... and {len(results) - QUERY_DISPLAY_LIMIT} more")
                    except Exception as e:
                        print(f"❌ Error: {e}")

            elif choice == "3":
                print("\n📋 Field Examples:")
                sample = db.query_products("SELECT * FROM products LIMIT 1")[0]
                examples = [
                    ("SKU", sample.get("SKU", "N/A")),
                    ("Name", sample.get("Name", "N/A")),
                    ("Price", sample.get("Price", "N/A")),
                    ("Brand", sample.get("Brand", "N/A")),
                    ("Category", sample.get("Category", "N/A")),
                    ("Weight", sample.get("Weight", "N/A")),
                ]
                for field, value in examples:
                    print(f"  {field}: {value}")

            elif choice == "4":
                break

            else:
                print("❌ Invalid choice")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
