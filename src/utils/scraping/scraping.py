import os
import re

from selenium.webdriver.chrome.options import Options


def get_standard_chrome_options(
    headless=True, profile_suffix="default", enable_devtools=False, devtools_port=9222
):
    """Get standardized Chrome options that suppress common errors and warnings."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")  # Use new headless mode

    # Enable remote debugging if requested
    if enable_devtools:
        options.add_argument(f"--remote-debugging-port={devtools_port}")
        options.add_argument("--remote-debugging-address=127.0.0.1")
        # Don't disable dev tools when debugging is enabled
    else:
        options.add_argument("--disable-dev-tools")

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

    # Suppress GPU and WebGL errors - enhanced suppression
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-webgl2")
    options.add_argument("--disable-3d-apis")
    options.add_argument("--disable-accelerated-2d-canvas")
    options.add_argument("--disable-accelerated-jpeg-decoding")
    options.add_argument("--disable-accelerated-mjpeg-decode")
    options.add_argument("--disable-accelerated-video-decode")
    options.add_argument("--disable-accelerated-video-encode")
    options.add_argument("--use-gl=swiftshader")  # Use software rendering
    options.add_argument("--disable-gpu-compositing")
    options.add_argument("--disable-gpu-driver-bug-workarounds")
    options.add_argument("--disable-gpu-early-init")
    options.add_argument("--disable-gpu-memory-buffer-video-frames")
    options.add_argument("--disable-gpu-process-crash-limit")
    options.add_argument("--disable-gpu-process-for-dx12-info-collection")
    options.add_argument("--disable-gpu-sandbox")
    options.add_argument("--disable-gpu-shader-disk-cache")
    options.add_argument("--disable-gpu-vsync")
    options.add_argument("--disable-gpu-watchdog")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-features=VizDisplayCompositor")

    # Final GPU error suppression - disable GPU watchdog and context lost recovery
    options.add_argument("--disable-gpu-watchdog")
    options.add_argument("--disable-features=ContextLostRecovery")
    options.add_argument("--disable-background-media-download")
    options.add_argument("--disable-features=MediaRouter")
    options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
    options.add_argument("--disable-features=WebRtcUseH264")
    # Remove duplicate options that are already set above
    options.add_argument("--log-level=3")  # Suppress INFO, WARNING, ERROR
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-background-networking")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    options.add_argument("--mute-audio")

    # Set logging preferences to suppress GPU errors
    options.set_capability(
        "goog:loggingPrefs", {"browser": "OFF", "driver": "OFF", "performance": "OFF"}
    )

    # User agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Standard window size for consistent responsive behavior across environments
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")

    # Additional consistency options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Profile directory - store in data/selenium_profiles
    if profile_suffix:
        # Find project root (where main.py is)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        while project_root != os.path.dirname(project_root):
            if os.path.exists(os.path.join(project_root, "main.py")):
                break
            project_root = os.path.dirname(project_root)

        profile_dir = os.path.join(
            project_root, "data", "browser_profiles", profile_suffix.replace(" ", "_")
        )
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")

    return options


def clean_string(s):
    s = s.strip()
    if s.isupper() and len(s) > 3:
        s = smart_title(s)

    s = re.sub(r"\d+\s*ea/?", "", s).strip()
    s = s.replace(",", "").strip()
    s = re.sub(r"[\|\u00AE\u2122\u00A9]", "", s)

    s = re.sub(r"(\d+)\s*[-–—]\s*(\d+)", r"\1-\2", s)
    s = re.sub(r"(\d+)\"", r"\1 in.", s)
    s = re.sub(r"(\d+)'", r"\1 ft.", s)

    units = ["oz", "lb", "ft", "cm", "kg", "in"]
    for unit in units:
        s = re.sub(rf"\b{unit}\b", f"{unit}.", s, flags=re.IGNORECASE)

    s = re.sub(r"\.{2,}", ".", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def smart_title(s):
    """Title case that handles apostrophes correctly (e.g., "world's best" -> "World's Best", not "World'S Best")"""
    # First do regular title case
    titled = s.title()

    # Fix apostrophes - lowercase the letter after an apostrophe if it's not at the start of a word
    # This handles cases like "World'S" -> "World's"
    import re

    titled = re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), titled)

    return titled


def clean_brand(brand):
    valid_name = re.sub(r"[^a-zA-Z0-9\s]", "", brand)
    valid_name = valid_name.replace(" ", "-")
    return valid_name.lower()


import hashlib


def create_fileName(s):
    base = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    base = re.sub(r"\s+", " ", base).strip().replace(" ", "-").lower()

    if len(base) > 100:
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        base = base[:90] + "-" + hash_suffix
    return f"{base}.jpg"


def create_html(s):
    base = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    base = re.sub(r"\s+", " ", base).strip().replace(" ", "-").lower()

    if len(base) > 100:
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        base = base[:90] + "-" + hash_suffix
    return f"{base}.html"


def full_name(brand, product_name):
    brand_clean = brand.strip().upper()
    if product_name.lower().startswith(brand_clean.lower()):
        return product_name
    else:
        return f"{brand} {product_name}"
