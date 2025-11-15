import os
import sys
import subprocess
import pandas as pd
import asyncio
import argparse

# Try to import PyQt6 for GUI file dialogs, fall back to text-based if not available
try:
    from PyQt6.QtWidgets import QApplication, QFileDialog
    from PyQt6.QtCore import QCoreApplication

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database.xml_import import import_from_shopsite_xml, publish_shopsite_changes
from src.core.database.refresh import refresh_database_from_xml
from src.core.scrapers.apify_client import ApifyScraperClient, ApifyAuthError, ApifyTimeoutError, ApifyJobError

# Conditional imports for core modules
log = print  # Default log function

# Only print module availability in non-GUI mode
try:
    import __main__

    is_gui_mode = hasattr(__main__, "__file__") and "main.py" in __main__.__file__
except:
    is_gui_mode = False

if not is_gui_mode:
    print("🔧 Checking module availability...")

try:
    from src.scrapers.master import ProductScraper

    PRODUCT_SCRAPER_AVAILABLE = True
    if not is_gui_mode:
        print("✅ ProductScraper module loaded")
except ImportError as e:
    PRODUCT_SCRAPER_AVAILABLE = False
    if not is_gui_mode:
        print(f"❌ ProductScraper module not available: {e}")

if not is_gui_mode:
    print("🔧 Module check complete")

# --- Core Logic Functions ---

def run_scraper_integration_tests(log_callback=None, progress_callback=None, editor_callback=None, status_callback=None):
    """Run integration tests for all scrapers with known working products.

    This function tests every scraper with a product we know works on that site,
    and reports which scrapers are working and which are failing.
    """
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback

    try:
        log("\n" + "="*60)
        log("🧪 SCRAPER INTEGRATION TESTS")
        log("Testing all scrapers with known working products...")
        log("="*60)

        # Import the test logic from the unit test
        import sys
        import os
        import importlib.util
        import glob
        import threading
        import time

        # Add project root to path
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Discover all scraper modules dynamically
        scrapers_dir = os.path.join(PROJECT_ROOT, "src", "scrapers")
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

        modules = {}
        for scraper_file in scraper_files:
            module_name = os.path.basename(scraper_file)[:-3]  # Remove .py extension

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, scraper_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[module_name] = module
            except Exception as e:
                log(f"❌ Failed to import scraper module {module_name}: {e}")
                continue

        # Filter to only include modules that actually have scrape functions (real scrapers)
        real_scrapers = {}
        for module_name, module in modules.items():
            # Find the scrape function
            scrape_func = None
            for attr_name in dir(module):
                if attr_name.startswith("scrape_"):
                    func = getattr(module, attr_name)
                    # Check if the function is defined in this module (not imported)
                    if hasattr(func, "__module__") and func.__module__ == module_name:
                        scrape_func = func
                        break

            if scrape_func is not None:
                real_scrapers[module_name] = (module, scrape_func)

        if not real_scrapers:
            log("❌ No scraper modules with scrape_ functions found!")
            return False

        log(f"📦 Found {len(real_scrapers)} scraper modules: {', '.join(real_scrapers.keys())}")

        # Track results for all scrapers
        results = {}
        passed_scrapers = []
        failed_scrapers = []
        skipped_scrapers = []

        total_scrapers = len(real_scrapers)
        current_scraper = 0

        for module_name, (module, scrape_func) in real_scrapers.items():
            current_scraper += 1
            if progress_callback:
                # Handle both signal objects (GUI) and plain functions (CLI)
                if hasattr(progress_callback, 'emit'):
                    progress_callback.emit(int((current_scraper - 1) / total_scrapers * 100))
                else:
                    progress_callback(int((current_scraper - 1) / total_scrapers * 100))

            log(f"\n🔍 Testing {module_name} ({current_scraper}/{total_scrapers})...")

            # Temporarily override HEADLESS setting for testing (set to False so we can see browser)
            original_headless = getattr(module, 'HEADLESS', True)
            module.HEADLESS = False
            log(f"   🌐 Running with HEADLESS=False (original: {original_headless})")

            # Get test SKU from module, fallback to default
            test_sku = getattr(module, 'TEST_SKU', '035585499741')  # Default KONG product

            try:
                # Use threading Timer for cross-platform timeout
                result_container = {'result': None, 'exception': None, 'completed': False}

                def run_actor():
                    try:
                        # Test with module-specific test SKU
                        result = scrape_func([test_sku])
                        result_container['result'] = result
                        result_container['completed'] = True
                    except Exception as e:
                        result_container['exception'] = e
                        result_container['completed'] = True

                # Start actor in a thread
                scraper_thread = threading.Thread(target=run_actor)
                scraper_thread.daemon = True
                scraper_thread.start()

                # Wait for completion with timeout (45 seconds for real scraping - login can be slow)
                scraper_thread.join(timeout=45)

                if scraper_thread.is_alive():
                    log(f"❌ {module_name}: FAILED - Test timed out after 45 seconds")
                    results[module_name] = "TIMEOUT"
                    failed_scrapers.append(module_name)
                    continue

                if result_container['exception']:
                    error_msg = str(result_container['exception'])
                    log(f"❌ {module_name}: FAILED - {error_msg}")
                    results[module_name] = f"ERROR: {error_msg}"
                    failed_scrapers.append(module_name)
                    continue

                result = result_container['result']

                # Validate the result - scrape_products returns a list
                if result is None:
                    log(f"❌ {module_name}: FAILED - Returned None for test SKU {test_sku}")
                    results[module_name] = "NO_RESULT"
                    failed_scrapers.append(module_name)
                    continue

                if not isinstance(result, list):
                    log(f"❌ {module_name}: FAILED - Did not return a list for test SKU {test_sku}")
                    results[module_name] = "INVALID_RETURN_TYPE"
                    failed_scrapers.append(module_name)
                    continue

                if len(result) == 0:
                    log(f"❌ {module_name}: FAILED - Returned empty list for test SKU {test_sku}")
                    results[module_name] = "EMPTY_RESULT"
                    failed_scrapers.append(module_name)
                    continue

                # Check if we got at least one product
                product = result[0]
                if product is None:
                    log(f"❌ {module_name}: FAILED - First product is None for test SKU {test_sku}")
                    results[module_name] = "NULL_PRODUCT"
                    failed_scrapers.append(module_name)
                    continue

                if not isinstance(product, dict):
                    log(f"❌ {module_name}: FAILED - Product data is not a dictionary")
                    results[module_name] = "INVALID_PRODUCT_DATA"
                    failed_scrapers.append(module_name)
                    continue

                # Check required fields - FAIL if missing, empty, or "N/A"
                required_fields = ['Name', 'SKU']  # Removed Price - we don't scrape prices
                invalid_fields = []

                for field in required_fields:
                    value = product.get(field)
                    if value is None or value == '' or str(value).strip().upper() == 'N/A':
                        invalid_fields.append(field)

                if invalid_fields:
                    log(f"❌ {module_name}: FAILED - Required fields missing/empty/N/A: {invalid_fields}")
                    results[module_name] = f"MISSING_FIELDS: {invalid_fields}"
                    failed_scrapers.append(module_name)
                    continue

                # Additional validation - ensure fields have meaningful content
                name = product.get('Name', '').strip()
                sku = product.get('SKU', '').strip()

                if len(name) < 3:
                    log(f"❌ {module_name}: FAILED - Product name too short: '{name}'")
                    results[module_name] = f"INVALID_NAME: '{name}'"
                    failed_scrapers.append(module_name)
                    continue

                if len(sku) < 3:
                    log(f"❌ {module_name}: FAILED - SKU too short: '{sku}'")
                    results[module_name] = f"INVALID_SKU: '{sku}'"
                    failed_scrapers.append(module_name)
                    continue

                # SUCCESS!
                brand = product.get('Brand', 'Unknown')
                weight = product.get('Weight', 'N/A')
                images_count = len(product.get('Image URLs', []))
                log(f"✅ {module_name}: PASSED - {name[:50]}{'...' if len(name) > 50 else ''}")
                log(f"   📦 SKU: {sku}, Brand: {brand}, Weight: {weight}, Images: {images_count}")
                results[module_name] = "PASSED"
                passed_scrapers.append(module_name)

            except Exception as e:
                error_msg = str(e)
                log(f"❌ {module_name}: FAILED - Test setup error: {error_msg}")
                results[module_name] = f"SETUP_ERROR: {error_msg}"
                failed_scrapers.append(module_name)
            finally:
                # Restore original HEADLESS setting
                module.HEADLESS = original_headless

        if progress_callback:
            # Handle both signal objects (GUI) and plain functions (CLI)
            if hasattr(progress_callback, 'emit'):
                progress_callback.emit(100)
            else:
                progress_callback(100)

        # Print summary
        log("\n" + "="*60)
        log("📊 TEST SUMMARY")
        log("="*60)
        log(f"✅ PASSED: {len(passed_scrapers)} scrapers")
        for scraper in passed_scrapers:
            log(f"   • {scraper}")

        if failed_scrapers:
            log(f"❌ FAILED: {len(failed_scrapers)} scrapers")
            for scraper in failed_scrapers:
                status = results[scraper]
                log(f"   • {scraper} ({status})")

        if skipped_scrapers:
            log(f"⚠️  SKIPPED: {len(skipped_scrapers)} scrapers")
            for scraper in skipped_scrapers:
                log(f"   • {scraper}")

        log(f"\nTotal scrapers tested: {len(results)}")

        # Return success if at least some scrapers passed
        success = len(passed_scrapers) > 0
        if success:
            log("✅ Integration tests completed successfully!")
        else:
            log("❌ All scrapers failed - no working scrapers found!")

        return success

    except Exception as e:
        log(f"❌ Error running integration tests: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        return False

def run_scraper_tests(run_integration=False, log_callback=None, progress_callback=None):
    """Run pytest on scraper tests and stream results."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback

    test_file = os.path.join(PROJECT_ROOT, "tests", "unit", "test_scrapers.py")

    if not os.path.exists(test_file):
        log("❌ Test file not found")
        return False

    try:
        log("\n" + "=" * 60)
        log("🧪 RUNNING SCRAPER TESTS")
        if run_integration:
            log("   📡 Including integration tests (real network calls)")
        else:
            log("   🔧 Running basic validation only")
        log("=" * 60)

        env = os.environ.copy()
        if run_integration:
            env['RUN_INTEGRATION_TESTS'] = '1'

        command = [
            sys.executable, "-m", "pytest", test_file,
            "-v", "--tb=short", "--disable-warnings"
        ]

        # Use Popen to stream output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
            bufsize=1,
            universal_newlines=True,
        )

        for line in process.stdout:
            log(line.strip())

        process.wait()

        if process.returncode == 0:
            log("✅ All tests passed!")
            return True
        else:
            log("❌ Some tests failed")
            return False

    except Exception as e:
        log(f"❌ Error running tests: {e}")
        return False


# ===================================
# Core logic functions remain above
# CLI code removed - use main.py for GUI
# ===================================


async def main():
    parser = argparse.ArgumentParser(description="Run scraper for specific site and SKUs using ApifyScraperClient")
    parser.add_argument("--site", required=True, help="The site to scrape (e.g., amazon, bradley)")
    parser.add_argument("--skus", nargs='+', required=True, help="List of SKUs to scrape")
    
    args = parser.parse_args()
    
    client = ApifyScraperClient()
    
    try:
        results = await client.scrape_skus(site=args.site, skus=args.skus)
        print("Scraping completed successfully!")
        for result in results:
            print(result)
    except ApifyAuthError as e:
        print(f"Authentication error: {e}")
    except ApifyTimeoutError as e:
        print(f"Timeout error: {e}")
    except ApifyJobError as e:
        print(f"Job error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())


# ===================================
# Core logic functions remain above
# CLI code removed - use main.py for GUI
# ===================================
