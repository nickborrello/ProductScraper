import pandas as pd
import os
import logging
import sqlite3
import json
from typing import Optional, Dict, Any, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime

# Set up logging (per project guidelines)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ShopSiteDatabase:
    """SQLite database manager for ShopSite products."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            db_path = os.path.join(project_root, "data", "databases", "products.db")
        self.db_path = db_path
        self.ensure_database()

    def ensure_database(self):
        """Create the products table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Check if we need to migrate from old schema
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
            )
            table_exists = cursor.fetchone()

            if table_exists:
                # Check current schema - look for old column names to determine if migration is needed
                cursor.execute("PRAGMA table_info(products)")
                columns_info = cursor.fetchall()
                columns = [row[1] for row in columns_info]

                # Check if we have old schema columns (migration needed)
                old_schema_indicators = [
                    "categories",
                    "brand",
                    "category",
                    "product_type",
                    "special_order",
                ]  # Old normalized column names
                has_old_schema = any(col in columns for col in old_schema_indicators)

                # Check if we have new schema columns (raw ShopSite columns with single Images column)
                new_schema_columns = [
                    "SKU",
                    "Name",
                    "Price",
                    "Images",
                    "Weight",
                    "Brand",
                ]
                has_new_schema = all(col in columns for col in new_schema_columns)

                if has_old_schema or not has_new_schema:
                    logging.info(
                        "🔄 Migrating database schema to use user-friendly column names..."
                    )
                    # Create new table with user-friendly column names
                    conn.execute(
                        """
                        CREATE TABLE products_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            SKU TEXT UNIQUE,
                            Name TEXT,
                            Price TEXT,
                            Images TEXT,
                            Weight TEXT,
                            Brand TEXT,
                            Special_Order TEXT,
                            Category TEXT,
                            Product_Type TEXT,
                            Product_On_Pages TEXT,
                            ProductDisabled TEXT,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                    )

                    # Copy existing data, mapping old fields to new ones
                    # Handle partially migrated schema - this will be a best-effort migration
                    conn.execute(
                        """
                        INSERT INTO products_new (id, SKU, Name, Price, Images, Weight, Brand,
                                                Special_Order, Category, Product_Type,
                                                Product_On_Pages, ProductDisabled, last_updated)
                        SELECT id, sku, name, '', '[]', weight,
                               Product_Field_16, Product_Field_11,
                               Product_Field_24, Product_Field_25, Product_On_Pages, ProductDisabled, last_updated
                        FROM products
                    """
                    )

                    # Replace old table with new one
                    conn.execute("DROP TABLE products")
                    conn.execute("ALTER TABLE products_new RENAME TO products")

                    # Recreate indexes with new column names
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_sku ON products(SKU)")
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_name ON products(Name)"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_brand ON products(Brand)"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_product_on_pages ON products(Product_On_Pages)"
                    )

                    logging.info("✅ Database schema migrated successfully")
                else:
                    logging.info("✅ Database schema is up to date")
            else:
                # Create new table with user-friendly column names
                conn.execute(
                    """
                    CREATE TABLE products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        SKU TEXT UNIQUE,
                        Name TEXT,
                        Price TEXT,
                        Images TEXT,
                        Weight TEXT,
                        Brand TEXT,
                        Special_Order TEXT,
                        Category TEXT,
                        Product_Type TEXT,
                        Product_On_Pages TEXT,
                        ProductDisabled TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                # Create indexes for better query performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sku ON products(SKU)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON products(Name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_brand ON products(Brand)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_product_on_pages ON products(Product_On_Pages)"
                )
                logging.info("✅ Database initialized")

    def clear_products(self):
        """Clear all products from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM products")
            logging.info("🗑️ Cleared all products from database")

    def upsert_product(self, product_data: Dict[str, Any]):
        """Insert or update a product in the database."""
        # Extract fields using user-friendly column names
        sku = product_data.get("SKU", product_data.get("sku", ""))
        name = product_data.get("Name", product_data.get("name", ""))
        price = product_data.get("Price", product_data.get("price", ""))

        # Collect all images into a comma-separated string
        image_urls = []
        graphic_url = product_data.get(
            "Graphic", product_data.get("More Information Graphic", "")
        )
        if (
            graphic_url
            and graphic_url.strip()
            and graphic_url.strip().lower() != "none"
        ):
            image_urls.append(graphic_url.strip())
        for i in range(1, 7):
            img_field = f"MoreInfoImage{i}"
            img_url = product_data.get(
                img_field, product_data.get(f"More Information Image {i}", "")
            )
            if img_url and img_url.strip() and img_url.strip().lower() != "none":
                image_urls.append(img_url.strip())
        images_csv = ", ".join(image_urls) if image_urls else ""

        weight = product_data.get("Weight", product_data.get("weight", ""))
        brand = product_data.get(
            "ProductField16",
            product_data.get("Product Field 16", product_data.get("Brand", "")),
        )
        special_order = product_data.get(
            "ProductField11", product_data.get("Product Field 11", "")
        )
        category = product_data.get(
            "ProductField24",
            product_data.get("Product Field 24", product_data.get("Category", "")),
        )
        product_type = product_data.get(
            "ProductField25",
            product_data.get("Product Field 25", product_data.get("Product Type", "")),
        )
        product_on_pages = product_data.get(
            "ProductOnPages", product_data.get("Product On Pages", "")
        )
        product_disabled = product_data.get("ProductDisabled", "")

        with sqlite3.connect(self.db_path) as conn:
            # Ensure connection uses UTF-8
            conn.text_factory = str
            conn.execute(
                """
                INSERT OR REPLACE INTO products
                (SKU, Name, Price, Images, Weight, Brand, Special_Order,
                 Category, Product_Type, Product_On_Pages, ProductDisabled, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    sku,
                    name,
                    price,
                    images_csv,
                    weight,
                    brand,
                    special_order,
                    category,
                    product_type,
                    product_on_pages,
                    product_disabled,
                    datetime.now(),
                ),
            )

    def batch_upsert_products(self, df: pd.DataFrame) -> int:
        """Batch insert/update multiple products for better performance."""
        products_data = []

        for _, product_row in df.iterrows():
            product_data = product_row.to_dict()

            # Extract fields using user-friendly column names
            sku = product_data.get("SKU", product_data.get("sku", ""))
            name = product_data.get("Name", product_data.get("name", ""))
            price = product_data.get("Price", product_data.get("price", ""))

            # Collect all images into a comma-separated string
            image_urls = []
            graphic_url = product_data.get(
                "Graphic", product_data.get("More Information Graphic", "")
            )
            if (
                graphic_url
                and graphic_url.strip()
                and graphic_url.strip().lower() != "none"
            ):
                image_urls.append(graphic_url.strip())
            for i in range(1, 7):
                img_field = f"MoreInfoImage{i}"
                img_url = product_data.get(
                    img_field, product_data.get(f"More Information Image {i}", "")
                )
                if img_url and img_url.strip() and img_url.strip().lower() != "none":
                    image_urls.append(img_url.strip())
            images_csv = ", ".join(image_urls) if image_urls else ""

            weight = product_data.get("Weight", product_data.get("weight", ""))
            brand = product_data.get(
                "ProductField16",
                product_data.get("Product Field 16", product_data.get("Brand", "")),
            )
            special_order = product_data.get(
                "ProductField11", product_data.get("Product Field 11", "")
            )
            category = product_data.get(
                "ProductField24",
                product_data.get("Product Field 24", product_data.get("Category", "")),
            )
            product_type = product_data.get(
                "ProductField25",
                product_data.get(
                    "Product Field 25", product_data.get("Product Type", "")
                ),
            )
            product_on_pages = product_data.get(
                "ProductOnPages", product_data.get("Product On Pages", "")
            )
            product_disabled = product_data.get("ProductDisabled", "")

            products_data.append(
                (
                    sku,
                    name,
                    price,
                    images_csv,
                    weight,
                    brand,
                    special_order,
                    category,
                    product_type,
                    product_on_pages,
                    product_disabled,
                    datetime.now(),
                )
            )

        # Batch insert using a single transaction
        with sqlite3.connect(self.db_path) as conn:
            conn.text_factory = str
            # Use a transaction for better performance
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO products
                    (SKU, Name, Price, Images, Weight, Brand, Special_Order,
                     Category, Product_Type, Product_On_Pages, ProductDisabled, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    products_data,
                )
                conn.execute("COMMIT")
                logging.info(
                    f"✅ Successfully inserted {len(products_data)} products in batch"
                )
                return len(products_data)
            except Exception as e:
                conn.execute("ROLLBACK")
                logging.error(f"❌ Batch insert failed, rolling back: {e}")
                raise

    def get_product_count(self) -> int:
        """Get the total number of products in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM products")
            return cursor.fetchone()[0]

    def get_column_statistics(self) -> Dict[str, int]:
        """
        Get statistics about non-empty values in all columns.

        Returns:
            Dict mapping column names to count of non-empty values
        """
        stats = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all column names from the products table
            cursor.execute("PRAGMA table_info(products)")
            columns_info = cursor.fetchall()
            all_columns = [
                row[1]
                for row in columns_info
                if row[1] != "id" and row[1] != "last_updated"
            ]  # Exclude id and last_updated

            for column in all_columns:
                cursor.execute(
                    f'SELECT COUNT(*) FROM products WHERE {column} IS NOT NULL AND {column} != ""'
                )
                count = cursor.fetchone()[0]
                stats[column] = count

        return stats

    def print_column_statistics(self):
        """Print formatted statistics about non-empty values in all columns."""
        stats = self.get_column_statistics()
        total_products = self.get_product_count()

        print("\n📊 Database Column Statistics")
        print("=" * 50)
        print(f"Total products in database: {total_products}")
        print()

        # All database columns with user-friendly display names
        print("📋 All Database Columns:")
        column_display_names = {
            "SKU": "SKU",
            "Name": "Product Name",
            "Price": "Price",
            "Images": "Images",
            "Weight": "Weight",
            "Brand": "Brand",
            "Special_Order": "Special Order",
            "Category": "Category",
            "Product_Type": "Product Type",
            "Product_On_Pages": "Product On Pages",
            "ProductDisabled": "Product Disabled",
        }

        # Sort columns for consistent display (important columns first, then others alphabetically)
        important_cols = [
            "SKU",
            "Name",
            "Price",
            "Images",
            "Weight",
            "Brand",
            "Special_Order",
            "Category",
            "Product_Type",
            "Product_On_Pages",
            "ProductDisabled",
        ]
        other_cols = sorted([col for col in stats.keys() if col not in important_cols])
        all_cols = important_cols + other_cols

        for col in all_cols:
            if col in stats:
                count = stats[col]
                percentage = (count / total_products * 100) if total_products > 0 else 0
                # Use user-friendly display names where available, otherwise format the column name
                display_name = column_display_names.get(col, col.replace("_", " "))
                print(
                    f"  {display_name:<25}: {count:>4} non-empty ({percentage:5.1f}%)"
                )

        print()
        print("💡 These statistics show data completeness for all product fields.")


def parse_xml_file_to_dataframe(xml_file_path: str) -> Optional[pd.DataFrame]:
    """Parse a local ShopSite XML file to pandas DataFrame."""
    try:
        # Explicitly parse with UTF-8 encoding to handle special characters properly
        with open(xml_file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Parse the XML content
        root = ET.fromstring(content)

        # ShopSite XML structure: ShopSiteProducts > Products > Product
        products = []

        # Find the Products container
        products_elem = root.find(".//Products")
        if products_elem is None:
            # Try direct root level if no Products container
            products_elem = root

        if products_elem is not None:
            # Find all Product elements
            for product_elem in products_elem.findall(".//Product"):
                product_data = {}

                # Extract all child elements as fields
                for child in product_elem:
                    if child.tag == "ProductOnPages":
                        # Special handling for ProductOnPages - can have different structures
                        page_names = []

                        # Try PageLink/Name structure first (import_shopsite.py style)
                        for page_link in child.findall("PageLink"):
                            name_elem = page_link.find("Name")
                            if (
                                name_elem is not None
                                and name_elem.text
                                and name_elem.text.strip()
                            ):
                                page_names.append(name_elem.text.strip())

                        # If no PageLink/Name found, try direct Name elements
                        if not page_names:
                            for name_elem in child.findall("Name"):
                                if name_elem.text and name_elem.text.strip():
                                    page_names.append(name_elem.text.strip())

                        # Store as comma-separated string
                        product_data[child.tag] = (
                            ", ".join(page_names) if page_names else ""
                        )
                    elif len(child) > 0:
                        # Element has children - serialize the entire subtree to XML string
                        # This preserves complex nested structures like QuantityPricing
                        xml_str = ET.tostring(child, encoding="unicode", method="xml")
                        product_data[child.tag] = xml_str
                    else:
                        # Simple text field - extract the text content
                        if child.text is not None:
                            # Preserve original text, don't strip whitespace
                            product_data[child.tag] = child.text
                        else:
                            product_data[child.tag] = ""

                # Only add if we have actual data
                if product_data:
                    products.append(product_data)

        if not products:
            logging.warning("⚠️ No products found in XML. Checking structure...")
            logging.info(f"Root tag: {root.tag}, attributes: {root.attrib}")
            products_elem = root.find(".//Products")
            if products_elem is not None:
                logging.info(
                    f"Found Products container with {len(products_elem)} children"
                )
                for child in list(products_elem)[:3]:
                    logging.info(f"Sample product child: {child.tag}")
                    if hasattr(child, "text") and child.text:
                        logging.info(f"  Text content: {child.text[:100]}...")
            else:
                logging.info("No Products container found")
                for child in list(root)[:5]:
                    logging.info(f"Root child: {child.tag}")

        df = pd.DataFrame(products)
        logging.info(f"📊 Parsed {len(df)} products from XML file")
        return df

    except ET.ParseError as e:
        logging.error(f"❌ XML parsing error: {e}")
        return None
    except UnicodeDecodeError as e:
        logging.error(f"❌ Unicode decoding error: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ Unexpected error parsing XML: {e}")
        return None


def process_xml_to_database(
    xml_file_path: str, db_path: str = None, clear_existing: bool = True
) -> bool:
    """
    Process a downloaded ShopSite XML file and save to SQLite database.

    Args:
        xml_file_path: Path to the downloaded XML file
        db_path: Path to the SQLite database
        clear_existing: Whether to clear existing products before importing
    """
    try:
        # Parse XML to DataFrame
        df = parse_xml_file_to_dataframe(xml_file_path)
        if df is None or df.empty:
            logging.error("Failed to parse XML or no products found")
            return False

        # Initialize database
        db = ShopSiteDatabase(db_path)

        # Clear existing data if requested
        if clear_existing:
            db.clear_products()

        # Batch insert/update products for better performance
        logging.info(f"📥 Starting batch insert of {len(df)} products...")
        start_time = datetime.now()
        products_processed = db.batch_upsert_products(df)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(
            f"⚡ Batch insert completed in {duration:.2f} seconds ({len(df)/duration:.0f} products/sec)"
        )

        final_count = db.get_product_count()
        logging.info(
            f"✅ Processed {products_processed} products, {final_count} total in database"
        )

        return True

    except Exception as e:
        logging.error(f"❌ Error processing XML to database: {e}")
        return False


def refresh_database_from_xml(
    xml_file_path: str, db_path: str = None
) -> Tuple[bool, str]:
    """
    Refresh the local database with new XML data.

    This clears existing data and imports fresh data from the XML file.
    """
    try:
        logging.info("🔄 Starting database refresh from XML...")

        if not os.path.exists(xml_file_path):
            return False, f"❌ XML file not found: {xml_file_path}"

        success = process_xml_to_database(xml_file_path, db_path, clear_existing=True)

        if success:
            db = ShopSiteDatabase(db_path)
            count = db.get_product_count()
            # Print column statistics after successful processing
            db.print_column_statistics()
            return True, f"✅ Database refreshed successfully with {count} products"
        else:
            return False, "❌ Database refresh failed"

    except Exception as e:
        error_msg = f"❌ Error refreshing database: {e}"
        logging.error(error_msg)
        return False, error_msg


def main():
    """Process a downloaded ShopSite XML file into the local database."""
    print("🛒 Process ShopSite XML to Local Database")
    print("=" * 50)
    print(
        "This will parse your downloaded XML file and save products to a local SQLite database."
    )
    print("The database will be refreshed with the new data.")
    print("=" * 50)

    # Prompt user for XML file path
    xml_file_path = input("Enter the path to your downloaded XML file: ").strip()

    if not os.path.exists(xml_file_path):
        print(f"❌ File not found: {xml_file_path}")
        return

    # Confirm database refresh
    confirm = (
        input("This will clear existing database data. Continue? (yes/no): ")
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("❌ Operation cancelled.")
        return

    print(f"📂 Processing: {xml_file_path}")
    print("🔄 Refreshing local database...")

    success, message = refresh_database_from_xml(xml_file_path)
    print(message)

    if success:
        print("💡 Database is now ready for queries and regular refreshes.")
        print("   Run this script again with new XML files to keep data current.")


if __name__ == "__main__":
    main()
