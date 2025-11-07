import os
import re
import time
import sys

# Add parent directory to path when running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.scraping.scraping import clean_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error, display_info

# Amazon scraper with optimizations for speed
# - Runs headless for maximum speed (no visual browser window)
# - Blocks images and ads to reduce page load time
# - Reduced wait times between operations
# - Optimized browser settings for faster scraping

# Amazon scraper can run headless - optimized browser blocks images/ads for speed
HEADLESS = True

# Optimization settings
USE_OPTIMIZED_BROWSER = True  # Set to False if you need images for debugging

def init_browser(profile_suffix="default", headless=True):
    """Initialize Chrome browser for Amazon scraping with proper profile management."""
    from src.utils.scraping.scraping import get_standard_chrome_options
    chrome_options = get_standard_chrome_options(headless=headless, profile_suffix=profile_suffix)
    
    # Use selenium_profiles directory for Amazon with unique suffix
    user_data_dir = os.path.abspath(f"data/selenium_profiles/Amazon_{profile_suffix}")
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Add service with error suppression
    service = Service(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

def get_amazon_optimized_options(profile_suffix="default", headless=True):
    """Get Chrome options optimized specifically for Amazon scraping - blocks ads, images, and unnecessary resources."""
    from selenium.webdriver.chrome.options import Options
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # Basic stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--no-first-run")
    options.add_argument("--enable-unsafe-swiftshader")  # Suppress WebGL warnings
    
    # Block images and media for faster loading
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-images")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Block ads, tracking, and analytics
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-background-media-download")
    
    # Block unnecessary resource types
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-features=BlinkGenPropertyTrees")
    options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
    options.add_argument("--disable-features=WebRtcUseH264")
    options.add_argument("--disable-features=MediaRouter")
    options.add_argument("--no-default-browser-check")
    
    # User agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Suppress logging
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation", "use-mock-keychain"])
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-tools")
    
    # Profile directory
    if profile_suffix:
        profile_dir = os.path.abspath(os.path.join("data", "selenium_profiles", f"Amazon_optimized_{profile_suffix}"))
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
    
    return options

def init_browser_optimized(profile_suffix="default", headless=True):
    """Initialize optimized Chrome browser for Amazon scraping that blocks ads and images."""
    chrome_options = get_amazon_optimized_options(headless=headless, profile_suffix=profile_suffix)
    
    # Add service with error suppression
    service = Service(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_amazon(skus):
    """Scrape Amazon products for multiple SKUs."""
    products = []
    start_time = time.time()

    # display_info(f"Starting Amazon scraping for {len(skus)} products")  # Removed verbose message

    # Choose browser type based on optimization setting
    if USE_OPTIMIZED_BROWSER:
        browser_context = init_browser_optimized("amazon_batch", headless=HEADLESS)
    else:
        browser_context = create_browser("Amazon", headless=HEADLESS)
    
    with browser_context as driver:
        if driver is None:
            display_error("Could not create browser for Amazon")
            return products

        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
            else:
                products.append(None)  # Keep None for failed products to maintain index alignment

            # Reduced delay between products for optimized scraping
            if i < len(skus):
                time.sleep(1)  # Reduced from 2 seconds

    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Amazon")

    return products

def scrape_single_product(UPC_or_ASIN, driver, max_retries=0):
    """Scrape a single Amazon product with improved automation and error handling."""
    if driver is None:
        display_error("WebDriver instance is None. Cannot scrape product.")
        return None

    product_info = {"SKU": UPC_or_ASIN}

    for attempt in range(max_retries + 1):
        try:
            # Try direct product URL first (if it's an ASIN)
            if len(UPC_or_ASIN) == 10 and UPC_or_ASIN.isalnum():
                # Looks like an ASIN, try direct URL
                direct_url = f"https://www.amazon.com/dp/{UPC_or_ASIN}"
                driver.get(direct_url)
                time.sleep(1)  # Reduced from 2 seconds
                return _extract_product_data(driver, product_info)
            else:
                # Try search URL
                search_url = f"https://www.amazon.com/s?k={UPC_or_ASIN}"
                driver.get(search_url)
                time.sleep(2)  # Reduced from 3 seconds

                # Check for no results before trying to click
                if _has_no_search_results(driver):
                    return None  # No results found

                if _click_first_search_result(driver):
                    time.sleep(1)  # Reduced from 2 seconds

                    # Verify we actually landed on a product page
                    if _is_product_page(driver):
                        return _extract_product_data(driver, product_info)
                    else:
                        return None  # Not a real product page

            # If we get here, we couldn't find a product
            # display_error(f"No product found for {UPC_or_ASIN} after {attempt + 1} attempts")  # Removed verbose message
            if attempt < max_retries:
                time.sleep(3)  # Wait before retry
                continue
            else:
                return None

        except Exception as e:
            display_error(f"Error on attempt {attempt + 1}: {str(e)}", UPC_or_ASIN)
            if attempt < max_retries:
                time.sleep(1)  # Reduced from 2 seconds
                continue
            else:
                return None

    return None


def _is_product_page(driver):
    """Check if the current page is a real product detail page (not sponsored/generic content)."""
    try:
        current_url = driver.current_url
        page_source = driver.page_source

        # Must have /dp/ in URL
        if "/dp/" not in current_url:
            return False

        # Must have actual product title element (not just in source)
        try:
            title_element = driver.find_element(By.ID, "productTitle")
            title_text = title_element.text.strip()
            if not title_text or len(title_text) < 3:
                return False
        except:
            return False

        # Should have product details section
        if "productDetails" not in page_source and "detailBullets" not in page_source:
            return False

        # Should not be a search page that redirected
        if "s?k=" in current_url and "/dp/" in current_url:
            # This might be a redirect from search - check if it's a real product
            try:
                # Look for product price or other product indicators
                price_indicators = driver.find_elements(By.CSS_SELECTOR, ".a-price, #priceblock_ourprice, #priceblock_dealprice")
                if not price_indicators:
                    return False
            except:
                return False

        return True

    except Exception as e:
        display_error(f"Error checking if product page: {e}")
        return False


def _has_no_search_results(driver):
    """Check if the current page shows 'no results found' from Amazon."""
    try:
        # Check for "no results" messages
        no_results_selectors = [
            ".s-no-results",
            "[data-component-type='s-no-results']",
            ".a-section h1",
            ".s-search-results-content h1",
            ".s-search-results-content"
        ]

        for selector in no_results_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.lower()
                if any(phrase in text for phrase in ['no results', 'did not match', 'no search results', 'we couldn\'t find', 'no products found']):
                    return True
            except:
                continue

        # Check page source for no results indicators
        page_source = driver.page_source.lower()
        no_results_phrases = [
            'no results for',
            'did not match any products',
            'no search results',
            'we couldn\'t find any matches',
            'no products found'
        ]

        for phrase in no_results_phrases:
            if phrase in page_source:
                return True

        # Additional check: if there are very few search results and they look like sponsored/generic content
        try:
            # Count actual product result containers
            result_count = len(driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
            if result_count == 0:
                return True
            else:
                # Check if all results are sponsored (regardless of count)
                sponsored_count = 0
                results = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
                for result in results:
                    try:
                        sponsored_indicators = result.find_elements(By.CSS_SELECTOR, ".s-sponsored-label-info, .sbv-sponsored, [data-sponsored='true'], .puis-sponsored-label-text, .puis-label-sponsored")
                        if sponsored_indicators:
                            sponsored_count += 1
                    except:
                        continue

                # If all results are sponsored, don't treat as no results - let click function handle it
                # Just log the information but continue
                if sponsored_count == result_count and result_count > 0:
                    # Don't return True here - let the click function try to find organic results
                    pass

                # Also check for "More Results" sections that contain only sponsored content
                try:
                    more_results_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'More Results')]/following-sibling::*")
                    for section in more_results_sections:
                        section_sponsored = section.find_elements(By.CSS_SELECTOR, ".s-sponsored-label-info, .sbv-sponsored, [data-sponsored='true'], .puis-sponsored-label-text, .puis-label-sponsored")
                        section_total = section.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
                        if section_total and len(section_sponsored) == len(section_total):
                            return True
                except:
                    pass

                # Check if there are ANY organic results at all - but don't treat as no results
                organic_count = result_count - sponsored_count
                if organic_count == 0 and result_count > 0:
                    # Continue and let click function try to find clickable organic results
                    pass

        except:
            pass

        return False

    except Exception as e:
        display_error(f"Error checking for no results: {e}")
        return False


def _click_first_search_result(driver):
    """Try to click on the first NON-SPONSORED search result."""
    try:
        # Find all search result containers first
        result_containers = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result'], .s-result-item")

        for i, container in enumerate(result_containers):
            try:
                # Check for sponsored indicators in this container
                sponsored_indicators = container.find_elements(By.CSS_SELECTOR,
                    ".s-sponsored-label-info, .sbv-sponsored, [data-sponsored='true'], .puis-sponsored-label-text, .puis-label-sponsored, .AdHolder")

                if sponsored_indicators:
                    continue  # Skip this sponsored result

                # Also check for "Sponsored" text in the container
                container_text = container.text.lower()
                if 'sponsored' in container_text:
                    continue

                # This container appears to be organic, find a product link within it
                try:
                    product_link = container.find_element(By.CSS_SELECTOR, "a.a-link-normal[href*='/dp/']")
                    
                    # Additional check: if the link URL contains '/sspa/click?', it's sponsored
                    link_href = product_link.get_attribute("href") or ""
                    if "/sspa/click?" in link_href:
                        continue  # Skip sponsored link
                    
                    product_link.click()
                    return True
                except:
                    continue

            except Exception as e:
                continue

        # display_info("No organic search results found - all results appear to be sponsored")  # Removed verbose debug message
        return False
    except Exception as e:
        display_error(f"Error clicking search result: {e}")
        return False


def _extract_product_data(driver, product_info):
    """Extract product data from a product page."""
    try:
        # Extract title
        try:
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            product_info["Name"] = clean_string(title_element.text)
        except TimeoutException:
            display_error("Could not find product title")
            product_info["Name"] = "N/A"

        # Extract and verify SKU/UPC/ASIN
        actual_sku = _extract_sku_from_page(driver)
        searched_sku = product_info.get("SKU", "")
        
        # Check if the searched SKU appears anywhere on the page
        page_contains_searched_sku = _page_contains_sku(driver, searched_sku)
        
        if actual_sku and actual_sku != searched_sku and not page_contains_searched_sku:
            display_error(f"SKU mismatch! Searched for {searched_sku} but found product with SKU {actual_sku} and searched SKU not found on page")
            return None  # Reject this product - wrong SKU
        elif page_contains_searched_sku:
            # Keep the searched SKU since we found it on the page
            pass
        elif actual_sku:
            # Keep the original searched SKU, don't overwrite with Amazon's identifier
            pass
        else:
            # No SKU information found, using searched SKU
            pass

        # Extract brand
        product_info["Brand"] = _extract_brand(driver)

        # Filter brand out of the name if present
        if product_info["Name"] != "N/A" and product_info["Brand"] != "Unknown":
            product_info["Name"] = _filter_brand_from_name(product_info["Name"], product_info["Brand"])

        # Extract images (always extract URLs even in optimized mode)
        product_info["Image URLs"] = _extract_images(driver)

        # Extract weight
        product_info["Weight"] = _extract_weight(driver)

        # Flag product if it has issues
        product_info['flagged'] = (
            any(value == 'N/A' for value in product_info.values() if isinstance(value, str)) or
            not product_info.get('Image URLs')
        )

        # Display the complete product result after all data is extracted
        display_product_result(product_info, None, None)

        return product_info

    except Exception as e:
        display_error(f"Error extracting product data: {e}")
        return None


def _extract_sku_from_page(driver):
    """Extract the actual SKU/UPC/ASIN from the product page to verify it matches what we searched for."""
    # Look for UPC/ASIN in product details tables
    try:
        detail_rows = driver.find_elements(By.CSS_SELECTOR, "#productDetails_detailBullets_sections1 tr, #productDetails_techSpec_section_1 tr")
        for row in detail_rows:
            try:
                text = row.text.lower()
                # Look for UPC
                if 'upc' in text:
                    match = re.search(r'upc\s*:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
                    if match:
                        sku = match.group(1).strip()
                        if len(sku) >= 10:  # Valid SKU length
                            return sku
                # Look for ASIN
                elif 'asin' in text:
                    match = re.search(r'asin\s*:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
                    if match:
                        sku = match.group(1).strip()
                        if len(sku) == 10:  # ASIN is always 10 characters
                            return sku
            except:
                continue
    except:
        pass
    
    # Look for UPC/ASIN in bullet points
    try:
        bullets = driver.find_elements(By.CSS_SELECTOR, "#detailBullets_feature_div li, [data-feature-name='Bullet Points'] li")
        for bullet in bullets:
            try:
                text = bullet.text.lower()
                # Look for UPC
                if 'upc' in text:
                    match = re.search(r'upc\s*:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
                    if match:
                        sku = match.group(1).strip()
                        if len(sku) >= 10:
                            return sku
                # Look for ASIN
                elif 'asin' in text:
                    match = re.search(r'asin\s*:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
                    if match:
                        sku = match.group(1).strip()
                        if len(sku) == 10:
                            return sku
            except:
                continue
    except:
        pass
    
    # Try to extract ASIN from URL as fallback
    try:
        current_url = driver.current_url
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', current_url)
        if asin_match:
            return asin_match.group(1)
    except:
        pass
    
    return None


def _page_contains_sku(driver, sku):
    """Check if the searched SKU appears anywhere on the product page."""
    try:
        page_source = driver.page_source
        # Remove spaces and case sensitivity for matching
        normalized_page = page_source.lower().replace(' ', '').replace('-', '')
        normalized_sku = sku.lower().replace(' ', '').replace('-', '')
        
        return normalized_sku in normalized_page
    except:
        return False


def _filter_brand_from_name(name, brand):
    """Remove brand from the beginning or end of product name if present, handling case variations."""
    if not name or not brand or name == "N/A" or brand == "Unknown":
        return name

    import re

    # Create case-insensitive pattern for the brand
    brand_pattern = re.escape(brand.lower())

    # Remove brand from beginning (with common separators) - case insensitive
    patterns = [
        rf"^{brand_pattern}\s*[:-]\s*",  # "Brand: Product" or "Brand - Product"
        rf"^{brand_pattern}\s+",  # "Brand Product"
    ]

    result = name
    for pattern in patterns:
        # Use case-insensitive replacement
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    # Remove brand from end (less common but possible) - case insensitive
    if result.lower().endswith(brand.lower()):
        # Remove the brand from the end, preserving original casing
        brand_len = len(brand)
        result = result[:-brand_len].strip()
        # Remove trailing separators
        result = re.sub(r"\s*[:-]\s*$", "", result)

    # If the name became too short or empty, revert to original
    if len(result) < 3:
        return name

    return result


def _extract_brand(driver):
    """Extract brand information from various possible locations."""
    brand_selectors = [
        "#bylineInfo",
        "#brand",
        ".a-brand",
        "[data-cy='brand-name']",
        ".brand-link"
    ]

    for selector in brand_selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            brand_text = element.text.strip()

            # Clean up common brand text patterns
            brand_text = re.sub(r'^(Brand|Visit the|by)\s*:?\s*', '', brand_text, flags=re.IGNORECASE)
            brand_text = re.sub(r'\s+Store$', '', brand_text, flags=re.IGNORECASE)

            if brand_text and len(brand_text) > 1:
                return clean_string(brand_text)
        except:
            continue

    return "Unknown"


def _extract_images(driver):
    """Extract product images by parsing thumbnail URLs and constructing high-res versions."""
    image_urls = []

    try:
        # Extract carousel images by parsing thumbnail URLs and constructing high-res versions
        try:
            # Find all thumbnail images in the carousel
            thumbnail_imgs = driver.find_elements(By.CSS_SELECTOR, "#altImages li.imageThumbnail img")

            for img in thumbnail_imgs:
                try:
                    thumbnail_src = img.get_attribute("src")
                    if thumbnail_src and 'media-amazon.com' in thumbnail_src:
                        # Extract the image ID from the thumbnail URL
                        # Example: https://m.media-amazon.com/images/I/41+MRN-56cL._AC_US40_.jpg
                        # We want: 41+MRN-56cL
                        import re
                        match = re.search(r'/images/I/([^.]+)', thumbnail_src)
                        if match:
                            image_id = match.group(1)
                            # Construct high-res URL
                            high_res_url = f"https://m.media-amazon.com/images/I/{image_id}._AC_SL1500_.jpg"

                            if (high_res_url not in image_urls and
                                _is_valid_image_url(high_res_url) and
                                _is_product_image(high_res_url)):

                                image_urls.append(high_res_url)

                except:
                    continue

        except Exception as e:
            display_error(f"Error extracting carousel images from thumbnails: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img_url in image_urls:
            if img_url not in seen:
                seen.add(img_url)
                unique_images.append(img_url)

        return unique_images

    except Exception as e:
        display_error(f"Error extracting images: {e}")
        return []


def _get_largest_image_from_data_attr(data_attr):
    """Extract the largest image URL from Amazon's data-a-dynamic-image JSON attribute."""
    if not data_attr:
        return None

    try:
        import json
        # The data attribute contains a JSON string with URLs as keys and dimensions as values
        # e.g., {"url1":[width,height], "url2":[width,height], ...}
        image_data = json.loads(data_attr)

        if not isinstance(image_data, dict):
            return None

        # Find the URL with the largest area (width * height)
        largest_url = None
        largest_area = 0

        for url, dimensions in image_data.items():
            if isinstance(dimensions, list) and len(dimensions) >= 2:
                try:
                    width, height = dimensions[0], dimensions[1]
                    area = width * height
                    if area > largest_area:
                        largest_area = area
                        largest_url = url
                except:
                    continue

        return largest_url

    except:
        return None


def _extract_weight(driver):
    """Extract weight from multiple possible locations."""
    weight_patterns = [
        r'(\d+\.?\d*)\s*(ounce|oz|pound|lb|ounces|lbs|gram|g|kilogram|kg)s?\b',
        r'(\d+\.?\d*)\s*(oz|lb|g|kg)\b',
        r'weight\s*:\s*(\d+\.?\d*)\s*(ounce|oz|pound|lb|ounces|lbs|gram|g|kilogram|kg)s?\b'
    ]

    # Locations to check for weight information
    selectors = [
        "#productDetails_detailBullets_sections1 tr",
        "#productDetails_techSpec_section_1 tr",
        "#detailBullets_feature_div li",
        "#feature-bullets li",
        ".a-expander-content",
        "[data-feature-name='Bullet Points'] li"
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)

            for element in elements:
                text = element.text.lower()

                # Check if this element contains weight info
                if 'weight' in text or 'oz' in text or 'lb' in text or 'pound' in text:
                    for pattern in weight_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            value = float(match.group(1))
                            unit = match.group(2).lower()

                            # Convert to pounds
                            if unit in ['ounce', 'oz', 'ounces']:
                                value = round(value / 16, 2)
                            elif unit in ['gram', 'g']:
                                value = round(value / 453.592, 2)
                            elif unit in ['kilogram', 'kg']:
                                value = round(value * 2.20462, 2)

                            return str(value)

        except:
            continue

    return "N/A"


def _is_valid_image_url(url):
    """Check if an image URL is valid and not a placeholder."""
    if not url or not isinstance(url, str):
        return False

    # Skip Amazon placeholder images
    if any(skip in url.lower() for skip in ['grey-pixel', 'transparent', 'placeholder', 'no-image']):
        return False

    # Must be a proper image URL
    return url.startswith(('http://', 'https://')) and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])


def _is_product_image(url):
    """Check if an image URL appears to be a product image (not a logo, badge, or icon)."""
    if not url or not isinstance(url, str):
        return False

    url_lower = url.lower()

    # Skip obvious non-product images
    skip_indicators = [
        'logo', 'badge', 'icon', 'button', 'arrow', 'star', 'rating',
        'prime', 'certified', 'warranty', 'guarantee', 'shipping',
        'payment', 'credit', 'card', 'badge', 'ribbon', 'award',
        'verified', 'trusted', 'secure', 'safe', 'lock', 'shield',
        '360_icon', 'home_custom_product'  # Skip 360 view icons and custom product icons
    ]

    # Check URL path for skip indicators
    for indicator in skip_indicators:
        if indicator in url_lower:
            return False

    # Prioritize high-resolution product images
    # Amazon product images typically have patterns like _AC_SL1500_, _AC_SL1000_, etc.
    import re
    if re.search(r'_AC_SL\d+', url_lower):  # High-res product images
        return True

    # Skip very small images (likely icons/logos) - check URL parameters
    # Amazon URLs often have size parameters like _SL75_ or _SS40_
    size_match = re.search(r'_SL(\d+)_|_SS(\d+)_|_US(\d+)_', url_lower)
    if size_match:
        # Extract the size from any of the capture groups
        size = None
        for group in size_match.groups():
            if group:
                size = int(group)
                break

        if size and size < 100:  # Skip images smaller than 100px
            return False

    return True


if __name__ == "__main__":
    # Test with both existing and non-existing products
    test_skus = [
        "035585499741",  # Known existing product (test successful scraping)
        # "21498219843718902410924781023498712"  # Non-existing SKU (test no-results detection)
    ]

    results = scrape_amazon(test_skus)
    print("Results:")
    for i, result in enumerate(results):
        sku = test_skus[i]
        if result:
            print(f"  {i+1}. SKU {sku}: Found '{result.get('Name', 'Unknown')[:50]}...'")
            print(f"     Full product data: {result}")
            # Print image URLs separately for debugging
            images = result.get('Image URLs', [])
            print(f"     Image URLs ({len(images)}):")
            for j, img_url in enumerate(images, 1):
                print(f"       {j}. {img_url}")
            print()
        else:
            # print(f"  {i+1}. SKU {sku}: No product found")  # Removed verbose message
            print()
