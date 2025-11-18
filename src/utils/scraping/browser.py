"""
Browser utility for scrapers - provides default browser setup and management.
Scrapers can use this as a base and customize as needed.
"""

import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService

from src.utils.scraping.scraping import get_standard_chrome_options


class ScraperBrowser:
    """Base browser class for scrapers with common functionality."""

    def __init__(
        self,
        site_name,
        headless=True,
        profile_suffix=None,
        custom_options=None,
        enable_devtools=False,
        devtools_port=9222,
    ):
        """
        Initialize browser for scraping.

        Args:
            site_name: Name of the site (used for profile directory)
            headless: Whether to run in headless mode
            profile_suffix: Optional suffix for profile directory
            custom_options: Additional Chrome options to add
            enable_devtools: Whether to enable Chrome DevTools remote debugging
            devtools_port: Port for DevTools remote debugging (default: 9222)
        """
        self.site_name = site_name
        self.headless = headless
        self.profile_suffix = profile_suffix or f"{int(time.time() * 1000)}"
        self.enable_devtools = enable_devtools
        self.devtools_port = devtools_port

        # Get standard options
        options = get_standard_chrome_options(
            headless=headless,
            profile_suffix=self.profile_suffix,
            enable_devtools=enable_devtools,
            devtools_port=devtools_port,
        )

        # Set Chrome binary location for CI environments
        import os
        is_ci = os.getenv('CI') == 'true'
        if is_ci:
            # Try common Chrome binary locations
            chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome"
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    break

        # Add custom options if provided
        if custom_options:
            for option in custom_options:
                options.add_argument(option)

        # Create service with suppressed logs
        service = ChromeService(log_path=os.devnull)

        # Set environment variables to suppress GPU errors
        os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
        os.environ["QT_QPA_PLATFORM"] = "offscreen"  # For Linux systems
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"  # Force software rendering

        # Initialize browser
        start_time = time.time()

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            init_time = time.time() - start_time
        except Exception as e:
            init_time = time.time() - start_time
            print(f"[WEB] [{site_name}] Browser initialization failed after {init_time:.2f}s: {e}")
            raise

        # Ensure consistent window size for responsive design consistency
        try:
            self.driver.set_window_size(1920, 1080)
            self.driver.maximize_window()
        except Exception as e:
            print(f"[WEB] [{site_name}] Failed to set window size: {e}")

        is_ci = os.getenv('CI') == 'true'
        print(
            f"[WEB] [{site_name}] Browser initialized in {init_time:.2f}s (headless={headless}, devtools={enable_devtools}, CI={is_ci}, size=1920x1080)"
        )

    def __getattr__(self, name):
        """Delegate WebDriver methods to the underlying driver."""
        return getattr(self.driver, name)

    def get(self, url):
        """Navigate to URL."""
        self.driver.get(url)

    def quit(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
                print(f"[LOCK] [{self.site_name}] Browser closed")
            except Exception as e:
                print(f"[WARN] [{self.site_name}] Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()


def create_browser(
    site_name,
    headless=True,
    profile_suffix=None,
    custom_options=None,
    enable_devtools=False,
    devtools_port=9222,
):
    """
    Factory function to create a browser instance.

    Args:
        site_name: Name of the site
        headless: Whether to run headless
        profile_suffix: Optional profile suffix
        custom_options: Additional Chrome options
        enable_devtools: Whether to enable Chrome DevTools remote debugging
        devtools_port: Port for DevTools remote debugging (default: 9222)

    Returns:
        ScraperBrowser instance
    """
    return ScraperBrowser(
        site_name,
        headless,
        profile_suffix,
        custom_options,
        enable_devtools,
        devtools_port,
    )
