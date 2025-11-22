"""
Browser utility for scrapers - provides default browser setup and management.
Scrapers can use this as a base and customize as needed.
"""

import os
import time
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

from src.utils.scraping.scraping import get_standard_chrome_options


@dataclass
class DevToolsConfig:
    """Configuration for Chrome DevTools."""

    enabled: bool = False
    port: int = 9222


class ScraperBrowser:
    """Base browser class for scrapers with common functionality."""

    def __init__(
        self,
        site_name,
        headless=True,
        profile_suffix=None,
        custom_options=None,
        devtools_config: DevToolsConfig | None = None,
    ):
        """
        Initialize browser for scraping.

        Args:
            site_name: Name of the site (used for profile directory)
            headless: Whether to run in headless mode
            profile_suffix: Optional suffix for profile directory
            custom_options: Additional Chrome options to add
            devtools_config: Configuration for Chrome DevTools
        """
        self.site_name = site_name
        self.headless = headless
        self.profile_suffix = profile_suffix or f"{int(time.time() * 1000)}"
        self.devtools_config = devtools_config or DevToolsConfig()

        # Get standard options
        options = get_standard_chrome_options(
            headless=headless,
            profile_suffix=self.profile_suffix,
            enable_devtools=self.devtools_config.enabled,
            devtools_port=self.devtools_config.port,
        )

        # Set Chrome binary location for CI environments
        is_ci = os.getenv("CI") == "true"
        if is_ci:
            # Try common Chrome binary locations
            chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome",
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

        # PERFORMANCE OPTIMIZATION: Add small implicit wait for dynamic content
        # Works with eager page load to catch late-loading elements
        # Explicit waits in workflow_executor still take precedence
        self.driver.implicitly_wait(2)  # 2 seconds for dynamic elements

        is_ci = os.getenv("CI") == "true"
        print(
            f"[WEB] [{site_name}] Browser initialized in {init_time:.2f}s "
            f"(headless={headless}, devtools={self.devtools_config.enabled}, CI={is_ci}, size=1920x1080, page_load=eager)"
        )

    def __getattr__(self, name):
        """Delegate WebDriver methods to the underlying driver."""
        return getattr(self.driver, name)

    def get(self, url):
        """Navigate to URL."""
        self.driver.get(url)

    def check_http_status(self) -> int | None:
        """
        Check the HTTP status code of the current page using JavaScript.

        Uses the Performance API to get the response status. Falls back to
        attempting a fetch request if Performance API is not available.

        Returns:
            HTTP status code (int) or None if unable to determine
        """
        try:
            # First try using Performance API (most reliable)
            script = """
            try {
                var entries = performance.getEntriesByType('navigation');
                if (entries.length > 0 && entries[0].responseStatus) {
                    return entries[0].responseStatus;
                }

                // Fallback: try to get status from document properties
                if (document.status) {
                    return document.status;
                }

                // Another fallback: check for error indicators in the page
                var bodyText = document.body ? document.body.textContent.toLowerCase() : '';
                var titleText = document.title ? document.title.toLowerCase() : '';

                if (bodyText.includes('404') || titleText.includes('404') ||
                    bodyText.includes('not found') || titleText.includes('not found')) {
                    return 404;
                }
                if (bodyText.includes('403') || titleText.includes('403') ||
                    bodyText.includes('forbidden') || bodyText.includes('access denied')) {
                    return 403;
                }
                if (bodyText.includes('500') || bodyText.includes('internal server error')) {
                    return 500;
                }

                return null;
            } catch (e) {
                return null;
            }
            """

            result = self.driver.execute_script(script)
            if result is not None:
                return int(result)

            # Second fallback: try a fetch request (may fail due to CORS)
            try:
                fetch_script = """
                try {
                    var xhr = new XMLHttpRequest();
                    xhr.open('HEAD', window.location.href, false);
                    xhr.send();
                    return xhr.status;
                } catch (e) {
                    return null;
                }
                """
                result = self.driver.execute_script(fetch_script)
                if result is not None:
                    return int(result)
            except Exception:
                pass

            return None

        except Exception as e:
            print(f"[WEB] [{self.site_name}] Failed to check HTTP status: {e}")
            return None

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
    devtools_config: DevToolsConfig | None = None,
):
    """
    Factory function to create a browser instance.

    Args:
        site_name: Name of the site
        headless: Whether to run headless
        profile_suffix: Optional profile suffix
        custom_options: Additional Chrome options
        devtools_config: Configuration for Chrome DevTools

    Returns:
        ScraperBrowser instance
    """
    return ScraperBrowser(
        site_name,
        headless,
        profile_suffix,
        custom_options,
        devtools_config,
    )
