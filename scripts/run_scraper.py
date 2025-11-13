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

from src.core.database_import import import_from_shopsite_xml, publish_shopsite_changes
from src.core.database_refresh import refresh_database_from_xml

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

try:
    from src.scrapers.discontinued import DiscontinuedChecker

    DISCONTINUED_CHECKER_AVAILABLE = True
    if not is_gui_mode:
        print("✅ DiscontinuedChecker module loaded")
except ImportError as e:
    DISCONTINUED_CHECKER_AVAILABLE = False
    if not is_gui_mode:
        print(f"❌ DiscontinuedChecker module not available: {e}")

if not is_gui_mode:
    print("🔧 Module check complete")

# --- Core Logic Functions ---

def run_scraping(file_path, progress_callback=None, log_callback=None, interactive=True, selected_sites=None, editor_callback=None, status_callback=None):
    """Handles the entire scraping process for a given file."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback
    
    log(f"🚀 run_scraping called with file: {file_path}")

    if not PRODUCT_SCRAPER_AVAILABLE:
        log("❌ ProductScraper module not available. Please check your installation.")
        return

    log(f"📂 Selected file: {os.path.basename(file_path)}")
    if progress_callback:
        progress_callback.emit(10)

    # Validate Excel columns
    is_valid, message = validate_excel_columns(file_path, log_callback=log)
    log(message)
    if not is_valid:
        if "Permission denied" in message:
            log("❌ The file is open elsewhere. Please close it and retry.")
        else:
            log("⚠️ Please update the Excel file with required data.")
        return
    if progress_callback:
        progress_callback.emit(20)

    # Check for empty file
    try:
        df_check = pd.read_excel(file_path, dtype=str)
        if df_check.empty:
            log(f"⚠️ Input file '{file_path}' is empty. Deleting file.")
            os.remove(file_path)
            log(f"🗑️ Deleted empty input file: {file_path}")
            return
    except Exception as e:
        log(f"❌ Error checking for empty file: {e}")
        return
    if progress_callback:
        progress_callback.emit(30)

    # Run scraper
    log("🚀 Starting scraper...")
    scraper = ProductScraper(file_path, interactive=interactive, selected_sites=selected_sites, log_callback=log_callback, progress_callback=progress_callback, editor_callback=editor_callback, status_callback=status_callback)
    if progress_callback:
        progress_callback.emit(40)
    scraper.run()
    if progress_callback:
        progress_callback.emit(90)
    log("✅ Product scraping completed!")

def run_discontinued_check(file_path, progress_callback=None, log_callback=None, editor_callback=None, status_callback=None):
    """Runs the discontinued product check."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback

    if not DISCONTINUED_CHECKER_AVAILABLE:
        log("❌ DiscontinuedChecker module not available.")
        return

    log(f"📂 Selected file: {os.path.basename(file_path)}")
    if progress_callback:
        progress_callback.emit(10)

    log("🚀 Starting discontinued products check...")
    if progress_callback:
        progress_callback.emit(20)

    checker = DiscontinuedChecker(file_path)
    checker.run()

    if progress_callback:
        progress_callback.emit(90)
    log("✅ Discontinued products check completed!")


def run_db_refresh(progress_callback=None, log_callback=None, editor_callback=None, status_callback=None):
    """Processes the downloaded XML and refreshes the database, with callbacks."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback
    log("💾 Refreshing database from XML file...")
    if progress_callback:
        progress_callback.emit(10)

    xml_path = os.path.join(
        PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
    )

    if not os.path.exists(xml_path):
        log(f"❌ XML file not found: {xml_path}")
        log("💡 Please download the XML from ShopSite first (Option 4 in CLI).")
        return

    if progress_callback:
        progress_callback.emit(30)

    try:
        log("🔄 Processing XML and updating database...")
        success, message = refresh_database_from_xml(xml_path)
        log(message)
        if success:
            log("💡 Database updated successfully.")
        if progress_callback:
            progress_callback.emit(90)
    except Exception as e:
        log(f"❌ XML processing failed: {e}")
        # The worker's error signal will catch this
        raise


def run_shopsite_xml_download(progress_callback=None, log_callback=None, editor_callback=None, status_callback=None):
    """Downloads and saves XML from ShopSite."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback
    
    log("🌐 Downloading XML from ShopSite...")
    if progress_callback:
        progress_callback.emit(10)
    
    try:
        success, message = import_from_shopsite_xml(save_excel=True, save_to_db=False, interactive=False, log_callback=log_callback)
        log(message)
        if success:
            log("💡 XML downloaded. Use 'Refresh from XML' to process it into the database.")
        if progress_callback:
            progress_callback.emit(100)
    except Exception as e:
        log(f"❌ ShopSite XML download failed: {e}")
        # The worker's error signal will catch this
        raise


def run_shopsite_publish(progress_callback=None, log_callback=None, editor_callback=None, status_callback=None):
    """Publishes changes to ShopSite by regenerating website content."""
    # Determine log function
    if log_callback is None:
        log = print
    elif hasattr(log_callback, 'emit'):
        # If it's a Qt signal object, use emit method
        log = log_callback.emit
    else:
        # If it's already a callable (like emit method or function), use it directly
        log = log_callback
    
    log("🚀 Publishing changes to ShopSite...")
    if progress_callback:
        progress_callback.emit(10)
    
    try:
        # Default options: regenerate everything
        success, message = publish_shopsite_changes(
            html_pages=True,
            custom_pages=True,
            search_index=True,
            sitemap=True,
            full_regen=False,  # Use incremental by default
            log_callback=log_callback
        )
        log(message)
        if success:
            log("💡 ShopSite publish completed successfully!")
        if progress_callback:
            progress_callback.emit(100)
    except Exception as e:
        log(f"❌ ShopSite publish failed: {e}")
        # The worker's error signal will catch this
        raise
    if not is_gui_mode:
        xml_path = os.path.join(
            PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
        )

    if not os.path.exists(xml_path):
        if not is_gui_mode:
            print(f"❌ XML file not found: {xml_path}")
            print("💡 Download XML from ShopSite first (Option 4).")
        return

    try:
        success, message = refresh_database_from_xml(xml_path)
        if not is_gui_mode:
            print(message)
        if success and not is_gui_mode:
            print("💡 Database updated successfully.")
    except Exception as e:
        if not is_gui_mode:
            print(f"❌ XML processing failed: {e}")


def run_product_viewer():
    """Opens the product database viewer GUI."""
    if not is_gui_mode:
        print("🖼️ Opening Product Database Viewer...")
    try:
        viewer_path = os.path.join(PROJECT_ROOT, "src", "ui", "product_viewer.py")
        result = subprocess.run(
            [sys.executable, viewer_path],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0 and result.stderr:
            if not is_gui_mode:
                print(f"❌ Viewer Error: {result.stderr}")
        else:
            if not is_gui_mode:
                print("✅ Product viewer closed.")
    except Exception as e:
        if not is_gui_mode:
            print(f"❌ Error opening product viewer: {e}")


def run_scraper_tests_from_main():
    """Runs scraper tests via pytest."""
    if not is_gui_mode:
        print("🧪 Running scraper tests...")
    run_scraper_tests()  # This function is already defined in the global scope
    if not is_gui_mode:
        print("✅ Scraper tests completed!")


def run_granular_field_tests_from_main():
    """Runs granular field tests for the scraper."""
    if not PRODUCT_SCRAPER_AVAILABLE:
        if not is_gui_mode:
            print("❌ ProductScraper module not available.")
        return

    if not is_gui_mode:
        print("🔬 Running granular field tests...")
    try:
        scraper = ProductScraper("")  # Path not needed for these tests
        if scraper.run_granular_field_tests():
            if not is_gui_mode:
                print("✅ Granular field tests completed!")
        else:
            if not is_gui_mode:
                print("❌ Granular tests failed or were cancelled.")
    except Exception as e:
        if not is_gui_mode:
            print(f"❌ Error during granular tests: {e}")


# --- Helper & Utility Functions ---


def validate_excel_columns(file_path, log_callback=None):
    """
    Validates required columns in the Excel file, adding them if missing.
    Returns: tuple (is_valid, message)
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
        df = pd.read_excel(file_path, dtype=str)
        required_cols = ["SKU", "Name"]
        optional_cols = ["Brand", "Weight", "Image URLs", "Price", "Sites"]
        column_mapping = {
            "SKU": ["SKU", "SKU_NO", "Sku"],
            "Name": ["Name", "DESCRIPTION1", "Product Name"],
            "Price": ["Price", "LIST_PRICE"],
            "Brand": ["Brand", "BRAND", "Manufacturer"],
            "Weight": ["Weight", "WEIGHT", "Size"],
            "Image URLs": ["Image URLs", "IMAGE_URLS"],
            "Sites": ["Sites", "Site Selection", "SCRAPE_SITES"],
        }

        # Normalize columns
        for standard, variants in column_mapping.items():
            for variant in variants:
                if variant in df.columns and standard not in df.columns:
                    df.rename(columns={variant: standard}, inplace=True)
                    if log_callback:
                        log(f"📋 Mapped column {variant} -> {standard}")

        missing_required = [col for col in required_cols if col not in df.columns]
        if missing_required:
            for col in missing_required:
                df[col] = ""
            df.to_excel(file_path, index=False)
            return False, (
                f"❌ Missing required columns: {', '.join(missing_required)}.\n"
                f"✅ Added them to {os.path.basename(file_path)}. Please fill them in."
            )

        missing_optional = [col for col in optional_cols if col not in df.columns]
        if missing_optional:
            for col in missing_optional:
                df[col] = ""
            df.to_excel(file_path, index=False)
            if log_callback:
                log(f"✅ Added optional columns: {', '.join(missing_optional)}")

        return True, "✅ Excel file validation passed."
    except Exception as e:
        return False, f"❌ Error validating Excel file: {e}"


def select_excel_file():
    """Select an Excel file using GUI dialog if available, otherwise text-based."""
    if QT_AVAILABLE:
        try:
            # Suppress prints when called from GUI
            if not is_gui_mode:
                print("🖼️ Using PyQt6 file dialog...")
            # Create a minimal QApplication if one doesn't exist
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Select Excel File",
                os.path.join(PROJECT_ROOT, "data", "input"),
                "Excel Files (*.xlsx *.xls);;All Files (*)",
            )

            # Don't quit the app if it was created just for this dialog
            if app and len(app.allWidgets()) == 0:
                app.quit()

            if not is_gui_mode:
                print(f"📁 Dialog result: '{file_path}'")
            return file_path if file_path else None
        except Exception as e:
            if not is_gui_mode:
                print(f"❌ PyQt6 dialog failed: {e}")
                print("💡 Falling back to text-based file selection...")
            return select_excel_file_text()
    else:
        if not is_gui_mode:
            print("💡 Using text-based file selection (PyQt6 not available)")
        return select_excel_file_text()


def select_excel_file_text():
    """Text-based file selection fallback when GUI is not available."""
    input_dir = os.path.join(PROJECT_ROOT, "data", "input")
    if not is_gui_mode:
        print(f"📁 Looking for Excel files in: {input_dir}")

    # List available Excel files
    if os.path.exists(input_dir):
        excel_files = [
            f for f in os.listdir(input_dir) if f.endswith((".xlsx", ".xls"))
        ]
        if excel_files:
            if not is_gui_mode:
                print("📁 Available Excel files:")
                for i, file in enumerate(excel_files, 1):
                    print(f"  {i}. {file}")
                print("  0. Enter custom path")

            while True:
                try:
                    choice = input(
                        "➤ Select file number or enter custom path: "
                    ).strip()
                    if choice == "0":
                        file_path = input("➤ Enter full path to Excel file: ").strip()
                        if file_path and os.path.exists(file_path):
                            return file_path
                        else:
                            if not is_gui_mode:
                                print("❌ File not found. Try again.")
                    elif choice.isdigit() and 1 <= int(choice) <= len(excel_files):
                        file_path = os.path.join(
                            input_dir, excel_files[int(choice) - 1]
                        )
                        return file_path
                    else:
                        if not is_gui_mode:
                            print("❌ Invalid choice. Try again.")
                except KeyboardInterrupt:
                    return None
        else:
            if not is_gui_mode:
                print("❌ No Excel files found in input directory.")
    else:
        if not is_gui_mode:
            print(f"❌ Input directory not found: {input_dir}")

    # Fallback to manual path entry
    while True:
        try:
            file_path = input(
                "➤ Enter full path to Excel file (or press Enter to cancel): "
            ).strip()
            if not file_path:
                return None
            if os.path.exists(file_path):
                return file_path
            else:
                if not is_gui_mode:
                    print("❌ File not found. Try again.")
        except KeyboardInterrupt:
            return None

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
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Discover all Apify actor modules
        apify_actors_dir = os.path.join(PROJECT_ROOT, "apify_actors")
        actor_folders = [f for f in os.listdir(apify_actors_dir) 
                        if os.path.isdir(os.path.join(apify_actors_dir, f)) and not f.startswith('.')]

        modules = {}
        for actor_folder in actor_folders:
            actor_src_dir = os.path.join(apify_actors_dir, actor_folder, "src")
            main_py_path = os.path.join(actor_src_dir, "main.py")
            
            if not os.path.exists(main_py_path):
                log(f"⚠️  Skipping {actor_folder}: main.py not found in src/")
                continue

            try:
                # Import the actor's main module
                spec = importlib.util.spec_from_file_location(f"{actor_folder}_main", main_py_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[actor_folder] = module
            except Exception as e:
                log(f"❌ Failed to import actor {actor_folder}: {e}")
                continue

        if not modules:
            log("❌ No Apify actor modules found!")
            return False

        log(f"📦 Found {len(modules)} Apify actors: {', '.join(modules.keys())}")

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
