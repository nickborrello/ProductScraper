import re
import os
from selenium.webdriver.chrome.options import Options

def get_login_safe_chrome_options(headless=False, profile_suffix="default"):
    """Get Chrome options optimized for login success (fewer restrictions)."""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # Essential stability options only
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Allow automation detection to be hidden (helps with login)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Keep images enabled for login forms
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values": {
            "notifications": 2  # Block notifications only
        }
    })
    
    # Minimal logging
    options.add_argument("--log-level=3")
    
    # Standard user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Profile directory
    if profile_suffix:
        profile_dir = os.path.abspath(f"browser_profiles/{profile_suffix}")
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
    
    return options

# Keep the original function for compatibility
def get_standard_chrome_options(headless=True, profile_suffix="default"):
    """Get standardized Chrome options that suppress common errors and warnings."""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")  # Use new headless mode
    
    # Ultra-conservative stability options for slow systems
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    
    # Suppress GPU and WebGL errors
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-webgl2")
    options.add_argument("--disable-3d-apis")
    options.add_argument("--disable-accelerated-2d-canvas")
    options.add_argument("--disable-accelerated-jpeg-decoding")
    options.add_argument("--disable-accelerated-mjpeg-decode")
    options.add_argument("--disable-accelerated-video-decode")
    options.add_argument("--disable-accelerated-video-encode")
    options.add_argument("--use-gl=swiftshader")  # Use software rendering
    
    # Memory and performance constraints for slow systems (removed problematic flags)
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=512")  # Reduced from 4096
    options.add_argument("--no-zygote")
    # Removed --single-process as it causes login issues
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--enable-low-end-device-mode")
    
    # Network and loading optimizations
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-ipc-flooding-protection")
    
    # Disable images for faster loading (can be overridden)
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values": {
            "notifications": 2
        }
    })
    
    # Suppress logging
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_argument("--log-level=3")  # Suppress INFO, WARNING, ERROR
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    
    # User agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Profile directory
    if profile_suffix:
        profile_dir = os.path.abspath(f"browser_profiles/{profile_suffix}")
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
    
    return options

def clean_string(s):
    """Clean and normalize text strings."""
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r'\s+', ' ', s)  # Replace multiple spaces with single space
    s = re.sub(r'[^\x00-\x7F]+', '', s)  # Remove non-ASCII characters
    return s

def create_fileName(name):
    """Create a safe filename from a product name."""
    if not name:
        return "unknown"
    
    # Clean the name
    clean_name = clean_string(name)
    
    # Replace problematic characters for filenames
    clean_name = re.sub(r'[<>:"/\\|?*]', '', clean_name)  # Remove invalid filename chars
    clean_name = re.sub(r'\s+', '_', clean_name)  # Replace spaces with underscores
    clean_name = clean_name.lower()
    
    # Limit length
    if len(clean_name) > 50:
        clean_name = clean_name[:50]
    
    return clean_name if clean_name else "unknown"

def create_html(name):
    """Create an HTML-safe filename."""
    return create_fileName(name) + ".html"

def clean_brand(brand):
    """Clean brand name for directory structure."""
    if not brand:
        return "unknown"
    
    clean_brand_name = clean_string(brand)
    clean_brand_name = re.sub(r'[<>:"/\\|?*]', '', clean_brand_name)
    clean_brand_name = re.sub(r'\s+', '-', clean_brand_name)
    clean_brand_name = clean_brand_name.lower()
    
    return clean_brand_name if clean_brand_name else "unknown"

def full_name(brand, name):
    """Create full product name combining brand and name."""
    clean_brand_name = clean_string(brand) if brand else ""
    clean_product_name = clean_string(name) if name else ""
    
    if clean_brand_name and clean_product_name:
        return f"{clean_brand_name} {clean_product_name}"
    elif clean_brand_name:
        return clean_brand_name
    elif clean_product_name:
        return clean_product_name
    else:
        return "Unknown Product"
