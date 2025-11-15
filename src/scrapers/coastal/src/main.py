import os
import sys
import time
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
import re
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

# HEADLESS is set to True for production deployment, but can be overridden by environment variable
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
DEBUG_MODE = False  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "076484648649"  # Valid Coastal Pet SKU

async def main() -> None:
    """
    Apify Actor for scraping Coastal products.
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

        Actor.log.info(f'Starting Coastal scraper for {len(skus)} SKUs')

        # Create browser
        driver = create_browser("Coastal", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            Actor.log.error("Could not create browser for Coastal")
            return

        try:
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

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        Actor.log.info(f'Coastal scraping completed. Found {len(products)} products.')

def scrape_products(skus, progress_callback=None, headless=None):
    """
    Scrape multiple products from Coastal website.
    Returns a list of product dictionaries.
    """
    # Use provided headless setting, fallback to module default
    if headless is None:
        headless = HEADLESS
    
    products = []
    
    # Create browser
    driver = create_browser("Coastal", headless=headless, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
    if driver is None:
        print("Could not create browser for Coastal")
        return products

    try:
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
    Scrape a single product from Coastal website.
    """
    if driver is None:
        return None

    url = f'https://coastalpet.com/products/search/?q={SKU}&currentPage=1'

    try:
        driver.get(url)
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error loading URL {url}: {e}')
        return None

    # Wait for search results or no-results message
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-item")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".no-results"))
            )
        )
    except Exception as e:
        Actor.log.error(f'[{SKU}] Timeout waiting for search results: {e}')
        return None

    # Check for no results
    try:
        no_results = driver.find_elements(By.CSS_SELECTOR, ".no-results")
        if no_results:
            return None
    except:
        pass

    # Find product items
    try:
        product_items = driver.find_elements(By.CSS_SELECTOR, ".product-item")
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error finding product items: {e}')
        return None

    if not product_items:
        return None

    # Process first product (assuming exact match or best match)
    product_item = product_items[0]

    try:
        # Click on the product to go to detail page
        link_element = product_item.find_element(By.CSS_SELECTOR, "a.product-item-link")
        product_url = link_element.get_attribute('href')

        if product_url:
            driver.get(product_url)

            # Wait for product page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail"))
            )

        # DEBUG MODE: Pause for manual inspection
        if DEBUG_MODE:
            Actor.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {SKU}")
            Actor.log.info("Press Enter in the terminal to continue with data extraction...")
            input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

    except Exception as e:
        Actor.log.error(f'[{SKU}] Error navigating to product detail page: {e}')
        return None

    # Extract product information
    product_info = {
        'SKU': SKU,
        'Name': 'N/A',
        'Brand': 'N/A',
        'Weight': 'N/A',
        'Image URLs': []
    }

    try:
        # Extract name
        try:
            name_element = driver.find_element(By.CSS_SELECTOR, ".product-title h1")
            product_info['Name'] = clean_string(name_element.text)
        except:
            pass

        # Extract brand
        try:
            brand_element = driver.find_element(By.CSS_SELECTOR, ".product-brand")
            product_info['Brand'] = clean_string(brand_element.text)
        except:
            pass

        # Extract weight from name or description
        name = product_info['Name']
        if name and name != 'N/A':
            import re
            # Look for weight patterns in name
            weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(lb|lbs|oz|kg|g)', name, re.IGNORECASE)
            if weight_match:
                weight_value = weight_match.group(1)
                weight_unit = weight_match.group(2).lower()

                # Convert to pounds
                if weight_unit in ['lb', 'lbs']:
                    product_info['Weight'] = weight_value
                elif weight_unit == 'oz':
                    product_info['Weight'] = str(float(weight_value) / 16)
                elif weight_unit == 'kg':
                    product_info['Weight'] = str(float(weight_value) * 2.20462)
                elif weight_unit == 'g':
                    product_info['Weight'] = str(float(weight_value) * 0.00220462)

        # Extract images
        try:
            image_elements = driver.find_elements(By.CSS_SELECTOR, ".product-gallery img")
            for img in image_elements:
                img_url = img.get_attribute('src')
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    if img_url not in product_info['Image URLs']:
                        product_info['Image URLs'].append(img_url)

            # Limit to 7 images
            product_info['Image URLs'] = product_info['Image URLs'][:7]

        except Exception as e:
            Actor.log.error(f'[{SKU}] Error extracting images: {e}')

        # Check for critical missing data
        critical_fields_missing = (
            product_info['Name'] == 'N/A' or
            not product_info.get('Image URLs')
        )

        if critical_fields_missing:
            Actor.log.warning(f'[{SKU}] Critical fields missing, skipping product')
            return None

        return product_info

    except Exception as e:
        Actor.log.error(f'[{SKU}] Error extracting product info: {e}')
        return None


if __name__ == "__main__":
    # Set debug mode when running directly
    os.environ['HEADLESS'] = 'False'
    os.environ['DEBUG_MODE'] = 'True'
    
    # Set default input if not provided
    if not os.getenv('APIFY_INPUT'):
        os.environ['APIFY_INPUT'] = '{"skus": ["CO001"]}'
    
    # Run the scraper
    asyncio.run(main())