import os
import sys
import time
import pickle
import re
import pandas as pd
from typing import Iterator, Dict, Any
import apify
from apify import Actor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
import random
import pathlib

# Add the project root to the Python path for direct execution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

def clean_string(text: str) -> str:
    """Clean and normalize string."""
    if not text:
        return ""
    return " ".join(text.split()).strip()

def create_browser(profile_suffix: str = "default", headless: bool = True, enable_devtools: bool = False, devtools_port: int = 9222) -> webdriver.Chrome:
    """Create Chrome driver with enhanced anti-detection measures and proxy support."""
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # Dynamic viewport to avoid detection
    width = random.randint(1024, 1920)
    height = random.randint(768, 1080)
    options.add_argument(f"--window-size={width},{height}")

    # Rotate user agents
    try:
        ua = UserAgent()
        user_agent = ua.random
    except:
        # Fallback user agent if fake-useragent fails
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    options.add_argument(f'--user-agent={user_agent}')

    # Enable Chrome DevTools remote debugging if configured
    if enable_devtools:
        options.add_argument(f"--remote-debugging-port={devtools_port}")
        options.add_argument("--remote-debugging-address=0.0.0.0")
        Actor.log.info(f"🔧 DevTools enabled on port {devtools_port}")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

# HEADLESS is set to True for production deployment
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM - test SKU for Phillips

LOGIN_URL = "https://shop.phillipspet.com/ccrz__CCSiteLogin"
HOME_URL = "https://shop.phillipspet.com/"
SEARCH_URL_TEMPLATE = "https://shop.phillipspet.com/ccrz__ProductList?cartID=&operation=quickSearch&searchText={}&portalUser=&store=DefaultStore&cclcl=en_US"

def load_cookies(driver):
    try:
        import pickle
        cookie_path = os.path.join(project_root, "data", "cookies", "phillips_cookies.pkl")
        if not os.path.exists(cookie_path):
            return
        with open(cookie_path, "rb") as f:
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
        cookie_dir = os.path.join(project_root, "data", "cookies")
        os.makedirs(cookie_dir, exist_ok=True)
        cookies = driver.get_cookies()
        with open(os.path.join(cookie_dir, "phillips_cookies.pkl"), "wb") as f:
            pickle.dump(cookies, f)
    except:
        pass

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

    # Try to get credentials from environment variables
    username = os.getenv('PHILLIPS_USERNAME')
    password = os.getenv('PHILLIPS_PASSWORD')

    if not username or not password:
        raise ValueError("Phillips credentials not configured. Set PHILLIPS_USERNAME and PHILLIPS_PASSWORD environment variables.")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "emailField"))
    ).send_keys(username)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "passwordField"))
    ).send_keys(password)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "send2Dsk"))
    ).click()

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.doLogout.cc_do_logout"))
    )
    # Save cookies after successful login
    save_cookies(driver)

async def main() -> None:
    """
    Apify Actor for scraping Phillips products.
    """
    async with apify.Actor as actor:
        # Get input - try multiple methods for local testing
        actor_input = await actor.get_input() or {}
        Actor.log.info(f"Received input from actor.get_input(): {actor_input}")
        
        # For local testing, also check environment variables
        if not actor_input.get('skus'):
            import os
            input_json = os.getenv('APIFY_INPUT')
            if input_json:
                import json
                try:
                    actor_input = json.loads(input_json)
                    Actor.log.info(f"Loaded input from APIFY_INPUT env var: {actor_input}")
                except json.JSONDecodeError:
                    Actor.log.warning("Failed to parse APIFY_INPUT as JSON")
        
        skus = actor_input.get('skus', [])
        
        if not skus:
            Actor.log.error('No SKUs provided in input')
            return

        Actor.log.info(f'Starting Phillips scraper for {len(skus)} SKUs')

        # Create browser
        driver = create_browser("Phillips", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            Actor.log.error("Could not create browser for Phillips")
            return

        try:
            # Handle login
            if not is_logged_in(driver):
                Actor.log.info("Logging in to Phillips...")
                login(driver)
                Actor.log.info("Login successful")
            else:
                Actor.log.info("Already logged in to Phillips")

            products = []

            for sku in skus:
                Actor.log.info(f'Processing SKU: {sku}')

                product_info = scrape_single_product(sku, driver)

                if product_info:
                    products.append(product_info)
                    Actor.log.info(f'Successfully scraped product: {product_info["Name"]}')

                    # Push data to dataset
                    await actor.push_data(product_info)
                else:
                    Actor.log.warning(f'No product found for SKU: {sku}')

        except ValueError as e:
            if "credentials not configured" in str(e):
                Actor.log.warning("Phillips credentials not configured - skipping login and attempting direct access")
                # Continue without login
                products = []

                for sku in skus:
                    Actor.log.info(f'Processing SKU: {sku}')

                    product_info = scrape_single_product(sku, driver)

                    if product_info:
                        products.append(product_info)
                        Actor.log.info(f'Successfully scraped product: {product_info["Name"]}')

                        # Push data to dataset
                        await actor.push_data(product_info)
                    else:
                        Actor.log.warning(f'No product found for SKU: {sku}')
            else:
                raise

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        Actor.log.info(f'Phillips scraping completed. Found {len(products)} products.')

def scrape_products(skus, progress_callback=None, headless=None):
    """
    Scrape multiple products from Phillips website.
    Returns a list of product dictionaries.
    """
    # Use provided headless setting, fallback to module default
    if headless is None:
        headless = HEADLESS
    
    products = []
    
    # Create browser
    driver = create_browser("Phillips", headless=headless, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
    if driver is None:
        print("Could not create browser for Phillips")
        return products

    try:
        # Handle login
        if not is_logged_in(driver):
            print("Logging in to Phillips...")
            login(driver)
            print("Login successful")
        else:
            print("Already logged in to Phillips")
        
        total_skus = len(skus)
        for i, sku in enumerate(skus):
            if progress_callback:
                progress_callback(i, f"Processing SKU {sku}")
            
            product_info = scrape_single_product(sku, driver)
            
            if product_info:
                products.append(product_info)
                print(f'Successfully scraped product: {product_info["Name"]}')
            else:
                print(f'No product found for SKU: {sku}')
                
        if progress_callback:
            progress_callback(total_skus, f"Completed scraping {total_skus} SKUs")
            
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return products

def scrape_single_product(SKU, driver):
    """
    Scrape a single product from Phillips website.
    """
    if driver is None:
        return None

    product_info = {
        'SKU': SKU,
        'Brand': 'N/A',
        'Name': 'N/A',
        'Weight': 'N/A',
        'Image URLs': []
    }
    Actor.log.info(f"🔍 Starting data extraction for SKU: {SKU}")

    try:
        search_url = SEARCH_URL_TEMPLATE.format(SKU)
        driver.get(search_url)
        Actor.log.info(f"Navigated to search URL: {search_url}")

        if SEARCH_URL_TEMPLATE.split("?")[0] not in driver.current_url:
            Actor.log.error("Navigation to search URL failed. Aborting.")
            return None

        # Wait for either product results or empty state message
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.cc_product_item")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.plp-empty-state-message-container h3"))
            )
        )

        # DEBUG MODE: Pause for manual inspection
        if DEBUG_MODE:
            apify.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {SKU}")
            apify.log.info("Press Enter in the terminal to continue with data extraction...")
            input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

        empty_msg_elements = driver.find_elements(By.CSS_SELECTOR, "div.plp-empty-state-message-container h3")
        if empty_msg_elements:
            empty_text = empty_msg_elements[0].text.strip().lower()
            if "no results were found" in empty_text:
                Actor.log.info(f"No results found for SKU: {SKU}")
                return None

        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.cc_product_item.cc_row_item")
        Actor.log.info(f"Found {len(product_elements)} product elements on the page.")

        for product in product_elements:
            try:
                upc_elem = product.find_element(By.XPATH, ".//div[contains(@class,'product-upc')]//span[contains(@class,'cc_value')]")
                current_upc = upc_elem.text.strip()
                if current_upc == SKU:
                    Actor.log.info(f"Found matching product for SKU: {SKU}")
                    name = product.find_element(By.CSS_SELECTOR, "a.cc_product_name").text.strip()
                    product_info['Name'] = name if name else 'N/A'
                    Actor.log.info(f"✅ Name extracted: {product_info['Name']}")

                    brand = product.find_element(By.CSS_SELECTOR, "div.product-brand span").text.strip()
                    product_info['Brand'] = brand if brand else 'N/A'
                    Actor.log.info(f"✅ Brand extracted: {product_info['Brand']}")

                    image = product.find_element(By.CSS_SELECTOR, "div.cc_product_image img").get_attribute("src")
                    product_info['Image URLs'] = [image] if image else []
                    Actor.log.info(f"🖼️ Image extracted: {image}")

                    # Check for critical missing data - return None if essential fields are missing
                    critical_fields_missing = (
                        any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
                        not product_info.get('Image URLs')
                    )

                    if critical_fields_missing:
                        Actor.log.warning(f"SKU {SKU} is missing critical data. Discarding.")
                        return None
                    
                    Actor.log.info(f"📊 Extracted data summary: Name={product_info.get('Name', 'N/A')[:30]}..., Brand={product_info.get('Brand', 'N/A')}, Images={len(product_info.get('Image URLs', []))}")
                    return product_info
            except Exception as e:
                continue
        
        Actor.log.warning(f"No exact UPC match for SKU {SKU}, products loaded but skipped.")
        return None

    except Exception as e:
        Actor.log.error(f"An exception occurred while scraping SKU {SKU}: {e}")
        return None


if __name__ == "__main__":
    # Set debug mode when running directly
    os.environ['HEADLESS'] = 'False'
    os.environ['DEBUG_MODE'] = 'True'
    
    # Set default input if not provided
    if not os.getenv('APIFY_INPUT'):
        os.environ['APIFY_INPUT'] = f'{{"skus": ["{TEST_SKU}"]}}'
    
    # Run the scraper
    asyncio.run(main())