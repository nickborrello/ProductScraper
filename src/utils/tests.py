import os
import sys
import subprocess
import importlib.util
import glob
import threading
import time

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_scraper_tests_from_main():
    """Runs scraper tests via pytest."""
    print("🧪 Running scraper tests...")
    run_scraper_tests()  # This function is already defined in the global scope
    print("✅ Scraper tests completed!")


# def run_granular_field_tests_from_main():
#     """Runs granular field tests for the scraper."""
#     # NOTE: This function is obsolete after reorganization.
#     # ProductScraper from src.scrapers.master no longer exists.
#     # The new modular scraper system doesn't have this functionality.
#     pass

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

        # Discover all scraper modules
        scrapers_dir = os.path.join(PROJECT_ROOT, "src", "scrapers")
        scraper_folders = [f for f in os.listdir(scrapers_dir)
                        if os.path.isdir(os.path.join(scrapers_dir, f)) and not f.startswith('.')]

        modules = {}
        for scraper_folder in scraper_folders:
            scraper_src_dir = os.path.join(scrapers_dir, scraper_folder)
            main_py_path = os.path.join(scraper_src_dir, "main.py")
            
            if not os.path.exists(main_py_path):
                log(f"⚠️  Skipping {scraper_folder}: main.py not found in src/")
                continue

            try:
                # Import the scraper's main module
                spec = importlib.util.spec_from_file_location(f"{scraper_folder}_main", main_py_path)
                if spec is None:
                    log(f"❌ Failed to create spec for scraper {scraper_folder}: spec is None")
                    continue
                if spec.loader is None:
                    log(f"❌ Failed to load scraper {scraper_folder}: spec.loader is None")
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[scraper_folder] = module
            except Exception as e:
                log(f"❌ Failed to import scraper {scraper_folder}: {e}")
                continue

        if not modules:
            log("❌ No scraper modules found!")
            return False

        log(f"📦 Found {len(modules)} scrapers: {', '.join(modules.keys())}")

        # Track results for all scrapers
        results = {}
        passed_scrapers = []
        failed_scrapers = []
        skipped_scrapers = []

        total_scrapers = len(modules)
        current_scraper = 0

        for module_name, module in modules.items():
            current_scraper += 1
            if progress_callback:
                # Handle both signal objects (GUI) and plain functions (CLI)
                if hasattr(progress_callback, 'emit'):
                    progress_callback.emit(int((current_scraper - 1) / total_scrapers * 100))
                else:
                    progress_callback(int((current_scraper - 1) / total_scrapers * 100))

            log(f"\n🔍 Testing {module_name} ({current_scraper}/{total_scrapers})...")

            # Check if the actor has a scrape_products function
            if not hasattr(module, 'scrape_products'):
                log(f"❌ {module_name}: FAILED - No scrape_products function found")
                results[module_name] = "NO_SCRAPE_PRODUCTS_FUNCTION"
                failed_scrapers.append(module_name)
                continue

            # Get test SKU from module, fallback to default
            test_sku = getattr(module, 'TEST_SKU', '035585499741')  # Default KONG product

            try:
                # Use threading Timer for cross-platform timeout
                result_container = {'result': None, 'exception': None, 'completed': False}

                def run_actor():
                    try:
                        # Test with module-specific test SKU
                        result = module.scrape_products([test_sku])
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

        if process.stdout:
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
