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
from selenium.webdriver.chrome.service import Service
import pathlib

# Add the project root to the Python path for direct execution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from utils.scraping.scraping import get_standard_chrome_options
from utils.scraping.browser import create_browser
from src.core.settings_manager import settings

# HEADLESS is set to True for production deployment
HEADLESS = True
DEBUG_MODE = False  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM - test SKU for Pet Food Experts

LOGIN_URL = "https://orders.petfoodexperts.com/SignIn"
HOME_URL = "https://orders.petfoodexperts.com/"

def load_cookies(driver):
    try:
        import pickle
        cookie_path = os.path.join(project_root, "data", "cookies", "petfoodex_cookies.pkl")
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
        with open(os.path.join(cookie_dir, "petfoodex_cookies.pkl"), "wb") as f:
            pickle.dump(cookies, f)
    except:
        pass

def is_logged_in(driver):
    # Load saved cookies first
    load_cookies(driver)

    driver.get(HOME_URL)
    time.sleep(3)  # Reduced wait time

    current_url = driver.current_url

    # Check if we're redirected to login page
    if "SignIn" in current_url or "login" in current_url.lower():
        return False

    # Check for various logout/signout links
    try:
        logout_selectors = [
            "a[href*='logout']", "a[href*='signout']", "a[href*='Logout']", "a[href*='SignOut']",
            "a[href*='logoff']", "a[href*='signoff']"
        ]
        for selector in logout_selectors:
            logout_links = driver.find_elements(By.CSS_SELECTOR, selector)
            if logout_links:
                return True
    except Exception:
        pass

    # Check for user account/profile links
    try:
        account_selectors = [
            "a[href*='account']", "a[href*='profile']", "a[href*='myaccount']",
            "a[href*='my-account']", "a[href*='user']"
        ]
        for selector in account_selectors:
            account_links = driver.find_elements(By.CSS_SELECTOR, selector)
            if account_links:
                return True
    except Exception:
        pass

    # Check page content for logged-in indicators
    try:
        page_text = driver.page_source.lower()
        logged_in_indicators = ['welcome', 'dashboard', 'my account', 'logout', 'sign out', 'hello']
        found_indicators = [indicator for indicator in logged_in_indicators if indicator in page_text]
        if found_indicators:
            return True
    except Exception:
        pass

    # Check if we're on the home page and not redirected to login
    if "petfoodexperts.com" in current_url and "SignIn" not in current_url:
        return True

    return False

def login(driver):
    driver.get(LOGIN_URL)
    time.sleep(3)  # Let page load

    username, password = settings.petfood_credentials

    if not username or not password:
        raise ValueError("PetFood credentials not configured in settings")

    try:
        # Wait for and fill username
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "userName"))
        )
        username_field.clear()
        username_field.send_keys(username)
    except Exception as e:
        raise Exception(f"Failed to enter username: {e}")

    try:
        # Wait for and fill password
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.clear()
        password_field.send_keys(password)
    except Exception as e:
        raise Exception(f"Failed to enter password: {e}")

    try:
        # Find the submit button
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-selector='signIn_submit']"))
        )

        # Try to click
        submit_button.click()
    except Exception as e:
        raise Exception(f"Failed to click login button: {e}")

    try:
        # Wait for redirect
        WebDriverWait(driver, 30).until(
            lambda d: d.current_url != LOGIN_URL and "SignIn" not in d.current_url
        )
        # Save cookies after successful login
        save_cookies(driver)
    except Exception as e:
        raise Exception(f"Login may have timed out: {e}")

def parse_weight_from_name(name):
    """
    Extract weight from product name and convert to pounds (LB).
    Handles formats like: 12 oz, 3 lb, 1.5kg, 500g, etc.
    Returns weight in LB as string, or empty string if not found.
    """
    import re

    if not name:
        return ""

    # Patterns to match various weight formats
    patterns = [
        # Pounds: "3 lb", "3lb", "3.5 lbs", "3-lb", "3LB"
        (r'(\d+(?:\.\d+)?)\s*-?\s*(?:lb|lbs|pound|pounds)\b', 1.0),
        # Ounces: "12 oz", "12oz", "12.5 oz.", "12-oz", "12OZ"
        (r'(\d+(?:\.\d+)?)\s*-?\s*(?:oz|ounce|ounces)\.?\b', 1.0/16.0),
        # Kilograms: "1.5 kg", "2kg", "1.5-kg", "2KG"
        (r'(\d+(?:\.\d+)?)\s*-?\s*(?:kg|kilogram|kilograms)\b', 2.20462),
        # Grams: "500 g", "500g", "500-g", "500G"
        (r'(\d+(?:\.\d+)?)\s*-?\s*(?:g|gram|grams)\b', 0.00220462),
    ]

    for pattern, conversion_factor in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                weight_lb = value * conversion_factor
                # Round to 2 decimal places
                return f"{weight_lb:.2f}"
            except (ValueError, IndexError):
                continue

    return ""

async def main() -> None:
    """
    Apify Actor for scraping Pet Food Experts products.
    """
    async with apify.Actor as actor:
        # Get input
        actor_input = await actor.get_input()
        skus = actor_input.get('skus', [])

        if not skus:
            await actor.log.error('No SKUs provided in input')
            return

        await actor.log.info(f'Starting Pet Food Experts scraper for {len(skus)} SKUs')

        # Create browser
        driver = create_browser("Pet Food Experts", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            await actor.log.error("Could not create browser for Pet Food Experts")
            return

        try:
            # Handle login
            if not is_logged_in(driver):
                await actor.log.info("Logging in to Pet Food Experts...")
                login(driver)
                await actor.log.info("Login successful")
            else:
                await actor.log.info("Already logged in to Pet Food Experts")

            products = []

            for sku in skus:
                await actor.log.info(f'Processing SKU: {sku}')

                product_info = scrape_single_product(sku, driver)

                if product_info:
                    products.append(product_info)
                    await actor.log.info(f'Successfully scraped product: {product_info["Name"]}')

                    # Push data to dataset
                    await actor.push_data(product_info)
                else:
                    await actor.log.warning(f'No product found for SKU: {sku}')

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        await actor.log.info(f'Pet Food Experts scraping completed. Found {len(products)} products.')

def scrape_products(skus, progress_callback=None, headless=None):
    """
    Scrape multiple products from Pet Food Experts website.
    Returns a list of product dictionaries.
    """
    # Use provided headless setting, fallback to module default
    if headless is None:
        headless = HEADLESS
    
    products = []
    
    # Create browser
    driver = create_browser("Pet Food Experts", headless=headless, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
    if driver is None:
        print("Could not create browser for Pet Food Experts")
        return products

    try:
        # Handle login
        if not is_logged_in(driver):
            print("Logging in to Pet Food Experts...")
            login(driver)
            print("Login successful")
        else:
            print("Already logged in to Pet Food Experts")
        
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

def scrape_single_product(sku, driver):
    """
    Scrape a single product from Pet Food Experts website.
    """
    if driver is None:
        return None

    try:
        search_url = f"https://orders.petfoodexperts.com/Search?query={sku}"
        driver.get(search_url)

        # Wait for page to load - either search results or product detail
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "label[data-test-selector='productListSortSelect-label']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.pf-detail-wrap")),
                # Also wait for "no results" message
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pf-no-results")),
            )
        )

        # Give page a moment to fully load
        time.sleep(2)

        # DEBUG MODE: Pause for manual inspection
        if DEBUG_MODE:
            apify.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {sku}")
            apify.log.info("Press Enter in the terminal to continue with data extraction...")
            input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

        # Check if we're on a product detail page (has highest priority)
        if driver.find_elements(By.CSS_SELECTOR, "div.pf-detail-wrap"):
            time.sleep(1)
            try:
                brand_elem = driver.find_element(By.CSS_SELECTOR, "a.pf-detail-title span")
            except:
                brand_elem = None
            try:
                name_elem = driver.find_element(By.CSS_SELECTOR, "div.pf-detail-heading h1")
            except:
                name_elem = None

            # Extract all images - main image and slider thumbnails
            image_urls = []
            try:
                # Get main image
                main_image = driver.find_element(By.CSS_SELECTOR, "img[data-test-selector='productDetails_mainImage']")
                main_image_src = main_image.get_attribute("src")
                if main_image_src:
                    image_urls.append(main_image_src)
            except:
                pass

            try:
                # Get all slider thumbnail images
                slider_images = driver.find_elements(By.CSS_SELECTOR, ".pf-detail-nav .pf-slide img")
                for img in slider_images:
                    img_src = img.get_attribute("src")
                    if img_src and img_src not in image_urls:
                        # Convert small (_sm) images to medium (_md) for better quality
                        if "_sm.png" in img_src:
                            img_src = img_src.replace("_sm.png", "_md.png")
                        elif "_sm.jpg" in img_src:
                            img_src = img_src.replace("_sm.jpg", "_md.jpg")
                        image_urls.append(img_src)
            except Exception as e:
                pass

            brand = brand_elem.text.strip() if brand_elem else ""
            name = name_elem.text.strip() if name_elem else ""
            # Normalize to title case if all caps
            if brand.isupper():
                brand = brand.title()
            if name.isupper():
                name = name.title()

            # Remove brand from beginning of name if present (case-insensitive)
            if brand and brand.strip() and name.startswith(brand + " "):
                name = name[len(brand) + 1:].strip()
            elif brand and brand.strip() and name.startswith(brand + "-"):
                name = name[len(brand) + 1:].strip()

            # Normalize weights like '12Oz' to '12 oz.' in name
            import re
            name = re.sub(r'(\d+)\s*[Oo][Zz]\b', r'\1 oz.', name)

            # Parse weight from name and convert to LB
            weight_lb = parse_weight_from_name(name)

            product_info = {
                "SKU": sku,
                "Name": name,
                "Brand": brand,
                "Image URLs": image_urls,
                "Weight": weight_lb,
            }

            # Check for critical missing data - return None if essential fields are missing
            critical_fields_missing = (
                not product_info.get('Name', '').strip() or
                not product_info.get('Brand', '').strip() or
                not product_info.get('Image URLs')
            )

            if critical_fields_missing:
                return None

            return product_info

        # Check for no results message
        elif driver.find_elements(By.CSS_SELECTOR, ".pf-no-results"):
            return None

        # Check if we're on search results page with actual results
        elif driver.find_elements(By.CSS_SELECTOR, "label[data-test-selector='productListSortSelect-label']"):
            # Look for product cards in search results - be more specific to avoid false positives
            product_cards = driver.find_elements(By.CSS_SELECTOR, ".pf-product-card, .product-card")
            if product_cards:
                # This might indicate the SKU matches multiple products - we could potentially scrape the first one
                # For now, return None since we expect direct navigation for exact SKU matches
                return None
            else:
                return None

        else:
            return None

    except Exception as e:
        apify.log.error(f"PetFoodExperts scrape error for SKU {sku}: {e}")
        return None