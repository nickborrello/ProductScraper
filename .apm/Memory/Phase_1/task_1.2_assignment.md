# Task 1.2: Refactor Core Logic from `main.py`

**Assigned to:** Agent_Core

## Objective
To decouple the core business logic from the command-line interface in `main.py`, making it importable and callable from the new GUI.

## Expected Output
A modified `main.py` file where the primary functionalities are encapsulated within distinct functions, and the existing CLI behavior is preserved.

## Guidance
The goal is to isolate logic, not to change its behavior. The refactored functions should accept parameters like file paths directly, rather than parsing `sys.argv`.

1.  **Analyze Logic:** Carefully read through `main.py` to identify the specific code blocks responsible for each major operation (e.g., the scraping process, the discontinued check, database refresh, and running tests).
2.  **Encapsulate Functions:** For each identified block, create a new, well-named function (e.g., `run_scraping(file_path)`, `run_discontinued_check()`). Move the relevant logic into this function and modify it to accept arguments instead of relying on CLI parsing.
3.  **Preserve CLI Entrypoint:** Update the `if __name__ == "__main__":` block to parse command-line arguments as before, but now have it call the newly created functions. This ensures the script remains fully functional as a CLI tool.

## `main.py` Content

'''python
import os
import sys

# Ensure project root is on sys.path before importing local packages to avoid shadowing
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tkinter as tk
from tkinter import filedialog
from inventory.import_shopsite import import_from_shopsite_xml
from inventory.process_xml_to_db import refresh_database_from_xml

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

import pandas as pd

def validate_excel_columns(file_path):
    """
    Check if Excel file has required columns for scraping.
    Add missing columns and prompt user to fill them in.
    
    Returns:
        tuple: (is_valid, message)
    """
    try:
        df = pd.read_excel(file_path, dtype=str)
        
        # Required columns for proper scraping
        required_cols = ['SKU', 'Name']
        optional_cols = ['Brand', 'Weight', 'Image URLs', 'Price', 'Sites']
        # Check for alternate column names and normalize
        column_mapping = {
            'SKU': ['SKU', 'SKU_NO', 'Sku'],
            'Name': ['Name', 'DESCRIPTION1', 'Product Name', 'PRODUCT_NAME'],
            'Price': ['Price', 'LIST_PRICE', 'List Price'],
            'Brand': ['Brand', 'BRAND', 'Manufacturer', 'MANUFACTURER'],
            'Weight': ['Weight', 'WEIGHT', 'Size', 'SIZE'],
            'Image URLs': ['Image URLs', 'IMAGE_URLS', 'Images', 'IMAGES'],
            'Sites': ['Sites', 'Site Selection', 'Sites to Scrape', 'SCRAPE_SITES']
        }
        
        # Map existing columns to standard names
        mapped_cols = []
        for standard_name, possible_names in column_mapping.items():
            for possible in possible_names:
                if possible in df.columns:
                    if standard_name != possible:
                        df[standard_name] = df[possible]
                        print(f"📋 Mapped {possible} -> {standard_name}")
                    mapped_cols.append(standard_name)
                    break
        
        # Check for missing required columns
        missing_required = [col for col in required_cols if col not in mapped_cols]
        missing_optional = [col for col in optional_cols if col not in mapped_cols]
        
        if missing_required:
            # Add missing required columns with empty values
            for col in missing_required:
                df[col] = ''
            
            # Save the updated file
            df.to_excel(file_path, index=False)
            
            return False, f"❌ Missing required columns: {', '.join(missing_required)}.\n" + \
                         f"✅ Added empty columns to {os.path.basename(file_path)}.\n" + \
                         f"💡 Please fill in the required data and run again."
        
        if missing_optional:
            # Add missing optional columns
            for col in missing_optional:
                df[col] = ''
            
            # Save the updated file
            df.to_excel(file_path, index=False)
            print(f"✅ Added optional columns: {', '.join(missing_optional)}")
        
        return True, f"✅ Excel file validation passed. All required columns present."
        
    except Exception as e:
        return False, f"❌ Error validating Excel file: {e}"

def select_txt_file():
    root = tk.Tk()
    root.withdraw()
    root.update()
    root.lift()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Select Inventory TXT File",
        filetypes=[("Text Files", "*.txt")]
    )
    root.destroy()
    return file_path

def select_excel_file():
    root = tk.Tk()
    root.withdraw()
    root.update()
    root.lift()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Select Excel File to Scrape",
        filetypes=[("Excel Files", "*.xlsx")]
    )
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

def main():
    # Fixed options menu - all options always available
    options = {
        "1": "Scrape products from Excel",
        "2": "Check discontinued products", 
        "3": "Assign cross-sell",
        "4": "Download XML from ShopSite",
        "5": "Process XML to Database",
        "6": "View and Edit Products in Database",
        "7": "Run scraper tests",
        "8": "Run granular field tests",
        "9": "Exit"
    }

    print("🚀 Welcome to ProductScraper!")
    print("=" * 50)

    while True:
        print(f"\n{'='*20} MAIN MENU {'='*20}")
        for key, desc in options.items():
            print(f"  {key}. {desc}")
        print("=" * 50)

        choice = input("➤ Enter your choice(s) separated by commas: ").strip()
        selected = [x.strip() for x in choice.split(',') if x.strip().isdigit()]

        if not selected:
            print("⚠️ Invalid input. Please enter valid numbers.")
            continue

        if "9" in selected:
            print("\n👋 Thank you for using ProductScraper!")
            break

        print(f"\n🔄 Processing {len(selected)} task(s)வுகளில்...")
        for i, option in enumerate(selected, 1):
            print(f"\n{'='*15} TASK {i}/{len(selected)}: OPTION {option} {'='*15}")
            
            if option == "1":
                if PRODUCT_SCRAPER_AVAILABLE:
                    print("🔍 Starting product scraping...")
                    file_path = select_excel_file()
                    while file_path:
                        print(f"📂 Selected file: {os.path.basename(file_path)}")
                        # Validate Excel columns before scraping
                        is_valid, message = validate_excel_columns(file_path)
                        print(message)
                        if not is_valid:
                            if "Permission denied" in message:
                                print("❌ The file is open in Excel or another program. Please close it and retry.")
                                retry = input("🔄 Close the file and press Enter to retry, or type 'skip' to cancel: ").strip().lower()
                                if retry == "skip":
                                    break
                                # Try again with the same file_path
                                continue
                            else:
                                print("⚠️ Please update the Excel file with required data and try again.")
                                input("➤ Press Enter when ready to continue...")
                                break
                        # Only proceed if validation passed
                        # Check if file is empty before scraping
                        try:
                            df_check = pd.read_excel(file_path, dtype=str)
                            if df_check.empty:
                                print(f"⚠️ The input file '{file_path}' has 0 rows. Deleting file.")
                                os.remove(file_path)
                                print(f"🗑️ Deleted empty input file: {file_path}")
                                break
                        except Exception as e:
                            print(f"❌ Error checking for empty file: {e}")
                            break
                        scraper = ProductScraper(file_path)  # Sequential mode, threading removed
                        scraper.run()
                        print("✅ Product scraping completed!")
                        break
                    else:
                        print("❌ No file selected. Skipping scraping.")
                else:
                    print("❌ ProductScraper module not available. Please check your installation.")

            elif option == "2":
                if DISCONTINUED_CHECKER_AVAILABLE:
                    print("🕵️ Starting discontinued products check...")
                    file_path = select_excel_file()
                    if file_path:
                        print(f"📂 Selected file: {os.path.basename(file_path)}")
                        checker = DiscontinuedChecker(file_path)
                        checker.run()
                        print("✅ Discontinued products check completed!")
                    else:
                        print("❌ No file selected. Skipping discontinued check.")
                else:
                    print("❌ DiscontinuedChecker module not available. Please check your installation.")

            elif option == "3":
                print("❌ Cross-sell assignment no longer available.")
                print("   Use SQLite database queries instead:")
                print("   cd inventory && python query_db.py")
                input("\n➤ Press Enter to return to main menu...")

            elif option == "4":
                print(" Downloading XML from ShopSite...")
                try:
                    success, message = import_from_shopsite_xml(save_excel=True, save_to_db=False)
                    print(message)
                    if success:
                        print("💡 XML downloaded and saved. Use option 5 to process it into the database.")
                except Exception as e:
                    print(f"❌ ShopSite XML download failed: {e}")

            elif option == "5":
                print("💾 Processing XML file to database...")
                try:
                    # Use the default cleaned XML file path
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    xml_path = os.path.join(script_dir, "inventory", "data", "shopsite_products_cleaned.xml")
                    
                    if not os.path.exists(xml_path):
                        print(f"❌ XML file not found: {xml_path}")
                        print("💡 Download XML from ShopSite first using option 4.")
                    else:
                        success, message = refresh_database_from_xml(xml_path)
                        print(message)
                        if success:
                            print("💡 Database updated with XML data.")
                except Exception as e:
                    print(f"❌ XML processing failed: {e}")

            elif option == "6":
                print(" Opening Product Database Viewer...")
                try:
                    import subprocess
                    import sys
                    result = subprocess.run([sys.executable, "inventory/classify/product_viewer.py"],
                                          capture_output=True, text=True, cwd=os.getcwd())
                    if result.returncode == 0:
                        print("✅ Product viewer closed successfully!")
                    else:
                        print("❌ Product viewer encountered an error!")
                        if result.stderr:
                            print(f"Error details: {result.stderr}")
                except Exception as e:
                    print(f"❌ Error opening product viewer: {e}")

            elif option == "7":
                print("🧪 Running scraper tests...")
                run_scraper_tests()
                print("✅ Scraper tests completed!")

            elif option == "8":
                print("🔬 Running granular field tests...")
                if PRODUCT_SCRAPER_AVAILABLE:
                    try:
                        scraper = ProductScraper("")  # Empty path since we don't need it for testing
                        results = scraper.run_granular_field_tests()
                        if results:
                            print("✅ Granular field tests completed!")
                        else:
                            print("❌ Granular field tests failed or were cancelled.")
                    except Exception as e:
                        print(f"❌ Error running granular field tests: {e}")
                else:
                    print("❌ ProductScraper module not available. Please check your installation.")

            elif option not in options:
                print(f"❌ Invalid option: {option}")

        print(f"\n✨ All {len(selected)} task(s) completed!")
        input("\n➤ Press Enter to return to main menu...")

if __name__ == "__main__":
    main()
'''