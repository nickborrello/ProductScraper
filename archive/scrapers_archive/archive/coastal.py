import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.general.display import (
    display_error,
    display_product_result,
    display_scraping_progress,
    display_scraping_summary,
)
from src.utils.scraping.browser import create_browser

HEADLESS = False
DEBUG_MODE = False  # Default to False, will be set to True when run from file
ENABLE_DEVTOOLS = True  # Set to True to enable Chrome DevTools remote debugging


def clean_string(s):
    s = re.sub(r"\d+\s*ea/?", "", s).strip()
    s = s.replace(",", "").strip()
    s = re.sub(r"[\|®™©]", "", s)
    s = re.sub(r"(\d+)\s*[-–—]\s*(\d+)", r"\1-\2", s)
    s = re.sub(r"(?<!\d)[-–—](?!\d)", " ", s)
    s = re.sub(r"(\d+)\"", r"\1 in.", s)
    s = re.sub(r"(\d+)'", r"\1 ft.", s)
    units = ["oz", "lb", "ft", "cm", "kg", "in"]
    for unit in units:
        s = re.sub(rf"\b{unit}\b", f"{unit}.", s, flags=re.IGNORECASE)
    s = re.sub(r"\.{2,}", ".", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def scrape_coastal_pet(skus, log_callback=None, progress_tracker=None, status_callback=None):
    """Scrape Coastal Pet products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    # Update status
    if status_callback:
        status_callback("Scraping Coastal Pet...")

    with create_browser(
        "Coastal Pet", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS
    ) as driver:
        if driver is None:
            display_error("Could not create browser for Coastal Pet", log_callback=log_callback)
            return products

        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver, log_callback=log_callback)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus), log_callback=log_callback)
            else:
                products.append(None)
            display_scraping_progress(
                i, len(skus), start_time, "Coastal Pet", log_callback=log_callback
            )
            # Update progress tracker if provided
            if progress_tracker:
                progress_tracker.update_sku_progress(
                    i, f"Processed {sku}", 1 if product_info else 0
                )

    successful_products = [p for p in products if p]
    display_scraping_summary(
        successful_products, start_time, "Coastal Pet", log_callback=log_callback
    )

    return products


def scrape_single_product(SKU, driver, log_callback=None):
    search_url = f"https://www.coastalpet.com/products/search/?q={SKU}"
    product_info = {}

    # Set the SKU in the product info
    product_info["SKU"] = SKU

    try:
        driver.get(search_url)
        print(f"DEBUG: Searched URL: {search_url}")
        print(f"DEBUG: Page title: {driver.title}")

        # Debug mode: pause for dev tools inspection
        if DEBUG_MODE:
            print("🔍 DEBUG MODE: Browser is paused for dev tools inspection")
            print(f"📄 Page URL: {driver.current_url}")
            print("💡 Open Chrome Dev Tools (F12) and inspect the page elements")
            print("📋 Copy the dev tools URL from the address bar and send it to me")
            print("⏸️  Press Enter in the terminal when ready to continue...")
            input()

        # Check if we got search results or an error page
        page_text = driver.page_source.lower()
        if "no results" in page_text or "not found" in page_text:
            print("DEBUG: Page indicates no results found")
            # Show a preview of the page content for debugging
            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            print(f"DEBUG: Page body preview: {body_text}")
            return None

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-listing"))
            )
            first_result = driver.find_element(By.CSS_SELECTOR, "div.product-listing")

            try:
                name_elem = first_result.find_element(
                    By.CSS_SELECTOR, "p.product-listing__title--text a"
                )
                name = clean_string(name_elem.text.strip())
                if not name:
                    product_info["Name"] = "N/A"  # Placeholder instead of failing
                else:
                    product_info["Name"] = name
            except:
                product_info["Name"] = "N/A"  # Placeholder instead of failing

            product_info["Brand"] = "Coastal"

            try:
                image_elem = first_result.find_element(
                    By.CSS_SELECTOR, "img.product-listing__product-image--image"
                )
                img_src = image_elem.get_attribute("src")
                product_info["Image URLs"] = [img_src] if img_src else []
            except:
                product_info["Image URLs"] = []

            product_info["Weight"] = "N/A"

        except Exception:
            display_error(f"No result found for {SKU}.", log_callback=log_callback)
            return None

    except Exception as e:
        display_error(f"Scraping error: {e}", log_callback=log_callback)
        return None

    # Check for critical missing data - return None if essential fields are missing
    critical_fields_missing = any(
        value == "N/A" for value in product_info.values() if isinstance(value, str)
    ) or not product_info.get("Image URLs")

    if critical_fields_missing:
        return None

    return product_info


if __name__ == "__main__":
    # Enable debug mode when running from file
    DEBUG_MODE = True

    test_sku = "076484648649"
    print(f"🔍 Scraping Coastal Pet for SKU: {test_sku}")
    results = scrape_coastal_pet([test_sku])

    if results and len(results) > 0:
        print("✅ Scrape successful:")
        for key, val in results[0].items():
            print(f"{key}: {val}")
    else:
        print("⚠️ No product data found.")
