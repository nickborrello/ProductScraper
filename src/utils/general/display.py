"""
Scrape Display Utility

Provides standardized functions for displaying scrape results across all scrapers.
This utility helps with debugging, progress tracking, and consistent output formatting.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable


def display_product_result(product: Dict[str, Any], index: Optional[int] = None, total: Optional[int] = None, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display a single product result in a standardized format.

    Args:
        product: Dictionary containing product information
        index: Current product index (1-based) for progress display
        total: Total number of products being scraped
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    
    if index is not None and total is not None:
        progress = f"[{index}/{total}] "
    else:
        progress = ""

    sku = product.get('SKU', product.get('UPC', 'Unknown'))
    name = product.get('Name', 'Unknown Product')
    brand = product.get('Brand', 'Unknown Brand')

    # Truncate long names for display
    if len(name) > 60:
        name = name[:57] + "..."

    output(f"📦 {progress}SKU: {sku}")
    output(f"   🏷️  Brand: {brand}")
    output(f"   📝 Name: {name}")

    # Show key fields
    weight = product.get('Weight', 'N/A')
    if weight and weight != 'N/A':
        output(f"   ⚖️  Weight: {weight}")

    images = product.get('Image URLs', [])
    if images:
        output(f"   🖼️  Images: {len(images)} found")
    else:
        output("   🖼️  Images: None found")

    # Show flags if any
    flagged = product.get('flagged', False)
    if flagged:
        missing_items = []
        
        # Check for N/A values in string fields
        for key, value in product.items():
            if isinstance(value, str) and value == 'N/A':
                missing_items.append(key)
        
        # Check for missing images
        images = product.get('Image URLs', [])
        if not images:
            missing_items.append('Images')
        
        if missing_items:
            missing_str = ', '.join(missing_items)
            output(f"   ⚠️  FLAGGED: Missing {missing_str}")
        else:
            output("   ⚠️  FLAGGED: Missing data or images")

    output("")  # Empty line for spacing
    output("")  # Extra buffer between products


def display_scraping_progress(current: int, total: int, start_time: float, scraper_name: str = "Scraper", log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display scraping progress with timing information.

    Args:
        current: Number of products completed
        total: Total number of products to scrape
        start_time: Time when scraping started (from time.time())
        scraper_name: Name of the scraper for display
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    remaining = total - current
    eta = remaining / rate if rate > 0 else 0

    # Show progress at start, every few items for small lists, every 10th for large lists, and at end
    if current == 1:
        progress_pct = (current / total) * 100
        output(f"🔄 {scraper_name}: {current}/{total} products ({progress_pct:.1f}%) | "
              f"Rate: {rate:.1f}/sec | ETA: {eta:.0f}s")
    elif total <= 10 or current % max(1, total // 10) == 0 or current == total:
        progress_pct = (current / total) * 100
        output(f"🔄 {scraper_name}: {current}/{total} products ({progress_pct:.1f}%) | "
              f"Rate: {rate:.1f}/sec | ETA: {eta:.0f}s")

    if current == total:
        output(f"✅ {scraper_name}: Scraping completed!")


# Global flag to suppress summary output during testing
_SUPPRESS_SUMMARY = False

def set_suppress_summary(suppress: bool):
    """Set whether to suppress scraping summary output (used during testing)."""
    global _SUPPRESS_SUMMARY
    _SUPPRESS_SUMMARY = suppress

def display_scraping_summary(products: List[Dict[str, Any]], start_time: float, scraper_name: str = "Scraper", quiet: bool = False, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display a summary of scraping results.

    Args:
        products: List of scraped product dictionaries
        start_time: Time when scraping started (from time.time())
        scraper_name: Name of the scraper for display
        quiet: If True, suppress the summary output (useful for testing)
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    
    if quiet or _SUPPRESS_SUMMARY:
        return
        
    total_time = time.time() - start_time
    successful = len([p for p in products if p])
    failed = len(products) - successful

    output(f"\n📊 {scraper_name} Summary:")
    output(f"   ⏱️  Total time: {total_time:.1f} seconds")
    output(f"   ✅ Successful: {successful} products")
    output(f"   ❌ Failed: {failed} products")

    if successful > 0:
        rate = successful / total_time
        output(f"   📈 Rate: {rate:.1f} products/second")

        # Show flagged products
        flagged = [p for p in products if p and p.get('flagged', False)]
        if flagged:
            output(f"   ⚠️  Flagged: {len(flagged)} products (missing data/images)")

        # Show image statistics
        total_images = sum(len(p.get('Image URLs', [])) for p in products if p)
        avg_images = total_images / successful if successful > 0 else 0
        output(f"   🖼️  Total images: {total_images} (avg: {avg_images:.1f} per product)")

    output("")


def display_error(message: str, sku: Optional[str] = None, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display an error message in a standardized format.

    Args:
        message: Error message to display
        sku: SKU/UPC that caused the error (optional)
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    
    if sku:
        output(f"❌ Error processing {sku}: {message}")
    else:
        output(f"❌ Error: {message}")
    
    output("")  # Add spacing after error messages


def display_info(message: str, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display an informational message.

    Args:
        message: Information message to display
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    output(f"ℹ️  {message}")


def display_success(message: str, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display a success message.

    Args:
        message: Success message to display
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    output(f"✅ {message}")


def display_warning(message: str, log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Display a warning message.

    Args:
        message: Warning message to display
        log_callback: Optional callback function for logging (defaults to print)
    """
    output = log_callback if log_callback else print
    output(f"⚠️  {message}")


# Example usage and testing
if __name__ == "__main__":
    # Test data
    test_products = [
        {
            'SKU': '123456789',
            'Name': 'Premium Dog Food - Chicken Flavor, 15lb Bag',
            'Brand': 'Premium Pet Foods',
            'Weight': '15.00',
            'Image URLs': ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
            'flagged': False
        },
        {
            'SKU': '987654321',
            'Name': 'Cat Toy Assortment - 6 Pack with Bells and Feathers',
            'Brand': 'Fun Pet Toys',
            'Weight': 'N/A',
            'Image URLs': [],
            'flagged': True
        }
    ]

    print("Testing scrape display utility...")
    print("=" * 50)

    # Test individual product display
    for i, product in enumerate(test_products, 1):
        display_product_result(product, i, len(test_products))

    # Test progress display
    start_time = time.time()
    for i in range(1, 11):
        time.sleep(0.1)  # Simulate work
        display_scraping_progress(i, 10, start_time, "Test Scraper")

    # Test summary
    display_scraping_summary(test_products, start_time, "Test Scraper")

    # Test other message types
    display_error("Network timeout", "123456789")
    display_warning("Some products may be missing images")
    display_success("Scraping completed successfully")
    display_info("All tests passed!")