import pandas as pd
import re


def log_error(message):
    print(f"❌ Excel: {message}")


def loose_parse_urls(url_field):
    """Parse image URLs from various formats in Excel cells"""
    if pd.isna(url_field):
        return []

    # Clean up common formatting
    cleaned = (
        str(url_field)
        .replace("[", "")
        .replace("]", "")
        .replace('"', "")
        .replace("'", "")
    )
    # Split on newlines, commas, or semicolons
    parts = re.split(r"[\n,;]", cleaned)
    # Return valid HTTP URLs
    return [p.strip() for p in parts if p.strip() and p.strip().startswith("http")]


def scrape_excel(SKU, driver=None, file_path=None, excel_data=None):
    if driver is None:
        print("❌ Error: WebDriver instance is None. Cannot scrape product.")
        return None
    """
    Excel scraper that extracts product info from the loaded spreadsheet data.
    This doesn't scrape the web - it just parses data from Excel.
    
    Args:
        SKU: The SKU to look up
        driver: Ignored (for compatibility with other scrapers)
        file_path: Ignored (uses excel_data instead)
        excel_data: pandas DataFrame with the Excel data (provided by master scraper)
    
    Returns:
        dict: Product information or None if not found
    """

    try:
        # Use the excel_data passed from master scraper
        if excel_data is None:
            log_error("No Excel data provided to Excel scraper")
            return None

        df = excel_data.copy()

        # Only rename and combine columns, do not add any columns
        if "SKU_NO" in df.columns:
            df["SKU"] = df["SKU_NO"].astype(str)
            print("📋 Renamed SKU_NO -> SKU")
        if "LIST_PRICE" in df.columns:
            df["Price"] = df["LIST_PRICE"]
            print("💰 Renamed LIST_PRICE -> Price")
        if "DESCRIPTION1" in df.columns and "DESCRIPTION2" in df.columns:
            df["Name"] = (
                df["DESCRIPTION1"].astype(str) + " " + df["DESCRIPTION2"].astype(str)
            )
            print("📝 Combined DESCRIPTION1 and DESCRIPTION2 -> Name")
        elif "DESCRIPTION1" in df.columns:
            df["Name"] = df["DESCRIPTION1"].astype(str)
            print("📝 Used DESCRIPTION1 as Name")
        elif "DESCRIPTION2" in df.columns:
            df["Name"] = df["DESCRIPTION2"].astype(str)
            print("📝 Used DESCRIPTION2 as Name")

        # Only keep normalized columns
        normalized_cols = ["SKU", "Name", "Price", "Brand", "Weight", "Image URLs"]
        missing = [col for col in normalized_cols if col not in df.columns]
        if missing:
            log_error(
                f"Missing required columns: {', '.join(missing)}. Please fix the input file."
            )
            return None
        # Only keep the required columns
        df = df[normalized_cols]
        print(f"🧹 Cleaned input: Only keeping columns {normalized_cols}")

        # Normalize SKU column (should already be done by master, but just in case)
        if "SKU" in df.columns:
            df["SKU"] = df["SKU"].astype(str)
        else:
            log_error("Excel data must contain a SKU column")
            return None

        # Find the row for this SKU
        row = df[df["SKU"] == str(SKU)]
        if row.empty:
            return None
        row = row.iloc[0]

        # Check for any empty required columns in this row
        required_cols = ["SKU", "Name", "Price", "Brand", "Weight", "Image URLs"]
        for col in required_cols:
            val = row.get(col, None)
            if pd.isna(val) or str(val).strip() == "":
                print(
                    f"⚠️ Excel: SKU {SKU} missing required field '{col}'. Setting to N/A."
                )
                row[col] = "N/A" if col != "Image URLs" else []

        # Build product info from Excel row data
        product_info = {
            "Brand": str(row["Brand"]).strip(),
            "Name": str(row["Name"]).strip(),
            "Weight": str(row["Weight"]).strip(),
            "Image URLs": loose_parse_urls(row["Image URLs"]),
        }

        # Flag product if it has any placeholders or missing images
        product_info["flagged"] = any(
            value == "N/A" for value in product_info.values() if isinstance(value, str)
        ) or not product_info.get("Image URLs")

        print(f"✅ Excel: Found product data for SKU {SKU}")
        return product_info

    except Exception as e:
        log_error(f"Error processing SKU {SKU}: {e}")
        return None


# Keep backward compatibility functions
def get_product_info(file_path, sku):
    """Original function signature for backward compatibility"""
    try:
        if file_path.endswith(".csv"):
            data = pd.read_csv(file_path, dtype=str)
        elif file_path.endswith(".xlsx"):
            data = pd.read_excel(file_path, dtype=str)
        else:
            return None

        # Auto-convert SKU_NO to SKU if needed
        if "SKU_NO" in data.columns and "SKU" not in data.columns:
            data["SKU"] = data["SKU_NO"].astype(str)
            print("✅ Excel: Converted SKU_NO to SKU.")
        # Auto-convert LIST_PRICE to Price if needed
        if "LIST_PRICE" in data.columns and "Price" not in data.columns:
            data["Price"] = data["LIST_PRICE"]
            print("✅ Excel: Converted LIST_PRICE to Price.")

        # Add required columns if missing
        required_cols = ["SKU", "Brand", "Name", "Weight", "Image URLs", "Price"]
        added_cols = []
        for col in required_cols:
            if col not in data.columns:
                data[col] = ""
                added_cols.append(col)
        if added_cols:
            print(
                f"⚠️ Excel: Added missing columns to spreadsheet: {', '.join(added_cols)}"
            )
            try:
                if file_path.endswith(".xlsx"):
                    # Save and flush to ensure changes are written
                    with pd.ExcelWriter(
                        file_path, engine="openpyxl", mode="w"
                    ) as writer:
                        data.to_excel(writer, index=False)
                        writer.book.save(file_path)
                elif file_path.endswith(".csv"):
                    data.to_csv(file_path, index=False)
                print(f"✅ Excel: Columns added and spreadsheet saved: {file_path}")
            except PermissionError:
                print(
                    f"❌ Excel: Could not save changes. Please close {file_path} in Excel and rerun."
                )
                return None
            except Exception as e:
                print(f"❌ Excel: Error saving updated spreadsheet: {e}")
                return None
            print(f"⚠️ Excel: Please fill in the new columns and rerun.")
            return None

        return scrape_excel(sku, excel_data=data)
    except Exception as e:
        log_error(f"Error loading file {file_path}: {e}")
        return None
