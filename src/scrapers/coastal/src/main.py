import os
import sys
import time
from typing import Iterator, Dict, Any
import apify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pathlib

# Add the parent of ProductScraper to sys.path
project_root = pathlib.Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.scraping.scraping import get_standard_chrome_options, clean_string
from src.utils.scraping.browser import create_browser

# HEADLESS is set to True for production deployment
HEADLESS = True
DEBUG_MODE = False  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = False  # Set to True to enable Chrome DevTools remote debugging
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging

async def main() -> None:
    """
    Apify Actor for scraping Coastal products.
    """
    async with apify.Actor:
        # Get input
        actor_input = await apify.get_input()
        skus = actor_input.get('skus', [])

        if not skus:
            await apify.log.error('No SKUs provided in input')
            return

        await apify.log.info(f'Starting Coastal scraper for {len(skus)} SKUs')

        # Initialize the Actor
        actor = apify.Actor()

        # Create browser
        driver = create_browser("Coastal", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            await apify.log.error("Could not create browser for Coastal")
            return

        try:
            products = []

            for sku in skus:
                await apify.log.info(f'Processing SKU: {sku}')

                product_info = scrape_single_product(sku, driver)

                if product_info:
                    products.append(product_info)
                    await apify.log.info(f'Successfully scraped product: {product_info["Name"]}')

                    # Push data to dataset
                    await actor.push_data(product_info)
                else:
                    await apify.log.warning(f'No product found for SKU: {sku}')

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        await apify.log.info(f'Coastal scraping completed. Found {len(products)} products.')

def scrape_single_product(SKU, driver):
    """
    Scrape a single product from Coastal website.
    """
    if driver is None:
        return None

    url = f'https://www.coastalpet.com/search?q={SKU}'

    try:
        driver.get(url)
    except Exception as e:
        apify.log.error(f'[{SKU}] Error loading URL {url}: {e}')
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
        apify.log.error(f'[{SKU}] Timeout waiting for search results: {e}')
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
        apify.log.error(f'[{SKU}] Error finding product items: {e}')
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
            apify.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {SKU}")
            apify.log.info("Press Enter in the terminal to continue with data extraction...")
            input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

    except Exception as e:
        apify.log.error(f'[{SKU}] Error navigating to product detail page: {e}')
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
            apify.log.error(f'[{SKU}] Error extracting images: {e}')

        # Check for critical missing data
        critical_fields_missing = (
            product_info['Name'] == 'N/A' or
            not product_info.get('Image URLs')
        )

        if critical_fields_missing:
            apify.log.warning(f'[{SKU}] Critical fields missing, skipping product')
            return None

        return product_info

    except Exception as e:
        apify.log.error(f'[{SKU}] Error extracting product info: {e}')
        return None