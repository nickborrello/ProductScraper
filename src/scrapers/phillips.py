import os
import sys
import time
import pickle
import re
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from src.utils.scraping.scraping import get_standard_chrome_options
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error
from src.core.settings_manager import settings

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
HEADLESS = False
TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM - test SKU for Phillips
LOGIN_URL = "https://shop.phillipspet.com/ccrz__CCSiteLogin"
HOME_URL = "https://shop.phillipspet.com/"
SEARCH_URL_TEMPLATE = "https://shop.phillipspet.com/ccrz__ProductList?cartID=&operation=quickSearch&searchText={}&portalUser=&store=DefaultStore&cclcl=en_US"

def load_cookies(driver):
    try:
        import pickle
        with open("cookies/phillips_cookies.pkl", "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
    except:
        pass

def save_cookies(driver):
    try:
        import pickle
        cookies = driver.get_cookies()
        with open("cookies/phillips_cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)
    except:
        pass

def init_browser(profile_suffix="default", headless=True):
    # Use standard Chrome options
    from src.utils.scraping.scraping import get_standard_chrome_options
    options = get_standard_chrome_options(headless=headless, profile_suffix=profile_suffix)
    
    # Use selenium_profiles directory for phillips with unique suffix
    user_data_dir = os.path.join(PROJECT_ROOT, "data", "selenium_profiles", f"phillips_{profile_suffix}")
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Add service with error suppression
    from selenium.webdriver.chrome.service import Service as ChromeService
    service = ChromeService(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=options)

def is_logged_in(driver):
    # Load saved cookies first
    load_cookies(driver)
    
    try:
        driver.get(HOME_URL)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.doLogout.cc_do_logout"))
        )
        return True
    except:
        return False

def login(driver):
    driver.get(LOGIN_URL)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "emailField"))
    ).send_keys(settings.phillips_credentials[0])

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "passwordField"))
    ).send_keys(settings.phillips_credentials[1])

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "send2Dsk"))
    ).click()

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.doLogout.cc_do_logout"))
    )
    # Save cookies after successful login
    save_cookies(driver)

def scrape_phillips(skus, browser=None, log_callback=None):
    """Scrape Phillips products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    # Use provided browser or create a new one
    if browser is not None:
        driver = browser
        if log_callback:
            log_callback("✅ Phillips: Using provided browser for scraping.")
        else:
            print("✅ Phillips: Using provided browser for scraping.")
    else:
        driver = create_browser("Phillips", headless=HEADLESS)
        if driver is None:
            display_error("Could not create browser for Phillips", log_callback=log_callback)
            return products
        if log_callback:
            log_callback("🌐 Phillips: Created new browser for scraping.")
        else:
            print("🌐 Phillips: Created new browser for scraping.")
    
    try:
        # Handle login if required (only if we created our own browser)
        if browser is None:
            if not is_logged_in(driver):
                if log_callback:
                    log_callback("🔐 Phillips: Logging in...")
                else:
                    print("🔐 Phillips: Logging in...")
                login(driver)
            else:
                if log_callback:
                    log_callback("✅ Phillips: Already logged in.")
                else:
                    print("✅ Phillips: Already logged in.")
                    
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus), log_callback=log_callback)
            else:
                products.append(None)
            
            display_scraping_progress(i, len(skus), start_time, "Phillips", log_callback=log_callback)
    
    finally:
        # Only quit browser if we created it ourselves
        if browser is None and driver:
            try:
                driver.quit()
            except:
                pass
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Phillips", log_callback=log_callback)
                
    return products

def scrape_single_product(SKU, driver, log_callback=None):
    if driver is None:
        error_msg = "❌ Error: WebDriver instance is None. Cannot scrape product."
        if log_callback:
            log_callback(error_msg)
        else:
            print(error_msg)
        return None
    product_info = {
        'SKU': SKU,
        'Brand': 'N/A',
        'Name': 'N/A',
        'Weight': 'N/A',
        'Image URLs': []
    }

    try:
        search_url = SEARCH_URL_TEMPLATE.format(SKU)
        driver.get(search_url)

        if SEARCH_URL_TEMPLATE.split("?")[0] not in driver.current_url:
            display_error("Navigation to search URL failed. Aborting.", log_callback=log_callback)
            return None

        # Wait for either product results or empty state message
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.cc_product_item")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.plp-empty-state-message-container h3"))
            )
        )

        empty_msg_elements = driver.find_elements(By.CSS_SELECTOR, "div.plp-empty-state-message-container h3")
        if empty_msg_elements:
            empty_text = empty_msg_elements[0].text.strip().lower()
            if "no results were found" in empty_text:
                return None

        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.cc_product_item.cc_row_item")

        for product in product_elements:
            try:
                upc_elem = product.find_element(By.XPATH, ".//div[contains(@class,'product-upc')]//span[contains(@class,'cc_value')]")
                current_upc = upc_elem.text.strip()
                if current_upc == SKU:
                    name = product.find_element(By.CSS_SELECTOR, "a.cc_product_name").text.strip()
                    brand = product.find_element(By.CSS_SELECTOR, "div.product-brand span").text.strip()
                    image = product.find_element(By.CSS_SELECTOR, "div.cc_product_image img").get_attribute("src")

                    product_info['Name'] = name if name else 'N/A'
                    product_info['Brand'] = brand if brand else 'N/A'
                    product_info['Image URLs'] = [image] if image else []

                    # Check for critical missing data - return None if essential fields are missing
                    critical_fields_missing = (
                        any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
                        not product_info.get('Image URLs')
                    )

                    if critical_fields_missing:
                        return None

                    return product_info
            except Exception as e:
                display_error(f"Error in product block: {e}", log_callback=log_callback)
                continue

        display_error(f"No exact UPC match for SKU {SKU}, products loaded but skipped.", log_callback=log_callback)
        return None

    except Exception as e:
        display_error(f"Exception while searching for SKU {SKU}: {e}", log_callback=log_callback)
        return None

if __name__ == "__main__":
    test_skus = [
        "123412431289705",
        "074198613953",
        "072705115211",
        "074198613939"
    ]

    print("� Scraping Phillips...")
    results = scrape_phillips(test_skus)
    for i, result in enumerate(results):
        print(f"✅ Result {i+1}: {result}")
        print("-" * 60)
