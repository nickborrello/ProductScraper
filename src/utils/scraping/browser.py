"""
Browser utility for scrapers - provides default browser setup and management.
Scrapers can use this as a base and customize as needed.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from src.utils.scraping.scraping import get_standard_chrome_options


class ScraperBrowser:
    """Base browser class for scrapers with common functionality."""

    def __init__(self, site_name, headless=True, profile_suffix=None, custom_options=None):
        """
        Initialize browser for scraping.

        Args:
            site_name: Name of the site (used for profile directory)
            headless: Whether to run in headless mode
            profile_suffix: Optional suffix for profile directory
            custom_options: Additional Chrome options to add
        """
        self.site_name = site_name
        self.headless = headless
        self.profile_suffix = profile_suffix or f"{int(time.time() * 1000)}"

        # Get standard options
        options = get_standard_chrome_options(headless=headless, profile_suffix=self.profile_suffix)

        # Add custom options if provided
        if custom_options:
            for option in custom_options:
                options.add_argument(option)

        # Create service with suppressed logs
        service = ChromeService(log_path=os.devnull)
        
        # Set environment variables to suppress GPU errors
        os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # For Linux systems
        os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'    # Force software rendering

        # Initialize browser
        self.driver = webdriver.Chrome(service=service, options=options)
        print(f"🌐 [{site_name}] Browser initialized (headless={headless})")

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
                print(f"🔒 [{self.site_name}] Browser closed")
            except Exception as e:
                print(f"⚠️ [{self.site_name}] Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()


def create_browser(site_name, headless=True, profile_suffix=None, custom_options=None):
    """
    Factory function to create a browser instance.

    Args:
        site_name: Name of the site
        headless: Whether to run headless
        profile_suffix: Optional profile suffix
        custom_options: Additional Chrome options

    Returns:
        ScraperBrowser instance
    """
    return ScraperBrowser(site_name, headless, profile_suffix, custom_options)