

import os
import sys

# Ensure project root is on sys.path before importing local packages
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time
import pickle
import re
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from src.utils.scraping.scraping import clean_string, get_standard_chrome_options
from src.utils.scraping.browser import create_browser
from src.utils.general.display import display_product_result, display_scraping_progress, display_scraping_summary, display_error
from src.core.settings_manager import SettingsManager

load_dotenv()
settings = SettingsManager()
HEADLESS = False
TEST_SKU = "755625011305" 
LOGIN_URL = 'https://www.orgill.com/index.aspx?tab=8'
BASE_SEARCH_URL = 'https://www.orgill.com/SearchResultN.aspx?ddlhQ={SKU}'

def init_browser(profile_suffix="default", headless=False):
    # Use standard Chrome options
    from src.utils.scraping.scraping import get_standard_chrome_options
    chrome_options = get_standard_chrome_options(headless=headless, profile_suffix=profile_suffix)
    
    # Disable auto-fill to prevent form pre-population
    chrome_options.add_argument("--disable-blink-features=Autofill")
    chrome_options.add_argument("--disable-features=Autofill")
    
    # Use selenium_profiles directory for orgill with unique suffix
    user_data_dir = os.path.join(PROJECT_ROOT, "data", "browser_profiles", f"orgill_{profile_suffix}")
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Add service with error suppression
    from selenium.webdriver.chrome.service import Service as ChromeService
    service = ChromeService(log_path=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

def is_logged_in(driver):
    # Always check login status on Orgill homepage
    try:
        driver.get("https://www.orgill.com/Default.aspx")
        time.sleep(2)
        signout_links = driver.find_elements(By.XPATH, "//a[@href='/signOut.aspx' and .//span[text()='Sign Out']]")
        if signout_links:
            print("Orgill: Found Sign Out link on homepage, login verified.")
            return True
    except Exception as e:
        print(f"Orgill: Error checking Sign Out link on homepage: {e}")
    return False

def login(driver, log_callback=None):
    if log_callback:
        log_callback("Orgill: Navigating to login page...")
    else:
        print("Orgill: Navigating to login page...")
    driver.get(LOGIN_URL)
    
    if log_callback:
        log_callback("Orgill: Waiting for username field...")
    else:
        print("Orgill: Waiting for username field...")
    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_loginOrgillxs_UserName"))
    )
    driver.execute_script("arguments[0].value = '';", username_field)
    username_field.send_keys(settings.orgill_credentials[0])
    if log_callback:
        log_callback("Orgill: Username entered")
    else:
        print("Orgill: Username entered")

    if log_callback:
        log_callback("Orgill: Waiting for password field...")
    else:
        print("Orgill: Waiting for password field...")
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_loginOrgillxs_Password"))
    )
    driver.execute_script("arguments[0].value = '';", password_field)
    password_field.send_keys(settings.orgill_credentials[1])
    if log_callback:
        log_callback("Orgill: Password entered")
    else:
        print("Orgill: Password entered")

    # Handle multiple types of cookie consent banners
    print("Orgill: Handling cookie consent banners...")

    # Try multiple selectors for consent buttons
    consent_selectors = [
        (By.CLASS_NAME, "termly-styles-button-d3um1t"),  # Accept button
        (By.CLASS_NAME, "termly-styles-buttons-bb7ad2"),  # Banner container (try to click accept inside)
        (By.XPATH, "//button[contains(text(), 'Accept')]"),
        (By.XPATH, "//button[contains(text(), 'Agree')]"),
        (By.XPATH, "//a[contains(text(), 'Accept')]"),
        (By.XPATH, "//a[contains(text(), 'Agree')]"),
    ]

    for selector_type, selector_value in consent_selectors:
        try:
            if selector_type == By.CLASS_NAME and selector_value == "termly-styles-buttons-bb7ad2":
                # Special handling for banner container - find accept button inside
                banner = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                accept_btn = banner.find_element(By.XPATH, ".//button[contains(text(), 'Accept')]")
                driver.execute_script("arguments[0].click();", accept_btn)
                print("Orgill: Clicked accept button inside banner")
            else:
                consent_btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                driver.execute_script("arguments[0].click();", consent_btn)
                print(f"Orgill: Clicked consent button ({selector_value})")
            time.sleep(1)
        except:
            continue

    # Additional wait and try to dismiss any remaining overlays
    print("Orgill: Waiting for overlays to clear...")
    time.sleep(2)

    # Try to click any remaining cookie banners or overlays
    try:
        # Look for any element with high z-index that might be overlaying
        overlays = driver.find_elements(By.XPATH, "//div[contains(@style, 'z-index') and contains(@style, '999')]")
        for overlay in overlays:
            try:
                driver.execute_script("arguments[0].style.display = 'none';", overlay)
                print("Orgill: Hidden overlay element")
            except:
                pass
    except:
        pass

    print("Orgill: Attempting to click login button...")
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "cphMainContent_ctl00_loginOrgillxs_LoginButton"))
    )

    # Try multiple click methods
    try:
        login_button.click()
        print("Orgill: Login button clicked successfully")
    except:
        try:
            driver.execute_script("arguments[0].click();", login_button)
            print("Orgill: Login button clicked via JavaScript")
        except Exception as e:
            print(f"Orgill: Failed to click login button: {e}")
            raise

    print("Orgill: Waiting for login to complete...")
    WebDriverWait(driver, 30).until(EC.url_changes(LOGIN_URL))
    print("Orgill: Login completed successfully")

    # After successful login, handle password expiration popup if present
    try:
        skip_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "lvwOrgill_PrivateHeaderV8_btnPWDAlertSkip"))
        )
        skip_button.click()
        print("Orgill: Password expiration popup detected and skipped.")
    except:
        pass  # No popup or not clickable, continue

def load_cookies(driver):
    try:
        cookie_path = os.path.join(PROJECT_ROOT, "data", "cookies", "orgill_cookies.pkl")
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
        cookies = driver.get_cookies()
        cookie_dir = os.path.join(PROJECT_ROOT, "data", "cookies")
        os.makedirs(cookie_dir, exist_ok=True)
        with open(os.path.join(cookie_dir, "orgill_cookies.pkl"), "wb") as f:
            pickle.dump(cookies, f)
    except:
        pass

def scrape_orgill(skus, browser=None, log_callback=None, progress_tracker=None):
    """Scrape Orgill products for multiple SKUs."""
    if not skus:
        return []

    products = []
    start_time = time.time()

    # Use provided browser or create a new one
    if browser is not None:
        driver = browser
    else:
        driver = create_browser("Orgill", headless=HEADLESS)
        if driver is None:
            display_error("Could not create browser for Orgill", log_callback=log_callback)
            return products
    
    try:
        # Handle login if required (only if we created our own browser)
        if browser is None:
            load_cookies(driver)
            if not is_logged_in(driver):
                login(driver, log_callback=log_callback)
                save_cookies(driver)
            
        for i, sku in enumerate(skus, 1):
            product_info = scrape_single_product(sku, driver, log_callback=log_callback)
            if product_info:
                products.append(product_info)
                display_product_result(product_info, i, len(skus))
            else:
                products.append(None)
            display_scraping_progress(i, len(skus), start_time, "Orgill")
            
            # Update progress tracker if provided
            if progress_tracker:
                progress_tracker.update_sku_progress(i, f"Processed {sku}", 1 if product_info else 0)
    
    finally:
        # Only quit browser if we created it ourselves
        if browser is None and driver:
            try:
                driver.quit()
            except:
                pass
    
    successful_products = [p for p in products if p]
    display_scraping_summary(successful_products, start_time, "Orgill", log_callback=log_callback)
                
    return products

def scrape_single_product(SKU, driver, log_callback=None):
    if driver is None:
        display_error("WebDriver instance is None. Cannot scrape product.", log_callback=log_callback)
        return None
    product_info = {
        'SKU': SKU,
        'Brand': 'N/A',
        'Name': 'N/A',
        'Weight': 'N/A',
        'Image URLs': []
    }
    try:
        # First try direct SKU search
        search_url = BASE_SEARCH_URL.format(SKU=SKU)
        driver.get(search_url)


        # Wait for page to load and check for either product or error
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblDescription")),
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblErrorMessage")),
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblSearchSubHeader"))
            )
        )

        # Additional wait to ensure content is loaded
        time.sleep(1)

        # Check for 'Found 0 results' in subheader span
        try:
            subheader = driver.find_element(By.ID, "cphMainContent_ctl00_lblSearchSubHeader")
            if subheader and "Found 0 results" in subheader.text:
                return None
        except Exception:
            pass

        try:
            error_element = driver.find_element(By.ID, "cphMainContent_ctl00_lblErrorMessage")
            if "No product(s) found." in error_element.text:
                return None
        except:
            pass

        # Check if we're actually on a product page (not search results)
        # Use the content count to determine if we have search results
        try:
            content_count_element = driver.find_element(By.ID, "cphMainContent_ctl00_lblContentCount")
            content_count = int(content_count_element.text.strip())
            
            if content_count == 0:
                # No results found
                return None
            elif content_count > 1:
                # Multiple results - not a single product page
                if log_callback:
                    log_callback(f"Orgill: Search for SKU {SKU} returned {content_count} results, skipping")
                else:
                    print(f"Orgill: Search for SKU {SKU} returned {content_count} results, skipping")
                return None
            # If content_count == 1, this shouldn't happen since it redirects to product page
            # but if it does, we can proceed with extraction
            
        except Exception as e:
            # Content count element not found - this means we're likely on a product page
            # (since search results pages have the content count element)
            # Continue with product extraction
            pass

        try:
            name_element = driver.find_element(By.ID, "cphMainContent_ctl00_lblDescription")
            
            # Wait a bit longer and check if element has text content
            for attempt in range(5):
                name_text = name_element.text.strip()
                if name_text:
                    product_info['Name'] = clean_string(name_text)
                    break
                time.sleep(0.5)
            else:
                # Try getting innerHTML if text is still empty
                name_text = driver.execute_script("return arguments[0].innerHTML;", name_element).strip()
                if name_text:
                    product_info['Name'] = clean_string(name_text)
                else:
                    product_info['Name'] = 'N/A'  # Placeholder instead of failing
        except Exception as e:
            product_info['Name'] = 'N/A'  # Placeholder instead of failing

        try:
            vendor_element = driver.find_element(By.ID, "cphMainContent_ctl00_lblVendorName")
            product_info['Brand'] = clean_string(vendor_element.text)
        except Exception as e:
            display_error(f"Error extracting brand: {e}", log_callback=log_callback)

        # If brand was found and is in the name, remove it
        if product_info.get('Brand') and product_info.get('Name') and product_info['Name'] != 'N/A':
            brand_name = product_info['Brand']
            name_lower = product_info['Name'].lower()
            brand_lower = brand_name.lower()
            if name_lower.startswith(brand_lower + ' ') or name_lower.startswith(brand_lower + '-'):
                product_info['Name'] = clean_string(product_info['Name'][len(brand_name):].lstrip(' -'))

        try:
            model_number_element = driver.find_element(By.ID, "cphMainContent_ctl00_lblModelNumber")
            model_number = clean_string(model_number_element.text)
            if model_number:
                product_info['Name'] = re.sub(rf'\b{re.escape(model_number)}\b', '', product_info['Name'])
                product_info['Name'] = re.sub(r'\s{2,}', ' ', product_info['Name']).strip()
        except Exception as e:
            # Model number is optional, don't display error for missing element
            pass

        try:
            consent_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "termly-styles-button-d3um1t"))
            )
            driver.execute_script("arguments[0].click();", consent_btn)
            time.sleep(0.5)
        except:
            pass

        try:
            ordering_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[div[contains(text(), 'Ordering Specifications')]]"))
            )
            driver.execute_script("arguments[0].click();", ordering_tab)

            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "orderSpecificationDiv"))
            )

            # Try multiple weight extraction patterns
            weight_found = False
            
            # Pattern 1: Weight(lb): in ordering specifications
            try:
                weight_row = driver.find_element(By.XPATH, "//strong[contains(text(),'Weight(lb):')]")
                weight_value_div = weight_row.find_element(
                    By.XPATH,
                    "./parent::div/following-sibling::div[contains(@class, 'detail-alternate-row')]"
                )
                weight_text = clean_string(weight_value_div.text)
                if weight_text:
                    product_info['Weight'] = weight_text
                    weight_found = True
            except:
                pass
            
            # Pattern 2: Weight(lb) in shipping unit dimensions
            if not weight_found:
                try:
                    weight_element = driver.find_element(By.XPATH, "//strong[text()='Weight(lb):']/following-sibling::*[1]")
                    weight_text = clean_string(weight_element.text)
                    if weight_text:
                        product_info['Weight'] = weight_text
                        weight_found = True
                except:
                    pass
            
            if not weight_found:
                pass  # Weight not found, but continue processing
                
        except Exception:
            pass  # Weight is optional; leave as N/A if not found

        try:
            # Get all product images from the main carousel (websmall images only)
            img_elements = driver.find_elements(By.XPATH, "//img[contains(@src, 'images.orgill.com/websmall/')]")
            for img_element in img_elements:
                img_url = img_element.get_attribute('src')
                if img_url and img_url not in product_info['Image URLs']:
                    product_info['Image URLs'].append(img_url)
        except Exception as e:
            display_error(f"Error extracting images: {e}", log_callback=log_callback)

        # After performing the search for the SKU
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblSearchSubHeader"))
            )
            subheader = driver.find_element(By.ID, "cphMainContent_ctl00_lblSearchSubHeader")
            if subheader and "Found 0 results" in subheader.text:
                return None
        except Exception:
            pass  # Suppress error if subheader is not present

        # Check for critical missing data - return None if essential fields are missing
        critical_fields_missing = (
            any(value == 'N/A' for key, value in product_info.items() 
                if isinstance(value, str) and key not in ['Weight']) or  # Weight is optional
            not product_info.get('Image URLs')
        )

        if critical_fields_missing:
            return None

        return product_info
    except Exception as e:
        display_error(f"Error processing SKU {SKU}: {e}", log_callback=log_callback)
        return None

# --- TEST BLOCK FOR DEBUGGING ---
if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--integration":
        # Run integration test with real SKUs
        test_sku = "017800149372"  # Replace with a real SKU for live test
        print(f"[Orgill Integration Test] Scraping real SKU: {test_sku}")
        results = scrape_orgill([test_sku])
        print("[Orgill Integration Test] Result:", results[0] if results else None)
    else:
        # Run unit tests by default
        import unittest
        from unittest.mock import Mock, MagicMock, patch, call

        class TestOrgillScraper(unittest.TestCase):
            def setUp(self):
                self.test_sku = "017800149372"

            @patch('scrapers.orgill.WebDriverWait')
            @patch('scrapers.orgill.EC')
            def test_no_results_content_count_zero(self, mock_ec, mock_wait):
                """Test handling when content count is 0 (no results)"""
                # Mock WebDriverWait to avoid actual waiting
                mock_wait_instance = Mock()
                mock_wait.return_value = mock_wait_instance
                mock_wait_instance.until = Mock()

                with patch('scrapers.orgill.webdriver.Chrome') as mock_chrome:
                    mock_driver = Mock()
                    mock_chrome.return_value = mock_driver

                    # Mock the page load and element finding
                    mock_driver.get = Mock()

                    # Mock find_element to return content count = 0
                    def mock_find_element(by, value):
                        if (by, value) == (By.ID, "cphMainContent_ctl00_lblContentCount"):
                            mock_elem = Mock()
                            mock_elem.text = "0"
                            return mock_elem
                        else:
                            raise Exception("Element not found")

                    mock_driver.find_element = mock_find_element

                    result = scrape_single_product(self.test_sku, mock_driver)
                    self.assertIsNone(result, "Should return None for no results")

            @patch('scrapers.orgill.WebDriverWait')
            @patch('scrapers.orgill.EC')
            def test_multiple_results_content_count_greater_than_one(self, mock_ec, mock_wait):
                """Test handling when content count > 1 (multiple results)"""
                # Mock WebDriverWait to avoid actual waiting
                mock_wait_instance = Mock()
                mock_wait.return_value = mock_wait_instance
                mock_wait_instance.until = Mock()

                with patch('scrapers.orgill.webdriver.Chrome') as mock_chrome:
                    mock_driver = Mock()
                    mock_chrome.return_value = mock_driver

                    # Mock the page load and element finding
                    mock_driver.get = Mock()

                    # Mock find_element to return content count > 1
                    def mock_find_element(by, value):
                        if (by, value) == (By.ID, "cphMainContent_ctl00_lblContentCount"):
                            mock_elem = Mock()
                            mock_elem.text = "5"
                            return mock_elem
                        else:
                            raise Exception("Element not found")

                    mock_driver.find_element = mock_find_element

                    result = scrape_single_product(self.test_sku, mock_driver)
                    self.assertIsNone(result, "Should return None for multiple results")

            @patch('scrapers.orgill.WebDriverWait')
            @patch('scrapers.orgill.EC')
            @patch('scrapers.orgill.time.sleep')  # Mock sleep to speed up tests
            def test_single_product_redirect_no_content_count(self, mock_sleep, mock_ec, mock_wait):
                """Test handling when redirected to product page (no content count element)"""
                # Mock WebDriverWait to avoid actual waiting
                mock_wait_instance = Mock()
                mock_wait.return_value = mock_wait_instance
                mock_wait_instance.until = Mock()  # This will make WebDriverWait.until() succeed

                with patch('scrapers.orgill.webdriver.Chrome') as mock_chrome:
                    mock_driver = Mock()
                    mock_chrome.return_value = mock_driver

                    # Mock the page load
                    mock_driver.get = Mock()

                    # Mock find_element - content count not found, but product elements are
                    def mock_find_element(by, value):
                        if (by, value) == (By.ID, "cphMainContent_ctl00_lblContentCount"):
                            raise Exception("Element not found")  # Content count not present
                        elif (by, value) == (By.ID, "cphMainContent_ctl00_lblDescription"):
                            mock_elem = Mock()
                            mock_elem.text = "Test Product Name"
                            return mock_elem
                        elif (by, value) == (By.ID, "cphMainContent_ctl00_lblVendorName"):
                            mock_elem = Mock()
                            mock_elem.text = "Test Brand"
                            return mock_elem
                        elif (by, value) == (By.ID, "cphMainContent_ctl00_lblModelNumber"):
                            mock_elem = Mock()
                            mock_elem.text = ""  # No model number to remove
                            return mock_elem
                        elif (by, value) == (By.ID, "cphMainContent_ctl00_lblSearchSubHeader"):
                            mock_elem = Mock()
                            mock_elem.text = "Found 1 result"
                            return mock_elem
                        else:
                            raise Exception("Element not found")

                    mock_driver.find_element = mock_find_element

                    # Mock find_elements for images
                    mock_img = Mock()
                    mock_img.get_attribute.return_value = "https://images.orgill.com/websmall/test.jpg"
                    mock_driver.find_elements.return_value = [mock_img]

                    # Mock execute_script for innerHTML
                    mock_driver.execute_script = Mock(return_value="Test Product Name MODEL123")

                    result = scrape_single_product(self.test_sku, mock_driver)

                    # Should return a product dict, not None
                    self.assertIsNotNone(result, "Should return product data for single product redirect")
                    self.assertEqual(result['SKU'], self.test_sku)
                    self.assertEqual(result['Name'], "Test Product Name")  # No model number to remove
                    self.assertEqual(result['Brand'], "Test Brand")
                    self.assertIn("https://images.orgill.com/websmall/test.jpg", result['Image URLs'])

        # Run the unit tests
        print("Running Orgill scraper unit tests...")
        print("Usage: python orgill.py --integration  (for real SKU testing)")
        unittest.main(argv=[''], exit=False, verbosity=2)
