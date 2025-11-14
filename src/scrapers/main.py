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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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