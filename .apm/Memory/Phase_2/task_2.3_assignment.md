# Task 2.3: Integrate the "Database Refresh" Feature

**Assigned to:** Agent_GUI

## Objective
To allow the user to refresh the database via a simple button click in the GUI.

## Expected Output
A functional "Refresh Database" button that executes the database refresh logic in a background thread and logs the outcome.

## Guidance
Follow the same pattern as Task 2.2.

- Connect the `clicked` signal of the "Refresh Database" button to a new slot method (e.g., `start_db_refresh`).
- In this method, instantiate the `Worker` thread with the refactored database refresh function.
- Connect the worker's signals to the log area and start the thread.

## `gui.py` Content

```python
import sys
import traceback
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

# Conditional import for core logic
try:
    from main import run_scraping, run_discontinued_check
except ImportError as e:
    print(f"Error importing from main: {e}")
    # Provide dummy functions if the import fails, so the GUI can still load.
    def run_scraping(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Scraping logic not found.")
        print("Error: Scraping logic not found.")
    def run_discontinued_check(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Discontinued check logic not found.")
        print("Error: Discontinued check logic not found.")


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class Worker(QThread):
    """
    Worker thread for executing long-running tasks.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add callbacks to kwargs for the target function
        self.kwargs["progress_callback"] = self.signals.progress
        self.kwargs["log_callback"] = self.signals.log.emit

    def run(self):
        """
        Execute the worker's target function.
        """
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Product Scraper")
        self.worker = None

        # Create widgets
        self.start_scraping_button = QPushButton("Start Scraping")
        self.check_discontinued_button = QPushButton("Check Discontinued")
        self.refresh_database_button = QPushButton("Refresh Database")
        self.run_tests_button = QPushButton("Run Tests")
        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.progress_bar = QProgressBar()

        # Group buttons for easy enabling/disabling
        self.buttons = [
            self.start_scraping_button,
            self.check_discontinued_button,
            self.refresh_database_button,
            self.run_tests_button,
        ]

        # Set up the layout
        layout = QVBoxLayout()
        for button in self.buttons:
            layout.addWidget(button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output_area)

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Connect signals
        self.start_scraping_button.clicked.connect(self.start_scraping)
        self.check_discontinued_button.clicked.connect(self.start_discontinued_check)

    def _set_buttons_enabled(self, enabled):
        """Enable or disable all action buttons."""
        for button in self.buttons:
            button.setEnabled(enabled)

    def _run_worker(self, fn, *args):
        """Generic method to run a function in the worker thread."""
        self.log_output_area.clear()
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)

        self.worker = Worker(fn, *args)
        self.worker.signals.log.connect(self.log_message)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.finished.connect(self.worker_finished)
        self.worker.start()

    def start_scraping(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;Text Files (*.txt)",
        )
        if file_path:
            self._run_worker(run_scraping, file_path)

    def start_discontinued_check(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File for Discontinued Check",
            "",
            "Excel Files (*.xlsx *.xls);;Text Files (*.txt)",
        )
        if file_path:
            self._run_worker(run_discontinued_check, file_path)

    def log_message(self, message):
        self.log_output_area.append(message)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def handle_error(self, error_tuple):
        err_type, err_val, err_tb = error_tuple
        self.log_message(f"❌ An error occurred: {err_val}")
        self.log_message(f"Traceback:\n{err_tb}")
        self.worker_finished(is_error=True)

    def worker_finished(self, is_error=False):
        if not is_error:
            self.progress_bar.setValue(100)
        self._set_buttons_enabled(True)
        self.worker = None
```

## `main.py` Content

```python
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog
import pandas as pd

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from inventory.import_shopsite import import_from_shopsite_xml
from inventory.process_xml_to_db import refresh_database_from_xml

# Conditional imports for core modules
try:
    from scrapers.master import ProductScraper
    PRODUCT_SCRAPER_AVAILABLE = True
except ImportError:
    PRODUCT_SCRAPER_AVAILABLE = False
    print("⚠️ ProductScraper module not available")

try:
    from scrapers.discontinued import DiscontinuedChecker
    DISCONTINUED_CHECKER_AVAILABLE = True
except ImportError:
    DISCONTINUED_CHECKER_AVAILABLE = False
    print("⚠️ DiscontinuedChecker module not available")

# --- Core Logic Functions ---

def run_scraping(file_path, progress_callback=None, log_callback=None):
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
    scraper = ProductScraper(file_path)
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

def run_scraper_tests():
    """Run pytest on scraper tests and return results."""
    import subprocess
    import sys
    import os
    
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(PROJECT_ROOT, "test", "test_scrapers.py")
    
    if not os.path.exists(test_file):
        print("❌ Test file not found")
        return False
    
    try:
        # Ask user if they want to run integration tests
        run_integration = input("Run integration tests with real network calls? (y/n): ").strip().lower() == 'y'
        
        print("\n" + "="*60)
        print("🧪 RUNNING SCRAPER TESTS")
        if run_integration:
            print("   📡 Including integration tests (real network calls)")
        else:
            print("   🔧 Running basic validation only")
        print("="*60)
        
        # Set environment variable for integration tests
        env = os.environ.copy()
        if run_integration:
            env['RUN_INTEGRATION_TESTS'] = '1'
        
        # Run pytest on the test file
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file, 
            "-v", "--tb=short", "--disable-warnings"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, env=env)
        
        print("Test output:")
        print(result.stdout)
        if result.stderr:
            print("Stderr:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
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
```