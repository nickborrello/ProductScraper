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

# HEADLESS is set to True for production deployment
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "3002770745"  # Valid Mazuri SKU

async def main() -> None:
    """
    Apify Actor for scraping Mazuri products.
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

        Actor.log.info(f'Starting Mazuri scraper for {len(skus)} SKUs')

        # Create browser
        driver = create_browser("Mazuri", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            Actor.log.error("Could not create browser for Mazuri")
            return

        try:
            products = []

            for sku in skus:
                Actor.log.info(f'Processing SKU: {sku}')

                product_info_list = scrape_single_product(sku, driver)

                if product_info_list:
                    for product_info in product_info_list:
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

        Actor.log.info(f'Mazuri scraping completed. Found {len(products)} products.')

def scrape_products(skus, progress_callback=None, headless=None):
    """
    Scrape multiple products from Mazuri website.
    Returns a list of product dictionaries.
    """
    # Use provided headless setting, fallback to module default
    if headless is None:
        headless = HEADLESS
    
    products = []
    
    # Create browser
    driver = create_browser("Mazuri", headless=headless, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
    if driver is None:
        print("Could not create browser for Mazuri")
        return products

    try:
        total_skus = len(skus)
        for i, sku in enumerate(skus):
            if progress_callback:
                progress_callback(i, f"Processing SKU {sku}")
            
            product_info_list = scrape_single_product(sku, driver)
            
            if product_info_list:
                for product_info in product_info_list:
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
    Scrape a single product from Mazuri website.
    Returns a list of product dictionaries (one per variant).
    """
    if driver is None:
        return None

    url = f'https://mazuri.com/pages/search-results-page?q={SKU}'
    Actor.log.info(f"Navigating to search URL: {url}")
    try:
        driver.get(url)
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error loading URL {url}: {e}')
        return None

    # No cookie/terms check

    # Wait for product results or no-results message (increase timeout for slow loads)
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.snize-product")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.snize-no-products-found"))
            )
        )
    except Exception as e:
        Actor.log.error(f'[{SKU}] Timeout waiting for product or no-results message: {e}')
        return None

    # Robust no-results detection
    try:
        no_results_elements = driver.find_elements(By.CSS_SELECTOR, "li.snize-no-products-found")
        for elem in no_results_elements:
            if "didn't match any results" in elem.text:
                Actor.log.info(f"No results found for SKU: {SKU}")
                return None
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error checking no-results elements: {e}')

    if "didn't match any results" in driver.page_source:
        Actor.log.info(f"No results found for SKU: {SKU}")
        return None

    # Find first product result
    try:
        product_li = driver.find_element(By.CSS_SELECTOR, "li.snize-product")
        Actor.log.info("Found product on search results page.")
    except Exception as e:
        Actor.log.error(f'[{SKU}] No product found for SKU: {e}')
        return None

    # Click the product link to go to the detail page
    try:
        link_element = product_li.find_element(By.CSS_SELECTOR, ".snize-view-link")
        product_url = link_element.get_attribute('href')
        if product_url:
            # Mazuri links are relative, so prepend domain if needed
            if product_url.startswith("/"):
                product_url = "https://mazuri.com" + product_url
            Actor.log.info(f"Navigating to product page: {product_url}")
            driver.get(product_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
            )
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error clicking product link or loading detail page: {e}')
        return None

    # DEBUG MODE: Pause for manual inspection
    if DEBUG_MODE:
        Actor.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {SKU}")
        Actor.log.info("Press Enter in the terminal to continue with data extraction...")
        input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

    # Try to parse embedded product JSON for robust extraction
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(driver.page_source, "html.parser")
    product_json = None
    product_dicts = []
    Actor.log.info("Attempting to extract data from embedded JSON...")
    try:
        script_tag = soup.find("script", {"type": "application/json", "id": re.compile(r"ProductJson")})
        if script_tag and script_tag.string:
            import json
            product_json = json.loads(script_tag.string)
            Actor.log.info("✅ Successfully parsed embedded product JSON.")
    except Exception as e:
        Actor.log.error(f'[{SKU}] Error parsing embedded product JSON: {e}')
        product_json = None

    if product_json:
        # Extract all variants
        variants = product_json.get("variants", [])
        images = product_json.get("images", [])
        title = product_json.get("title", "Mazuri Product")
        brand = product_json.get("vendor", "Mazuri")
        Actor.log.info(f"Found {len(variants)} variants in JSON data.")
        # Try to get weight from SIZE selector (visible dropdown)
        size_weight = None
        size_labels = soup.find_all('label')
        size_label = None
        for label in size_labels:
            if label.get_text(strip=True).upper() == 'SIZE':
                size_label = label
                break
        if size_label:
            select_tag = size_label.find_next('select', {'data-index': 'option1'})
            if select_tag:
                selected_option = select_tag.find('option', selected=True)
                if not selected_option:
                    selected_option = select_tag.find('option')
                if selected_option:
                    size_weight = selected_option.get('value') or selected_option.text
                    if size_weight:
                        size_weight = str(size_weight).strip()
                        Actor.log.info(f"Found size/weight from dropdown: {size_weight}")
        seen = set()
        for i, variant in enumerate(variants):
            Actor.log.info(f"--- Processing variant {i+1}/{len(variants)} ---")
            v = {}
            # Set the SKU for each variant
            v['SKU'] = SKU
            v['Brand'] = brand if brand else "N/A"
            Actor.log.info(f"  - Brand: {v['Brand']}")
            # Weight: always use size_weight if available, and clean to just the number
            if size_weight:
                m = re.search(r'(\d+(?:\.\d+)?)', str(size_weight))
                weight_value = m.group(1) if m else "N/A"
                # Normalize weight to include LB unit
                if weight_value != "N/A":
                    v['Weight'] = f"{weight_value} LB"
                else:
                    v['Weight'] = "N/A"
            else:
                weight_raw = variant.get('option1', '') or variant.get('title', '')
                m = re.search(r'(\d+(?:\.\d+)?)', weight_raw)
                weight_value = m.group(1) if m else "N/A"
                # Normalize weight to include LB unit
                if weight_value != "N/A":
                    v['Weight'] = f"{weight_value} LB"
                else:
                    v['Weight'] = "N/A"
            Actor.log.info(f"  - Weight: {v['Weight']}")
            # Name: append weight with 'lb.' if not already present
            base_name = title if title else "N/A"
            weight_str = v['Weight']
            if weight_str and weight_str != "N/A":
                if not base_name.endswith(f"{weight_str} lb."):
                    v['Name'] = f"{base_name} {weight_str} lb."
                else:
                    v['Name'] = base_name
            else:
                v['Name'] = base_name
            Actor.log.info(f"  - Name: {v['Name']}")
            # Images: carousel images in order, fallback to other sources if <7
            image_list = []
            # Carousel images (in order)
            carousel_imgs = soup.select(".carousel-item img")
            for img_tag in carousel_imgs:
                img_url = img_tag.get("src")
                if img_url:
                    img_url = str(img_url)
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    image_list.append(img_url)
            # If fewer than 7, add main image and other fallbacks
            if len(image_list) < 7:
                # Main image (from main display area)
                main_img_tag = soup.find("img", id=re.compile(r"product-featured-image|main-product-image|product-image"))
                if main_img_tag:
                    main_img_url = main_img_tag.get("src")
                    if main_img_url:
                        main_img_url = str(main_img_url)
                        if main_img_url.startswith("//"):
                            main_img_url = "https:" + main_img_url
                        image_list.append(main_img_url)
                # Fallback: featured_image from variant
                featured = variant.get('featured_image', {})
                if featured and 'src' in featured:
                    img_url = featured['src']
                    if isinstance(img_url, str) and img_url.startswith("//"):
                        img_url = "https:" + img_url
                    image_list.append(img_url)
                # Fallback: images from product_json
                for img_url in images:
                    if isinstance(img_url, str) and img_url.startswith("//"):
                        img_url = "https:" + img_url
                    image_list.append(img_url)
            # Deduplicate, preserve order, limit to 7
            seen_imgs = set()
            deduped_imgs = []
            for img_url in image_list:
                if img_url and img_url not in seen_imgs:
                    deduped_imgs.append(img_url)
                    seen_imgs.add(img_url)
                if len(deduped_imgs) == 7:
                    break
            v['Image URLs'] = deduped_imgs
            Actor.log.info(f"  - Images found: {len(v['Image URLs'])}")
            # Deduplicate product variants by Name, Brand, Weight, and images
            key = (v['Brand'], v['Name'], v['Weight'], tuple(sorted(v['Image URLs'])))
            if key in seen:
                continue
            seen.add(key)
            product_dicts.append(v)
        if product_dicts:
            Actor.log.info(f"✅ Successfully extracted {len(product_dicts)} variants from JSON.")
            return product_dicts

    # Fallback to previous logic for single product
    Actor.log.warning("Could not use embedded JSON, falling back to HTML parsing.")
    product_info = {
        'SKU': SKU,
        'Name': 'N/A',
        'Brand': 'N/A',
        'Weight': 'N/A',
        'Image URLs': []
    }

    try:
        # Extract Brand
        try:
            brand_element = soup.find("a", class_=re.compile("product-brand"))
            product_info['Brand'] = clean_string(brand_element.text) if brand_element and brand_element.text.strip() else "N/A"
            Actor.log.info(f"✅ Brand extracted (fallback): {product_info['Brand']}")
        except Exception as e:
            Actor.log.error(f"[{SKU}] Error extracting Brand (fallback): {e}")
            product_info['Brand'] = "N/A"
        # Extract Name (append weight with 'lb.' if available)
        try:
            name_element = soup.find("h1")
            base_name = clean_string(name_element.text) if name_element and name_element.text.strip() else "N/A"
        except Exception as e:
            Actor.log.error(f"[{SKU}] Error extracting Name (fallback): {e}")
            base_name = "N/A"
        weight_str = product_info.get('Weight', None)
        if weight_str and weight_str != "N/A":
            if not base_name.endswith(f"{weight_str} lb."):
                product_info['Name'] = f"{base_name} {weight_str} lb."
            else:
                product_info['Name'] = base_name
        else:
            product_info['Name'] = base_name
        Actor.log.info(f"✅ Name extracted (fallback): {product_info['Name']}")
        # Extract Weight
        weight = None
        size_labels = soup.find_all('label')
        size_label = None
        for label in size_labels:
            if label.get_text(strip=True).upper() == 'SIZE':
                size_label = label
                break
        if size_label:
            select_tag = size_label.find_next('select', {'data-index': 'option1'})
            if select_tag:
                selected_option = select_tag.find('option', selected=True)
                if not selected_option:
                    selected_option = select_tag.find('option')
                if selected_option:
                    weight_raw = selected_option.get('value') or selected_option.text
                    if weight_raw:
                        weight_raw = str(weight_raw).strip()
                        m = re.search(r'(\d+(?:\.\d+)?)', weight_raw)
                        weight_value = m.group(1) if m else "N/A"
                        # Normalize weight to include LB unit
                        if weight_value != "N/A":
                            weight = f"{weight_value} LB"
                        else:
                            weight = "N/A"
        if not weight:
            try:
                weight_elem = soup.find("select", class_=re.compile("single-option-selector"))
                if weight_elem:
                    selected_option = weight_elem.find("option", selected=True)
                    if selected_option:
                        weight_raw = selected_option.text.strip()
                        m = re.search(r'(\d+(?:\.\d+)?)', weight_raw)
                        weight_value = m.group(1) if m else "N/A"
                        # Normalize weight to include LB unit
                        if weight_value != "N/A":
                            weight = f"{weight_value} LB"
                        else:
                            weight = "N/A"
            except Exception as e:
                Actor.log.error(f"[{SKU}] Error extracting Weight (fallback): {e}")
                weight = "N/A"
        product_info['Weight'] = weight if weight else "N/A"
        Actor.log.info(f"⚖️ Weight extracted (fallback): {product_info['Weight']}")
        # Extract Images (carousel images in order, fallback if <7)
        product_info['Image URLs'] = []
        try:
            image_list = []
            # Carousel images (in order)
            carousel_imgs = soup.select(".carousel-item img")
            for img_tag in carousel_imgs:
                img_url = img_tag.get("src")
                if img_url:
                    img_url = str(img_url)
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    image_list.append(img_url)
            # If fewer than 7, add main image and other fallbacks
            if len(image_list) < 7:
                main_img_tag = soup.find("img", id=re.compile(r"product-featured-image|main-product-image|product-image"))
                if main_img_tag:
                    main_img_url = main_img_tag.get("src")
                    if main_img_url:
                        main_img_url = str(main_img_url)
                        if main_img_url.startswith("//"):
                            main_img_url = "https:" + main_img_url
                        image_list.append(main_img_url)
                img_tags = soup.find_all("img")
                for img in img_tags:
                    img_url = img.get("src")
                    if img_url and isinstance(img_url, str) and "mazuri.com" in img_url:
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        image_list.append(img_url)
            # Deduplicate, preserve order, limit to 7
            seen_imgs = set()
            deduped_imgs = []
            for img_url in image_list:
                if img_url and img_url not in seen_imgs:
                    deduped_imgs.append(img_url)
                    seen_imgs.add(img_url)
                if len(deduped_imgs) == 7:
                    break
            product_info['Image URLs'] = deduped_imgs
            Actor.log.info(f"🖼️ Extracted {len(product_info['Image URLs'])} images (fallback).")
        except Exception as e:
            Actor.log.error(f"[{SKU}] Error extracting Image URLs (fallback): {e}")
        # Always return the required fields, even if some are missing
        # Print missing fields for debugging
        missing = []
        for key in ["Name", "Brand", "Weight", "Image URLs"]:
            if not product_info.get(key):
                missing.append(key)
        if missing:
            Actor.log.warning(f"[{SKU}] Missing fields in extracted product_info (fallback): {', '.join(missing)}")

        # Check for critical missing data - return None if essential fields are missing
        critical_fields_missing = (
            any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
            not product_info.get('Image URLs')
        )

        if critical_fields_missing:
            Actor.log.warning(f"SKU {SKU} is missing critical data (fallback). Discarding.")
            return None

        Actor.log.info(f"📊 Extracted data summary (fallback): Name={product_info.get('Name', 'N/A')[:30]}..., Brand={product_info.get('Brand', 'N/A')}, Images={len(product_info.get('Image URLs', []))}, Weight={product_info.get('Weight', 'N/A')}")
        return [product_info]

    except Exception as e:
        Actor.log.error(f'[{SKU}] Error extracting product info (fallback): {e}')
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