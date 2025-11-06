import sqlite3
from pathlib import Path

DB_PATH = Path('../data/databases/products.db')

if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check classification completeness
        cursor = conn.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN Category IS NOT NULL AND Category != "" THEN 1 ELSE 0 END) as has_category,
                SUM(CASE WHEN Product_Type IS NOT NULL AND Product_Type != "" THEN 1 ELSE 0 END) as has_type,
                SUM(CASE WHEN Product_On_Pages IS NOT NULL AND Product_On_Pages != "" THEN 1 ELSE 0 END) as has_pages
            FROM products
        ''')
        stats = cursor.fetchone()

        print(f'Total products: {stats[0]}')
        print(f'With Category: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)')
        print(f'With Product Type: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)')
        print(f'With Product On Pages: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)')

        # Check unique categories and types
        cursor = conn.execute('SELECT Category FROM products WHERE Category IS NOT NULL AND Category != ""')
        categories = set(row[0] for row in cursor.fetchall())

        cursor = conn.execute('SELECT Product_Type FROM products WHERE Product_Type IS NOT NULL AND Product_Type != ""')
        types = set(row[0] for row in cursor.fetchall())

        print(f'Unique Categories: {len(categories)}')
        print(f'Unique Product Types: {len(types)}')

    finally:
        conn.close()
else:
    print('Database not found')