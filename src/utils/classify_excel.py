#!/usr/bin/env python3
"""
Standalone Excel Classification Tool Launcher
Run this script to classify products in Excel files independently.
"""

import sys
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import classification functions
from src.core.classification.ui import edit_classification_in_batch
from src.core.classification.manager import classify_products_batch
from src.core.settings_manager import SettingsManager


def classify_excel_file():
    """
    Standalone classification tool for Excel files.
    Prompts user to select an Excel file, loads products, runs classification, and saves back.
    Works with files output by master.py scraping system.
    """
    print("🏷️ Standalone Excel Classification Tool")
    print("=" * 50)

    # Prompt user to select Excel file
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Default to spreadsheets directory
    spreadsheets_dir = Path(PROJECT_ROOT) / "data" / "spreadsheets"
    spreadsheets_dir.mkdir(exist_ok=True)

    file_path = filedialog.askopenfilename(
        initialdir=str(spreadsheets_dir),
        title="Select Excel file to classify",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
    )

    root.destroy()  # Clean up the file dialog root

    if not file_path:
        print("❌ No file selected")
        return

    print(f"📁 Selected file: {file_path}")

    try:
        # Load the original DataFrame, keeping all original data
        df = pd.read_excel(file_path, dtype=str).fillna('')
        print(f"📊 Loaded {len(df)} rows from Excel file")

        if df.empty:
            print("❌ Excel file is empty")
            return

        # Check for required columns for classification
        required_cols = ["SKU", "Name"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ Missing required columns for classification: {missing_cols}")
            return

        # Create a temporary list of dicts for the classification functions
        # This uses the specific column names the classifiers expect
        products_for_classification = df.rename(columns={
            "Product Field 16": "Brand",
            "Product Field 11": "Special Order",
            "Product Field 32": "Product Cross Sell",
            "ProductDisabled": "Product Disabled"
        }).to_dict('records')

        # --- Classification Process ---
        settings = SettingsManager()
        classification_method = settings.get("classification_method", "llm")
        
        print(f"🤖 Running automatic classification using {classification_method} method...")
        classified_products = classify_products_batch(
            products_for_classification, method=classification_method
        )
        print("✅ Automatic classification complete")

        print("🖱️ Opening manual classification editor...")
        edited_products = edit_classification_in_batch(classified_products)

        if edited_products is None:
            print("❌ Classification cancelled by user. No file will be saved.")
            return

        print("✅ Manual classification complete")
        # --- End of Classification Process ---

        # Create a DataFrame from the results
        results_df = pd.DataFrame(edited_products)

        # Set SKU as the index on both DataFrames to join the data
        df = df.set_index('SKU')
        results_df = results_df.set_index('SKU')

        # Define the mapping from classification results to final Excel columns
        column_mapping = {
            "Category": "Product Field 24",
            "Product Type": "Product Field 25",
            "Product On Pages": "Product On Pages"
        }
        
        # Rename the columns in the results DataFrame to match the target columns
        results_to_update = results_df.rename(columns=column_mapping)

        # Update the original DataFrame with the new classification data
        # This only affects columns present in `results_to_update` and preserves all others
        df.update(results_to_update)
        
        # Add/update the 'Last Edited' timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df['Last Edited'] = timestamp

        # Restore SKU from index to a column
        df.reset_index(inplace=True)

        # --- Save back to Excel ---
        save_path = Path(file_path)
        # Always save as .xlsx for compatibility, even if original was .xls
        if save_path.suffix.lower() == ".xls":
            save_path = save_path.with_suffix(".xlsx")
            print(f"📝 Original was .xls, saving as .xlsx to preserve features: {save_path.name}")

        df.to_excel(save_path, index=False)

        print(f"💾 Saved {len(df)} classified products back to: {save_path}")
        print("🎉 Excel classification complete!")

    except Exception as e:
        print(f"❌ Error during classification: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    classify_excel_file()
