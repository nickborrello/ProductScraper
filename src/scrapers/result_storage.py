"""
Result Storage Module

Handles storing scraper results to the database.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class ResultStorage:
    """Utility class to store scraper results to database."""

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize result storage.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Default to project data/databases/products.db
            # Use absolute path to avoid issues with working directory
            import os

            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "databases" / "products.db"

            # Ensure the directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path).resolve()  # Get absolute path

    def save(self, sku: str, scraper_name: str, results: dict[str, Any]) -> bool:
        """
        Save scraper results to database.

        Args:
            sku: Product SKU
            scraper_name: Name of scraper that produced results
            results: Dictionary of extracted fields

        Returns:
            True if save successful, False otherwise
        """
        import time

        # Try up to 3 times in case database is temporarily locked
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use timeout to avoid indefinite waiting
                # isolation_level=None enables autocommit mode for better concurrency
                conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level="DEFERRED")
                cursor = conn.cursor()

                # Enable WAL mode for concurrent access (only needs to be done once)
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout

                # Map result fields to database columns
                data = {
                    "SKU": sku,
                    "Name": results.get("Name", results.get("name", "")),
                    "Brand": results.get("Brand", results.get("brand", "")),
                    "Price": results.get("Price", results.get("price", "")),
                    "Weight": results.get("Weight", results.get("weight", "")),
                    "Images": self._format_images(results.get("Images", results.get("images", ""))),
                    "Special_Order": results.get("Special Order", results.get("special_order", "")),
                    "last_updated": datetime.now().isoformat(),
                }

                # Check if product exists
                cursor.execute("SELECT SKU FROM products WHERE SKU = ?", (sku,))
                exists = cursor.fetchone() is not None

                if exists:
                    # Update existing product
                    set_clause = ", ".join(f"{k} = ?" for k in data.keys() if k != "SKU")
                    values = [v for k, v in data.items() if k != "SKU"]
                    values.append(sku)  # For WHERE clause

                    cursor.execute(f"UPDATE products SET {set_clause} WHERE SKU = ?", values)
                else:
                    # Insert new product
                    columns = ", ".join(data.keys())
                    placeholders = ", ".join("?" * len(data))
                    cursor.execute(
                        f"INSERT INTO products ({columns}) VALUES ({placeholders})",
                        list(data.values()),
                    )

                conn.commit()
                conn.close()
                return True

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # Database is locked, wait and retry
                    print(f"[WARNING] Database locked, retrying in {attempt + 1} seconds...")
                    time.sleep(attempt + 1)
                    continue
                else:
                    print(f"[ERROR] Failed to save results for SKU {sku}: {e}")
                    return False
            except Exception as e:
                print(f"[ERROR] Failed to save results for SKU {sku}: {e}")
                return False

        return False

    def _format_images(self, images: Any) -> str:
        """
        Format images field for database storage.

        Args:
            images: Images as string, list, or other

        Returns:
            Pipe-separated string of image URLs
        """
        if isinstance(images, list):
            # Join list with pipes
            return "|".join(str(img) for img in images if img)
        elif isinstance(images, str):
            return images
        else:
            return str(images) if images else ""

    def batch_save(self, results_list: list[dict[str, Any]]) -> tuple[int, int]:
        """
        Save multiple results in batch.

        Args:
            results_list: List of result dicts with 'sku', 'scraper', 'results' keys

        Returns:
            Tuple of (successful_count, failed_count)
        """
        success_count = 0
        fail_count = 0

        for item in results_list:
            sku = item.get("sku", "")
            scraper = item.get("scraper", "unknown")
            results = item.get("results", {})

            if self.save(sku, scraper, results):
                success_count += 1
            else:
                fail_count += 1

        return success_count, fail_count
