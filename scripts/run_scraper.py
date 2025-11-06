import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog
import pandas as pd

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database_import import import_from_shopsite_xml
from src.core.database_refresh import refresh_database_from_xml

# Conditional imports for core modules
try:
    from src.scrapers.master import ProductScraper
    PRODUCT_SCRAPER_AVAILABLE = True
except ImportError:
    PRODUCT_SCRAPER_AVAILABLE = False
    print("⚠️ ProductScraper module not available")

try:
    from src.scrapers.discontinued import DiscontinuedChecker
    DISCONTINUED_CHECKER_AVAILABLE = True
except ImportError:
    DISCONTINUED_CHECKER_AVAILABLE = False
    print("⚠️ DiscontinuedChecker module not available")

# --- Core Logic Functions ---

def run_scraping(file_path, progress_callback=None, log_callback=None, interactive=True):
    """Handles the entire scraping process for a given file."""
    log = log_callback if log_callback else print

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
    scraper = ProductScraper(file_path, interactive=interactive)
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

    xml_path = os.path.join(PROJECT_ROOT, "inventory", "data", "shopsite_products_cleaned.xml")
    
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
    print("🌐 Downloading XML from ShopSite...")
    try:
        success, message = import_from_shopsite_xml(save_excel=True, save_to_db=False)
        print(message)
        if success:
            print("💡 XML downloaded. Use option 5 to process it into the database.")
    except Exception as e:
        print(f"❌ ShopSite XML download failed: {e}")

def run_xml_to_db_processing():
    """Processes the downloaded XML and refreshes the database."""
    print("💾 Processing XML file to database...")
    xml_path = os.path.join(PROJECT_ROOT, "inventory", "data", "shopsite_products_cleaned.xml")
    
    if not os.path.exists(xml_path):
        print(f"❌ XML file not found: {xml_path}")
        print("💡 Download XML from ShopSite first (Option 4).")
        return

    try:
        success, message = refresh_database_from_xml(xml_path)
        print(message)
        if success:
            print("💡 Database updated successfully.")
    except Exception as e:
        print(f"❌ XML processing failed: {e}")

def run_product_viewer():
    """Opens the product database viewer GUI."""
    print("🖼️ Opening Product Database Viewer...")
    try:
        viewer_path = os.path.join(PROJECT_ROOT, "inventory", "classify", "product_viewer.py")
        result = subprocess.run([sys.executable, viewer_path], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0 and result.stderr:
            print(f"❌ Viewer Error: {result.stderr}")
        else:
            print("✅ Product viewer closed.")
    except Exception as e:
        print(f"❌ Error opening product viewer: {e}")

def run_scraper_tests_from_main():
    """Runs scraper tests via pytest."""
    print("🧪 Running scraper tests...")
    run_scraper_tests() # This function is already defined in the global scope
    print("✅ Scraper tests completed!")

def run_granular_field_tests_from_main():
    """Runs granular field tests for the scraper."""
    if not PRODUCT_SCRAPER_AVAILABLE:
        print("❌ ProductScraper module not available.")
        return
    
    print("🔬 Running granular field tests...")
    try:
        scraper = ProductScraper("")  # Path not needed for these tests
        if scraper.run_granular_field_tests():
            print("✅ Granular field tests completed!")
        else:
            print("❌ Granular tests failed or were cancelled.")
    except Exception as e:
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
        required_cols = ['SKU', 'Name']
        optional_cols = ['Brand', 'Weight', 'Image URLs', 'Price', 'Sites']
        column_mapping = {
            'SKU': ['SKU', 'SKU_NO', 'Sku'], 'Name': ['Name', 'DESCRIPTION1', 'Product Name'],
            'Price': ['Price', 'LIST_PRICE'], 'Brand': ['Brand', 'BRAND', 'Manufacturer'],
            'Weight': ['Weight', 'WEIGHT', 'Size'], 'Image URLs': ['Image URLs', 'IMAGE_URLS'],
            'Sites': ['Sites', 'Site Selection', 'SCRAPE_SITES']
        }

        # Normalize columns
        for standard, variants in column_mapping.items():
            for variant in variants:
                if variant in df.columns and standard not in df.columns:
                    df.rename(columns={variant: standard}, inplace=True)
                    log(f"📋 Mapped column {variant} -> {standard}")

        missing_required = [col for col in required_cols if col not in df.columns]
        if missing_required:
            for col in missing_required:
                df[col] = ''
            df.to_excel(file_path, index=False)
            return False, (f"❌ Missing required columns: {', '.join(missing_required)}.\n" 
                         f"✅ Added them to {os.path.basename(file_path)}. Please fill them in.")

        missing_optional = [col for col in optional_cols if col not in df.columns]
        if missing_optional:
            for col in missing_optional:
                df[col] = ''
            df.to_excel(file_path, index=False)
            log(f"✅ Added optional columns: {', '.join(missing_optional)}")
        
        return True, "✅ Excel file validation passed."
    except Exception as e:
        return False, f"❌ Error validating Excel file: {e}"
def select_excel_file():
    """Opens a dialog to select an Excel file."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx")])
    root.destroy()
    return file_path

def run_scraper_tests(run_integration=False, log_callback=None, progress_callback=None):
    """Run pytest on scraper tests and stream results."""
    log = log_callback if log_callback else print
    
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(PROJECT_ROOT, "test", "test_scrapers.py")
    
    if not os.path.exists(test_file):
        log("❌ Test file not found")
        return False
    
    try:
        log("\n" + "="*60)
        log("🧪 RUNNING SCRAPER TESTS")
        if run_integration:
            log("   📡 Including integration tests (real network calls)")
        else:
            log("   🔧 Running basic validation only")
        log("="*60)

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
            universal_newlines=True
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

# --- CLI Entrypoint ---

def main_cli():
    """The main command-line interface loop."""
    options = {
        "1": "Scrape products from Excel", "2": "Check discontinued products",
        "3": "Assign cross-sell (DEPRECATED)", "4": "Download XML from ShopSite",
        "5": "Process XML to Database", "6": "View/Edit Products in DB",
        "7": "Run scraper tests", "8": "Run granular field tests", "9": "Exit"
    }

    print("🚀 Welcome to ProductScraper!")
    while True:
        print(f"\n{'='*20} MAIN MENU {'='*20}")
        for key, desc in options.items():
            print(f"  {key}. {desc}")
        print("=" * 50)

        choice = input("➤ Enter your choice(s) separated by commas: ").strip()
        selected = [x.strip() for x in choice.split(',') if x.strip().isdigit()]

        if not selected:
            print("⚠️ Invalid input. Please enter numbers.")
            continue
        if "9" in selected:
            break

        for option in selected:
            if option == "1":
                file_path = select_excel_file()
                if file_path:
                    run_scraping(file_path)
            elif option == "2":
                file_path = select_excel_file()
                if file_path:
                    run_discontinued_check(file_path)
            elif option == "3":
                print("❌ Cross-sell assignment is deprecated. Use SQLite queries.")
            elif option == "4":
                run_shopsite_xml_download()
            elif option == "5":
                run_xml_to_db_processing()
            elif option == "6":
                run_product_viewer()
            elif option == "7":
                run_scraper_tests_from_main()
            elif option == "8":
                run_granular_field_tests_from_main()
            else:
                print(f"❌ Invalid option: {option}")
        
        input("\n➤ Press Enter to return to the main menu...")

    print("\n👋 Thank you for using ProductScraper!")

if __name__ == "__main__":
    main_cli()