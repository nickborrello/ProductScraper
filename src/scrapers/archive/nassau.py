import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils.scraping.scraping import clean_string
from src.utils.scraping.browser import create_browser
from util.scrape_display import display_product_result, display_scraping_progress, display_scraping_summary, display_error
import time

HEADLESS = True

def scrape_nassau_candy(skus):
    """Scrape Nassau Candy products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    with create_browser("Nassau Candy", headless=HEADLESS) as driver:
        if driver is None:
            display_error("Could not create browser for Nassau Candy")
            return products
            
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus))
            else:
                display_error(f"No product found for SKU {sku}")
                products.append(None)
            
            display_scraping_progress(i, len(skus), start_time, "Nassau Candy")
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Nassau Candy")
                
    return products

def scrape_single_product(SKU, driver):
    if driver is None:
        print("❌ Error: WebDriver instance is None. Cannot scrape product.")
        return None
    search_url = f'https://www.nassaucandy.com/catalogsearch/result/?q={SKU}'
    product_info = {}

    try:
        driver.get(search_url)
        print(f"DEBUG: Navigated to search URL: {search_url}")

        # Wait for page to load and check what we got
        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ol.products.list.items.product-items")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".products.list")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-items")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Your search returned no results')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'no results')]"))
                )
            )
        except Exception as e:
            print(f"DEBUG: Timeout waiting for search results. Page title: {driver.title}")
            print(f"DEBUG: Current URL: {driver.current_url}")
            print(f"DEBUG: Page source contains 'results': {'results' in driver.page_source.lower()}")
            display_error("Timeout waiting for search results or no-results message")
            return None

        # Check for no results messages
        page_source_lower = driver.page_source.lower()
        if any(phrase in page_source_lower for phrase in ["no results", "no products", "0 items"]):
            print(f"DEBUG: No results found for SKU {SKU}")
            return None

        # Find product link with multiple selectors
        try:
            # Try different selectors for product links
            link_selectors = [
                'ol.products.list.items.product-items li.item a.product-item-link',
                '.products.list .product-item-link',
                '.product-items .product-item-link',
                'a.product-item-link',
                '.product-item a'
            ]
            
            product_link = None
            product_url = None
            
            for selector in link_selectors:
                try:
                    product_link = driver.find_element(By.CSS_SELECTOR, selector)
                    product_url = product_link.get_attribute("href")
                    if product_url:
                        print(f"DEBUG: Found product link with selector '{selector}': {product_url}")
                        break
                except Exception:
                    continue
            
            if not product_url:
                print(f"DEBUG: No product link found. Available links on page:")
                links = driver.find_elements(By.TAG_NAME, "a")
                for i, link in enumerate(links[:5]):  # Show first 5 links
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    print(f"DEBUG: Link {i+1}: {href} (text: '{text}')")
                display_error("No product link found.")
                return None
                
            driver.get(product_url)
            print(f"DEBUG: Navigated to product page: {product_url}")
            
        except Exception as e:
            display_error(f"Failed to get product link: {e}")
            return None

        # Wait for product name
        try:
            product_name_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "span.base[data-ui-id='page-title-wrapper']"))
            )
            product_name = clean_string(product_name_element.text)
            product_info['Name'] = product_name
        except Exception:
            display_error("Product name not found.")
            product_info['Name'] = 'N/A'  # Placeholder instead of None

        # Get image URL from Fotorama gallery
        try:
            print("DEBUG: Starting image extraction...")
            
            # Wait longer for the gallery to load and be interactive
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.gallery-placeholder"))
            )
            print("DEBUG: Gallery placeholder found")
            
            # Give extra time for JavaScript to load the images
            import time
            time.sleep(3)
            
            # Try multiple selectors for the main product image
            image_selectors = [
                "div.fotorama__stage__frame img[src*='nassau-candy']",  # Any Nassau candy image in frame
                "div.fotorama__stage__frame.fotorama__active img",  # Active frame image (any img)
                "img.fotorama__img[src*='cloudinary']",  # Cloudinary hosted images
                "div.fotorama__stage img[src*='nassau-candy']",  # Any Nassau image in stage
                "div.fotorama__stage img.fotorama__img",  # Any fotorama image in stage
                "img.fotorama__img.magnify-opaque",  # Image with magnify class
                "div.gallery-placeholder img[src*='http']",  # Any http image in gallery
                "img.fotorama__img",  # Fallback to any fotorama image
                ".product-info-container img[src*='http']"  # Any image in product container
            ]
            
            image_url = None
            for i, selector in enumerate(image_selectors):
                try:
                    print(f"DEBUG: Trying selector {i+1}: {selector}")
                    images = driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"DEBUG: Found {len(images)} images with this selector")
                    
                    for j, image_element in enumerate(images):
                        src = image_element.get_attribute('src')
                        print(f"DEBUG: Image {j+1} src: {src}")
                        
                        if src and src.startswith('http') and 'nassau-candy' in src:
                            image_url = src
                            print(f"DEBUG: Selected image URL: {image_url}")
                            break
                    
                    if image_url:
                        break
                        
                except Exception as e:
                    print(f"DEBUG: Error with selector '{selector}': {e}")
                    continue
            
            if not image_url:
                # Last resort: look for any image on the page
                print("DEBUG: Last resort - looking for any product images...")
                all_images = driver.find_elements(By.TAG_NAME, "img")
                print(f"DEBUG: Found {len(all_images)} total images on page")
                
                for i, img in enumerate(all_images[:10]):  # Check first 10 images
                    src = img.get_attribute('src')
                    alt = img.get_attribute('alt')
                    print(f"DEBUG: Image {i+1}: src='{src}' alt='{alt}'")
                    
                    if src and ('cloudinary' in src or 'nassau' in src.lower()) and src.startswith('http'):
                        image_url = src
                        print(f"DEBUG: Found suitable image in last resort: {image_url}")
                        break
            
            if image_url:
                product_info['Image URLs'] = [image_url]
                print(f"DEBUG: Final image URL set: {image_url}")
            else:
                print("DEBUG: No image found with any method")
                product_info['Image URLs'] = []
                
        except Exception as e:
            print(f"DEBUG: Error in image extraction: {e}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            product_info['Image URLs'] = []

        # Get brand and UPC from the spec table
        try:
            # Wait for the table to exist first
            spec_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "product-attribute-specs-table"))
            )
            print("DEBUG: Found product attribute specs table")
            
            # Wait for table rows to be populated with actual content
            # This is crucial because the content might be loaded via JavaScript
            try:
                WebDriverWait(driver, 15).until(
                    EC.text_to_be_present_in_element((By.CSS_SELECTOR, "#product-attribute-specs-table tbody tr td"), "")
                )
                print("DEBUG: Table content appears to be loaded")
            except Exception:
                print("DEBUG: Warning - couldn't confirm table content loaded, proceeding anyway")
            
            # Give a bit more time for all dynamic content to settle
            import time
            time.sleep(2)
            
            # Re-find the table after waiting (in case DOM was updated)
            spec_table = driver.find_element(By.ID, "product-attribute-specs-table")
            rows = spec_table.find_elements(By.TAG_NAME, "tr")
            print(f"DEBUG: Found {len(rows)} rows in table after waiting")
            
            for i, row in enumerate(rows):
                label = None
                value = None
                
                try:
                    # Traditional structure: th for label, td for value
                    label_elem = row.find_element(By.TAG_NAME, "th")
                    value_elem = row.find_element(By.TAG_NAME, "td")
                    
                    # Try multiple ways to get text content
                    label = label_elem.text.strip()
                    if not label:
                        label = label_elem.get_attribute('textContent').strip()
                    if not label:
                        label = label_elem.get_attribute('innerText').strip()
                    
                    value = value_elem.text.strip()
                    if not value:
                        value = value_elem.get_attribute('textContent').strip()
                    if not value:
                        value = value_elem.get_attribute('innerText').strip()
                    
                    print(f"DEBUG: Row {i+1} (th/td): '{label}' = '{value}'")
                except Exception:
                    # Alternative structure: td with data-th attribute
                    try:
                        td_elements = row.find_elements(By.TAG_NAME, "td")
                        for td in td_elements:
                            data_th = td.get_attribute("data-th")
                            if data_th:
                                label = data_th.strip()
                                
                                # Try multiple ways to get text content
                                value = td.text.strip()
                                if not value:
                                    value = td.get_attribute('textContent').strip()
                                if not value:
                                    value = td.get_attribute('innerText').strip()
                                
                                print(f"DEBUG: Row {i+1} (data-th): '{label}' = '{value}'")
                                break
                        else:
                            continue
                    except Exception:
                        continue

                # Process the extracted label and value
                if label and value:
                    if label.lower() == "brand":
                        product_info['Brand'] = value
                        print(f"DEBUG: Set Brand to '{value}'")
                    elif label.lower() == "upc" or (label.lower().startswith("upc") and "inner" not in label.lower()):
                        product_info['UPC'] = value
                        print(f"DEBUG: Set UPC to '{value}'")
                        if value != SKU:
                            print(f"DEBUG: UPC mismatch - UPC: {value}, SKU: {SKU}")
                            display_error(f"UPC ({value}) does not match SKU ({SKU})")
                            return None
            
            # Try direct selector approach if nothing found
            if 'Brand' not in product_info:
                print("DEBUG: Trying direct selector for brand...")
                try:
                    brand_element = spec_table.find_element(By.CSS_SELECTOR, 'td[data-th="Brand"]')
                    brand_value = brand_element.text.strip()
                    product_info['Brand'] = brand_value
                    print(f"DEBUG: Found brand with direct selector: '{brand_value}'")
                except Exception as e:
                    print(f"DEBUG: Direct brand selector failed: {e}")
                    
        except Exception as e:
            print(f"DEBUG: Error reading product table: {e}")
            display_error(f"Error reading product table: {e}")

        # Clean up name if brand is duplicated
        if product_info.get('Name') and product_info.get('Brand'):
            brand_lower = product_info['Brand'].lower()
            if product_info['Name'].lower().startswith(brand_lower):
                product_info['Name'] = re.sub(f"^{re.escape(brand_lower)}", "", product_info['Name'], flags=re.IGNORECASE).strip()

        # Flag product if it has any placeholders or missing images
        product_info['flagged'] = (
            any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
            not product_info.get('Image URLs')
        )

        return product_info

    except Exception as e:
        display_error(f"Unexpected error: {e}")
        return None
