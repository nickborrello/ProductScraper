import os
import sys
import subprocess
import pandas as pd

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

# Conditional imports for core modules
log = print  # Default log function

# Only print module availability in non-GUI mode
try:
    import __main__

    is_gui_mode = hasattr(__main__, "__file__") and "main.py" in __main__.__file__
except:
    is_gui_mode = False

if not is_gui_mode:
    print("[INFO] Checking module availability...")

try:
    # Import removed - master module no longer exists after migration
    PRODUCT_SCRAPER_AVAILABLE = False
    if not is_gui_mode:
        print("[INFO] ProductScraper module removed (migrated to YAML configs)")
except ImportError as e:
    PRODUCT_SCRAPER_AVAILABLE = False
    if not is_gui_mode:
        print(f"[INFO] ProductScraper module not available: {e}")

if not is_gui_mode:
    print("[INFO] Module check complete")

# --- Core Logic Functions ---

def run_scraper_integration_tests(log_callback=None, progress_callback=None, editor_callback=None, status_callback=None, confirmation_callback=None, metrics_callback=None):
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
        log("[TEST] SCRAPER INTEGRATION TESTS")
        log("Testing all scrapers with known working products...")
        log("="*60)

        # Import the test logic from the unit test
        import sys
        import os
        import importlib.util
        import threading
        import time

        # Add project root to path
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Discover all scraper modules dynamically - now looking for directories
        scrapers_dir = os.path.join(PROJECT_ROOT, "src", "scrapers")
        scraper_dirs = [d for d in os.listdir(scrapers_dir) 
                       if os.path.isdir(os.path.join(scrapers_dir, d)) and 
                       not d.startswith('.') and d != 'archive']
        
        modules = {}
        for scraper_dir in scraper_dirs:
            main_py_path = os.path.join(scrapers_dir, scraper_dir, "src", "main.py")
            if os.path.exists(main_py_path):
                try:
                    # Import the module
                    spec = importlib.util.spec_from_file_location(f"{scraper_dir}_scraper", main_py_path)
                    if spec is None or spec.loader is None:
                        log(f"[ERROR] Failed to create module spec for {scraper_dir}")
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    modules[scraper_dir] = module
                except Exception as e:
                    log(f"[ERROR] Failed to import scraper module {scraper_dir}: {e}")
                    continue

        # Filter to only include modules that have scrape_products function
        real_scrapers = {}
        for module_name, module in modules.items():
            # Find the scrape_products function
            scrape_func = getattr(module, 'scrape_products', None)
            if scrape_func is not None and callable(scrape_func):
                # Get the TEST_SKU from the module
                test_sku = getattr(module, 'TEST_SKU', '035585499741')  # fallback
                real_scrapers[module_name] = (module, scrape_func, test_sku)

        if not real_scrapers:
            log("❌ No scraper modules with scrape_products function found!")
            return False

        log(f"📦 Found {len(real_scrapers)} scraper modules: {', '.join(real_scrapers.keys())}")

        # Track results for all scrapers
        results = {}
        passed_scrapers = []
        failed_scrapers = []
        skipped_scrapers = []

        total_scrapers = len(real_scrapers)
        current_scraper = 0

        for site_name, (module, scrape_func, test_sku) in real_scrapers.items():
            current_scraper += 1
            if progress_callback:
                # Handle both signal objects (GUI) and plain functions (CLI)
                if hasattr(progress_callback, 'emit'):
                    progress_callback.emit(int((current_scraper - 1) / total_scrapers * 100))
                else:
                    progress_callback(int((current_scraper - 1) / total_scrapers * 100))

            log(f"\n🔍 Testing {site_name} ({current_scraper}/{total_scrapers})...")

            # Get test SKU for this site (already extracted from module)

            # Initialize original_headless before try block
            original_headless = getattr(module, 'HEADLESS', True)

            try:
                # Temporarily override HEADLESS setting for testing (set to False so we can see browser)
                module.HEADLESS = False
                log(f"   🌐 Running with HEADLESS=False (original: {original_headless})")

                # Use threading Timer for cross-platform timeout
                result_container = {'result': None, 'exception': None, 'completed': False}

                def run_scraper():
                    try:
                        # Test with module-specific test SKU
                        if scrape_func is not None:
                            result = scrape_func([test_sku])
                            result_container['result'] = result
                        else:
                            result_container['exception'] = Exception("scrape_func is None")
                        result_container['completed'] = True
                    except Exception as e:
                        result_container['exception'] = e
                        result_container['completed'] = True

                # Start scraper in a thread
                scraper_thread = threading.Thread(target=run_scraper)
                scraper_thread.daemon = True
                scraper_thread.start()

                # Wait for completion with timeout (45 seconds for real scraping - login can be slow)
                scraper_thread.join(timeout=45)

                if scraper_thread.is_alive():
                    log(f"❌ {site_name}: FAILED - Test timed out after 45 seconds")
                    results[site_name] = "TIMEOUT"
                    failed_scrapers.append(site_name)
                    continue

                if result_container['exception']:
                    error_msg = str(result_container['exception'])
                    log(f"❌ {site_name}: FAILED - {error_msg}")
                    results[site_name] = f"ERROR: {error_msg}"
                    failed_scrapers.append(site_name)
                    continue

                result = result_container['result']

                # Validate the result - scrape_products returns a list
                if result is None:
                    log(f"❌ {site_name}: FAILED - Returned None for test SKU {test_sku}")
                    results[site_name] = "NO_RESULT"
                    failed_scrapers.append(site_name)
                    continue

                if not isinstance(result, list):
                    log(f"❌ {site_name}: FAILED - Did not return a list for test SKU {test_sku}")
                    results[site_name] = "INVALID_RETURN_TYPE"
                    failed_scrapers.append(site_name)
                    continue

                if len(result) == 0:
                    log(f"❌ {site_name}: FAILED - Returned empty list for test SKU {test_sku}")
                    results[site_name] = "EMPTY_RESULT"
                    failed_scrapers.append(site_name)
                    continue

                # Check if we got at least one product
                product = result[0]
                if product is None:
                    log(f"❌ {site_name}: FAILED - First product is None for test SKU {test_sku}")
                    results[site_name] = "NULL_PRODUCT"
                    failed_scrapers.append(site_name)
                    continue

                if not isinstance(product, dict):
                    log(f"❌ {site_name}: FAILED - Product data is not a dictionary")
                    results[site_name] = "INVALID_PRODUCT_DATA"
                    failed_scrapers.append(site_name)
                    continue

                # Check required fields - FAIL if missing, empty, or "N/A"
                required_fields = ['Name', 'SKU']  # Removed Price - we don't scrape prices
                invalid_fields = []

                for field in required_fields:
                    value = product.get(field)
                    if value is None or value == '' or str(value).strip().upper() == 'N/A':
                        invalid_fields.append(field)

                if invalid_fields:
                    log(f"❌ {site_name}: FAILED - Required fields missing/empty/N/A: {invalid_fields}")
                    results[site_name] = f"MISSING_FIELDS: {invalid_fields}"
                    failed_scrapers.append(site_name)
                    continue

                # Additional validation - ensure fields have meaningful content
                name = product.get('Name', '').strip()
                sku = product.get('SKU', '').strip()

                if len(name) < 3:
                    log(f"❌ {site_name}: FAILED - Product name too short: '{name}'")
                    results[site_name] = f"INVALID_NAME: '{name}'"
                    failed_scrapers.append(site_name)
                    continue

                if len(sku) < 3:
                    log(f"❌ {site_name}: FAILED - SKU too short: '{sku}'")
                    results[site_name] = f"INVALID_SKU: '{sku}'"
                    failed_scrapers.append(site_name)
                    continue

                # SUCCESS!
                brand = product.get('Brand', 'Unknown')
                weight = product.get('Weight', 'N/A')
                images_count = len(product.get('Image URLs', []))
                log(f"✅ {site_name}: PASSED - {name[:50]}{'...' if len(name) > 50 else ''}")
                log(f"   📦 SKU: {sku}, Brand: {brand}, Weight: {weight}, Images: {images_count}")
                results[site_name] = "PASSED"
                passed_scrapers.append(site_name)

            except Exception as e:
                error_msg = str(e)
                log(f"❌ {site_name}: FAILED - Test setup error: {error_msg}")
                results[site_name] = f"SETUP_ERROR: {error_msg}"
                failed_scrapers.append(site_name)
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

def run_scraper_tests(run_integration=False, log_callback=None, progress_callback=None, status_callback=None, editor_callback=None, confirmation_callback=None, metrics_callback=None):
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

    test_file = os.path.join(PROJECT_ROOT, "tests", "integration", "test_scraper_integration.py")

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

        if process.stdout is not None:
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


# CLI functionality removed - use platform_test_scrapers.py for testing


# ===================================
# Core logic functions remain above
# CLI code removed - use main.py for GUI
# ===================================
