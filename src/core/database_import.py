import os
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import logging
import sqlite3
import json
from typing import Tuple, Optional, Dict
from dotenv import load_dotenv
from datetime import datetime

# Define project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Import field mapping configuration
try:
    from .field_mapping import map_shopsite_fields, REQUIRED_FIELDS
except ImportError:
    # Fallback for standalone execution
    from field_mapping import map_shopsite_fields, REQUIRED_FIELDS

# Import settings manager
try:
    from .settings_manager import SettingsManager
except ImportError:
    # Fallback for standalone execution
    from settings_manager import SettingsManager

# Load environment variables
load_dotenv()

# Initialize settings manager
settings = SettingsManager()

# Set up logging (per project guidelines)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ShopSite XML Download configuration
SHOPSITE_CONFIG = {
    **settings.shopsite_credentials,
    "xml_url": "https://www.baystatepet.com/cgi-baystatepet/bo/db_xml.cgi",
    "version": "14.0",  # Latest XML version for products
}


def get_product_count(db_path: str) -> int:
    """Get the total number of products in the database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM products")
        return cursor.fetchone()[0]


def get_column_statistics(db_path: str) -> Dict[str, int]:
    """
    Get statistics about non-empty values in important columns.

    Returns:
        Dict mapping column names to count of non-empty values
    """
    stats = {}

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Main database columns
        main_columns = [
            "sku",
            "name",
            "price",
            "description",
            "category",
            "inventory",
            "weight",
            "image_url",
        ]

        for column in main_columns:
            cursor.execute(
                f'SELECT COUNT(*) FROM products WHERE {column} IS NOT NULL AND {column} != ""'
            )
            count = cursor.fetchone()[0]
            stats[column] = count

        # Extra data JSON fields (from our optimized field mapping)
        extra_fields = [
            "Name",
            "Brand",
            "Weight",
            "Special_Order",
            "Category",
            "Product_Type",
            "Product_On_Pages",
            "Graphic",
        ]

        for field in extra_fields:
            # Count products where the field exists in extra_data and is not empty
            cursor.execute(
                """
                SELECT COUNT(*) FROM products
                WHERE json_extract(extra_data, ?) IS NOT NULL
                AND json_extract(extra_data, ?) != ""
            """,
                (f"$.{field}", f"$.{field}"),
            )
            count = cursor.fetchone()[0]
            stats[f"extra_{field.lower()}"] = count

    return stats


def print_column_statistics(stats: Dict[str, int], total_products: int):
    """Print formatted statistics about non-empty values in important columns."""
    print("\n📊 Database Column Statistics")
    print("=" * 50)
    print(f"Total products in database: {total_products}")
    print()

    # Main database columns
    print("📋 Main Database Columns:")
    main_cols = [
        "sku",
        "name",
        "price",
        "description",
        "category",
        "inventory",
        "weight",
        "image_url",
    ]
    for col in main_cols:
        if col in stats:
            count = stats[col]
            percentage = (count / total_products * 100) if total_products > 0 else 0
            print(f"  {col:<12}: {count:>4} non-empty ({percentage:5.1f}%)")

    print()

    # Extra data fields (optimized editor fields)
    print("🎯 Optimized Editor Fields (stored in extra_data):")
    extra_cols = [
        "extra_name",
        "extra_brand",
        "extra_weight",
        "extra_special_order",
        "extra_category",
        "extra_product_type",
        "extra_product_on_pages",
        "extra_graphic",
    ]
    for col in extra_cols:
        if col in stats:
            count = stats[col]
            percentage = (count / total_products * 100) if total_products > 0 else 0
            field_name = col.replace("extra_", "")
            print(f"  {field_name:<18}: {count:>4} non-empty ({percentage:5.1f}%)")

    print()
    print("💡 These statistics show data completeness for important product fields.")


# ShopSite XML Download configuration
SHOPSITE_CONFIG = {
    **settings.shopsite_credentials,
    "xml_url": "https://www.baystatepet.com/cgi-baystatepet/bo/db_xml.cgi",
    "version": "14.0",  # Latest XML version for products
}


class ShopSiteXMLClient:
    """Client for ShopSite Database Automated XML Download."""

    def __init__(self, log_callback=None):
        self.session = requests.Session()
        self.config = SHOPSITE_CONFIG
        self.log_callback = log_callback

    def _estimate_download_size(self) -> int:
        """Estimate download size based on previous downloads."""
        try:
            # Check if we have a saved raw XML file from previous downloads
            xml_file_path = os.path.join(
                PROJECT_ROOT, "data", "databases", "shopsite_products_raw.xml"
            )
            
            if os.path.exists(xml_file_path):
                size = os.path.getsize(xml_file_path)
                # Add 10% buffer for potential changes
                return int(size * 1.1)
            
            # Could also check logs for previous download sizes
            # For now, return 0 if no previous data
            return 0
            
        except Exception:
            return 0

    def authenticate(self) -> bool:
        """Authenticate with ShopSite using basic auth (username/password)."""
        if not (self.config.get("username") and self.config.get("password")):
            logging.error(
                "❌ ShopSite XML credentials not found in environment variables"
            )
            return False

        # Use basic HTTP authentication
        self.session.auth = (self.config["username"], self.config["password"])
        logging.info("✅ Using basic authentication with ShopSite XML interface")
        return True

    def download_products_xml(self) -> Optional[str]:
        """Download products database as XML from ShopSite with progress tracking."""
        try:
            params = {
                "clientApp": "1",  # Required: identifies client application version
                "dbname": "products",  # Required: database name for products
                "version": "14.0",  # XML format version (14.0 latest)
                # No fieldmap specified - download all columns
            }

            logging.info("📥 Downloading products XML from ShopSite...")
            logging.info(f"URL: {self.config['xml_url']}")
            logging.info(f"Parameters: {params}")

            # Use streaming to track download progress
            response = self.session.get(
                self.config["xml_url"], params=params, timeout=300, stream=True
            )

            if response.status_code == 200:
                import time

                # Try to estimate total size based on previous downloads
                # Look for previous download sizes in the log or saved files
                estimated_size = self._estimate_download_size()
                if estimated_size > 0:
                    if self.log_callback:
                        self.log_callback(f"📊 Estimated download size: ~{estimated_size:,} bytes (based on previous downloads)")
                    else:
                        print(f"📊 Estimated download size: ~{estimated_size:,} bytes (based on previous downloads)")

                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0
                content_chunks = []
                start_time = time.time()

                if total_size > 0:
                    if self.log_callback:
                        self.log_callback(f"📊 Downloading {total_size:,} bytes...")
                    else:
                        print(f"📊 Downloading {total_size:,} bytes...")
                else:
                    if self.log_callback:
                        self.log_callback(f"📊 Downloading (size unknown - showing progress info)...")
                    else:
                        print(f"📊 Downloading (size unknown - showing progress info)...")

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content_chunks.append(chunk)
                        downloaded_size += len(chunk)

                        # Show progress
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = downloaded_size / elapsed
                                eta = (
                                    (total_size - downloaded_size) / speed
                                    if speed > 0
                                    else 0
                                )
                                eta_str = (
                                    f" ETA: {eta:.0f}s"
                                    if eta < 3600
                                    else f" ETA: {eta/3600:.1f}h"
                                )
                            else:
                                eta_str = ""
                            
                            # Send progress update to log callback (every 1MB or every 5 seconds)
                            current_time = time.time()
                            if (downloaded_size % (1024 * 1024) < 8192 or  # Every ~1MB
                                current_time - (getattr(self, 'last_progress_time', 0)) > 5):  # Or every 5 seconds
                                progress_msg = f"📥 Progress: {progress:.1f}% ({downloaded_size:,}/{total_size:,} bytes){eta_str}"
                                if self.log_callback:
                                    self.log_callback(progress_msg)
                                else:
                                    print(f"\r{progress_msg}", end="", flush=True)
                                self.last_progress_time = current_time
                        else:
                            # Show download speed and time elapsed when size unknown
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = downloaded_size / elapsed
                                speed_str = (
                                    f" @ {speed/1024:.0f}KB/s" if speed > 0 else ""
                                )
                            else:
                                speed_str = ""
                            
                            # Send progress update to log callback (every 5 seconds)
                            current_time = time.time()
                            if current_time - getattr(self, 'last_progress_time', 0) > 5:
                                progress_msg = f"📥 Downloaded: {downloaded_size:,} bytes{speed_str} ({elapsed:.1f}s elapsed)"
                                if self.log_callback:
                                    self.log_callback(progress_msg)
                                else:
                                    print(f"\r{progress_msg}", end="", flush=True)
                                self.last_progress_time = current_time

                # Send final download complete message
                final_msg = f"📥 Downloaded: {downloaded_size:,} bytes @ {downloaded_size/(time.time()-start_time)/1024:.0f}KB/s ({time.time()-start_time:.1f}s elapsed)"
                if self.log_callback:
                    self.log_callback(final_msg)
                else:
                    print(final_msg)

                # Combine chunks into full content
                full_content = b"".join(content_chunks).decode(
                    "utf-8", errors="replace"
                )

                logging.info(
                    f"✅ Products XML downloaded successfully ({len(full_content)} characters)"
                )

                # Save raw XML to file for debugging and backup
                xml_file_path = os.path.join(
                    PROJECT_ROOT, "data", "databases", "shopsite_products_raw.xml"
                )
                os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)
                try:
                    with open(xml_file_path, "w", encoding="utf-8") as f:
                        f.write(full_content)
                    logging.info(f"💾 Raw XML saved to: {xml_file_path}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to save raw XML file: {e}")

                return full_content
            else:
                logging.error(
                    f"❌ Download failed: {response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logging.error(f"❌ Download request failed: {e}")
            return None


def save_dataframe_to_database(
    df: pd.DataFrame, db_path: str = None, clear_existing: bool = True
) -> Tuple[bool, str]:
    """Save DataFrame directly to SQLite database."""
    try:
        if db_path is None:
            db_path = os.path.join(PROJECT_ROOT, "data", "databases", "products.db")

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create database connection
        with sqlite3.connect(db_path) as conn:
            # Check if table exists and has the correct schema
            cursor = conn.execute("PRAGMA table_info(products)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            expected_columns = {
                "id",
                "sku",
                "name",
                "price",
                "description",
                "category",
                "inventory",
                "weight",
                "image_url",
                "extra_data",
                "last_updated",
                "created_at",
            }

            # If table doesn't exist or has wrong schema, recreate it
            if not existing_columns or existing_columns != expected_columns:
                logging.info("🔄 Recreating products table with correct schema...")
                conn.execute("DROP TABLE IF EXISTS products")
                conn.execute(
                    """
                    CREATE TABLE products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sku TEXT UNIQUE,
                        name TEXT,
                        price TEXT,
                        description TEXT,
                        category TEXT,
                        inventory TEXT,
                        weight TEXT,
                        image_url TEXT,
                        extra_data TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                logging.info("✅ Products table recreated with correct schema")

            # Clear existing data if requested
            if clear_existing:
                conn.execute("DELETE FROM products")
                logging.info("🗑️ Cleared existing products from database")

            # Insert products
            inserted_count = 0
            for _, product_row in df.iterrows():
                product_data = product_row.to_dict()

                # Deduplicate pipe-separated fields before saving
                def deduplicate_pipe_separated(value):
                    """Split by |, remove duplicates while preserving order, rejoin with |"""
                    if not value:
                        return ""
                    parts = [part.strip() for part in str(value).split("|") if part.strip()]
                    unique_parts = list(dict.fromkeys(parts))  # Preserve order while removing duplicates
                    return "|".join(unique_parts)

                # Apply deduplication to relevant fields
                for field in ["Category", "Product_Type", "Product_On_Pages"]:
                    if field in product_data:
                        product_data[field] = deduplicate_pipe_separated(product_data[field])

                # Extract individual fields for database columns
                sku = str(product_data.get("SKU", "")).strip()
                name = str(product_data.get("Name", "")).strip()
                price = str(product_data.get("Price", "")).strip()
                category = str(product_data.get("Category", "")).strip()
                weight = str(product_data.get("Weight", "")).strip()

                # Get main image URL
                image_url = ""
                if "Image_URLs" in product_data and product_data["Image_URLs"]:
                    image_url = (
                        str(product_data["Image_URLs"][0]).strip()
                        if isinstance(product_data["Image_URLs"], list)
                        else str(product_data["Image_URLs"]).strip()
                    )

                # Store mapped fields as JSON in extra_data (now much smaller)
                extra_json = json.dumps(product_data) if product_data else "{}"

                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO products
                        (sku, name, price, category, weight, image_url, extra_data, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            sku,
                            name,
                            price,
                            category,
                            weight,
                            image_url,
                            extra_json,
                            datetime.now(),
                        ),
                    )
                    inserted_count += 1
                except Exception as insert_error:
                    logging.error(f"❌ Failed to insert product {sku}: {insert_error}")
                    # Continue with next product

            # Commit the transaction
            conn.commit()
            logging.info(
                f"💾 Successfully inserted {inserted_count} out of {len(df)} products"
            )

        logging.info(f"💾 Saved {len(df)} products directly to database")
        return True, db_path

    except Exception as e:
        logging.error(f"❌ Failed to save to database: {e}")
        return False, db_path


def parse_xml_to_dataframe(xml_content: str) -> Optional[pd.DataFrame]:
    """Parse ShopSite XML content to pandas DataFrame."""
    try:
        # Preprocess XML to handle HTML entities that aren't valid in XML
        import re

        # Replace common HTML entities with XML-safe equivalents
        entity_replacements = {
            "&nbsp;": "&#160;",  # non-breaking space
            "&copy;": "&#169;",  # copyright
            "&reg;": "&#174;",  # registered trademark
            "&trade;": "&#8482;",  # trademark
            "&hellip;": "&#8230;",  # horizontal ellipsis
            "&mdash;": "&#8212;",  # em dash
            "&ndash;": "&#8211;",  # en dash
            "&lsquo;": "&#8216;",  # left single quotation mark
            "&rsquo;": "&#8217;",  # right single quotation mark
            "&ldquo;": "&#8220;",  # left double quotation mark
            "&rdquo;": "&#8221;",  # right double quotation mark
            "&bull;": "&#8226;",  # bullet
            "&deg;": "&#176;",  # degree symbol
            "&frac12;": "&#189;",  # 1/2 fraction
            "&frac14;": "&#188;",  # 1/4 fraction
            "&frac34;": "&#190;",  # 3/4 fraction
            # Accented characters
            "&eacute;": "&#233;",  # e with acute accent
            "&Eacute;": "&#201;",  # E with acute accent
            "&agrave;": "&#224;",  # a with grave accent
            "&Agrave;": "&#192;",  # A with grave accent
            "&ecirc;": "&#234;",  # e with circumflex
            "&Ecirc;": "&#202;",  # E with circumflex
            "&iuml;": "&#239;",  # i with diaeresis
            "&Iuml;": "&#207;",  # I with diaeresis
            "&ouml;": "&#246;",  # o with diaeresis
            "&Ouml;": "&#214;",  # O with diaeresis
            "&uuml;": "&#252;",  # u with diaeresis
            "&Uuml;": "&#220;",  # U with diaeresis
            "&ccedil;": "&#231;",  # c with cedilla
            "&Ccedil;": "&#199;",  # C with cedilla
            "&ntilde;": "&#241;",  # n with tilde
            "&Ntilde;": "&#209;",  # N with tilde
            "&szlig;": "&#223;",  # sharp s
            "&thorn;": "&#254;",  # thorn
            "&THORN;": "&#222;",  # THORN
            # Other common entities
            "&amp;": "&amp;",  # ampersand (should be first)
            "&lt;": "&lt;",  # less than
            "&gt;": "&gt;",  # greater than
            "&quot;": "&quot;",  # quotation mark
            "&apos;": "&#39;",  # apostrophe
            "&cent;": "&#162;",  # cent sign
            "&pound;": "&#163;",  # pound sign
            "&yen;": "&#165;",  # yen sign
            "&euro;": "&#8364;",  # euro sign
            "&sect;": "&#167;",  # section sign
            "&para;": "&#182;",  # paragraph sign
            "&micro;": "&#181;",  # micro sign
            "&times;": "&#215;",  # multiplication sign
            "&divide;": "&#247;",  # division sign
            "&plusmn;": "&#177;",  # plus-minus sign
            "&sup1;": "&#185;",  # superscript 1
            "&sup2;": "&#178;",  # superscript 2
            "&sup3;": "&#179;",  # superscript 3
            "&frac13;": "&#8531;",  # 1/3 fraction
            "&frac23;": "&#8532;",  # 2/3 fraction
            "&frac15;": "&#8533;",  # 1/5 fraction
            "&frac25;": "&#8534;",  # 1/5 fraction
            "&frac35;": "&#8535;",  # 3/5 fraction
            "&frac45;": "&#8536;",  # 4/5 fraction
            "&frac16;": "&#8537;",  # 1/6 fraction
            "&frac56;": "&#8538;",  # 5/6 fraction
        }

        # Apply entity replacements
        for html_entity, xml_entity in entity_replacements.items():
            xml_content = xml_content.replace(html_entity, xml_entity)

        # CRITICAL: Replace any remaining unencoded ampersands with &amp;
        # Use regex to only replace ampersands that are NOT already part of XML entities
        import re

        # Replace & that is not followed by a valid entity pattern (letters, numbers, #, or ; at end)
        xml_content = re.sub(r"&(?![a-zA-Z0-9#]+;)", "&amp;", xml_content)

        # Handle any remaining HTML entities by converting them to numeric references
        # This catches entities that aren't in our predefined list
        import html

        try:
            # Find any remaining &entity; patterns and replace with safe alternatives
            def replace_unknown_entity(match):
                entity = match.group(1)
                # Try to get the numeric value using html.entities if available
                try:
                    import html.entities

                    if entity in html.entities.name2codepoint:
                        return f"&#{html.entities.name2codepoint[entity]};"
                    else:
                        # Unknown entity - replace with a safe character
                        logging.warning(
                            f"Unknown HTML entity '&{entity};' found, replacing with '?'"
                        )
                        return "?"
                except (ImportError, AttributeError):
                    # html.entities not available or entity not found
                    logging.warning(
                        f"Unknown HTML entity '&{entity};' found, replacing with '?'"
                    )
                    return "?"

            xml_content = re.sub(
                r"&([a-zA-Z][a-zA-Z0-9]*);", replace_unknown_entity, xml_content
            )

        except Exception as e:
            logging.warning(f"Entity processing warning: {e}")
            # Continue with what we have

        # Save cleaned XML for debugging
        cleaned_xml_path = os.path.join(
            PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
        )
        try:
            with open(cleaned_xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            logging.info(f"💾 Cleaned XML saved to: {cleaned_xml_path}")
        except Exception as e:
            logging.warning(f"⚠️ Failed to save cleaned XML: {e}")

        # Try to parse the cleaned XML
        root = ET.fromstring(xml_content)

        # ShopSite XML structure for products
        products = []

        # Look for Products container, then Product elements
        products_elem = root.find(".//Products")
        if products_elem is None:
            # Try direct root level
            products_elem = root

        if products_elem is not None:
            for product_elem in products_elem.findall(".//Product"):
                product_data = {}

                # Extract all child elements as fields
                for child in product_elem:
                    if child.tag == "ProductOnPages":
                        # Special handling for ProductOnPages - it's a container with PageLink/Name elements
                        page_names = []
                        # Look for Name elements under PageLink elements
                        for page_link in child.findall("PageLink"):
                            name_elem = page_link.find("Name")
                            if (
                                name_elem is not None
                                and name_elem.text
                                and name_elem.text.strip()
                            ):
                                page_names.append(name_elem.text.strip())

                        # Store as comma-separated string
                        product_data[child.tag] = (
                            ", ".join(page_names) if page_names else ""
                        )
                    else:
                        # Preserve the original text for other fields, don't strip whitespace
                        if child.text is not None:
                            product_data[child.tag] = child.text
                        else:
                            product_data[child.tag] = ""

                # Only add if we have actual data
                if product_data and any(product_data.values()):
                    # Map to editor fields only (instead of storing all 200+ fields)
                    mapped_product = map_shopsite_fields(product_data)
                    if mapped_product:  # Only add if mapping produced valid data
                        products.append(mapped_product)

        if not products:
            logging.warning(
                "⚠️ No products with data found in XML. Checking structure..."
            )
            # Log XML structure for debugging
            logging.info(f"Root tag: {root.tag}")
            for child in list(root)[:5]:  # First 5 elements
                logging.info(
                    f"Child tag: {child.tag}, text length: {len(child.text) if child.text else 0}"
                )
                for subchild in list(child)[:3]:
                    logging.info(
                        f"  Subchild: {subchild.tag}, text length: {len(subchild.text) if subchild.text else 0}"
                    )

        df = pd.DataFrame(products)
        logging.info(f"📊 Parsed {len(df)} products with data from XML")
        return df

    except ET.ParseError as e:
        logging.error(f"❌ XML parsing error: {e}")
        # Log some context around the error
        lines = xml_content.split("\n")
        error_line = getattr(e, "position", [0, 0])[0] if hasattr(e, "position") else 0
        if 0 < error_line <= len(lines):
            start_line = max(1, error_line - 2)
            end_line = min(len(lines), error_line + 2)
            logging.error(f"❌ Error context (lines {start_line}-{end_line}):")
            for i in range(start_line, end_line + 1):
                marker = ">>> " if i == error_line else "    "
                logging.error(
                    f"{marker}Line {i}: {lines[i-1][:200]}{'...' if len(lines[i-1]) > 200 else ''}"
                )

        # Save the problematic XML for manual inspection
        error_xml_path = os.path.join(
            PROJECT_ROOT, "data", "databases", "shopsite_error_debug.xml"
        )
        try:
            with open(error_xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            logging.info(
                f"💾 Error XML saved to: {error_xml_path} for manual inspection"
            )
        except Exception as save_error:
            logging.warning(f"⚠️ Failed to save error XML: {save_error}")

        return None
    except Exception as e:
        logging.error(f"❌ Unexpected error parsing XML: {e}")
        return None


def import_from_shopsite_xml(
    save_excel: bool = True, save_to_db: bool = False, interactive: bool = True, log_callback=None
) -> Tuple[bool, str]:
    """
    Import products from ShopSite using Database Automated XML Download.

    Downloads product data as XML from the products database and saves to Excel and/or database.
    
    Args:
        save_excel: Whether to save to Excel file
        save_to_db: Whether to save to database
        interactive: Whether to prompt for user confirmation (should be False for GUI mode)
        log_callback: Callback function for logging messages (for GUI integration)
    """
    client = ShopSiteXMLClient(log_callback=log_callback)

    # Authenticate first
    if not client.authenticate():
        return (
            False,
            "❌ Failed to authenticate with ShopSite XML interface. Check credentials in .env file.",
        )

    # Confirm with user before downloading live data (only in interactive mode)
    if interactive:
        print("\n⚠️  WARNING: This will download LIVE product data from ShopSite!")
        print("   This is production data - proceed with caution.")
        confirm = input("   Continue? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            return False, "❌ Import cancelled by user."

    # Download XML
    xml_content = client.download_products_xml()
    if not xml_content:
        return False, "❌ Failed to download products XML from ShopSite."

    # Parse to DataFrame
    df = parse_xml_to_dataframe(xml_content)
    if df is None or df.empty:
        return False, "❌ Failed to parse products from XML or no products found."

    # Basic data validation
    if "SKU" not in df.columns and "Name" not in df.columns:
        logging.warning(
            "⚠️ Expected columns (SKU, Name) not found. Available: "
            + ", ".join(df.columns.tolist())
        )

    # Save operations
    results = []

    if save_excel:
        output_path = os.path.join(PROJECT_ROOT, "data", "spreadsheets", "website.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            df.to_excel(output_path, index=False)
            logging.info(f"💾 Saved {len(df)} products to Excel: {output_path}")
            results.append(f"Excel: {len(df)} products")
        except Exception as e:
            logging.error(f"❌ Failed to save to Excel: {e}")
            return False, f"❌ Failed to save to Excel: {e}"

    if save_to_db:
        try:
            db_success, db_path_used = save_dataframe_to_database(df)
            if db_success:
                results.append("Database: saved successfully")
                # Print column statistics after successful database save
                try:
                    stats = get_column_statistics(db_path_used)
                    print_column_statistics(stats, get_product_count(db_path_used))
                except Exception as e:
                    logging.warning(f"⚠️ Could not generate database statistics: {e}")
            else:
                results.append("Database: failed to save")
        except Exception as e:
            logging.error(f"❌ Failed to save to database: {e}")
            results.append(f"Database: error - {e}")

    if not results:
        return False, "❌ No save operations specified or all failed"

    return True, f"✅ Successfully imported {len(df)} products ({', '.join(results)})"


# For backwards compatibility
def publish_shopsite_changes(
    html_pages: bool = True,
    custom_pages: bool = True,
    search_index: bool = True,
    sitemap: bool = True,
    full_regen: bool = False,
    log_callback=None
) -> Tuple[bool, str]:
    """
    Publish changes to ShopSite by regenerating website content.

    Args:
        html_pages: Whether to regenerate HTML product pages
        custom_pages: Whether to regenerate custom pages
        search_index: Whether to update search index
        sitemap: Whether to generate Google XML sitemap
        full_regen: Whether to do full regeneration (overrides incremental updates)
        log_callback: Callback function for logging messages (for GUI integration)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get ShopSite credentials
        config = SHOPSITE_CONFIG
        if not (config.get("username") and config.get("password")):
            error_msg = "❌ ShopSite credentials not found in environment variables"
            if log_callback:
                log_callback(error_msg)
            return False, error_msg

        # Build parameters for generate.cgi
        params = {
            "clientApp": "1",  # Required: identifies client application version
        }

        if html_pages:
            params["htmlpages"] = "1"  # Generate HTML pages
        if custom_pages:
            params["custompages"] = "1"  # Generate custom pages
        if search_index:
            params["index"] = "1"  # Update search index
        if sitemap:
            params["sitemap"] = "1"  # Generate Google XML sitemap
        if full_regen:
            params["regen"] = "1"  # Full regeneration (overrides incremental)

        publish_url = "https://www.baystatepet.com/cgi-baystatepet/bo/generate.cgi"

        if log_callback:
            log_callback("🚀 Publishing changes to ShopSite...")
            log_callback(f"URL: {publish_url}")
            log_callback(f"Parameters: {params}")
        else:
            logging.info("🚀 Publishing changes to ShopSite...")
            logging.info(f"URL: {publish_url}")
            logging.info(f"Parameters: {params}")

        # Create session with authentication
        session = requests.Session()
        session.auth = (config["username"], config["password"])

        # Make the publish request
        response = session.get(publish_url, params=params, timeout=600)  # 10 minute timeout

        if response.status_code == 200:
            success_msg = "✅ ShopSite publish completed successfully"
            if log_callback:
                log_callback(success_msg)
            else:
                logging.info(success_msg)

            # Check response content for any messages
            if response.text.strip():
                content_msg = f"📄 Response: {response.text.strip()[:200]}{'...' if len(response.text.strip()) > 200 else ''}"
                if log_callback:
                    log_callback(content_msg)
                else:
                    logging.info(content_msg)

            return True, success_msg
        else:
            error_msg = f"❌ Publish failed: {response.status_code} - {response.text[:200]}"
            if log_callback:
                log_callback(error_msg)
            else:
                logging.error(error_msg)
            return False, error_msg

    except requests.RequestException as e:
        error_msg = f"❌ Publish request failed: {e}"
        if log_callback:
            log_callback(error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"❌ Unexpected error during publish: {e}"
        if log_callback:
            log_callback(error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg
    """
    Import products from a saved ShopSite XML file (for testing/debugging).

    Args:
        xml_file_path: Path to the XML file. If None, uses the default cleaned file.
        save_to_db: Whether to save to database
    """
    if xml_file_path is None:
        xml_file_path = os.path.join(
            PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
        )

    if not os.path.exists(xml_file_path):
        return False, f"❌ XML file not found: {xml_file_path}"

    logging.info(f"📖 Reading saved XML file: {xml_file_path}")
    try:
        with open(xml_file_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        logging.info(f"✅ XML file loaded ({len(xml_content)} characters)")
    except Exception as e:
        return False, f"❌ Failed to read XML file: {e}"

    # Parse to DataFrame
    df = parse_xml_to_dataframe(xml_content)
    if df is None or df.empty:
        return False, "❌ Failed to parse products from XML or no products found."

    # Basic data validation
    if "SKU" not in df.columns and "Name" not in df.columns:
        logging.warning(
            "⚠️ Expected columns (SKU, Name) not found. Available: "
            + ", ".join(df.columns.tolist())
        )

    # Save operations
    results = []

    if save_to_db:
        try:
            db_success, db_path_used = save_dataframe_to_database(df)
            if db_success:
                results.append("Database: saved successfully")
                # Print column statistics after successful database save
                try:
                    stats = get_column_statistics(db_path_used)
                    print_column_statistics(stats, get_product_count(db_path_used))
                except Exception as e:
                    logging.warning(f"⚠️ Could not generate database statistics: {e}")
            else:
                results.append("Database: failed to save")
        except Exception as e:
            logging.error(f"❌ Failed to save to database: {e}")
            results.append(f"Database: error - {e}")

    if not results:
        return False, "❌ No save operations specified or all failed"

    return True, f"✅ Successfully imported {len(df)} products ({', '.join(results)})"


def main() -> None:
    import sys

    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--use-saved-xml":
        print("🛒 ShopSite XML Import Tool (Using Saved XML)")
        print("=" * 50)
        print("⚠️  Using previously downloaded and cleaned XML file")
        print("   This will parse and save to database only")
        print("=" * 50)

        print("\n🔄 Starting import from saved XML...")
        success, message = import_from_saved_xml()
        print(message)
        return

    print("🛒 ShopSite XML Import Tool")
    print("=" * 50)
    print("⚠️  WARNING: This imports LIVE PRODUCTION DATA")
    print("   - This will access real product data from your e-commerce site")
    print("   - Data will be saved to inventory/data/website.xlsx")
    print("   - Existing data may be merged or overwritten")
    print("   - This operation cannot be easily undone")
    print("=" * 50)

    confirm = (
        input(
            "Are you sure you want to import live product data? (type 'yes' to proceed): "
        )
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("❌ Import cancelled by user.")
        return

    print("\n🔄 Starting ShopSite XML import...")
    print("   This may take several minutes depending on product count.\n")

    success, message = import_from_shopsite_xml()
    print(message)

    if success:
        print(
            "💡 Tip: Run 'update_website_cache.py' to generate cleaned files for viewing."
        )
    else:
        print("❌ Import failed. Check the logs above for details.")


if __name__ == "__main__":
    main()
