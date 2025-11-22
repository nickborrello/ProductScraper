import hashlib
import os
import re

from selenium.webdriver.chrome.options import Options

MAX_FILENAME_LENGTH = 100
MIN_UPPERCASE_LENGTH = 3
HASH_SUFFIX_LENGTH = 8
TRUNCATE_LENGTH = 90


def _add_debugging_options(options: Options, enable_devtools: bool, devtools_port: int) -> None:
    """Add remote debugging options if enabled."""
    if enable_devtools:
        options.add_argument(f"--remote-debugging-port={devtools_port}")
        options.add_argument("--remote-debugging-address=127.0.0.1")
    else:
        options.add_argument("--disable-dev-tools")


def _add_stability_options(options: Options) -> None:
    """Add stability options for Chrome."""
    stability_options = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-hang-monitor",
        "--disable-prompt-on-repost",
        "--disable-component-update",
        "--disable-domain-reliability",
        "--disable-client-side-phishing-detection",
        "--no-default-browser-check",
        "--no-first-run",
        "--mute-audio",
    ]
    for option in stability_options:
        options.add_argument(option)


def _add_gpu_suppression_options(options: Options) -> None:
    """Add options to suppress GPU and WebGL errors."""
    gpu_options = [
        "--disable-webgl",
        "--disable-webgl2",
        "--disable-3d-apis",
        "--disable-accelerated-2d-canvas",
        "--disable-accelerated-jpeg-decoding",
        "--disable-accelerated-mjpeg-decode",
        "--disable-accelerated-video-decode",
        "--disable-accelerated-video-encode",
        "--use-gl=swiftshader",
        "--disable-gpu-compositing",
        "--disable-gpu-driver-bug-workarounds",
        "--disable-gpu-early-init",
        "--disable-gpu-memory-buffer-video-frames",
        "--disable-gpu-process-crash-limit",
        "--disable-gpu-process-for-dx12-info-collection",
        "--disable-gpu-sandbox",
        "--disable-gpu-shader-disk-cache",
        "--disable-gpu-vsync",
        "--disable-gpu-watchdog",
        "--disable-ipc-flooding-protection",
        "--disable-features=VizDisplayCompositor,ContextLostRecovery,MediaRouter,WebRtcHideLocalIpsWithMdns,WebRtcUseH264",
        "--log-level=3",
        "--silent",
        "--disable-logging",
    ]
    for option in gpu_options:
        options.add_argument(option)


def _add_user_agent_and_window_options(options: Options) -> None:
    """Add user agent and window size options."""
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")


def _add_automation_options(options: Options) -> None:
    """Add options to make automation less detectable."""
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")


def _add_profile_options(options: Options, profile_suffix: str) -> None:
    """Add Chrome profile options."""
    if profile_suffix:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        while not os.path.exists(os.path.join(project_root, "main.py")):
            project_root = os.path.dirname(project_root)
            if project_root == os.path.dirname(project_root):
                break

        profile_dir = os.path.join(
            project_root, "data", "browser_profiles", profile_suffix.replace(" ", "_")
        )
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")


def get_standard_chrome_options(
    headless=True, profile_suffix="default", enable_devtools=False, devtools_port=9222
):
    """Get standardized Chrome options that suppress common errors and warnings."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # PERFORMANCE OPTIMIZATION: Use eager page load strategy
    # Waits for DOM ready + initial JS, but not images/stylesheets/subframes
    # This makes scraping 30-50% faster while still reliable
    options.page_load_strategy = "eager"

    _add_debugging_options(options, enable_devtools, devtools_port)
    _add_stability_options(options)
    _add_gpu_suppression_options(options)
    _add_user_agent_and_window_options(options)
    _add_automation_options(options)
    _add_profile_options(options, profile_suffix)

    options.set_capability(
        "goog:loggingPrefs", {"browser": "OFF", "driver": "OFF", "performance": "OFF"}
    )

    return options


def clean_string(s):
    s = s.strip()
    if s.isupper() and len(s) > MIN_UPPERCASE_LENGTH:
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
    """Title case that handles apostrophes correctly."""
    titled = s.title()
    return re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), titled)


def clean_brand(brand):
    valid_name = re.sub(r"[^a-zA-Z0-9\s]", "", brand)
    valid_name = valid_name.replace(" ", "-")
    return valid_name.lower()


def create_filename(s):
    base = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    base = re.sub(r"\s+", " ", base).strip().replace(" ", "-").lower()

    if len(base) > MAX_FILENAME_LENGTH:
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:HASH_SUFFIX_LENGTH]
        base = base[:TRUNCATE_LENGTH] + "-" + hash_suffix
    return f"{base}.jpg"


def create_html(s):
    base = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    base = re.sub(r"\s+", " ", base).strip().replace(" ", "-").lower()

    if len(base) > MAX_FILENAME_LENGTH:
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:HASH_SUFFIX_LENGTH]
        base = base[:TRUNCATE_LENGTH] + "-" + hash_suffix
    return f"{base}.html"


def full_name(brand, product_name):
    brand_clean = brand.strip().upper()
    if product_name.lower().startswith(brand_clean.lower()):
        return product_name
    else:
        return f"{brand} {product_name}"
