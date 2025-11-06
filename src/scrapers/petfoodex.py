import os
import sys
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from src.utils.scraping.scraping import get_standard_chrome_options
from src.utils.scraping.browser import create_browser
from util.scrape_display import display_product_result, display_scraping_progress, display_scraping_summary, display_error

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()
HEADLESS = False
TEST_SKU = "855089008580"  # KONG Pull A Partz Pals Koala SM - test SKU for Pet Food Experts

LOGIN_URL = "https://orders.petfoodexperts.com/SignIn"
HOME_URL = "https://orders.petfoodexperts.com/"

def init_browser(profile_suffix="default", headless=True):
    # Use login-safe Chrome options instead of standard ones
    from util.scrape_util_fixed import get_login_safe_chrome_options
    chrome_options = get_login_safe_chrome_options(headless=headless, profile_suffix=profile_suffix)
    
    # Use selenium_profiles directory for petfoodex with unique suffix
    user_data_dir = os.path.abspath(f"selenium_profiles/petfoodex_{profile_suffix}")
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Add service with error suppression
    service = Service(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

def load_cookies(driver):
    try:
        import pickle
        with open("cookies/petfoodex_cookies.pkl", "rb") as f:
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
        import os
        os.makedirs("cookies", exist_ok=True)
        cookies = driver.get_cookies()
        with open("cookies/petfoodex_cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)
    except Exception as e:
        print(f"⚠️ Failed to save cookies: {e}")

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
    print("🚪 Starting login process...")
    driver.get(LOGIN_URL)
    time.sleep(3)  # Let page load

    username = os.getenv("PETFOOD_USERNAME")
    password = os.getenv("PETFOOD_PASSWORD")

    if not username or not password:
        print("❌ Missing PETFOOD_USERNAME or PETFOOD_PASSWORD environment variables")
        raise ValueError("PETFOOD_USERNAME or PETFOOD_PASSWORD not set in .env")

    print("📝 Filling login form...")
    try:
        # Wait for and fill username
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "userName"))
        )
        username_field.clear()
        username_field.send_keys(username)
        print("✅ Username entered")
    except Exception as e:
        print(f"❌ Failed to enter username: {e}")
        return

    try:
        # Wait for and fill password
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.clear()
        password_field.send_keys(password)
        print("✅ Password entered")
    except Exception as e:
        print(f"❌ Failed to enter password: {e}")
        return

    print("🔘 Clicking login button...")
    try:
        # Find the submit button
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-selector='signIn_submit']"))
        )
        
        # Try to click
        submit_button.click()
        print("✅ Login button clicked")
    except Exception as e:
        print(f"❌ Failed to click login button: {e}")
        return

    print("⏳ Waiting for login to complete...")
    try:
        # Wait for redirect
        WebDriverWait(driver, 30).until(
            lambda d: d.current_url != LOGIN_URL and "SignIn" not in d.current_url
        )
        print("✅ Login process completed")
        # Save cookies after successful login
        save_cookies(driver)
    except Exception as e:
        print(f"⚠️ Login may have timed out: {e}")
        print(f"   Current URL: {driver.current_url}")

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

def scrape_petfood_experts(skus, browser=None):
    """Scrape Pet Food Experts products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    # Use provided browser or create a new one
    if browser is not None:
        driver = browser
    else:
        driver = create_browser("Pet Food Experts", headless=HEADLESS)
        if driver is None:
            display_error("Could not create browser for Pet Food Experts")
            return products
    
    try:
        # Handle login if required (only if we created our own browser)
        if browser is None:
            if not is_logged_in(driver):
                login(driver)
            
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus))
            else:
                products.append(None)
            
            display_scraping_progress(i, len(skus), start_time, "Pet Food Experts")
    
    finally:
        # Only quit browser if we created it ourselves
        if browser is None and driver:
            try:
                driver.quit()
            except:
                pass
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Pet Food Experts")
                
    return products

def scrape_single_product(sku, driver):
    if driver is None:
        display_error("WebDriver instance is None. Cannot scrape product.")
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

        # Check if we're on a product detail page (has highest priority)
        if driver.find_elements(By.CSS_SELECTOR, "div.pf-detail-wrap"):
            print(f"DEBUG: Found product detail page for SKU {sku}")
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
                print(f"DEBUG: Critical fields missing for SKU {sku}, returning None")
                return None

            return product_info

        # Check for no results message
        elif driver.find_elements(By.CSS_SELECTOR, ".pf-no-results"):
            print(f"DEBUG: No results found for SKU {sku}")
            return None

        # Check if we're on search results page with actual results
        elif driver.find_elements(By.CSS_SELECTOR, "label[data-test-selector='productListSortSelect-label']"):
            # Look for product cards in search results - be more specific to avoid false positives
            product_cards = driver.find_elements(By.CSS_SELECTOR, ".pf-product-card, .product-card")
            if product_cards:
                print(f"DEBUG: Found {len(product_cards)} products in search results for SKU {sku}, but expected direct navigation to product page")
                # This might indicate the SKU matches multiple products - we could potentially scrape the first one
                # For now, return None since we expect direct navigation for exact SKU matches
                return None
            else:
                print(f"DEBUG: On search results page but no product cards found for SKU {sku}")
                return None

        else:
            print(f"DEBUG: Unexpected page state for SKU {sku} - no recognized elements found")
            return None

    except Exception as e:
        display_error(f"PetFoodExperts scrape error for SKU {sku}: {e}")
        return None

if __name__ == "__main__":
    test_sku = "10852301008912"
    results = scrape_petfood_experts([test_sku])
    print(results[0] if results else None)
