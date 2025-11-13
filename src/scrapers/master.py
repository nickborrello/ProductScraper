import os
import sys
import time
import pandas as pd
from collections import defaultdict
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import importlib.util
import glob
import subprocess

# Ensure project root is on sys.path before importing local packages to avoid shadowing
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import classification module (after ensuring project root is first on sys.path)
from src.core.classification.classifier import (
    classify_products_batch,
    classify_single_product,
)
from src.ui.product_editor import product_editor_interactive, edit_products_in_batch
from src.ui.product_cross_sell_ui import assign_cross_sells_batch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.scraping.scraping import (
    create_fileName,
    create_html,
    clean_brand,
    full_name,
    get_standard_chrome_options,
)
from src.utils.images.processing import download_image
from src.utils.files.excel import convert_xlsx_to_xls_with_excel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class ScrapingProgressTracker:
    """Tracks and displays persistent progress bars for scraping operations."""

    def __init__(self, progress_callback=None, log_callback=None):
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
                    int(
                        round(
                            (self.current_sku_index / self.total_skus_current_site)
                            * 100
                        )
                    ),
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

        self._display_progress(status_message)

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
            overall_progress = min(
                self.total_processed_skus / self.total_input_skus, 1.0
            )
        else:
            overall_progress = 0.0
        overall_percent = overall_progress * 100

        # Calculate site progress
        site_progress = 0.0
        if self.total_skus_current_site > 0:
            site_progress = min(
                self.current_sku_index / self.total_skus_current_site, 1.0
            )
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
                    eta_str = f" ETA: {eta_seconds/60:.1f}m"
                else:  # More than 1 hour
                    eta_str = f" ETA: {eta_seconds/3600:.1f}h"

        # Format elapsed time
        if elapsed < 60:
            elapsed_str = f"{elapsed:.0f}s"
        elif elapsed < 3600:
            elapsed_str = f"{elapsed/60:.1f}m"
        else:
            elapsed_str = f"{elapsed/3600:.1f}h"

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


def get_browser(site, headless_settings=None):
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
            headless = headless_settings.get(site, True) if headless_settings else True

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
            options = get_standard_chrome_options(
                headless=headless, profile_suffix=unique_profile
            )
            from selenium.webdriver.chrome.service import Service as ChromeService

            service = ChromeService(log_path=os.devnull)
            browser = webdriver.Chrome(service=service, options=options)
            browser.get("about:blank")
            return browser
        except Exception as e:
            error_msg = str(e)
            if "user data directory is already in use" in error_msg:
                pass  # Continue with retry logic for this specific error
            else:
                if attempt < max_retries - 1:
                    time.sleep(1 + attempt)
                    try:
                        if browser is not None:
                            browser.quit()
                    except:
                        pass
                else:
                    return None
    return None


def discover_scrapers():
    """Dynamically discover and load scraper modules from the scrapers directory."""
    scrapers_dir = os.path.join(os.path.dirname(__file__))
    scraping_options = {}
    headless_settings = {}  # Store headless preference per site

    # Mapping from function names to display names
    name_mapping = {
        "scrape_amazon": "Amazon",
        "scrape_bradley_caldwell": "Bradley Caldwell",
        "scrape_central": "Central Pet",
        "scrape_coastal_pet": "Coastal Pet",
        "scrape_generic": "Generic Search",
        "scrape_mazuri": "Mazuri",
        "scrape_nassau_candy": "Nassau",
        "scrape_orgill": "Orgill",
        "scrape_petfood_experts": "Pet Food Experts",
        "scrape_phillips": "Phillips",
    }

    # Find all .py files in scrapers directory, excluding __init__.py and archived files
    scraper_files = glob.glob(os.path.join(scrapers_dir, "*.py"))
    scraper_files = [f for f in scraper_files if not f.endswith("__init__.py")]

    # Exclude archived scrapers
    archive_dir = os.path.join(scrapers_dir, "archive")
    if os.path.exists(archive_dir):
        archived_files = glob.glob(os.path.join(archive_dir, "*.py"))
        archived_names = [os.path.basename(f) for f in archived_files]
        scraper_files = [
            f for f in scraper_files if os.path.basename(f) not in archived_names
        ]

    for scraper_file in scraper_files:
        module_name = os.path.basename(scraper_file)[:-3]  # Remove .py extension

        module = None  # Initialize module to avoid unbound variable
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, scraper_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # Find the scrape function - only if it's defined in this module
            scrape_func = None
            if module is not None:  # Only proceed if module was successfully loaded
                for attr_name in dir(module):
                    if attr_name.startswith("scrape_"):
                        func = getattr(module, attr_name)
                        # Check if the function is defined in this module (not imported)
                        if (
                            hasattr(func, "__module__")
                            and func.__module__ == module_name
                        ):
                            scrape_func = func
                            break

            if scrape_func and callable(scrape_func):
                # Get display name
                func_name = scrape_func.__name__
                display_name = name_mapping.get(
                    func_name,
                    func_name.replace("scrape_", "").replace("_", " ").title(),
                )

                scraping_options[display_name] = scrape_func

                # Check for headless preference (default to True if not specified)
                headless_pref = getattr(module, "HEADLESS", True)
                headless_settings[display_name] = headless_pref

            else:
                pass

        except Exception as e:
            pass

    return scraping_options, headless_settings


class ProductScraper:
    def __init__(
        self,
        file_path,
        interactive=True,
        selected_sites=None,
        log_callback=None,
        progress_callback=None,
        editor_callback=None,
    ):
        self.file_path = file_path
        self.interactive = interactive
        self.selected_sites = selected_sites
        self.log_callback = log_callback or print
        self.progress_callback = progress_callback
        self.editor_callback = (
            editor_callback  # Callback to request editor on main thread
        )

        # Dynamically discover and load scraper modules
        self.scraping_options, self.headless_settings = discover_scrapers()

        self.site_locks = defaultdict(lambda: None)
        self.all_found_products = {}  # SKU -> list of product results

        # Initialize progress tracker
        self.progress_tracker = ScrapingProgressTracker(progress_callback, log_callback)

    def run_granular_field_tests(self):
        """Run granular field-level tests for all scrapers to identify specific failures."""
        try:
            import sys
            import os

            test_dir = os.path.join(PROJECT_ROOT, "test")
            if test_dir not in sys.path:
                sys.path.insert(0, test_dir)

            from tests.unit.test_scraper_fields import run_granular_tests

            print("\n🔬 Running Granular Scraper Field Tests...")
            results = run_granular_tests()
            return results
        except ImportError as e:
            print(f"❌ Could not import granular testing module: {e}")
            print("💡 Make sure test_scraper_fields.py exists in the test directory")
            return None
        except Exception as e:
            print(f"❌ Error running granular tests: {e}")
            return None

    def run_scraper_tests(self, run_integration_tests=False):
        """Run pytest on scraper tests and return list of passing scrapers.

        Args:
            run_integration_tests: If True, also run integration tests that make real network calls

        Returns:
            dict: Mapping of site names to scraper functions for scrapers that passed tests
        """
        print("\n" + "=" * 60)
        print("🧪 RUNNING SCRAPER TESTS")
        if run_integration_tests:
            print("   📡 Including integration tests (real network calls)")
        else:
            print("   🔧 Running basic validation only")
        print("=" * 60)

        test_file = os.path.join(PROJECT_ROOT, "test", "test_scrapers.py")

        if not os.path.exists(test_file):
            print("❌ Test file not found, skipping tests")
            # Ensure scraping_options is initialized
            if not hasattr(self, "scraping_options"):
                self.scraping_options, self.headless_settings = discover_scrapers()
            return self.scraping_options

        try:
            # Set environment variable for integration tests
            env = os.environ.copy()
            if run_integration_tests:
                env["RUN_INTEGRATION_TESTS"] = "true"

            # Run pytest on the test file
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    test_file,
                    "-v",
                    "--tb=short",
                    "--disable-warnings",
                ],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                env=env,
            )

            print("Test output:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)

            if result.returncode == 0:
                print("✅ All scraper tests passed!")
                # Ensure scraping_options is initialized
                if not hasattr(self, "scraping_options"):
                    self.scraping_options, self.headless_settings = discover_scrapers()
                return self.scraping_options
            else:
                print("❌ Some scraper tests failed!")

                # Parse the test output to find which scrapers failed
                failed_scrapers = self._parse_test_failures(
                    result.stdout + result.stderr
                )

                if failed_scrapers:
                    print(f"🚫 Skipping failed scrapers: {', '.join(failed_scrapers)}")

                    # Ensure scraping_options is initialized
                    if not hasattr(self, "scraping_options"):
                        self.scraping_options, self.headless_settings = (
                            discover_scrapers()
                        )

                    # Filter out failed scrapers
                    passing_options = {}
                    passing_headless = {}

                    for site, func in self.scraping_options.items():
                        # Map site name back to module name for comparison
                        module_name = site.lower().replace(" ", "_")
                        if module_name not in failed_scrapers:
                            passing_options[site] = func
                            passing_headless[site] = self.headless_settings.get(
                                site, True
                            )

                    self.scraping_options = passing_options
                    self.headless_settings = passing_headless

                    print(
                        f"✅ {len(passing_options)} scrapers passed tests and will be available"
                    )

                    if not passing_options:
                        print("❌ No scrapers passed tests, cannot continue")
                        return {}

                    return passing_options
                else:
                    print(
                        "⚠️ Could not determine which scrapers failed, proceeding with all"
                    )
                    # Ensure scraping_options is initialized
                    if not hasattr(self, "scraping_options"):
                        self.scraping_options, self.headless_settings = (
                            discover_scrapers()
                        )
                    return self.scraping_options

        except Exception as e:
            print(f"❌ Error running tests: {e}")
            print("⚠️ Proceeding without test validation")
            # Ensure scraping_options is initialized
            if not hasattr(self, "scraping_options"):
                self.scraping_options, self.headless_settings = discover_scrapers()
            return self.scraping_options

    def _parse_test_failures(self, test_output):
        """Parse pytest output to find which scraper modules failed tests.

        Args:
            test_output: Combined stdout and stderr from pytest

        Returns:
            set: Set of module names that failed tests
        """
        failed_modules = set()

        lines = test_output.split("\n")
        for line in lines:
            line = line.strip()
            # Look for patterns like "test_scraper_functions_exist[module_name]"
            if "FAILED" in line and "[" in line and "]" in line:
                # Extract the module name from the test parametrization
                start = line.find("[") + 1
                end = line.find("]")
                if start > 0 and end > start:
                    module_name = line[start:end]
                    failed_modules.add(module_name)

            # Also look for module names in error messages
            elif "ERROR" in line or "FAILED" in line:
                for module in [
                    "orgill",
                    "bradley_caldwell",
                    "central_pet",
                    "coastal",
                    "mazuri",
                    "nassau_candy",
                    "petfoodex",
                    "phillips",
                ]:
                    if module in line.lower():
                        failed_modules.add(module)

        return failed_modules

    def run(self):
        try:
            self.scrape()
        except KeyboardInterrupt:
            pass

    def get_scraping_order(self, completed_sites=None):
        """Ask the user for the websites to scrape, showing completed status."""
        if completed_sites is None:
            completed_sites = set()

        print("\n" + "=" * 60)
        print("🛒 Available scraping options:")
        print("=" * 60)
        sites_list = list(self.scraping_options.keys())
        for idx, site in enumerate(sites_list, 1):
            status = "✅ COMPLETED" if site in completed_sites else "⏳ PENDING"
            print(f"{idx:2d}. {site:<20} [{status}]")

        # Add "Scrape All" option
        scrape_all_idx = len(sites_list) + 1
        print(f"{scrape_all_idx:2d}. 🔄 Scrape All Sites (automatic)")

        if completed_sites:
            pass
        print("\n📝 Enter the numbers of websites to scrape (comma-separated)")
        print("💡 Example: 1,3,5 or just 2 for single site")
        print("🚪 Type 'done' to finish scraping and process results")
        while True:
            if not self.interactive:
                # In non-interactive mode, scrape all remaining sites
                all_sites = list(self.scraping_options.keys())
                pending_sites = [
                    site for site in all_sites if site not in completed_sites
                ]
                if pending_sites:
                    return pending_sites
                else:
                    return []
            order_input = input("\nYour selection: ").strip().lower()
            if order_input == "done":
                return None  # Signal to finish scraping
            try:
                if "," in order_input:
                    order_indices = [
                        int(x.strip()) - 1
                        for x in order_input.split(",")
                        if x.strip().isdigit()
                    ]
                else:
                    order_indices = (
                        [int(order_input) - 1] if order_input.isdigit() else []
                    )

                # Check if "Scrape All" was selected
                if scrape_all_idx - 1 in order_indices:
                    # Return all sites that aren't completed yet
                    all_sites = list(self.scraping_options.keys())
                    pending_sites = [
                        site for site in all_sites if site not in completed_sites
                    ]
                    if pending_sites:
                        return pending_sites
                    else:
                        return []

                selected_sites = [
                    sites_list[i] for i in order_indices if 0 <= i < len(sites_list)
                ]
                if not selected_sites:
                    continue
                already_completed = [
                    site for site in selected_sites if site in completed_sites
                ]
                if already_completed:
                    confirm = input("Continue anyway? (y/n): ")
                    if confirm != "y":
                        continue
                return selected_sites
            except ValueError:
                continue

    def cleanup_chrome_processes(self):
        """Kill any lingering Chrome processes that might cause conflicts."""
        try:
            import psutil
            import subprocess

            killed_count = 0
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if "chrome" in proc.info["name"].lower():
                        proc.kill()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed_count > 0:
                import time

                time.sleep(2)  # Give time for cleanup
            else:
                pass

        except ImportError:
            # psutil not available, try taskkill on Windows
            try:
                import subprocess
                import os

                if os.name == "nt":  # Windows
                    subprocess.run(
                        ["taskkill", "/f", "/im", "chrome.exe"],
                        capture_output=True,
                        text=True,
                    )
            except:
                pass
        except Exception as e:
            pass

    def load_existing_skus(self, site):
        try:
            # Use combined output file instead of site-specific files
            from pathlib import Path

            output_dir = Path(PROJECT_ROOT) / "data" / "spreadsheets"
            combined_file_path = output_dir / "products.xlsx"

            if os.path.exists(combined_file_path):
                try:
                    existing_df = pd.read_excel(combined_file_path, dtype={"SKU": str})
                    existing_count = len(existing_df)
                    return set(existing_df["SKU"].astype(str).tolist())
                except Exception as e:
                    return set()
            else:
                return set()
        except Exception as e:
            return set()

    def get_existing_skus_from_database(self):
        """Query the SQLite database directly for existing SKUs."""
        try:
            # Import database path from classification module
            from src.ui.product_classify_ui import DB_PATH
            import sqlite3

            if not DB_PATH.exists():
                print("ℹ️ Database file does not exist yet")
                return set()

            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.execute("SELECT SKU FROM products WHERE SKU IS NOT NULL")
                existing_skus = {
                    str(row[0]).strip() for row in cursor.fetchall() if row[0]
                }
                print(f"📊 Found {len(existing_skus)} existing products in database")
                return existing_skus
            finally:
                conn.close()
        except Exception as e:
            print(f"⚠️ Error querying database: {e}")
            return set()

    def download_images(self, brand, file_name, image_urls, site):
        """Download images for a product."""
        # Organize images by brand only (no longer by site)
        subdir = clean_brand(brand)
        for img_idx, img_url in enumerate(image_urls):
            if not isinstance(img_url, str) or not img_url:
                continue
            try:
                download_image(img_url, subdir, file_name, img_idx)
            except Exception as e:
                pass

    def cleanup_temp_profiles(self):
        """Clean up temporary browser profile directories created during this session."""
        try:
            import glob
            import shutil

            # Remove any browser_profiles with timestamp pattern (no thread ID)
            profile_pattern = os.path.join("data/browser_profiles", "*_*")
            temp_profiles = glob.glob(profile_pattern)
            cleaned_count = 0
            for profile_dir in temp_profiles:
                try:
                    if os.path.exists(profile_dir):
                        shutil.rmtree(profile_dir)
                        cleaned_count += 1
                except Exception:
                    pass  # Ignore cleanup errors
            if cleaned_count > 0:
                pass
        except Exception:
            pass  # Ignore any cleanup errors

    def cleanup_old_files(self):
        """Clean up old temporary files and directories."""
        try:
            import glob
            import shutil
            import os
            from datetime import datetime, timedelta

            cleanup_count = 0

            # Clean up old temporary browser profiles (older than 1 hour)
            try:
                profile_dirs = glob.glob(
                    "data/browser_profiles/*_*_*"
                )  # Match the timestamp pattern
                one_hour_ago = datetime.now().timestamp() * 1000 - (
                    60 * 60 * 1000
                )  # 1 hour ago in milliseconds

                for profile_dir in profile_dirs:
                    try:
                        # Extract timestamp from directory name
                        parts = os.path.basename(profile_dir).split("_")
                        if len(parts) >= 3 and parts[-1].isdigit():
                            timestamp = int(parts[-1])
                            if timestamp < one_hour_ago:
                                shutil.rmtree(profile_dir)
                                cleanup_count += 1
                    except (ValueError, IndexError):
                        pass  # Skip directories that don't match expected pattern

            except Exception:
                pass

            # Clean up old selenium profiles with timestamp patterns
            try:
                selenium_dirs = glob.glob("data/browser_profiles/*_*_*")
                for selenium_dir in selenium_dirs:
                    try:
                        # Check if directory is old (not accessed in last hour)
                        stat = os.stat(selenium_dir)
                        if datetime.now().timestamp() - stat.st_atime > 3600:  # 1 hour
                            shutil.rmtree(selenium_dir)
                            cleanup_count += 1
                    except Exception:
                        pass
            except Exception:
                pass

            # Clean up any temporary xlsx files (backup files, temp files, etc.)
            try:
                temp_patterns = ["*.tmp", "*~*.xlsx", "*.bak", ".~lock.*"]
                for pattern in temp_patterns:
                    for temp_file in glob.glob(pattern):
                        try:
                            os.remove(temp_file)
                            cleanup_count += 1
                        except Exception:
                            pass
            except Exception:
                pass

            if cleanup_count > 0:
                pass
            else:
                pass

        except Exception as e:
            pass

    def save_incremental_results(self, new_row, source_site):
        # Save to data/spreadsheets/ instead of src/scrapers/output/
        from pathlib import Path

        output_dir = Path(PROJECT_ROOT) / "data" / "spreadsheets"
        output_dir.mkdir(parents=True, exist_ok=True)
        # Use single combined output file instead of site-specific files
        site_file_path = output_dir / "products.xlsx"
        try:
            # Map new user-friendly column names to old ShopSite column names for Excel output
            shopsite_row = new_row.copy()

            # Map new names to old ShopSite names
            if "Brand" in shopsite_row:
                shopsite_row["Product Field 16"] = shopsite_row.pop("Brand")
            if "Category" in shopsite_row:
                shopsite_row["Product Field 24"] = shopsite_row.pop("Category")
            if "Product_Type" in shopsite_row:
                shopsite_row["Product Field 25"] = shopsite_row.pop("Product_Type")
            if "Special_Order" in shopsite_row:
                shopsite_row["Product Field 11"] = shopsite_row.pop("Special_Order")
            if "Product_Cross_Sell" in shopsite_row:
                shopsite_row["Product Field 32"] = shopsite_row.pop(
                    "Product_Cross_Sell"
                )

            # Use the mapped row for all subsequent operations
            new_row = shopsite_row

            # Ensure SKU is always text (string)
            if "SKU" in new_row:
                new_row["SKU"] = str(new_row["SKU"])
            # Ensure Weight is always a number (string of digits, or empty string)
            if "Weight" in new_row:
                import re, math

                weight_val = str(new_row["Weight"])
                match = re.search(r"(\d+(?:\.\d+)?)", weight_val)
                if match:
                    num = float(match.group(1))
                    rounded = math.ceil(num * 100) / 100
                    new_row["Weight"] = f"{rounded:.2f}"
                else:
                    new_row["Weight"] = ""
            # Ensure Price is a float with two decimals (no currency symbol)
            if "Price" in new_row:
                price_val = (
                    str(new_row["Price"]).replace("$", "").replace("USD", "").strip()
                )
                import re

                match = re.search(r"(\d+(?:\.\d+)?)", price_val)
                if match:
                    price_num = float(match.group(1))
                    new_row["Price"] = f"{price_num:.2f}"
                else:
                    new_row["Price"] = ""
            if os.path.exists(site_file_path):
                site_df = pd.read_excel(site_file_path, dtype={"SKU": str})
            else:
                # Only add More Information Image columns if present in new_row
                more_info_image_cols = [
                    key
                    for key in new_row.keys()
                    if key.startswith("More Information Image")
                ]
                columns = (
                    [
                        "SKU",
                        "Name",
                        "Product Description",
                        "Price",
                        "Weight",
                        "Product Field 16",
                        "File name",
                        "Graphic",
                        "More Information Graphic",
                        "Product Field 1",
                        "Product Field 11",
                    ]
                    + more_info_image_cols
                    + [
                        "Product Field 24",
                        "Product Field 25",
                        "Product On Pages",
                        "Product Field 32",
                    ]
                )
                site_df = pd.DataFrame(columns=columns)
            # No deduplication: always add new row
            site_df = pd.concat([site_df, pd.DataFrame([new_row])], ignore_index=True)
            site_df.to_excel(site_file_path, index=False, engine="openpyxl")
            image_count = 0
            for i in range(1, 6):
                if (
                    new_row.get(f"More Information Image {i}")
                    and new_row.get(f"More Information Image {i}") != "none"
                ):
                    image_count += 1
        except Exception as e:
            print(f"❌ Error saving to Excel file {site_file_path}: {e}")

    def convert_input_file_to_new_format(self, input_path):
        """Convert legacy input file formats to current format (only for column renaming, no file modification)."""
        try:
            df = pd.read_excel(input_path, dtype=str)

            # Only do column renaming for legacy formats - don't add columns or save back
            modified = False

            # Rename SKU_NO to SKU
            if "SKU_NO" in df.columns and "SKU" not in df.columns:
                df["SKU"] = df["SKU_NO"].astype(str)
                modified = True

            # Combine DESCRIPTION1 and DESCRIPTION2 into Name
            if (
                "DESCRIPTION1" in df.columns
                and "DESCRIPTION2" in df.columns
                and "Name" not in df.columns
            ):
                df["Name"] = (
                    df["DESCRIPTION1"].astype(str)
                    + " "
                    + df["DESCRIPTION2"].astype(str)
                )
                modified = True
            elif "DESCRIPTION1" in df.columns and "Name" not in df.columns:
                df["Name"] = df["DESCRIPTION1"].astype(str)
                modified = True
            elif "DESCRIPTION2" in df.columns and "Name" not in df.columns:
                df["Name"] = df["DESCRIPTION2"].astype(str)
                modified = True

            # Rename LIST_PRICE to Price
            if "LIST_PRICE" in df.columns and "Price" not in df.columns:
                df["Price"] = df["LIST_PRICE"]
                modified = True

            if modified:
                print(
                    f"✅ Converted legacy column names in {os.path.basename(input_path)}"
                )

            # Don't add extra columns or save back to input file
            return True

        except Exception as e:
            print(f"❌ Error checking input file format: {e}")
            return False

    def prompt_for_input_spreadsheet_tk(self):
        input_dir = os.path.join(PROJECT_ROOT, "data", "input")
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            initialdir=input_dir,
            title="Select spreadsheet for scraping",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if file_path:
            return file_path
        else:
            return None

    def scrape(self):
        # Convert input file to normalized format before scraping
        self.convert_input_file_to_new_format(self.file_path)
        # Read with dtype=str to preserve leading zeros
        df = pd.read_excel(self.file_path, dtype=str)
        if df.empty:
            return

        # Store original DataFrame for Excel scraper
        self.original_df = df.copy()

        # Only require and use SKU, Name, and Price for scraping
        required_cols = ["SKU", "Name", "Price"]
        for col in required_cols:
            if col not in df.columns:
                return
        df = df[required_cols]

        # Check for existing products in database and filter them out
        self.log_callback("🔍 Checking for existing products in database...")
        existing_skus = self.get_existing_skus_from_database()
        if existing_skus:
            original_count = len(df)
            # Filter out SKUs that already exist in the database
            df = df[~df["SKU"].astype(str).str.strip().isin(existing_skus)]
            filtered_count = len(df)
            removed_count = original_count - filtered_count

            if removed_count > 0:
                self.log_callback(
                    f"🗑️ Removed {removed_count} existing products from input file"
                )
                self.log_callback(f"📊 Remaining products to scrape: {filtered_count}")

                # Save the filtered dataframe back to the input file
                try:
                    df.to_excel(self.file_path, index=False)
                    self.log_callback(f"💾 Updated input file: {self.file_path}")
                except Exception as e:
                    self.log_callback(f"⚠️ Could not update input file: {e}")
            else:
                self.log_callback(
                    "✅ No existing products found - all products are new"
                )
        else:
            self.log_callback("ℹ️ No existing database found - processing all products")

        # Filter out SKUs that are not 12 characters long or contain non-numeric characters (invalid for accurate scraping)
        if not df.empty:
            original_count = len(df)
            df = df[df["SKU"].astype(str).str.strip().str.match(r"^\d{12}$")]
            filtered_count = len(df)
            invalid_count = original_count - filtered_count

            if invalid_count > 0:
                self.log_callback(
                    f"🗑️ Removed {invalid_count} SKUs with invalid format (must be exactly 12 digits, no letters)"
                )
                self.log_callback(
                    f"📊 Remaining valid SKUs to scrape: {filtered_count}"
                )

                # Save the filtered dataframe back to the input file
                try:
                    df.to_excel(self.file_path, index=False)
                    self.log_callback(f"💾 Updated input file: {self.file_path}")
                except Exception as e:
                    self.log_callback(f"⚠️ Could not update input file: {e}")
            else:
                self.log_callback("✅ All SKUs have valid format (12 digits)")

        # If no products remain after filtering, exit early
        if df.empty:
            self.log_callback(
                "🎉 All products in input file already exist in database or have invalid SKUs!"
            )
            self.log_callback("📁 No scraping needed.")
            return

        # Initialize tracking for completed sites
        completed_sites = set()
        session_start_time = datetime.now()

        self.cleanup_chrome_processes()

        existing_skus_by_site = {
            site: self.load_existing_skus(site) for site in self.scraping_options.keys()
        }

        # Calculate initial SKUs to process per site (no filtering - process all)
        rows = list(df.iterrows())

        def is_valid_sku(sku_str):
            import re

            return bool(
                re.match(r"^\d{12}$", str(sku_str).strip())
            )  # Only accept SKUs that are exactly 12 digits

        for site in self.scraping_options.keys():
            if site == "Excel":
                skus_for_site = [
                    str(row["SKU"]).strip() for _, row in rows
                ]  # Process all SKUs regardless of existing
            else:
                skus_for_site = [
                    str(row["SKU"]).strip() for _, row in rows
                ]  # Process all SKUs regardless of existing
            existing_count = len(
                [
                    str(row["SKU"]).strip()
                    for _, row in rows
                    if str(row["SKU"]).strip() in existing_skus_by_site.get(site, set())
                ]
            )

        # Main scraping loop
        all_collected_products = []  # Collect all product data before consolidation

        # Manual mode: keep asking for sites until user says 'done'
        scrape_all_mode = False
        if not self.interactive:
            scrape_all_mode = True
        while True:
            self.log_callback("\n" + "=" * 70)
            self.log_callback("🔄 CONTINUOUS SCRAPING MODE")
            self.log_callback("=" * 70)
            # Ask user for the scraping order, showing completed sites
            if self.selected_sites:
                scraping_sites = self.selected_sites
                self.selected_sites = None  # Use only once
            else:
                scraping_sites = self.get_scraping_order(completed_sites)
            # Check if user wants to finish
            if scraping_sites is None:
                break
            if not scraping_sites:
                continue

            # Check if this is "Scrape All" mode (all remaining sites selected)
            all_sites = set(self.scraping_options.keys())
            remaining_sites = all_sites - completed_sites
            if set(scraping_sites) == remaining_sites and len(scraping_sites) > 1:
                scrape_all_mode = True

            # Initialize progress tracking for this batch
            self.progress_tracker.start_overall_progress(len(scraping_sites), len(rows))

            # Re-calculate SKUs to process for selected sites (in case data changed)
            current_existing_skus = {
                site: self.load_existing_skus(site) for site in scraping_sites
            }
            total_skus_to_process = 0
            for site in scraping_sites:
                if site == "Excel":
                    skus_to_process = [
                        str(row["SKU"]).strip() for _, row in rows
                    ]  # Process all SKUs regardless of existing
                else:
                    skus_to_process = [
                        str(row["SKU"]).strip() for _, row in rows
                    ]  # Process all SKUs regardless of existing
                existing_count = len(
                    [
                        str(row["SKU"]).strip()
                        for _, row in rows
                        if str(row["SKU"]).strip()
                        in current_existing_skus.get(site, set())
                    ]
                )
                total_skus_to_process += len(skus_to_process)
            # Always proceed with scraping - remove the early return check
            iteration_start_time = datetime.now()
            # Process each site sequentially and collect all product data
            for site in scraping_sites:
                skus_for_this_site = [
                    str(row["SKU"]).strip() for _, row in rows
                ]  # Process all SKUs for this site

                existing_count = len(
                    [
                        str(row["SKU"]).strip()
                        for _, row in rows
                        if str(row["SKU"]).strip()
                        in current_existing_skus.get(site, set())
                    ]
                )
                site_results = self.process_site(
                    site, skus_for_this_site, current_existing_skus, rows
                )
                if site_results:
                    all_collected_products.extend(site_results)
                else:
                    pass
                completed_sites.add(site)
                self.progress_tracker.complete_site()

            # Add newline after progress display
            self.log_callback("")

            total_sites_processed = len(scraping_sites)
            iteration_end_time = datetime.now()
            iteration_elapsed = iteration_end_time - iteration_start_time
            session_elapsed = iteration_end_time - session_start_time

            # In scrape all mode or non-interactive, exit after processing all sites
            if scrape_all_mode or not self.interactive:
                break

        # CONSOLIDATION PHASE: Merge data from multiple sites and present options to user
        if all_collected_products:
            # Add final newline after all scraping progress
            consolidated_products = self.consolidate_products_by_sku(
                all_collected_products, rows
            )

            if consolidated_products:
                final_products = self.edit_consolidated_products(consolidated_products)

                if final_products:
                    self.save_final_products(final_products, rows)
                else:
                    pass
            else:
                pass

        # Calculate final session results
        all_found_skus = set(self.all_found_products.keys())

        # Ask if user wants to remove found SKUs from input file
        if all_found_skus:
            if self.interactive:
                remove_choice = (
                    input("\nRemove found SKUs from input file? (y/n): ")
                    .strip()
                    .lower()
                )
            else:
                remove_choice = "y"  # Default to yes in non-interactive mode

            if remove_choice == "y":
                try:
                    # Read the original input file with all columns
                    original_df = pd.read_excel(self.file_path, dtype=str)
                    original_count = len(original_df)

                    # Filter out found SKUs
                    remaining_df = original_df[
                        ~original_df["SKU"].astype(str).str.strip().isin(all_found_skus)
                    ]
                    remaining_count = len(remaining_df)
                    removed_count = original_count - remaining_count

                    if removed_count > 0:
                        # Save the updated file
                        remaining_df.to_excel(self.file_path, index=False)
                    else:
                        pass

                except Exception as e:
                    pass
            else:
                pass

        # Only offer manual product creation in "Scrape All" mode after trying all sites
        if scrape_all_mode:
            unfound_skus = [sku for sku in df["SKU"] if sku not in all_found_skus]
            if unfound_skus:
                if self.interactive:
                    create_choice = (
                        input(
                            "\nCreate new products manually for these unfound SKUs? (y/n): "
                        )
                        .strip()
                        .lower()
                    )
                else:
                    create_choice = "n"  # Skip manual creation in non-interactive mode
                if create_choice == "y":
                    try:
                        from src.ui.product_creator_ui import (
                            create_new_product_via_editor,
                        )

                        created_count = 0
                        for i, sku in enumerate(unfound_skus, 1):
                            result_path = create_new_product_via_editor()
                            if result_path:
                                created_count += 1
                            else:
                                cancel_all = (
                                    input("Cancel creating remaining products? (y/n): ")
                                    .strip()
                                    .lower()
                                )
                                if cancel_all == "y":
                                    break

                        if created_count > 0:
                            pass

                    except ImportError:
                        pass
                    except Exception as e:
                        pass
                else:
                    pass
            else:
                pass

        convert_xlsx_to_xls_with_excel()

    def process_site(self, site, skus_to_process, existing_skus_by_site, rows):
        """Process a site using the new architecture - pass SKU array to scraper.

        Returns: List of (product_info, site, input_row) tuples for found products
        """

        # Removed SKU filtering - process all SKUs regardless of existing

        if not skus_to_process:
            return []

        scraping_function = self.scraping_options.get(site)
        if not scraping_function:
            return []

        # Initialize site progress tracking
        self.progress_tracker.start_site_progress(site, len(skus_to_process))
        self.progress_tracker.update_sku_progress(0, f"Starting {site}")

        try:
            # NEW ARCHITECTURE: Call scraper with SKU array
            scraped_products = scraping_function(
                skus_to_process,
                log_callback=self.log_callback,
                progress_tracker=self.progress_tracker,
            )

            # Handle different return types
            if scraped_products is None:
                scraped_products = []
            elif isinstance(scraped_products, dict):
                # Single product returned, wrap in list
                scraped_products = (
                    [scraped_products] if scraped_products.get("Name") else []
                )
            elif not isinstance(scraped_products, list):
                self.log_callback(
                    f"⚠️ {site}: Scraper returned unexpected type: {type(scraped_products)}"
                )
                scraped_products = []

            # Filter out invalid products and ensure required fields
            valid_products = []
            for product in scraped_products:
                if isinstance(product, dict):
                    name = product.get("Name", "").strip()
                    # Reject products with invalid/empty names
                    if name and name not in ["N/A", "Unknown", "", "None"]:
                        # Ensure required fields exist
                        required_fields = [
                            "Name",
                            "SKU",
                            "Price",
                            "Weight",
                            "Image URLs",
                        ]
                        for field in required_fields:
                            if field not in product:
                                product[field] = [] if field == "Image URLs" else ""
                        valid_products.append(product)

            self.log_callback(
                f"✅ {site}: Scraper returned {len(valid_products)} valid products"
            )

            if not valid_products:
                return []

            # Return raw product data for consolidation (classification happens later)
            self.log_callback(
                f"📦 Preparing {len(valid_products)} products for consolidation..."
            )
            site_results = []
            for product_info in valid_products:
                sku = product_info.get("SKU", "Unknown")
                input_row = next(
                    (r[1] for r in rows if str(r[1]["SKU"]).strip() == sku), {}
                )
                site_results.append((product_info, site, input_row))

                # Still track in all_found_products for progress reporting
                if sku not in self.all_found_products:
                    self.all_found_products[sku] = []
                self.all_found_products[sku].append((product_info, site, input_row))

            return site_results

        except Exception as e:
            # Update progress with error status
            self.progress_tracker.update_sku_progress(
                len(skus_to_process), f"Error: {str(e)[:50]}"
            )
            self.log_callback(f"❌ Error processing {site}: {e}")
            return []

    def consolidate_products_by_sku(self, all_products, rows):
        """Consolidate products from multiple sites by SKU, collecting all options for each field.

        Args:
            all_products: List of (product_info, site, input_row) tuples
            rows: Original input rows for price data

        Returns:
            Dict with SKU as key and consolidated product data as value
        """
        from collections import defaultdict

        # Group products by SKU
        products_by_sku = defaultdict(list)
        for product_info, site, input_row in all_products:
            sku = product_info.get("SKU", "Unknown")
            products_by_sku[sku].append((product_info, site, input_row))

        consolidated = {}

        self.log_callback(
            f"🔄 Consolidating {len(products_by_sku)} SKUs from scraped data..."
        )

        for sku, product_list in products_by_sku.items():

            # Collect all options for each field (single value per site)
            name_by_site = {}  # Single value per site
            brand_by_site = {}  # Single value per site
            weight_by_site = {}  # Single value per site
            images_by_site = {}  # List of images per site
            product_cross_sell_by_site = {}  # Single value per site

            for product_info, site, input_row in product_list:
                # Collect raw scraped data without classification

                # Names - each site provides one name
                name = product_info.get("Name", "").strip()
                if name:
                    name_by_site[site] = name  # Single value per site

                # Brands - each site provides one brand
                brand = product_info.get("Brand", "").strip()
                if brand:
                    brand_by_site[site] = brand  # Single value per site

                # Weights - each site provides one weight
                weight = product_info.get("Weight", "").strip()
                if weight:
                    weight_by_site[site] = weight  # Single value per site

                # Images - each site provides a set of images
                images = product_info.get("Image URLs", [])
                if images:
                    images_by_site[site] = images  # List of images per site

                # Product Cross Sell - each site provides one value
                product_cross_sell = product_info.get("Product Cross Sell", "").strip()
                if product_cross_sell:
                    product_cross_sell_by_site[site] = (
                        product_cross_sell  # Single value per site
                    )

            # Helper function to get most common value (ignoring empty strings)
            def most_common_value(values):
                from collections import Counter

                filtered = [v for v in values if v.strip()]
                if not filtered:
                    return ""
                return Counter(filtered).most_common(1)[0][0]

            # Get input row for this SKU
            input_row = next(
                (r[1] for r in rows if str(r[1]["SKU"]).strip() == sku), {}
            )

            # Create consolidated product with all options (single value per site)
            consolidated[sku] = {
                "SKU": sku,
                "input_price": input_row.get("Price", ""),
                "input_name": input_row.get("Name", ""),
                "name_by_site": name_by_site,  # Single value per site
                "brand_by_site": brand_by_site,  # Single value per site
                "weight_by_site": weight_by_site,  # Single value per site
                "images_by_site": images_by_site,  # List of images per site
                "product_cross_sell_by_site": product_cross_sell_by_site,  # Single value per site
            }

            # Debug: Show consolidated raw scraped options
            # print(f"📊 Consolidated {sku}:")
            # print()

        self.log_callback(f"✅ Consolidation complete for {len(consolidated)} SKUs")
        return consolidated

    def edit_consolidated_products(self, consolidated_products):
        """Present consolidated products to user for selection of best options.

        Args:
            consolidated_products: Dict with SKU as key and consolidated data as value

        Returns:
            List of final product dictionaries with user-selected options
        """
        if not consolidated_products:
            return []

        # Convert consolidated data to format expected by product editor
        editor_products = []

        self.log_callback(
            f"🎯 Preparing {len(consolidated_products)} SKUs for editing..."
        )

        for sku, product_data in consolidated_products.items():

            # Convert _by_site dicts to _options arrays for the editor
            name_options = list(product_data.get("name_by_site", {}).values())
            brand_options = list(product_data.get("brand_by_site", {}).values())
            weight_options = list(product_data.get("weight_by_site", {}).values())
            images_by_site = product_data.get("images_by_site", {})

            # Create a product dict for the editor with all options
            editor_product = {
                "SKU": sku,
                "Name": "",  # Empty - editor will use _consolidated_data arrays for default selection
                "Brand": "",  # Empty - editor will use _consolidated_data arrays
                "Weight": "",  # Empty - editor will use _consolidated_data arrays
                "Image URLs": [],  # Empty - editor will use _consolidated_data arrays
                "Price": product_data.get(
                    "input_price", ""
                ),  # Use original input price
                "Category": "",  # Empty - editor will use _consolidated_data arrays
                "Product Type": "",  # Empty - editor will use _consolidated_data arrays
                "Product On Pages": "",  # Empty - editor will use _consolidated_data arrays
                "Special Order": "",  # Empty - editor will use _consolidated_data arrays
                "Product Cross Sell": "",  # Empty - editor will use _consolidated_data arrays
                "ProductDisabled": "",  # Empty - editor will use _consolidated_data arrays
                # Add metadata for the editor
                "input_name": product_data.get(
                    "input_name", ""
                ),  # Original input name for display only
                "input_price": product_data.get(
                    "input_price", ""
                ),  # Original input price for display only
                "_consolidated_data": {
                    "name_options": name_options,
                    "brand_options": brand_options,
                    "weight_options": weight_options,
                    "images_by_site": images_by_site,
                    "price_options": [product_data.get("input_price", "")],
                },
            }

            editor_products.append(editor_product)

        # In non-interactive mode (GUI), use callback to open editor on main thread
        # Interactive mode (terminal) opens the product editor directly
        if not self.interactive:
            if self.editor_callback:
                # Call callback - it will block until editor closes (synchronous)
                self.log_callback(
                    f"📝 Requesting product editor for {len(editor_products)} products..."
                )
                edited_products = self.editor_callback(editor_products)

                if edited_products:
                    self.log_callback(f"✅ User edited {len(edited_products)} products")
                    return edited_products
                else:
                    self.log_callback("❌ User cancelled editing")
                    return []
            else:
                # No editor callback available, auto-select first options
                self.log_callback(
                    f"🤖 Auto-selecting best options for {len(editor_products)} products (no editor callback)..."
                )

                final_products = []
                for product in editor_products:
                    cons_data = product["_consolidated_data"]

                    # Select first option for each field
                    product["Brand"] = cons_data.get("brand_options", [""])[0]
                    product["Name"] = cons_data.get("name_options", [""])[0]
                    product["Weight"] = cons_data.get("weight_options", [""])[0]

                    # Select first image set
                    images_by_site = cons_data.get("images_by_site", {})
                    if images_by_site:
                        first_site = list(images_by_site.keys())[0]
                        product["Image URLs"] = images_by_site[first_site]
                    else:
                        product["Image URLs"] = []

                    final_products.append(product)

                self.log_callback(
                    f"✅ Auto-selected options for {len(final_products)} products"
                )
                return final_products

        # Interactive mode - open the product editor directly (terminal mode)
        self.log_callback("📝 Opening product editor for manual selection...")
        try:
            from src.ui.product_editor import edit_products_in_batch

            edited_products = edit_products_in_batch(editor_products)
        except Exception as e:
            import traceback

            error_msg = f"Failed to open product editor:\n\n{str(e)}\n\n{traceback.format_exc()}"
            self.log_callback(f"❌ Error opening product editor: {str(e)}")
            print(f"DEBUG: {error_msg}")
            return []

        if edited_products:
            self.log_callback(f"✅ User edited {len(edited_products)} products")
            return edited_products
        else:
            self.log_callback("❌ User cancelled editing")
            return []

    def save_final_products(self, final_products, rows):
        """Save the final user-selected products to the appropriate site spreadsheets."""

        # Ask if user wants to run auto-classification
        classify_choice = (
            "y"
            if not self.interactive
            else input(
                f"\n🤖 Auto-classify {len(final_products)} products using existing database? (y/n): "
            )
            .strip()
            .lower()
        )

        if classify_choice == "y":
            self.log_callback(
                f"🤖 Auto-classifying {len(final_products)} products using existing database..."
            )
            from src.core.classification.classifier import classify_products_batch

            final_products = classify_products_batch(final_products)
            self.log_callback(f"✅ Auto-classification complete")

            # Ask if user wants to review/edit classifications
            review_choice = (
                "n"
                if not self.interactive
                else input(
                    f"\n📋 Open classification editor to review/edit {len(final_products)} products? (y/n): "
                )
                .strip()
                .lower()
            )

            if review_choice == "y":
                self.log_callback(
                    f"📋 Opening classification editor for {len(final_products)} final products..."
                )
                from src.ui.product_classify_ui import edit_classification_in_batch

                # Convert products from scraper format to classification UI format
                classification_products = []
                for product in final_products:
                    # Convert Image URLs list to Images comma-separated string
                    image_urls = product.get("Image URLs", [])
                    images_string = ",".join(url for url in image_urls if url)

                    classification_product = {
                        "SKU": product.get("SKU", ""),
                        "Name": product.get("Name", ""),
                        "Brand": product.get("Brand", ""),
                        "Price": product.get("Price", ""),
                        "Weight": product.get("Weight", ""),
                        "Images": images_string,
                        # Preserve existing classification fields (may be populated by auto-classification)
                        "Category": product.get("Category", ""),
                        "Product Type": product.get("Product Type", ""),
                        "Product On Pages": product.get("Product On Pages", ""),
                    }
                    classification_products.append(classification_product)

                final_products = edit_classification_in_batch(classification_products)
                if final_products is None:
                    self.log_callback(
                        "❌ User cancelled classification - aborting save"
                    )
                    return
                self.log_callback(f"✅ Classification review complete")
            else:
                self.log_callback("ℹ️ Skipping classification review")
        else:
            self.log_callback("ℹ️ Skipping auto-classification")

        # Cross-sell assignment disabled for now
        # TODO: Re-enable cross-sell assignment after fixing UI issues
        self.log_callback("ℹ️ Skipping cross-sell assignment (disabled)")

        # Proceed with saving products
        self.log_callback(f"\n💾 Saving {len(final_products)} products to database...")

        for product_info in final_products:
            sku = product_info.get("SKU", "Unknown")

            # No longer using site-specific files - all products go to combined file
            source_site = "combined"  # Placeholder since parameter is still required

            brand = product_info.get("Brand", "Unknown")
            product_name = product_info.get("Name", "Unknown Product")
            full_product_name = full_name(brand, product_name)
            file_name = create_fileName(full_product_name)
            image_urls = product_info.get("Image URLs", [])
            weight = product_info.get("Weight", "N/A")
            image_count = len([url for url in image_urls if url])
            self.log_callback(
                f"📦 SKU: {sku} | Name: {full_product_name} | Weight: {weight} | Images: {image_count}"
            )

            if image_urls:
                self.download_images(brand, file_name, image_urls, source_site)

            today = datetime.now()
            date_string = today.strftime("%m%d%y")
            input_row = next(
                (r[1] for r in rows if str(r[1]["SKU"]).strip() == sku), {}
            )

            new_row = {
                "SKU": sku,
                "Name": full_product_name,
                "Product Description": full_product_name,
                "Price": input_row.get("Price", ""),
                "Weight": weight,
                "Brand": brand,
                "File name": create_html(full_product_name),
                "Graphic": f"{clean_brand(brand)}/{file_name}",
                "More Information Graphic": f"{clean_brand(brand)}/{file_name}",
                "Product Field 1": f"new{date_string}",
            }

            for i, url in enumerate(image_urls[1:], start=1):
                if url:
                    local_image_path = (
                        f"{clean_brand(brand)}/{file_name.replace('.jpg', f'-{i}.jpg')}"
                    )
                    new_row[f"More Information Image {i}"] = local_image_path
                else:
                    new_row[f"More Information Image {i}"] = "none"

            # Use new user-friendly column names
            new_row["Category"] = product_info.get("Category", "")
            new_row["Product_Type"] = product_info.get("Product Type", "")
            new_row["Product_On_Pages"] = product_info.get("Product On Pages", "")
            new_row["Special_Order"] = product_info.get("Special Order", "")
            new_row["Product_Cross_Sell"] = product_info.get("Product Cross Sell", "")
            new_row["ProductDisabled"] = product_info.get("ProductDisabled", "")

            self.save_incremental_results(new_row, source_site)

        self.log_callback(f"✅ Successfully saved {len(final_products)} products!")
