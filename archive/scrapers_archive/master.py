import importlib.util
import os
import sys
import time
import warnings
from typing import Any

from src.scrapers.models.config import ScraperConfig

# DEPRECATION WARNING: This archived scraper system is deprecated
warnings.warn(
    "The archived scraper system (archive/scrapers_archive/) is deprecated and will be removed in a future version. "
    "Please migrate to the new modular scraper system using YAML configurations. "
    "See docs/SCRAPER_MIGRATION_GUIDE.md for migration instructions.",
    DeprecationWarning,
    stacklevel=2,
)

# Ensure project root is on sys.path before importing local packages to avoid shadowing
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import classification module (after ensuring project root is first on sys.path)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver

from src.utils.scraping.scraping import (
    get_standard_chrome_options,
)


class ScrapingProgressTracker:
    """Tracks and displays persistent progress bars for scraping operations."""

    def __init__(self, progress_callback=None, log_callback=None, metrics_callback=None):
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.current_site = ""
        self.total_sites = 0
        self.completed_sites = 0
        self.current_sku_index = 0
        self.total_skus_current_site = 0
        self.total_input_skus = 0
        self.total_processed_skus = 0
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.metrics_callback = metrics_callback

    def start_overall_progress(self, total_sites, total_input_skus):
        """Initialize overall progress tracking."""
        self.total_sites = total_sites
        self.total_input_skus = total_input_skus
        self.completed_sites = 0
        self.total_processed_skus = 0
        self.current_site = ""
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # Don't emit 0% here - start_site_progress will do it

    def start_site_progress(self, site_name, total_skus):
        """Start tracking progress for a specific site."""
        self.current_site = site_name
        self.total_skus_current_site = total_skus
        self.current_sku_index = 0
        self.last_update_time = time.time()

        # Reset GUI progress bar to 0% for new site
        if self.progress_callback:
            if hasattr(self.progress_callback, "emit"):
                self.progress_callback.emit(0)
            else:
                self.progress_callback(0)

    def update_sku_progress(self, sku_index, status_message="", scraped_count=0):
        """Update progress for current SKU within site."""
        self.current_sku_index = sku_index
        if scraped_count > 0:
            self.total_processed_skus += scraped_count
        else:
            # If no scraped_count provided, assume we're processing one SKU
            self.total_processed_skus = max(self.total_processed_skus, sku_index)

        # Update GUI progress bar if callback provided
        if self.progress_callback:
            # Calculate progress as: current SKU / total SKUs for current site
            site_progress = (
                min(
                    round((self.current_sku_index / self.total_skus_current_site) * 100),
                    100,
                )
                if self.total_skus_current_site > 0
                else 0
            )
            # Handle both PyQt signals (with emit method) and regular callbacks
            if hasattr(self.progress_callback, "emit"):
                self.progress_callback.emit(site_progress)
            else:
                self.progress_callback(site_progress)

        # Emit metrics update
        if self.metrics_callback:
            elapsed = time.time() - self.start_time
            elapsed_str = self._format_time(elapsed)
            processed_str = f"{self.total_processed_skus}/{self.total_input_skus}"
            current_op = (
                f"{self.current_site}: {status_message}" if status_message else self.current_site
            )
            eta_str = self._calculate_eta()

            metrics = {
                "elapsed": elapsed_str,
                "processed": processed_str,
                "current_op": current_op,
                "eta": eta_str,
            }

            if hasattr(self.metrics_callback, "emit"):
                self.metrics_callback.emit(metrics)
            else:
                self.metrics_callback(metrics)

        self._display_progress(status_message)

    def _format_time(self, seconds):
        """Format seconds into HH:MM:SS or MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _calculate_eta(self):
        """Calculate estimated time remaining"""
        elapsed = time.time() - self.start_time
        if elapsed > 10 and self.total_processed_skus > 0 and self.total_input_skus > 0:
            progress = self.total_processed_skus / self.total_input_skus
            if progress > 0:
                total_estimated = elapsed / progress
                remaining = total_estimated - elapsed
                if remaining < 3600:  # Less than 1 hour
                    return f"{remaining / 60:.1f}m"
                else:  # More than 1 hour
                    return f"{remaining / 3600:.1f}h"
        return "--"

    def complete_site(self):
        """Mark current site as completed."""
        self.completed_sites += 1

        # Update GUI progress bar if callback provided
        if self.progress_callback:
            # Set to 100% when site is completed
            if hasattr(self.progress_callback, "emit"):
                self.progress_callback.emit(100)
            else:
                self.progress_callback(100)

        self._display_progress("Site completed")

    def _display_progress(self, status_message=""):
        """Display the persistent progress bar."""
        # Suppress terminal output in GUI mode (when log_callback is not the print function)
        if self.log_callback is not print:
            return

        elapsed = time.time() - self.start_time

        # Calculate progress as: processed SKUs / total input SKUs
        if self.total_input_skus > 0:
            overall_progress = min(self.total_processed_skus / self.total_input_skus, 1.0)
        else:
            overall_progress = 0.0
        overall_percent = overall_progress * 100

        # Calculate site progress
        site_progress = 0.0
        if self.total_skus_current_site > 0:
            site_progress = min(self.current_sku_index / self.total_skus_current_site, 1.0)
        site_percent = site_progress * 100

        # Calculate ETA
        eta_str = ""
        if (
            elapsed > 10 and overall_progress > 0
        ):  # Only show ETA after 10 seconds and some progress
            remaining_progress = 1.0 - overall_progress
            if remaining_progress > 0:
                eta_seconds = (elapsed / overall_progress) * remaining_progress
                if eta_seconds < 3600:  # Less than 1 hour
                    eta_str = f" ETA: {eta_seconds / 60:.1f}m"
                else:  # More than 1 hour
                    eta_str = f" ETA: {eta_seconds / 3600:.1f}h"

        # Format elapsed time
        if elapsed < 60:
            elapsed_str = f"{elapsed:.0f}s"
        elif elapsed < 3600:
            elapsed_str = f"{elapsed / 60:.1f}m"
        else:
            elapsed_str = f"{elapsed / 3600:.1f}h"

        # Build progress bar
        bar_width = 20
        overall_filled = int(bar_width * overall_progress)
        site_filled = int(bar_width * site_progress)

        overall_bar = "█" * overall_filled + "░" * (bar_width - overall_filled)
        site_bar = "█" * site_filled + "░" * (bar_width - site_filled)

        # Display progress on new line instead of using carriage return
        progress_line = (
            f"🔄 Overall: [{overall_bar}] {overall_percent:.1f}% ({self.total_processed_skus}/{self.total_input_skus} SKUs){eta_str} | "
            f"Site: [{site_bar}] {site_percent:.1f}% ({self.current_sku_index}/{self.total_skus_current_site} SKUs) | "
            f"Time: {elapsed_str} | {self.current_site}"
        )

        if status_message:
            progress_line += f" | {status_message}"

        print(progress_line)


def get_browser(site, headless_settings=None, force_headless=False):
    """Create and retrieve browser instance per site with a custom profile directory."""
    # Excel scraper doesn't need a browser
    if site == "Excel":
        return None
    max_retries = 3
    browser = None
    for attempt in range(max_retries):
        try:
            timestamp = int(time.time() * 1000)  # millisecond timestamp for uniqueness
            unique_profile = f"{site.replace(' ', '_')}_{timestamp}"

            # Get headless preference for this site
            headless = force_headless or (
                headless_settings.get(site, True) if headless_settings else True
            )

            # Check if site has its own init_browser function
            try:
                # Try to import the module and check for init_browser
                module_name = site.lower().replace(" ", "_")
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    os.path.join(os.path.dirname(__file__), f"{module_name}.py"),
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    init_browser_func = getattr(module, "init_browser", None)
                    if init_browser_func:
                        browser = init_browser_func(
                            profile_suffix=unique_profile, headless=headless
                        )
                        browser.get("about:blank")
                        return browser
            except:
                pass  # Fall back to standard initialization

            # Standard browser initialization
            options = get_standard_chrome_options(headless=headless, profile_suffix=unique_profile)
            from selenium.webdriver.chrome.service import Service as ChromeService

            service = ChromeService(log_path=os.devnull)
            browser = webdriver.Chrome(service=service, options=options)
            browser.get("about:blank")
            return browser
        except Exception as e:
            error_msg = str(e)
            if "user data directory is already in use" in error_msg:
                pass  # Continue with retry logic for this specific error
            elif attempt < max_retries - 1:
                time.sleep(1 + attempt)
                try:
                    if browser is not None:
                        browser.quit()
                except:
                    pass
            else:
                return None
    return None


class ModularScraper:
    """Scraper that uses WorkflowExecutor and YAML configurations."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: ScraperConfig | None = None
        self._load_config()
        self._logged_in = False

    def _load_config(self):
        """Load the YAML configuration."""
        try:
            from src.scrapers.parser.yaml_parser import ScraperConfigParser

            parser = ScraperConfigParser()
            self.config = parser.load_from_file(self.config_path)
            assert self.config is not None
        except Exception as e:
            raise Exception(f"Failed to load config from {self.config_path}: {e}")

    def _get_credentials(self) -> dict[str, str] | None:
        """
        Get login credentials from environment variables.

        Returns:
            Dict with 'username' and 'password' keys, or None if not available
        """
        assert self.config is not None
        scraper_name = self.config.name.lower().replace(" ", "_")
        username_key = f"{scraper_name}_username"
        password_key = f"{scraper_name}_password"

        username = os.getenv(username_key)
        password = os.getenv(password_key)

        if username and password:
            return {"username": username, "password": password}
        return None

    def _perform_login(self, executor: Any) -> bool:
        """
        Perform login using the configured login workflow.

        Args:
            executor: WorkflowExecutor instance with initialized browser

        Returns:
            True if login successful, False otherwise
        """
        assert self.config is not None
        if not self.config.login:
            return True  # No login required

        credentials = self._get_credentials()
        if not credentials:
            raise Exception(
                f"Login required for {self.config.name} but credentials not found in environment variables"
            )

        try:
            # Create login workflow step
            login_params = {
                "username": credentials["username"],
                "password": credentials["password"],
                "url": self.config.login.url,
                "username_field": self.config.login.username_field,
                "password_field": self.config.login.password_field,
                "submit_button": self.config.login.submit_button,
                "success_indicator": self.config.login.success_indicator,
            }

            # Execute login action
            executor._action_login(login_params)
            self._logged_in = True
            return True

        except Exception as e:
            self._logged_in = False
            raise Exception(f"Login failed for {self.config.name}: {e}")

    def scrape_products(self, skus: list, progress_callback=None, headless=True):
        """
        Scrape products for the given SKUs using the workflow.

        Args:
            skus: List of SKU strings to scrape
            progress_callback: Optional callback for progress updates
            headless: Whether to run browser in headless mode

        Returns:
            List of product dictionaries
        """
        if not self.config:
            return []

        from src.scrapers.executor.workflow_executor import WorkflowExecutor

        products = []
        executor = None

        try:
            # Create base config for login (without SKU placeholders)
            base_config = self.config

            # Initialize executor for login and scraping
            executor = WorkflowExecutor(base_config, headless=headless)

            # Perform login if required
            if self.config.login and not self._logged_in:
                if progress_callback:
                    progress_callback(0, "Performing login...")
                self._perform_login(executor)

            for i, sku in enumerate(skus):
                if progress_callback:
                    progress_callback(i, f"Processing SKU: {sku}")

                try:
                    # Create a copy of config with SKU-specific URL
                    # Assume the workflow can be parameterized with {sku}
                    config_dict = self.config.model_dump()
                    config_dict_copy = config_dict.copy()

                    # Replace {sku} placeholders in URLs and selectors
                    def replace_sku_placeholders(obj):
                        if isinstance(obj, str):
                            return obj.replace("{sku}", sku)
                        elif isinstance(obj, dict):
                            return {k: replace_sku_placeholders(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [replace_sku_placeholders(item) for item in obj]
                        else:
                            return obj

                    config_dict_copy = replace_sku_placeholders(config_dict_copy)

                    # Reconstruct config
                    from src.scrapers.models.config import ScraperConfig

                    sku_config = ScraperConfig(**config_dict_copy)  # type: ignore

                    # Update executor config for this SKU
                    executor.config = sku_config
                    executor.results = {}  # Clear previous results

                    # Execute workflow steps (reuse the same browser session)
                    result = executor.execute_steps(sku_config.workflows)

                    if result["success"]:
                        # Transform workflow results to product format
                        product = self._transform_workflow_results(result["results"], sku)
                        if product:
                            products.append(product)
                    else:
                        print(f"Workflow failed for SKU {sku}")

                except Exception as e:
                    print(f"Error scraping SKU {sku}: {e}")
                    continue

        except Exception as e:
            print(f"Error during scraping session: {e}")
        finally:
            # Clean up browser
            if executor and executor.browser:
                executor.browser.quit()

        if progress_callback:
            progress_callback(len(skus), "Completed")

        return products

    def _transform_workflow_results(self, workflow_results: dict, sku: str):
        """Transform workflow execution results to product dictionary format."""
        product: dict[str, Any] = {"SKU": sku}

        # Map workflow results to standard product fields
        field_mapping = {
            "product_name": "Name",
            "name": "Name",
            "price": "Price",
            "weight": "Weight",
            "brand": "Brand",
            "image_urls": "Image URLs",
            "images": "Image URLs",
        }

        for workflow_field, product_field in field_mapping.items():
            if workflow_field in workflow_results:
                value = workflow_results[workflow_field]
                product[product_field] = value

        # Ensure required fields exist with proper types
        if "Name" not in product:
            product["Name"] = ""
        if "Price" not in product:
            product["Price"] = ""
        if "Weight" not in product:
            product["Weight"] = ""
        if "Image URLs" not in product:
            product["Image URLs"] = []
        elif not isinstance(product["Image URLs"], list):
            product["Image URLs"] = [product["Image URLs"]]

        return product


def discover_scrapers():
    """Dynamically discover and load scraper modules from the scrapers directory."""
    scrapers_dir = os.path.join(os.path.dirname(__file__))
    scraping_options = {}
    headless_settings = {}  # Store headless preference per site

    # Mapping from subdirectory names to display names
    name_mapping = {
        "amazon": "Amazon",
        "bradley": "Bradley Caldwell",
        "central_pet": "Central Pet",
        "coastal": "Coastal Pet",
        "mazuri": "Mazuri",
        "nassau": "Nassau",
        "orgill": "Orgill",
        "petfoodex": "Pet Food Experts",
        "phillips": "Phillips",
    }

    # Find all subdirectories in scrapers directory (excluding archive and __pycache__)
    subdirs = []
    for item in os.listdir(scrapers_dir):
        item_path = os.path.join(scrapers_dir, item)
        if os.path.isdir(item_path) and item not in ["archive", "__pycache__", "output"]:
            subdirs.append(item)

    for subdir in subdirs:
        # Look for main.py in src/ subdirectory
        main_py_path = os.path.join(scrapers_dir, subdir, "src", "main.py")
        if not os.path.exists(main_py_path):
            continue

        module_name = f"{subdir}_scraper"

        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, main_py_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for scrape_products function
                scrape_func = getattr(module, "scrape_products", None)

                if scrape_func and callable(scrape_func):
                    # Get display name
                    display_name = name_mapping.get(subdir, subdir.replace("_", " ").title())

                    scraping_options[display_name] = scrape_func

                    # Check for headless preference (default to True if not specified)
                    headless_pref = getattr(module, "HEADLESS", True)
                    headless_settings[display_name] = headless_pref

        except Exception:
            pass

    # Discover YAML-based scraper configurations
    config_dir = os.path.join(PROJECT_ROOT, "src", "scrapers", "config")
    if os.path.exists(config_dir):
        for file_name in os.listdir(config_dir):
            if file_name.endswith((".yaml", ".yml")) and file_name != "sample_config.yaml":
                config_path = os.path.join(config_dir, file_name)
                scraper_name = (
                    file_name.replace(".yaml", "").replace(".yml", "").replace("_", " ").title()
                )

                try:
                    # Create a ModularScraper instance
                    modular_scraper = ModularScraper(config_path)

                    # Create a wrapper function that matches the expected interface
                    def create_scraper_func(scraper_instance):
                        def scrape_func(skus, progress_callback=None, headless=True):
                            return scraper_instance.scrape_products(
                                skus, progress_callback, headless
                            )

                        return scrape_func

                    scraping_options[scraper_name] = create_scraper_func(modular_scraper)
                    headless_settings[scraper_name] = (
                        True  # Default to headless for modular scrapers
                    )

                except Exception as e:
                    print(f"Failed to load modular scraper from {config_path}: {e}")

    return scraping_options, headless_settings
