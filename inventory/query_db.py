#!/usr/bin/env python3
"""
SQLite Query Interface for ShopSite Products Database
"""
import sqlite3
import json
import os
from typing import List, Dict, Any

class ProductDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "data", "products.db")

        self.db_path = db_path
        self.conn = None

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
        cursor = self.conn.execute('SELECT COUNT(*) FROM products')
        return cursor.fetchone()[0]

    def get_sample_fields(self) -> List[str]:
        """Get list of available fields from a sample product"""
        cursor = self.conn.execute('SELECT extra_data FROM products LIMIT 1')
        row = cursor.fetchone()
        if row and row[0]:
            data = json.loads(row[0])
            return list(data.keys())
        return []

    def query_products(self, sql_query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query on the products table
        Returns list of dictionaries with product data
        """
        try:
            # Add LIMIT if not present
            if 'LIMIT' not in sql_query.upper():
                sql_query += f' LIMIT {limit}'

            cursor = self.conn.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                product = dict(zip(columns, row))

                # Parse extra_data JSON if present
                if 'extra_data' in product and product['extra_data']:
                    try:
                        product['extra_data'] = json.loads(product['extra_data'])
                    except json.JSONDecodeError:
                        pass

                results.append(product)

            return results

        except sqlite3.Error as e:
            raise Exception(f"SQL Error: {e}")

    def search_products(self, field: str, value: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for products where a specific field contains a value
        """
        # Build JSON query for extra_data field
        json_query = f"SELECT * FROM products WHERE json_extract(extra_data, '$.{field}') LIKE ? LIMIT {limit}"
        cursor = self.conn.execute(json_query, (f'%{value}%',))

        columns = [desc[0] for desc in cursor.description]
        results = []

        for row in cursor.fetchall():
            product = dict(zip(columns, row))
            if 'extra_data' in product and product['extra_data']:
                product['extra_data'] = json.loads(product['extra_data'])
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
        print("Common fields:", ', '.join(fields[:10]))
        if len(fields) > 10:
            print(f"... and {len(fields) - 10} more")

        print("\n" + "=" * 50)
        print("Query Examples:")
        print("1. Search by name: 'Name' contains 'dog'")
        print("2. Custom SQL: SELECT * FROM products WHERE sku LIKE '2028%'")
        print("3. Count by category: SELECT json_extract(extra_data, '$.Category') as cat, COUNT(*) FROM products GROUP BY cat")
        print("=" * 50)

        while True:
            print("\nOptions:")
            print("1. Search products by field/value")
            print("2. Run custom SQL query")
            print("3. Show field examples")
            print("4. Exit")

            choice = input("\nEnter choice (1-4): ").strip()

            if choice == '1':
                field = input("Field to search: ").strip()
                value = input("Value to find: ").strip()
                try:
                    results = db.search_products(field, value)
                    print(f"\n🔍 Found {len(results)} products:")
                    for i, product in enumerate(results[:5], 1):  # Show first 5
                        sku = product.get('sku', 'No SKU')
                        name = product.get('extra_data', {}).get('Name', 'No Name')
                        print(f"  {i}. {sku}: {name}")
                    if len(results) > 5:
                        print(f"     ... and {len(results) - 5} more")
                except Exception as e:
                    print(f"❌ Error: {e}")

            elif choice == '2':
                print("Enter SQL query (products table has: id, sku, name, price, description, category, inventory, weight, image_url, extra_data)")
                query = input("SQL> ").strip()
                if query:
                    try:
                        results = db.query_products(query)
                        print(f"\n📊 Query returned {len(results)} results:")
                        for i, product in enumerate(results[:10], 1):  # Show first 10
                            print(f"  {i}. {product}")
                        if len(results) > 10:
                            print(f"     ... and {len(results) - 10} more")
                    except Exception as e:
                        print(f"❌ Error: {e}")

            elif choice == '3':
                print("\n📋 Field Examples:")
                sample = db.query_products("SELECT extra_data FROM products LIMIT 1")[0]
                if 'extra_data' in sample:
                    data = sample['extra_data']
                    examples = [
                        ('Name', data.get('Name', 'N/A')),
                        ('Price', data.get('Price', 'N/A')),
                        ('SKU', data.get('SKU', 'N/A')),
                        ('Category', data.get('Category', 'N/A')),
                        ('ProductDescription', data.get('ProductDescription', 'N/A')[:100] + '...'),
                    ]
                    for field, value in examples:
                        print(f"  {field}: {value}")

            elif choice == '4':
                break

            else:
                print("❌ Invalid choice")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()