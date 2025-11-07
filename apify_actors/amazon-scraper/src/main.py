"""Amazon Product Scraper Actor"""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any

from apify import Actor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def create_driver() -> webdriver.Chrome:
    """Create Chrome driver for headless scraping."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    # Use webdriver-manager or assume chromedriver is in PATH
    service = Service()
    return webdriver.Chrome(service=service, options=options)


def clean_string(text: str) -> str:
    """Clean and normalize string."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def extract_product_data(driver: webdriver.Chrome, sku: str) -> dict[str, Any] | None:
    """Extract product data from Amazon page."""
    product_info = {"SKU": sku}

    try:
        # Extract title
        try:
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            product_info["Name"] = clean_string(title_element.text)
        except TimeoutException:
            product_info["Name"] = "N/A"

        # Extract brand
        try:
            brand_element = driver.find_element(By.ID, "bylineInfo")
            product_info["Brand"] = clean_string(brand_element.text).replace("Visit the", "").replace("Brand:", "").strip()
        except NoSuchElementException:
            product_info["Brand"] = "Unknown"

        # Extract images
        image_urls = []
        try:
            img_elements = driver.find_elements(By.CSS_SELECTOR, "#altImages img")
            for img in img_elements[:5]:  # Limit to 5 images
                src = img.get_attribute("src")
                if src and "amazon.com" in src:
                    # Convert to high res
                    high_res = re.sub(r'\._AC_[^.]+\.jpg', '._AC_SL1500_.jpg', src)
                    image_urls.append(high_res)
        except Exception:
            pass
        product_info["Image URLs"] = image_urls

        # Extract weight
        weight = "N/A"
        try:
            # Look in product details
            detail_rows = driver.find_elements(By.CSS_SELECTOR, "#productDetails tr")
            for row in detail_rows:
                if "weight" in row.text.lower():
                    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(lbs?|oz|g|kg)', row.text, re.I)
                    if weight_match:
                        value = float(weight_match.group(1))
                        unit = weight_match.group(2).lower()
                        if unit in ['oz', 'ounces']:
                            value /= 16
                        elif unit in ['g', 'gram']:
                            value /= 453.592
                        elif unit in ['kg']:
                            value *= 2.20462
                        weight = f"{value:.2f}"
                        break
        except Exception:
            pass
        product_info["Weight"] = weight

        return product_info

    except Exception as e:
        Actor.log.error(f"Error extracting data for {sku}: {e}")
        return None


def scrape_single_product(driver: webdriver.Chrome, sku: str) -> dict[str, Any] | None:
    """Scrape a single Amazon product."""
    try:
        # Try direct ASIN URL
        if len(sku) == 10 and sku.isalnum():
            url = f"https://www.amazon.com/dp/{sku}"
        else:
            url = f"https://www.amazon.com/s?k={sku}"

        driver.get(url)
        time.sleep(2)

        # Check if product page
        if "/dp/" not in driver.current_url:
            # Try to click first result
            try:
                first_result = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-component-type='s-search-result'] a"))
                )
                first_result.click()
                time.sleep(2)
            except TimeoutException:
                return None

        return extract_product_data(driver, sku)

    except Exception as e:
        Actor.log.error(f"Error scraping {sku}: {e}")
        return None


async def main() -> None:
    """Main actor function."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        skus = actor_input.get('skus', [])
        
        if not skus:
            Actor.log.error("No SKUs provided in input")
            return

        Actor.log.info(f"Starting Amazon scraping for {len(skus)} SKUs")

        # Run scraping in thread pool since Selenium is sync
        products = await asyncio.get_event_loop().run_in_executor(None, scrape_products, skus)

        # Push results
        valid_products = [p for p in products if p]
        await Actor.push_data(valid_products)
        
        Actor.log.info(f"Scraped {len(valid_products)} products successfully")


def scrape_products(skus: list[str]) -> list[dict[str, Any] | None]:
    """Scrape multiple products (runs in thread pool)."""
    driver = None
    try:
        driver = create_driver()
        products = []
        
        for sku in skus:
            product = scrape_single_product(driver, sku)
            products.append(product)
            time.sleep(1)  # Rate limiting
            
        return products
    finally:
        if driver:
            driver.quit()
