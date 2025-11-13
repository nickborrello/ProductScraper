import os
import sys
import time
import pickle
import re
import pandas as pd
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

from src.utils.scraping.scraping import get_standard_chrome_options
from src.utils.scraping.browser import create_browser
from src.core.settings_manager import settings

# HEADLESS is set to True for production deployment
HEADLESS = True

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

async def main() -> None:
    """
    Apify Actor for scraping Phillips products.
    """
    async with apify.Actor:
        # Get input
        actor_input = await apify.get_input()
        skus = actor_input.get('skus', [])

        if not skus:
            await apify.log.error('No SKUs provided in input')
            return

        await apify.log.info(f'Starting Phillips scraper for {len(skus)} SKUs')

        # Initialize the Actor
        actor = apify.Actor()

        # Create browser
        driver = create_browser("Phillips", headless=HEADLESS)
        if driver is None:
            await apify.log.error("Could not create browser for Phillips")
            return

        try:
            # Handle login
            if not is_logged_in(driver):
                await apify.log.info("Logging in to Phillips...")
                login(driver)
                await apify.log.info("Login successful")
            else:
                await apify.log.info("Already logged in to Phillips")

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

        await apify.log.info(f'Phillips scraping completed. Found {len(products)} products.')

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

    try:
        search_url = SEARCH_URL_TEMPLATE.format(SKU)
        driver.get(search_url)

        if SEARCH_URL_TEMPLATE.split("?")[0] not in driver.current_url:
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
                continue

        return None

    except Exception as e:
        return None