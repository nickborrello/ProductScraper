import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from src.utils.scraping.scraping import get_standard_chrome_options
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error
import os
import time

HEADLESS = True
TEST_SKU = "076484061233"

def clean_string(s):
    s = re.sub(r'\d+\s*ea/?', '', s).strip()
    s = s.replace(',', '').strip()
    s = re.sub(r'[\|®™©]', '', s)
    s = re.sub(r'(\d+)\s*[-–—]\s*(\d+)', r'\1-\2', s)
    s = re.sub(r'(?<!\d)[-–—](?!\d)', ' ', s)
    s = re.sub(r'(\d+)\"', r'\1 in.', s)
    s = re.sub(r"(\d+)'", r'\1 ft.', s)
    units = ['oz', 'lb', 'ft', 'cm', 'kg', 'in']
    for unit in units:
        s = re.sub(rf'\b{unit}\b', f'{unit}.', s, flags=re.IGNORECASE)
    s = re.sub(r'\.{2,}', '.', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()

def scrape_coastal_pet(skus):
    """Scrape Coastal Pet products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    with create_browser("Coastal Pet", headless=HEADLESS) as driver:
        if driver is None:
            display_error("Could not create browser for Coastal Pet")
            return products
            
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus))
            else:
                products.append(None)
            
            display_scraping_progress(i, len(skus), start_time, "Coastal Pet")
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Coastal Pet")
                
    return products

def scrape_single_product(SKU, driver):
    search_url = f"https://www.coastalpet.com/products/search/?q={SKU}"
    product_info = {}
    
    # Set the SKU in the product info
    product_info['SKU'] = SKU

    try:
        driver.get(search_url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-listing"))
            )
            first_result = driver.find_element(By.CSS_SELECTOR, "div.product-listing")

            try:
                name_elem = first_result.find_element(By.CSS_SELECTOR, "p.product-listing__title--text a")
                name = clean_string(name_elem.text.strip())
                if not name:
                    product_info['Name'] = 'N/A'  # Placeholder instead of failing
                else:
                    product_info['Name'] = name
            except:
                product_info['Name'] = 'N/A'  # Placeholder instead of failing

            product_info['Brand'] = 'Coastal'

            try:
                image_elem = first_result.find_element(By.CSS_SELECTOR, "img.product-listing__product-image--image")
                img_src = image_elem.get_attribute("src")
                product_info['Image URLs'] = [img_src] if img_src else []
            except:
                product_info['Image URLs'] = []

            product_info['Weight'] = 'N/A'

        except Exception:
            display_error(f"No result found for {SKU}.")
            return None

    except Exception as e:
        display_error(f"Scraping error: {e}")
        return None

    # Check for critical missing data - return None if essential fields are missing
    critical_fields_missing = (
        any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
        not product_info.get('Image URLs')
    )

    if critical_fields_missing:
        return None

    return product_info

if __name__ == "__main__":
    test_sku = "076484648649"
    print(f"🔍 Scraping Coastal Pet for SKU: {test_sku}")
    results = scrape_coastal_pet([test_sku])

    if results and len(results) > 0:
        print("✅ Scrape successful:")
        for key, val in results[0].items():
            print(f"{key}: {val}")
    else:
        print("⚠️ No product data found.")
