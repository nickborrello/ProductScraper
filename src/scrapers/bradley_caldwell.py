import os
import platform
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.utils.scraping.scraping import clean_string
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error

# Bradley Caldwell can run headless
HEADLESS = True
TEST_SKU = "791611038437"  # SKU that previously had empty brand

def wait_for_element(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))

def scrape_bradley_caldwell(skus):
    """
    Scrape Bradley Caldwell for multiple SKUs.

    Args:
        skus: List of SKU strings to scrape

    Returns:
        List of product dictionaries
    """
    if not skus:
        return []

    products = []
    start_time = time.time()

    # Create browser instance for this scraper
    with create_browser("Bradley Caldwell", headless=HEADLESS) as driver:
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus))
            else:
                products.append(None)
            
            display_scraping_progress(i, len(skus), start_time, "Bradley Caldwell")
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Bradley Caldwell")
                
    return products

def scrape_single_product(SKU, driver):
    if driver is None:
        display_error("WebDriver instance is None. Cannot scrape product.")
        return None

    search_url = f"https://www.bradleycaldwell.com/searchresults?Ntk=All|product.active%7C&Ntt=*{SKU}*&Nty=1&No=0&Nrpp=12&Rdm=323&searchType=simple&type=search"
    product_info = {}
    
    # Set the SKU in the product info
    product_info['SKU'] = SKU

    try:
        driver.get(search_url)

        try:
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name")),
                    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'No products were found.')]"))
                )
            )
        except TimeoutException:
            print(f"❌ TIMEOUT: Product page failed to load within 20s for SKU: {SKU}")
            display_error("Timeout: Neither product nor 'no results' message appeared.")
            return None

        try:
            not_found = driver.find_element(By.XPATH, "//h2[contains(text(), 'No products were found.')]")
            if not_found:
                return None
        except NoSuchElementException:
            pass

        try:
            name_element = wait_for_element(driver, By.CSS_SELECTOR, "h1.product-name")
            # Wait a bit for JavaScript to potentially update the content
            WebDriverWait(driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(2)  # Give extra time for dynamic content to load
            
            product_info['Name'] = clean_string(name_element.text)
        except TimeoutException:
            print(f"❌ TIMEOUT: Product name element not found within 15s for SKU: {SKU}")
            display_error("Name not found.")
            product_info['Name'] = ''  # Return empty instead of trying alternatives

        # Try multiple selectors for brand extraction with shorter timeout
        brand_found = False
        brand_selectors = [
            "//div[@class='product-brand']/a",
            "//div[contains(@class, 'product-brand')]//a",
            "//span[@class='product-brand']",
            "//div[@class='product-brand']",
            "//a[contains(@href, '/brand/')]",
            "//span[contains(@class, 'brand')]",
            "//div[contains(@class, 'brand')]"
        ]

        for selector in brand_selectors:
            try:
                brand_element = WebDriverWait(driver, 3).until(  # Reduced to 3 seconds for optional elements
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                brand_name = clean_string(brand_element.text)
                if brand_name and len(brand_name.strip()) > 0:
                    product_info['Brand'] = brand_name
                    brand_found = True
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        if not brand_found:
            # Try to extract brand from product details table
            try:
                brand_table_element = WebDriverWait(driver, 3).until(  # Reduced timeout
                    EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Brand']]/td[2]"))
                )
                brand_name = clean_string(brand_table_element.text)
                if brand_name and len(brand_name.strip()) > 0:
                    product_info['Brand'] = brand_name
                    brand_found = True
            except (TimeoutException, NoSuchElementException):
                pass

        if not brand_found:
            product_info['Brand'] = ''  # Return empty if not found        # If brand was found and is in the name, remove it
        if brand_found and product_info['Brand']:
            brand_name = product_info['Brand']
            if brand_name.lower() in product_info['Name'].lower():
                product_info['Name'] = clean_string(product_info['Name'].replace(brand_name, ''))

        # Build complete product name from base name + color/size with shorter timeouts
        # Only add color/size if we have a base name
        if product_info['Name']:
            name_parts = [product_info['Name']]

            try:
                color_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional elements
                    EC.presence_of_element_located((By.XPATH, "//span[@data-bind='text: colorDesc']"))
                )
                color_desc = clean_string(color_element.text)
                if color_desc:
                    name_parts.append(color_desc)
            except (TimeoutException, NoSuchElementException):
                pass

            try:
                size_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional elements
                    EC.presence_of_element_located((By.XPATH, "//span[@data-bind='text: sizeDesc']"))
                )
                size_desc = clean_string(size_element.text)
                if size_desc:
                    name_parts.append(size_desc)
            except (TimeoutException, NoSuchElementException):
                pass

            product_info['Name'] = ' '.join(name_parts)
        # If no base name found, leave it empty (don't include just color/size)

        try:
            weight_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional weight
                EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Weight']]/td[2]"))
            )
            weight_html = weight_element.get_attribute('innerHTML')
            match = re.search(r'(\d*\.?\d+)\s*(lbs?|kg|oz)?', weight_html, re.IGNORECASE)
            if match:
                product_info['Weight'] = f"{match.group(1)} {match.group(2) or ''}".strip()
            else:
                product_info['Weight'] = ''  # Return empty if not parseable
        except (TimeoutException, NoSuchElementException):
            product_info['Weight'] = ''  # Return empty if not found

        # ✅ Scrape images from desktop and mobile carousels with shorter timeout
        try:
            WebDriverWait(driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")  # Reduced timeout
            time.sleep(1)

            image_urls = set()

            # Desktop thumbnails
            try:
                desktop_thumbs = WebDriverWait(driver, 3).until(  # Reduced timeout for optional images
                    lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-desktop a[href*='/ccstore/v1/images']")
                )
                for el in desktop_thumbs:
                    href = el.get_attribute("href")
                    if href:
                        if href.startswith("/ccstore"):
                            href = "https://www.bradleycaldwell.com" + href
                        image_urls.add(href)
            except (TimeoutException, NoSuchElementException):
                pass

            # Mobile thumbnails
            try:
                mobile_thumbs = WebDriverWait(driver, 3).until(  # Reduced timeout for optional images
                    lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-mobile a[href*='/ccstore/v1/images']")
                )
                for el in mobile_thumbs:
                    href = el.get_attribute("href")
                    if href:
                        if href.startswith("/ccstore"):
                            href = "https://www.bradleycaldwell.com" + href
                        image_urls.add(href)
            except (TimeoutException, NoSuchElementException):
                pass

            product_info['Image URLs'] = list(image_urls)

        except Exception as e:
            product_info['Image URLs'] = []
            display_error(f"Image fetch failed: {e}")

    except Exception as e:
        driver.save_screenshot("scrape_error.png")
        display_error(f"WebDriver error: {e}")
        return None

    # Check for critical missing data - only discard if no images found
    critical_fields_missing = not product_info.get('Image URLs')

    if critical_fields_missing:
        return None

    return product_info

def init_test_browser():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--v=0")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = ChromeService(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

if __name__ == "__main__":
    test_sku = "072725005516"
    print(f"🔍 Scraping SKU: {test_sku}")
    result = scrape_bradley_caldwell([test_sku])
    if result:
        print("✅ Scrape successful:")
        for product in result:
            print(product)
