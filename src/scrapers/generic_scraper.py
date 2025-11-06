"""
Generic Product Scraper

This scraper provides a general-purpose solution for scraping any e-commerce website.
It works by:

1. Searching Google for the SKU + "product"
2. Presenting top results to the user for selection
3. Attempting to extract product data using common e-commerce patterns

LIMITATIONS:
- Requires user interaction for result selection
- Success rate depends on website structure following common patterns
- May not work well on highly customized or JavaScript-heavy sites
- Google search results may vary and could miss products
- No site-specific optimizations

USAGE:
- Best for one-off products from unknown websites
- Use site-specific scrapers when available for better reliability
- May require multiple attempts to find the right product page

# Generic scraper can run headless
HEADLESS = True
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.utils.scraping.scraping import clean_string
from src.utils.scraping.browser import create_browser

# Google Search API would be ideal, but for demo purposes using Selenium
GOOGLE_SEARCH_URL = "https://www.google.com/search?q={}+product"

def search_google_for_sku(sku):
    """Search Google for SKU + 'product' and return top results."""
    print(f"🔍 Searching Google for SKU: {sku}")

    with create_browser("Google Search", headless=True) as driver:
        search_url = GOOGLE_SEARCH_URL.format(sku)
        driver.get(search_url)

        # Wait for results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
        )

        results = []
        result_elements = driver.find_elements(By.CSS_SELECTOR, "div.g")[:10]  # Top 10 results

        for elem in result_elements:
            try:
                title_elem = elem.find_element(By.CSS_SELECTOR, "h3")
                link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                snippet_elem = elem.find_elements(By.CSS_SELECTOR, "span")

                title = title_elem.text
                url = link_elem.get_attribute("href")
                snippet = snippet_elem[0].text if snippet_elem else ""

                # Filter for likely product pages
                if any(keyword in url.lower() for keyword in ['product', 'item', 'detail', 'shop']):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            except:
                continue

    return results

def present_search_results_to_user(results, sku):
    """Present search results to user for selection."""
    if not results:
        print(f"❌ No search results found for SKU: {sku}")
        return None

    print(f"\n📋 Found {len(results)} potential product pages for SKU: {sku}")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:100]}...")
        print()

    # Simple console selection (could be enhanced with GUI)
    while True:
        try:
            choice = input(f"Select a result (1-{len(results)}) or 'skip': ").strip().lower()
            if choice == 'skip':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                selected = results[idx]
                print(f"✅ Selected: {selected['title']}")
                return selected
        except ValueError:
            continue

def generic_product_scraper(url, sku):
    """Generic scraper that tries common e-commerce patterns."""
    print(f"🔧 Attempting generic scrape of: {url}")

    with create_browser("Generic Scraper", headless=True) as driver:
        driver.get(url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        product_info = {'SKU': sku}

        # Try various selectors for product name
        name_selectors = [
            "h1.product-title", "h1.product-name", ".product-title", ".product-name",
            "[data-testid*='product-title']", "[class*='product-title']",
            "h1", ".title", "#product-title"
        ]

        for selector in name_selectors:
            try:
                name_elem = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                name = clean_string(name_elem.text)
                if name and len(name) > 3:
                    product_info['Name'] = name
                    print(f"✅ Found name: {name}")
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        # Try various selectors for price
        price_selectors = [
            ".price", ".product-price", "[data-price]", ".current-price",
            "[class*='price']", ".sale-price", ".regular-price"
        ]

        for selector in price_selectors:
            try:
                price_elem = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                price_text = clean_string(price_elem.text)
                if price_text and ('$' in price_text or any(char.isdigit() for char in price_text)):
                    product_info['Price'] = price_text
                    print(f"✅ Found price: {price_text}")
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        # Try various selectors for brand
        brand_selectors = [
            ".brand", ".manufacturer", ".vendor", "[class*='brand']",
            ".product-brand", ".brand-name"
        ]

        for selector in brand_selectors:
            try:
                brand_elem = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                brand = clean_string(brand_elem.text)
                if brand and len(brand) > 1:
                    product_info['Brand'] = brand
                    print(f"✅ Found brand: {brand}")
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        # Try to find images
        image_selectors = [
            ".product-image img", ".product-gallery img", ".product-photos img",
            "[class*='product-image'] img", ".zoom img"
        ]

        image_urls = []
        for selector in image_selectors:
            try:
                img_elements = WebDriverWait(driver, 3).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, selector)
                )
                for img in img_elements[:5]:  # Limit to 5 images
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and src.startswith('http') and src not in image_urls:
                        image_urls.append(src)
                if image_urls:
                    print(f"✅ Found {len(image_urls)} images")
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        product_info['Image URLs'] = image_urls

        # Set defaults for missing fields
        product_info.setdefault('Name', '')
        product_info.setdefault('Price', '')
        product_info.setdefault('Brand', '')
        product_info.setdefault('Weight', '')

        return product_info

def scrape_generic(skus):
    """Main function for generic scraping workflow."""
    products = []

    for sku in skus:
        print(f"\n🎯 Processing SKU: {sku}")

        # Step 1: Search Google
        search_results = search_google_for_sku(sku)

        # Step 2: Let user select result
        selected_result = present_search_results_to_user(search_results, sku)

        if not selected_result:
            print(f"⏭️ Skipping SKU: {sku}")
            products.append(None)
            continue

        # Step 3: Scrape the selected page
        product_info = generic_product_scraper(selected_result['url'], sku)

        if product_info and product_info.get('Name'):
            products.append(product_info)
            print(f"✅ Successfully scraped: {product_info['Name']}")
        else:
            print(f"❌ Failed to extract product data from selected page")
            products.append(None)

    return products

# Example usage
if __name__ == "__main__":
    test_skus = ["035585499741"]
    results = scrape_generic(test_skus)
    for result in results:
        if result:
            print(f"📦 Scraped: {result}")