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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import classification functions
from src.ui.product_classify_ui import edit_classification_in_batch
from src.core.classification.classifier import classify_products_batch
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
        # Load Excel file
        df = pd.read_excel(file_path, dtype=str)
        print(f"📊 Loaded {len(df)} rows from Excel file")

        if df.empty:
            print("❌ Excel file is empty")
            return

        # Check required columns
        required_cols = ["SKU", "Name"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return

        # Convert Excel columns to internal format
        products_list = []
        for _, row in df.iterrows():
            # Map Excel columns to internal format
            # Exclude existing classifications since classifier.py will set fresh ones
            product = {
                "SKU": str(row.get("SKU", "")).strip(),
                "Name": str(row.get("Name", "")).strip(),
                "Brand": str(row.get("Product Field 16", "")).strip(),  # Brand
                "Price": str(row.get("Price", "")).strip(),
                "Weight": str(row.get("Weight", "")).strip(),
                "Images": str(row.get("Images", "")).strip(),
                "Special Order": (
                    "yes"
                    if str(row.get("Product Field 11", "")).strip().lower() == "yes"
                    else ""
                ),
                "Category": "",  # Will be set by classifier.py
                "Product Type": "",  # Will be set by classifier.py
                "Product On Pages": "",  # Will be set by classifier.py
                "Product Cross Sell": str(row.get("Product Field 32", "")).strip(),
                "Product Disabled": (
                    "checked"
                    if str(row.get("ProductDisabled", "")).strip().lower() == "checked"
                    else "uncheck"
                ),
            }
            products_list.append(product)

        print(f"✅ Converted {len(products_list)} products to internal format")

        # Run automatic classification first
        settings = SettingsManager()
        classification_method = settings.get("classification_method", "llm")
        print(
            f"🤖 Running automatic classification using {classification_method} method..."
        )
        products_list = classify_products_batch(
            products_list, method=classification_method
        )
        print("✅ Automatic classification complete")

        # Run manual classification UI
        print("🖱️ Opening manual classification editor...")
        products_list = edit_classification_in_batch(products_list)

        if products_list is None:
            print("❌ Classification cancelled by user")
            return

        print("✅ Manual classification complete")

        # Convert back to Excel format
        excel_data = []
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for product in products_list:
            row = {
                "SKU": product.get("SKU", ""),
                "Name": product.get("Name", ""),
                "Price": product.get("Price", ""),
                "Images": product.get("Images", ""),
                "Weight": product.get("Weight", ""),
                "Product Field 16": product.get("Brand", ""),  # Brand
                "Product Field 11": (
                    "yes" if product.get("Special Order") == "yes" else ""
                ),  # Special Order
                "Product Field 24": product.get("Category", ""),  # Category
                "Product Field 25": product.get("Product Type", ""),  # Product Type
                "Product On Pages": product.get("Product On Pages", ""),
                "Product Field 32": product.get("Product Cross Sell", ""),  # Cross-sell
                "ProductDisabled": (
                    "checked"
                    if product.get("Product Disabled") == "checked"
                    else "uncheck"
                ),
                "Last Edited": timestamp,
            }
            excel_data.append(row)

        # Save back to Excel file
        # Always save as .xlsx since pandas can't write to .xls
        save_path = file_path
        if file_path.lower().endswith(".xls"):
            save_path = file_path[:-4] + ".xlsx"
            print(f"📝 Converting to .xlsx format: {save_path}")

        new_df = pd.DataFrame(excel_data)
        new_df.to_excel(save_path, index=False)

        print(f"💾 Saved {len(products_list)} classified products back to: {save_path}")
        print("🎉 Excel classification complete!")

    except Exception as e:
        print(f"❌ Error during classification: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    classify_excel_file()
