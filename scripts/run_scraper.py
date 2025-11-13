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

from src.core.database_import import import_from_shopsite_xml
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


def run_scraping(
    file_path,
    progress_callback=None,
    log_callback=None,
    interactive=True,
    selected_sites=None,
    editor_callback=None,
):
    """Handles the entire scraping process for a given file."""
    log = log_callback if log_callback else print
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
    scraper = ProductScraper(
        file_path,
        interactive=interactive,
        selected_sites=selected_sites,
        log_callback=log_callback,
        progress_callback=progress_callback,
        editor_callback=editor_callback,
    )
    if progress_callback:
        progress_callback.emit(40)
    scraper.run()
    if progress_callback:
        progress_callback.emit(90)
    log("✅ Product scraping completed!")


def run_discontinued_check(file_path, progress_callback=None, log_callback=None):
    """Runs the discontinued product check."""
    log = log_callback if log_callback else print

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


def run_db_refresh(progress_callback=None, log_callback=None):
    """Processes the downloaded XML and refreshes the database, with callbacks."""
    log = log_callback if log_callback else print

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


def run_shopsite_xml_download():
    """Downloads and saves XML from ShopSite."""
    # Suppress prints when called from GUI
    if not is_gui_mode:
        print("🌐 Downloading XML from ShopSite...")
    try:
        success, message = import_from_shopsite_xml(save_excel=True, save_to_db=False)
        if not is_gui_mode:
            print(message)
        if success and not is_gui_mode:
            print("💡 XML downloaded. Use option 5 to process it into the database.")
    except Exception as e:
        if not is_gui_mode:
            print(f"❌ ShopSite XML download failed: {e}")


def run_xml_to_db_processing():
    """Processes the downloaded XML and refreshes the database."""
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
    log = log_callback if log_callback else print
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


def run_scraper_tests(run_integration=False, log_callback=None, progress_callback=None):
    """Run pytest on scraper tests and stream results."""
    log = log_callback if log_callback else print

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
            env["RUN_INTEGRATION_TESTS"] = "1"

        command = [
            sys.executable,
            "-m",
            "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--disable-warnings",
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
