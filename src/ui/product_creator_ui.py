"""Product creator/exporter

Provides utilities to create new product rows and export them to a ShopSite-compatible
Excel file (same columns used by master.save_incremental_results).

Usage:
    from inventory.UI.product_creator import create_and_save_products
    products = [ { 'SKU': '123', 'Name': 'Foo', 'Brand': 'Bar', 'Image URLs': ['http://...'], ... } ]
    create_and_save_products(products, site='MySite', output_dir='./output')
"""
from pathlib import Path
import os
import pandas as pd
from datetime import datetime
from inventory.UI.product_editor import product_editor_interactive


def _map_product_to_shopsite_row(product, date_string):
    """Map friendly product dict to ShopSite column names used in master.save_incremental_results."""
    brand = product.get('Brand', '')
    name = product.get('Name', '')
    sku = str(product.get('SKU', ''))
    weight = product.get('Weight', '')
    price = product.get('Price', '')

    # File name and Graphics - mimic master behavior but keep simple (no HTML creation here)
    file_name = f"{sku}.jpg"

    row = {
        'SKU': sku,
        'Name': name,
        'Product Description': product.get('Product Description', ''),
        'Price': price,
        'Weight': weight,
        'Product Field 16': brand,
        'File name': file_name,
        'Graphic': f"{brand}/{file_name}" if brand else file_name,
        'More Information Graphic': f"{brand}/{file_name}" if brand else file_name,
        'Product Field 1': f"new{date_string}",
        'Product Field 11': 'yes' if product.get('Special Order', '').lower() == 'yes' else ''
    }

    # Add up to 5 More Information Image columns
    image_urls = product.get('Image URLs', []) or []
    for i in range(1, 6):
        if i - 1 < len(image_urls) and image_urls[i-1]:
            local_image_path = f"{brand}/{sku.replace('.jpg','')}-{i}.jpg"
            row[f'More Information Image {i}'] = local_image_path
        else:
            row[f'More Information Image {i}'] = 'none'

    # Facet fields
    row['Product Field 24'] = product.get('Category', '')
    row['Product Field 25'] = product.get('Product Type', '')
    row['Product On Pages'] = product.get('Product On Pages', '')
    row['Product Field 32'] = product.get('Product Cross Sell', '')
    row['ProductDisabled'] = product.get('ProductDisabled', '')

    return row


def create_and_save_products(products_list, site, output_dir=None):
    """Create ShopSite Excel file from products_list.

    products_list: list of product dicts (friendly keys)
    site: source site name (used for filename)
    output_dir: where to save file (defaults to inventory/classify/output)
    Returns path to saved file.
    """
    if not products_list:
        raise ValueError("products_list must contain at least one product")

    # Prepare output directory
    base_dir = Path(output_dir) if output_dir else (Path(__file__).parent / 'output')
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = base_dir / f"{site.replace(' ','_').lower()}_{timestamp}.xlsx"

    date_string = datetime.now().strftime('%m%d%y')
    rows = []
    for p in products_list:
        rows.append(_map_product_to_shopsite_row(p, date_string))

    df = pd.DataFrame(rows)
    df.to_excel(out_path, index=False, engine='openpyxl')
    return str(out_path)


def append_row_to_site_file(row: dict, site: str, output_dir=None):
    """Append a single mapped ShopSite row to the site's spreadsheet (like master.save_incremental_results)."""
    base_dir = Path(output_dir) if output_dir else (Path(__file__).parent / 'output')
    base_dir.mkdir(parents=True, exist_ok=True)
    site_file = base_dir / f"{site.replace(' ','-').lower()}.xlsx"

    # Determine columns used by master.save_incremental_results
    more_info_cols = [f'More Information Image {i}' for i in range(1, 6)]
    columns = ['SKU', 'Name', 'Product Description', 'Price', 'Weight', 'Product Field 16', 'File name', 'Graphic', 'More Information Graphic', 'Product Field 1', 'Product Field 11'] \
              + more_info_cols \
              + ['Product Field 24', 'Product Field 25', 'Product On Pages', 'Product Field 32', 'ProductDisabled']

    if site_file.exists():
        try:
            site_df = pd.read_excel(site_file, dtype=str)
        except Exception:
            site_df = pd.DataFrame(columns=columns)
    else:
        site_df = pd.DataFrame(columns=columns)

    # Ensure all columns exist on the row (fill missing with '')
    for col in columns:
        if col not in row:
            row[col] = ''

    site_df = pd.concat([site_df, pd.DataFrame([row])], ignore_index=True)
    site_df.to_excel(site_file, index=False, engine='openpyxl')
    return str(site_file)


def create_new_product_via_editor(output_dir=None):
    """Open the interactive product editor with an empty product, then prompt for site and append the result to the site's spreadsheet.

    Returns path to the site file or None if cancelled.
    """
    # Template product expected by editor
    template = {
        'SKU': '',
        'Name': '',
        'Brand': '',
        'Weight': '',
        'Image URLs': [],
        'Category': '',
        'Product Type': '',
        'Product On Pages': '',
        'Special Order': '',
        'Product Disabled': '',
        'Product Cross Sell': ''
    }

    edited = product_editor_interactive(template)
    if not edited:
        return None

    # Prompt for site name after successful editing
    site = input("🏷️ Enter site name (e.g., 'Bradley_Caldwell'): ").strip()
    if not site:
        print("❌ No site name provided. Product not saved.")
        return None

    # Map to ShopSite row and append
    date_string = datetime.now().strftime('%m%d%y')
    mapped = _map_product_to_shopsite_row(edited, date_string)
    site_path = append_row_to_site_file(mapped, site, output_dir=output_dir)
    return site_path


if __name__ == '__main__':
    # Quick demo
    demo = [
        {'SKU': 'DEMO1', 'Name': 'Demo Product 1', 'Brand': 'DemoBrand', 'Image URLs': ['https://example.com/1.jpg'], 'Category': 'Dog Food', 'Product Type': 'Dry'},
        {'SKU': 'DEMO2', 'Name': 'Demo Product 2', 'Brand': 'DemoBrand', 'Image URLs': ['https://example.com/2.jpg','https://example.com/2b.jpg'], 'Category': 'Cat Food', 'Product Type': 'Wet'},
    ]
    out = create_and_save_products(demo, 'DemoSite')
    print(f"Saved demo products to: {out}")
