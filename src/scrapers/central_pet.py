import os
import platform
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from src.utils.scraping.scraping import get_standard_chrome_options
from src.utils.scraping.scraping import clean_string
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error, display_success, display_warning

HEADLESS = True
TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM - test SKU for Central Pet

def scrape_central(skus, log_callback=None, progress_tracker=None):
    """Scrape Central Pet products for multiple SKUs."""
    products = []
    start_time = time.time()
    
    with create_browser("Central Pet", headless=HEADLESS) as driver:
        if driver is None:
            display_error("Could not create browser for Central Pet", log_callback=log_callback)
            return products
            
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver, log_callback=log_callback)
            if product_info:
                products.append(product_info)
                # Display individual product result
                display_product_result(product_info, i, len(skus), log_callback=log_callback)
            else:
                # Display error for failed product
                products.append(None)  # Keep list aligned with SKUs
            
            # Show progress
            display_scraping_progress(i, len(skus), start_time, "Central Pet", log_callback=log_callback)
            
            # Update progress tracker if provided
            if progress_tracker:
                progress_tracker.update_sku_progress(i, f"Processed {sku}", 1 if product_info else 0)
    
    # Display final summary
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Central Pet", log_callback=log_callback)
                
    return products

def scrape_single_product(UPC, driver, log_callback=None):
    if driver is None:
        display_error("WebDriver instance is None. Cannot scrape product.", log_callback=log_callback)
        return None
    url = f'https://www.centralpet.com/Search?criteria={UPC}'

    try:
        driver.get(url)

        # Accept cookie/terms if present (fast, no sleep)
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            ).click()
        except Exception:
            pass

        # Wait for either product detail or no-results message (short timeout)
        try:
            WebDriverWait(driver, 6).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "tst_productDetail_erpDescription")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.no-results-found"))
                )
            )
        except Exception:
            display_error("Timeout waiting for product or no-results message", UPC, log_callback=log_callback)
            return None

        # Robust no-results detection
        try:
            no_results_elements = driver.find_elements(By.CSS_SELECTOR, "span.no-results-found")
            for elem in no_results_elements:
                if "No results found for" in elem.text:
                    return None
        except Exception:
            pass

        if "No results found for" in driver.page_source:
            return None

        product_info = {}

        # Add SKU to product info
        product_info['SKU'] = UPC

        # Brand extraction (no sleep)
        try:
            brand_elements = driver.find_elements(By.CSS_SELECTOR, "a[ng-if='vm.product.brand.detailPagePath']")
            if brand_elements:
                brand_name = brand_elements[0].get_attribute('title') or brand_elements[0].text
                product_info['Brand'] = brand_name.strip() if brand_name else 'No brand found'
            else:
                product_info['Brand'] = 'No brand found'
        except Exception as e:
            display_error(f"Error extracting brand: {e}", UPC, log_callback=log_callback)
            product_info['Brand'] = 'N/A'  # Placeholder instead of failing

        # Name extraction
        try:
            name_element = driver.find_element(By.ID, "tst_productDetail_erpDescription")
            product_info['Name'] = clean_string(name_element.text) if name_element else 'No name found'
        except Exception:
            display_error("Error extracting name", UPC, log_callback=log_callback)
            product_info['Name'] = 'N/A'  # Placeholder instead of failing

        # Short description extraction
        try:
            short_description_element = driver.find_element(By.ID, "tst_productDetail_shortDescription")
            product_info['Short Description'] = short_description_element.text if short_description_element else 'No short description found'
        except Exception:
            product_info['Short Description'] = ''

        combined_name = f"{product_info['Brand']} {product_info['Name']} {product_info.get('Short Description', '')}"
        if product_info['Brand'].lower() in combined_name.lower():
            combined_name = combined_name.replace(product_info['Brand'], '').strip()
        
        # Remove unwanted suffixes and format name
        import re
        name_clean = combined_name.strip()
        
        # Remove 'One Size' and 'Assorted' (case-insensitive, only at end, with optional spacing)
        # This regex will match these words at the end, even with extra spaces
        name_clean = re.sub(r'\s+(one\s+size|assorted)\s*$', '', name_clean, flags=re.IGNORECASE)
        
        # Replace 'pk' (case-insensitive, as a word) with 'Pack'
        name_clean = re.sub(r'\bpk\b', 'Pack', name_clean, flags=re.IGNORECASE)
        
        product_info['Name'] = clean_string(name_clean)

        # Weight extraction
        try:
            weight_element = driver.find_element(By.XPATH, "//div[@class='specification-container']//li[strong[contains(text(), 'Product Gross Weight')]]/span")
            weight_text = driver.execute_script("return arguments[0].innerHTML;", weight_element).strip()
            product_info['Weight'] = f"{float(weight_text.replace('lb', '').strip()):.2f}" if weight_text else 'N/A'
        except Exception as e:
            product_info['Weight'] = 'N/A'

        # Image extraction (no sleep, minimal clicks)
        product_info['Image URLs'] = []
        try:
            thumbnails = driver.find_elements(By.CSS_SELECTOR, "li[id^='tst_productDetailPage_mainThumbnail']")
            if thumbnails:
                for thumbnail in thumbnails:
                    driver.execute_script("arguments[0].scrollIntoView();", thumbnail)
                    driver.execute_script("arguments[0].click();", thumbnail)
                    main_image_element = driver.find_element(By.ID, "mainProductImage")
                    main_image_url = main_image_element.get_attribute('ng-src')
                    if main_image_url and main_image_url not in product_info['Image URLs']:
                        product_info['Image URLs'].append(main_image_url)
            else:
                main_image_element = driver.find_element(By.ID, "mainProductImage")
                main_image_url = main_image_element.get_attribute('ng-src')
                if main_image_url:
                    product_info['Image URLs'].append(main_image_url)
        except Exception:
            product_info['Image URLs'] = []

    except Exception as e:
        display_error(f"Error processing UPC {UPC}: {e}", log_callback=log_callback)
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
    # Test with a valid UPC
    UPC_valid = '810833020324'
    print(f"\nTesting Central Pet scraper with valid UPC: {UPC_valid}")
    data = scrape_central([UPC_valid])
    successful = [p for p in data if p]
    if successful:
        display_success(f"Found {len(successful)} product(s)")
    else:
        display_error("No product data found for valid UPC")

    # Test with an invalid UPC (should trigger 'no results found')
    UPC_invalid = '21348792147892178900231494'
    print(f"\nTesting with invalid UPC: {UPC_invalid}")
    data = scrape_central([UPC_invalid])
    successful = [p for p in data if p]
    if successful:
        display_warning("Unexpected: Product data found for invalid UPC!")
    else:
        display_success("Correctly detected no results for invalid UPC")
