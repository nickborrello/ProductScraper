"""
Scrapy-based scraper for ProductScraper

This module provides a bridge between the existing Selenium-based scraping system
and Scrapy spiders. It allows using Scrapy for sites that don't require JavaScript
execution or complex session management.

For JavaScript-heavy sites, you would need to install and configure Scrapy-Splash.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the Scrapy project to Python path
SCRAPY_PROJECT_DIR = Path(__file__).parent.parent.parent / "scrapy_project"
sys.path.insert(0, str(SCRAPY_PROJECT_DIR))

def scrape_with_scrapy(skus: List[str], spider_name: str = "product_spider", **kwargs) -> List[Optional[Dict[str, Any]]]:
    """
    Run a Scrapy spider and return results in format compatible with existing scrapers.

    Args:
        skus: List of SKUs to scrape
        spider_name: Name of the Scrapy spider to run
        **kwargs: Additional arguments to pass to the spider

    Returns:
        List of product dictionaries (or None for failed SKUs), matching the format
        expected by the existing scraping system
    """
    if not skus:
        return []

    # Change to Scrapy project directory
    original_cwd = os.getcwd()
    try:
        os.chdir(SCRAPY_PROJECT_DIR)

        # Prepare spider arguments
        spider_args = [str(sku) for sku in skus]

        # Build scrapy command
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider_name,
            "-a", f"skus={','.join(spider_args)}"
        ]

        # Add any additional arguments
        for key, value in kwargs.items():
            cmd.extend(["-a", f"{key}={value}"])

        print(f"🕷️ Running Scrapy spider: {' '.join(cmd)}")

        # Run the spider
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"❌ Scrapy spider failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return [None] * len(skus)

        print("✅ Scrapy spider completed successfully")

        # Try to load results from the output file
        return _load_scrapy_results(skus)

    except subprocess.TimeoutExpired:
        print("❌ Scrapy spider timed out")
        return [None] * len(skus)
    except Exception as e:
        print(f"❌ Error running Scrapy spider: {e}")
        return [None] * len(skus)
    finally:
        os.chdir(original_cwd)

def _load_scrapy_results(expected_skus: List[str]) -> List[Optional[Dict[str, Any]]]:
    """
    Load results from Scrapy output files and format them for the existing system.

    Args:
        expected_skus: List of SKUs that were scraped

    Returns:
        List of product dictionaries in the format expected by existing scrapers
    """
    results = [None] * len(expected_skus)
    sku_to_index = {sku: i for i, sku in enumerate(expected_skus)}

    # Look for the most recent output file
    output_dir = SCRAPY_PROJECT_DIR / "data"
    if not output_dir.exists():
        print("⚠️ No Scrapy output directory found")
        return results

    # Find the most recent scrapy output file
    scrapy_files = list(output_dir.glob("scrapy_output.xlsx"))
    if not scrapy_files:
        print("⚠️ No Scrapy output files found")
        return results

    latest_file = max(scrapy_files, key=lambda f: f.stat().st_mtime)

    try:
        import pandas as pd

        # Read the Excel file
        df = pd.read_excel(latest_file, dtype=str)

        # Convert each row to the expected format
        for _, row in df.iterrows():
            sku = str(row.get('SKU', '')).strip()
            if sku in sku_to_index:
                idx = sku_to_index[sku]

                # Convert to the format expected by existing scrapers
                product = {
                    'SKU': sku,
                    'Name': str(row.get('Name', '')),
                    'Price': str(row.get('Price', '')),
                    'Brand': str(row.get('Product Field 16', '')),  # Brand field
                    'Weight': str(row.get('Weight', '')),
                    'Image URLs': [],  # Would need to be populated from additional processing
                    'Category': str(row.get('Product Field 24', '')),  # Category
                    'Product Type': str(row.get('Product Field 25', '')),  # Product Type
                    'Product On Pages': str(row.get('Product On Pages', '')),
                    'Special Order': str(row.get('Product Field 11', '')),  # Special Order
                    'Product Cross Sell': str(row.get('Product Field 32', '')),  # Cross-sell
                    'ProductDisabled': '',  # Default empty
                }

                # Clean up empty strings
                for key, value in product.items():
                    if isinstance(value, str) and value.strip() == '':
                        product[key] = ''

                results[idx] = product

        found_count = sum(1 for r in results if r is not None)
        print(f"📦 Loaded {found_count} products from Scrapy output")

    except Exception as e:
        print(f"❌ Error loading Scrapy results: {e}")

    return results

# Example usage and testing
if __name__ == "__main__":
    # Test with a sample SKU
    test_skus = ["035585499741"]
    print(f"Testing Scrapy scraper with SKUs: {test_skus}")

    results = scrape_with_scrapy(test_skus)

    print("\nResults:")
    for i, result in enumerate(results):
        sku = test_skus[i]
        if result:
            print(f"✅ SKU {sku}: Found '{result.get('Name', 'Unknown')}'")
        else:
            print(f"❌ SKU {sku}: No product found")