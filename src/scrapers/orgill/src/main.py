import os
import sys
import time
import pickle
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, WebDriverException
import apify
from apify import Actor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent
import logging

# Add the project root to the Python path for direct execution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Module configuration
HEADLESS = False  # Now works in headless mode after fixing Chrome options  # Set to False only if CAPTCHA solving requires visible browser
DEBUG_MODE = False  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM - test SKU for Orgill

# URLs and constants
LOGIN_URL = 'https://www.orgill.com/index.aspx?tab=8'
BASE_SEARCH_URL = 'https://www.orgill.com/SearchResultN.aspx?ddlhQ={SKU}'

@dataclass
class ScrapingMetrics:
    """Metrics for monitoring scraping performance."""
    total_products: int = 0
    successful_products: int = 0
    failed_products: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_products / self.total_products if self.total_products > 0 else 0.0

    @property
    def average_time_per_product(self) -> float:
        total_time = self.end_time - self.start_time
        return total_time / self.total_products if self.total_products > 0 else 0.0

class BrowserSession:
    """Manages Chrome browser sessions with automatic rotation and cleanup."""

    def __init__(self, headless: bool = True, profile_suffix: str = "orgill"):
        self.headless = headless
        self.profile_suffix = profile_suffix
        self.driver: Optional[webdriver.Chrome] = None
        self.ua = UserAgent()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Initialize Chrome browser with optimized settings."""
        try:
            chrome_options = self._get_chrome_options()
            service = ChromeService(log_path=os.devnull)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Browser session started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")
            raise

    def close(self):
        """Clean up browser session."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser session closed")
            except Exception as e:
                logger.warning(f"Error closing browser session: {e}")
            finally:
                self.driver = None

    def _get_chrome_options(self) -> Options:
        """Get optimized Chrome options for scraping."""
        options = Options()

        if self.headless:
            options.add_argument('--headless')

        # Basic options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        # Anti-detection measures
        options.add_argument(f'--user-agent={self.ua.random}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Enable Chrome DevTools remote debugging if configured
        if ENABLE_DEVTOOLS:
            options.add_argument(f"--remote-debugging-port={DEVTOOLS_PORT}")
            options.add_argument("--remote-debugging-address=0.0.0.0")
            logger.info(f"🔧 DevTools enabled on port {DEVTOOLS_PORT}")

        # Performance optimizations
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        # Note: JavaScript and images are REQUIRED for Orgill website functionality
        # Removed: --disable-images (needed for proper page loading)
        # Removed: --disable-javascript (required for login/forms)
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')

        # Cookie and autofill settings
        options.add_argument("--disable-blink-features=Autofill")
        options.add_argument("--disable-features=Autofill")

        # Profile directory
        user_data_dir = f"/tmp/orgill_browser_{self.profile_suffix}_{int(time.time())}"
        os.makedirs(user_data_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={user_data_dir}")

        return options

class RateLimiter:
    """Simple rate limiter with randomized delays."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self.min_delay = min_delay
        self.max_delay = max_delay

    def wait(self):
        """Wait for a random interval between min and max delay."""
        import random
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

class OrgillScraper:
    """Main scraper class for Orgill products."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser_session = BrowserSession(headless=headless)
        self.rate_limiter = RateLimiter()
        self.metrics = ScrapingMetrics()

    def __enter__(self):
        self.browser_session.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser_session.close()

    @property
    def driver(self) -> webdriver.Chrome:
        """Get the current browser driver."""
        return self.browser_session.driver

    def login(self) -> bool:
        """Handle Orgill login process."""
        try:
            logger.info("Starting Orgill login process")

            # Get credentials from environment variables or settings manager
            username = os.getenv('ORGILL_USERNAME')
            password = os.getenv('ORGILL_PASSWORD')
            
            # Fallback to settings manager if env vars not set
            if not username or not password:
                try:
                    # Import settings manager dynamically to avoid dependency issues
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    sys.path.insert(0, os.path.join(project_root, 'src'))
                    from core.settings_manager import SettingsManager
                    settings = SettingsManager()
                    username, password = settings.orgill_credentials
                except ImportError:
                    pass

            if not username or not password:
                raise ValueError("ORGILL_USERNAME and ORGILL_PASSWORD environment variables or settings required")

            self.driver.get(LOGIN_URL)

            # Wait for username field
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_loginOrgillxs_UserName"))
            )
            self.driver.execute_script("arguments[0].value = '';", username_field)
            username_field.send_keys(username)

            # Wait for password field
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_loginOrgillxs_Password"))
            )
            self.driver.execute_script("arguments[0].value = '';", password_field)
            password_field.send_keys(password)

            # Handle cookie consent
            self._handle_cookie_consent()

            # Click login button
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "cphMainContent_ctl00_loginOrgillxs_LoginButton"))
            )

            try:
                login_button.click()
            except:
                self.driver.execute_script("arguments[0].click();", login_button)

            # Wait for login completion
            WebDriverWait(self.driver, 30).until(EC.url_changes(LOGIN_URL))

            # Handle password expiration popup
            self._handle_password_popup()

            # Verify login
            if self._is_logged_in():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login verification failed")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def _handle_cookie_consent(self):
        """Handle various cookie consent banners."""
        consent_selectors = [
            (By.CLASS_NAME, "termly-styles-button-d3um1t"),
            (By.XPATH, "//button[contains(text(), 'Accept')]"),
            (By.XPATH, "//button[contains(text(), 'Agree')]"),
            (By.XPATH, "//a[contains(text(), 'Accept')]"),
            (By.XPATH, "//a[contains(text(), 'Agree')]"),
        ]

        for selector_type, selector_value in consent_selectors:
            try:
                if selector_type == By.CLASS_NAME and "termly-styles-buttons" in selector_value:
                    banner = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    accept_btn = banner.find_element(By.XPATH, ".//button[contains(text(), 'Accept')]")
                    self.driver.execute_script("arguments[0].click();", accept_btn)
                else:
                    consent_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    self.driver.execute_script("arguments[0].click();", consent_btn)
                logger.info("Cookie consent handled")
                time.sleep(1)
                break
            except:
                continue

    def _handle_password_popup(self):
        """Handle password expiration popup if present."""
        try:
            skip_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "lvwOrgill_PrivateHeaderV8_btnPWDAlertSkip"))
            )
            skip_button.click()
            logger.info("Password expiration popup handled")
        except:
            pass  # No popup present

    def _is_logged_in(self) -> bool:
        """Check if user is logged in."""
        try:
            self.driver.get("https://www.orgill.com/Default.aspx")
            time.sleep(2)
            signout_links = self.driver.find_elements(By.XPATH, "//a[@href='/signOut.aspx' and .//span[text()='Sign Out']]")
            return len(signout_links) > 0
        except Exception as e:
            logger.warning(f"Login check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutException, WebDriverException))
    )
    def scrape_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """Scrape a single product by SKU."""
        try:
            logger.info(f"Scraping product SKU: {sku}")

            # Apply rate limiting
            self.rate_limiter.wait()

            # Navigate to search URL
            search_url = BASE_SEARCH_URL.format(SKU=sku)
            self.driver.get(search_url)

            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblDescription")),
                    EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblErrorMessage")),
                    EC.presence_of_element_located((By.ID, "cphMainContent_ctl00_lblSearchSubHeader"))
                )
            )

            time.sleep(1)  # Additional wait for content

            # Check for no results
            if self._check_no_results():
                logger.info(f"No results found for SKU: {sku}")
                return None

            # Check for multiple results
            if self._check_multiple_results():
                logger.info(f"Multiple results found for SKU: {sku}, skipping")
                return None

            # DEBUG MODE: Pause for manual inspection
            if DEBUG_MODE:
                logger.info(f"🐛 DEBUG MODE: Product page loaded for SKU {sku}")
                logger.info("Press Enter in the terminal to continue with data extraction...")
                input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

            # Extract product data
            product_data = self._extract_product_data(sku)

            # Validate data quality
            if self._validate_product_data(product_data):
                logger.info(f"Successfully scraped product: {sku}")
                return product_data
            else:
                logger.warning(f"Product data validation failed for SKU: {sku}")
                logger.warning(f"Extracted data: {product_data}")
                return None

        except Exception as e:
            logger.error(f"Error scraping SKU {sku}: {e}")
            return None

    def _check_no_results(self) -> bool:
        """Check if search returned no results."""
        try:
            # Check subheader for "Found 0 results"
            subheader = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblSearchSubHeader")
            if "Found 0 results" in subheader.text:
                return True
        except:
            pass

        try:
            # Check error message
            error_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblErrorMessage")
            if "No product(s) found." in error_element.text:
                return True
        except:
            pass

        try:
            # Check content count
            content_count_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblContentCount")
            content_count = int(content_count_element.text.strip())
            return content_count == 0
        except:
            pass

        return False

    def _check_multiple_results(self) -> bool:
        """Check if search returned multiple results."""
        try:
            content_count_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblContentCount")
            content_count = int(content_count_element.text.strip())
            return content_count > 1
        except:
            return False  # If no content count, assume single product page

    def _extract_product_data(self, sku: str) -> Dict[str, Any]:
        """Extract product data from the page."""
        product_info = {
            'SKU': sku,
            'Brand': 'N/A',
            'Name': 'N/A',
            'Weight': 'N/A',
            'Image URLs': []
        }

        # Extract name
        try:
            name_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblDescription")
            for attempt in range(5):
                name_text = name_element.text.strip()
                if name_text:
                    product_info['Name'] = self._clean_string(name_text)
                    break
                time.sleep(0.5)
            else:
                # Try innerHTML
                name_text = self.driver.execute_script("return arguments[0].innerHTML;", name_element).strip()
                if name_text:
                    product_info['Name'] = self._clean_string(name_text)
        except Exception as e:
            logger.warning(f"Error extracting name: {e}")

        # Extract brand
        try:
            vendor_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblVendorName")
            product_info['Brand'] = self._clean_string(vendor_element.text)
        except Exception as e:
            logger.warning(f"Error extracting brand: {e}")

        # Remove brand from name if present
        if product_info.get('Brand') and product_info.get('Name') and product_info['Name'] != 'N/A':
            brand_name = product_info['Brand']
            name_lower = product_info['Name'].lower()
            brand_lower = brand_name.lower()
            if name_lower.startswith(brand_lower + ' ') or name_lower.startswith(brand_lower + '-'):
                product_info['Name'] = self._clean_string(product_info['Name'][len(brand_name):].lstrip(' -'))

        # Remove model number from name
        try:
            model_number_element = self.driver.find_element(By.ID, "cphMainContent_ctl00_lblModelNumber")
            model_number = self._clean_string(model_number_element.text)
            if model_number:
                product_info['Name'] = re.sub(rf'\b{re.escape(model_number)}\b', '', product_info['Name'])
                product_info['Name'] = re.sub(r'\s{2,}', ' ', product_info['Name']).strip()
        except:
            pass  # Model number is optional

        # Extract weight
        try:
            self._handle_cookie_consent()  # Handle any cookie banners

            ordering_tab = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[div[contains(text(), 'Ordering Specifications')]]"))
            )
            self.driver.execute_script("arguments[0].click();", ordering_tab)

            WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "orderSpecificationDiv"))
            )

            # Try multiple weight extraction patterns
            weight_found = False

            # Pattern 1: Weight(lb): in ordering specifications
            try:
                weight_row = self.driver.find_element(By.XPATH, "//strong[contains(text(),'Weight(lb):')]")
                weight_value_div = weight_row.find_element(
                    By.XPATH,
                    "./parent::div/following-sibling::div[contains(@class, 'detail-alternate-row')]"
                )
                weight_text = self._clean_string(weight_value_div.text)
                if weight_text:
                    product_info['Weight'] = weight_text
                    weight_found = True
            except:
                pass

            # Pattern 2: Weight(lb) in shipping unit dimensions
            if not weight_found:
                try:
                    weight_element = self.driver.find_element(By.XPATH, "//strong[text()='Weight(lb):']/following-sibling::*[1]")
                    weight_text = self._clean_string(weight_element.text)
                    if weight_text:
                        product_info['Weight'] = weight_text
                        weight_found = True
                except:
                    pass

        except Exception as e:
            logger.warning(f"Error extracting weight: {e}")

        # Extract images
        try:
            img_elements = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'images1.orgill.com/websmall/')]")
            for img_element in img_elements:
                img_url = img_element.get_attribute('src')
                if img_url and img_url not in product_info['Image URLs']:
                    product_info['Image URLs'].append(img_url)
        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        return product_info

    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Validate extracted product data quality."""
        # Check critical fields
        critical_fields_missing = (
            any(value == 'N/A' for key, value in product_data.items()
                if isinstance(value, str) and key not in ['Weight', 'Image URLs']) or  # Weight and Images are optional
            not product_data.get('Name') or product_data.get('Name') == 'N/A' or  # Name is required
            not product_data.get('Brand') or product_data.get('Brand') == 'N/A'   # Brand is required
        )
        return not critical_fields_missing

    @staticmethod
    def _clean_string(text: str) -> str:
        """Clean and normalize string data."""
        if not text:
            return 'N/A'
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        return cleaned if cleaned else 'N/A'

async def main() -> None:
    """Main actor function."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        skus = actor_input.get('skus', [TEST_SKU])

        logger.info(f"Starting Orgill scraper for {len(skus)} SKUs")

        # Initialize metrics
        metrics = ScrapingMetrics()
        metrics.total_products = len(skus)
        metrics.start_time = time.time()

        successful_products = []
        failed_skus = []

        try:
            with OrgillScraper(headless=HEADLESS) as scraper:
                # Login
                if not scraper.login():
                    await Actor.fail("Failed to login to Orgill")

                # Process each SKU
                for i, sku in enumerate(skus, 1):
                    logger.info(f"Processing SKU {i}/{len(skus)}: {sku}")

                    product_data = scraper.scrape_product(sku)

                    if product_data:
                        successful_products.append(product_data)
                        metrics.successful_products += 1

                        # Push to dataset
                        await Actor.push_data(product_data)
                    else:
                        failed_skus.append(sku)
                        metrics.failed_products += 1

                    # Log progress
                    progress = (i / len(skus)) * 100
                    await Actor.set_status_message(f"Processed {i}/{len(skus)} SKUs ({progress:.1f}%)")

        except Exception as e:
            logger.error(f"Scraper execution failed: {e}")
            await Actor.fail(f"Scraper execution failed: {e}")

        finally:
            # Update final metrics
            metrics.end_time = time.time()

            # Log final results
            logger.info(f"Scraping completed. Success rate: {metrics.success_rate:.2%}")
            logger.info(f"Total products: {metrics.total_products}")
            logger.info(f"Successful: {metrics.successful_products}")
            logger.info(f"Failed: {metrics.failed_products}")
            logger.info(f"Average time per product: {metrics.average_time_per_product:.2f}s")

            if failed_skus:
                logger.warning(f"Failed SKUs: {failed_skus}")

            # Set final status
            await Actor.set_status_message(
                f"Completed: {metrics.successful_products}/{metrics.total_products} products scraped successfully"
            )

def main_local():
    """Run locally for testing."""
    import json
    
    # Default test SKU
    skus = [TEST_SKU]
    
    # Check command line arguments
    if len(sys.argv) > 1:
        try:
            input_data = json.loads(sys.argv[1])
            skus = input_data.get('skus', skus)
        except json.JSONDecodeError:
            print("Invalid JSON input, using default SKUs")
    
    print(f"Starting local Orgill scraping for {len(skus)} SKUs: {skus}")
    
    products = scrape_products(skus)
    valid_products = [p for p in products if p]
    
    print(f"Scraped {len(valid_products)} products successfully")
    print("Results:")
    for product in valid_products:
        print(json.dumps(product, indent=2))
    
    return valid_products


def scrape_products(skus: List[str], progress_callback=None, headless=None) -> List[Optional[Dict[str, Any]]]:
    """Scrape multiple Orgill products with session management and monitoring.
    
    This function provides a direct interface for testing and can be called
    independently of the Apify actor framework.
    """
    if headless is None:
        headless = HEADLESS
    logger.info(f"Starting Orgill scraper for {len(skus)} SKUs")
    
    # Initialize metrics
    metrics = ScrapingMetrics()
    metrics.total_products = len(skus)
    metrics.start_time = time.time()
    
    products = []
    
    try:
        with OrgillScraper(headless=headless) as scraper:
            # Login
            if not scraper.login():
                logger.error("Failed to login to Orgill")
                return [None] * len(skus)
            
            # Process each SKU
            for i, sku in enumerate(skus, 1):
                # Update progress callback if provided
                if progress_callback:
                    progress_callback(i-1, f"Processing SKU {sku}")

                logger.info(f"Processing SKU {i}/{len(skus)}: {sku}")
                
                product_data = scraper.scrape_product(sku)
                
                if product_data:
                    products.append(product_data)
                    metrics.successful_products += 1
                else:
                    products.append(None)
                    metrics.failed_products += 1
        
        # Final progress update
        if progress_callback:
            progress_callback(len(skus), "Completed processing all SKUs")
        
    except Exception as e:
        logger.error(f"Scraper execution failed: {e}")
        # Fill remaining products with None
        remaining = len(skus) - len(products)
        products.extend([None] * remaining)
        metrics.failed_products += remaining
    
    finally:
        # Update final metrics
        metrics.end_time = time.time()
        
        # Log final results
        logger.info(f"Scraping completed. Success rate: {metrics.success_rate:.2%}")
        logger.info(f"Total products: {metrics.total_products}")
        logger.info(f"Successful: {metrics.successful_products}")
        logger.info(f"Failed: {metrics.failed_products}")
        logger.info(f"Average time per product: {metrics.average_time_per_product:.2f}s")
    
    return products

if __name__ == '__main__':
    # Check if running locally or on Apify
    if os.getenv('APIFY_IS_AT_HOME') or os.getenv('APIFY_ACTOR_ID'):
        # Running on Apify platform
        main()
    else:
        # Running locally
        main_local()