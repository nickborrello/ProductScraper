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
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging

async def main() -> None:
    """
    Apify Actor for scraping Mazuri products.
    """
    async with apify.Actor:
        # Get input
        actor_input = await apify.get_input()
        skus = actor_input.get('skus', [])

        if not skus:
            await apify.log.error('No SKUs provided in input')
            return

        await apify.log.info(f'Starting Mazuri scraper for {len(skus)} SKUs')

        # Initialize the Actor
        actor = apify.Actor()

        # Create browser
        driver = create_browser("Mazuri", headless=HEADLESS, enable_devtools=ENABLE_DEVTOOLS, devtools_port=DEVTOOLS_PORT)
        if driver is None:
            await apify.log.error("Could not create browser for Mazuri")
            return

        try:
            products = []

            for sku in skus:
                await apify.log.info(f'Processing SKU: {sku}')

                product_info_list = scrape_single_product(sku, driver)

                if product_info_list:
                    for product_info in product_info_list:
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

        await apify.log.info(f'Mazuri scraping completed. Found {len(products)} products.')

def scrape_single_product(SKU, driver):
    """
    Scrape a single product from Mazuri website.
    Returns a list of product dictionaries (one per variant).
    """
    if driver is None:
        return None

    url = f'https://mazuri.com/pages/search-results-page?q={SKU}'
    try:
        driver.get(url)
    except Exception as e:
        apify.log.error(f'[{SKU}] Error loading URL {url}: {e}')
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
        apify.log.error(f'[{SKU}] Timeout waiting for product or no-results message: {e}')
        return None

    # Robust no-results detection
    try:
        no_results_elements = driver.find_elements(By.CSS_SELECTOR, "li.snize-no-products-found")
        for elem in no_results_elements:
            if "didn't match any results" in elem.text:
                return None
    except Exception as e:
        apify.log.error(f'[{SKU}] Error checking no-results elements: {e}')

    if "didn't match any results" in driver.page_source:
        return None

    # Find first product result
    try:
        product_li = driver.find_element(By.CSS_SELECTOR, "li.snize-product")
    except Exception as e:
        apify.log.error(f'[{SKU}] No product found for SKU: {e}')
        return None

    # Click the product link to go to the detail page
    try:
        link_element = product_li.find_element(By.CSS_SELECTOR, ".snize-view-link")
        product_url = link_element.get_attribute('href')
        if product_url:
            # Mazuri links are relative, so prepend domain if needed
            if product_url.startswith("/"):
                product_url = "https://mazuri.com" + product_url
            driver.get(product_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
            )
    except Exception as e:
        apify.log.error(f'[{SKU}] Error clicking product link or loading detail page: {e}')
        return None

    # DEBUG MODE: Pause for manual inspection
    if DEBUG_MODE:
        apify.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {SKU}")
        apify.log.info("Press Enter in the terminal to continue with data extraction...")
        input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

    # Try to parse embedded product JSON for robust extraction
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(driver.page_source, "html.parser")
    product_json = None
    product_dicts = []
    try:
        script_tag = soup.find("script", {"type": "application/json", "id": re.compile(r"ProductJson")})
        if script_tag and script_tag.string:
            import json
            product_json = json.loads(script_tag.string)
    except Exception as e:
        apify.log.error(f'[{SKU}] Error parsing embedded product JSON: {e}')
        product_json = None

    if product_json:
        # Extract all variants
        variants = product_json.get("variants", [])
        images = product_json.get("images", [])
        title = product_json.get("title", "Mazuri Product")
        brand = product_json.get("vendor", "Mazuri")
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
        seen = set()
        for variant in variants:
            v = {}
            # Set the SKU for each variant
            v['SKU'] = SKU
            v['Brand'] = brand if brand else "N/A"
            # Weight: always use size_weight if available, and clean to just the number
            if size_weight:
                m = re.search(r'(\d+(?:\.\d+)?)', str(size_weight))
                v['Weight'] = m.group(1) if m else "N/A"
            else:
                weight_raw = variant.get('option1', '') or variant.get('title', '')
                m = re.search(r'(\d+(?:\.\d+)?)', weight_raw)
                v['Weight'] = m.group(1) if m else "N/A"
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
            # Deduplicate product variants by Name, Brand, Weight, and images
            key = (v['Brand'], v['Name'], v['Weight'], tuple(sorted(v['Image URLs'])))
            if key in seen:
                continue
            seen.add(key)
            product_dicts.append(v)
        if product_dicts:
            return product_dicts

    # Fallback to previous logic for single product
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
        except Exception as e:
            apify.log.error(f"[{SKU}] Error extracting Brand: {e}")
            product_info['Brand'] = "N/A"
        # Extract Name (append weight with 'lb.' if available)
        try:
            name_element = soup.find("h1")
            base_name = clean_string(name_element.text) if name_element and name_element.text.strip() else "N/A"
        except Exception as e:
            apify.log.error(f"[{SKU}] Error extracting Name: {e}")
            base_name = "N/A"
        weight_str = product_info.get('Weight', None)
        if weight_str and weight_str != "N/A":
            if not base_name.endswith(f"{weight_str} lb."):
                product_info['Name'] = f"{base_name} {weight_str} lb."
            else:
                product_info['Name'] = base_name
        else:
            product_info['Name'] = base_name
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
                        weight = m.group(1) if m else "N/A"
        if not weight:
            try:
                weight_elem = soup.find("select", class_=re.compile("single-option-selector"))
                if weight_elem:
                    selected_option = weight_elem.find("option", selected=True)
                    if selected_option:
                        weight_raw = selected_option.text.strip()
                        m = re.search(r'(\d+(?:\.\d+)?)', weight_raw)
                        weight = m.group(1) if m else "N/A"
            except Exception as e:
                apify.log.error(f"[{SKU}] Error extracting Weight (fallback): {e}")
                weight = "N/A"
        product_info['Weight'] = weight if weight else "N/A"
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
        except Exception as e:
            apify.log.error(f"[{SKU}] Error extracting Image URLs: {e}")
        # Always return the required fields, even if some are missing
        # Print missing fields for debugging
        missing = []
        for key in ["Name", "Brand", "Weight", "Image URLs"]:
            if not product_info.get(key):
                missing.append(key)
        if missing:
            apify.log.warning(f"[{SKU}] Missing fields in extracted product_info: {', '.join(missing)}")

        # Check for critical missing data - return None if essential fields are missing
        critical_fields_missing = (
            any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
            not product_info.get('Image URLs')
        )

        if critical_fields_missing:
            return None

        return [product_info]

    except Exception as e:
        apify.log.error(f'[{SKU}] Error extracting product info: {e}')
        return None