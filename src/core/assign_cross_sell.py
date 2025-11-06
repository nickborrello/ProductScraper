import pandas as pd
import sys
import random

# Fields and scoring weights
NAME_FIELD = "Name"
PRODUCT_TYPE_FIELD = "Product Field 25"
CATEGORY_FIELD = "Product Field 24"
BRAND_FIELD = "Product Field 16"
PAGES_FIELD = "Product On Pages"
CROSS_SELL_FIELD = "Product Field 32"
SKU_FIELD = "SKU"
SUBPRODUCTS_FIELD = "Subproducts"
MAX_CROSS_SELLS = 4

SCORING_WEIGHTS = {
    PRODUCT_TYPE_FIELD: 4,
    CATEGORY_FIELD: 3,
    BRAND_FIELD: 1,
    PAGES_FIELD: 2  # per shared page
}
REQUIRED_FIELDS = [NAME_FIELD, SKU_FIELD, PRODUCT_TYPE_FIELD, CATEGORY_FIELD, BRAND_FIELD, PAGES_FIELD]


def clean_df(df):
    # Robust column detection and auto-rename
    def find_col(target):
        for col in df.columns:
            if col.strip().lower() == target.strip().lower():
                return col
        return None

    col12 = find_col('Product Field 12')
    col_sub = find_col('Subproducts')
    # Always keep required fields, cross sell, and subproducts if present
    # Robust column detection and auto-rename
    def find_col(target):
        for col in df.columns:
            if col.strip().lower() == target.strip().lower():
                return col
        return None

    actions = []
    col12 = find_col('Product Field 12')
    col_sub = find_col('Subproducts')
    missing = []
    if col12 is None:
        missing.append('Product Field 12')
    if col_sub is None:
        missing.append('Subproducts')
    if missing:
        print("❌ ERROR: The following required column(s) are missing from the input file:", ", ".join(missing))
        print("Available columns (showing repr to reveal hidden whitespace):")
        for c in df.columns.tolist():
            print(f"  - {repr(c)}")
        print("\nGuidance: \n - Ensure the exact header names exist: 'Product Field 12' and 'Subproducts'.\n - Remove leading/trailing spaces from headers.\n - If the header looks identical in Excel, try saving a fresh copy/exporting to .xlsx to clear hidden formatting.\n - If you want, rename the matching header in Excel to exactly 'Product Field 12' and 'Subproducts' and retry.")
        sys.exit(1)
    # Auto-rename fuzzy matches
    if col12 != 'Product Field 12':
        df.rename(columns={col12: 'Product Field 12'}, inplace=True)
        actions.append(f"Renamed column {repr(col12)} → 'Product Field 12'")
    if col_sub != 'Subproducts':
        df.rename(columns={col_sub: 'Subproducts'}, inplace=True)
        actions.append(f"Renamed column {repr(col_sub)} → 'Subproducts'")

    # Only keep necessary columns for cross-sell assignment and reporting
    keep_cols = [SKU_FIELD, NAME_FIELD, PRODUCT_TYPE_FIELD, CATEGORY_FIELD, BRAND_FIELD, PAGES_FIELD, CROSS_SELL_FIELD, 'Subproducts', 'Product Field 12']
    keep_cols = [col for col in keep_cols if col in df.columns]
    df = df[keep_cols].copy()
    # Trim whitespace
    for col in REQUIRED_FIELDS:
        df[col] = df[col].astype(str).str.strip()
    # Drop rows where both SKU and Name are empty
    df = df[(df[SKU_FIELD] != "") | (df[NAME_FIELD] != "")]
    # Count subproducts and out-of-stock before filtering
    subproduct_skus = set()
    for subproducts in df['Subproducts'].dropna():
        for entry in str(subproducts).split("|"):
            parts = entry.split("~")
            if len(parts) == 2:
                sub_sku = parts[1].strip()
                subproduct_skus.add(sub_sku)
    subproduct_count = len(subproduct_skus)
    # Count out-of-stock before filtering
    out_of_stock_count = int(df['Product Field 12'].fillna('').str.strip().str.lower().eq('yes').sum())
    actions.append(f"Excluding {subproduct_count} subproduct SKUs from cross-sell candidates.")
    actions.append(f"Excluding {out_of_stock_count} out-of-stock products (Product Field 12 = yes) from cross-sell candidates.")
    # Exclude out-of-stock
    df = df[df['Product Field 12'].fillna('').str.strip().str.lower() != 'yes']
    df = df.drop_duplicates(subset=[SKU_FIELD])
    print("CLEANING SUMMARY:")
    for act in actions:
        print(f"  - {act}")
    return df

def get_all_subproduct_skus(df):
    subproduct_skus = set()
    if SUBPRODUCTS_FIELD in df.columns:
        for subproducts in df[SUBPRODUCTS_FIELD].dropna():
            for entry in str(subproducts).split("|"):
                parts = entry.split("~")
                if len(parts) == 2:
                    sub_sku = parts[1].strip()
                    subproduct_skus.add(sub_sku)
    # Only print summary once in clean_df
    return subproduct_skus

def get_column_name(df, target):
    for col in df.columns:
        if col.strip().lower() == target.strip().lower():
            return col
    return None

def get_cleaned_parent_products(df):
    # Build a set of SKUs to exclude (all subproducts except the current row's SKU)
    exclude_skus = set()
    if SUBPRODUCTS_FIELD in df.columns:
        for idx, row in df.iterrows():
            sku = str(row[SKU_FIELD]).strip()
            if pd.notna(row[SUBPRODUCTS_FIELD]) and row[SUBPRODUCTS_FIELD]:
                for entry in str(row[SUBPRODUCTS_FIELD]).split("|"):
                    parts = entry.split("~")
                    if len(parts) == 2:
                        sub_sku = parts[1].strip()
                        if sub_sku != sku:
                            exclude_skus.add(sub_sku)
    # Only keep rows where SKU is not in exclude_skus
    cleaned_df = df[~df[SKU_FIELD].isin(exclude_skus)].copy()
    return cleaned_df

def assign_cross_sell(df, max_cross_sells=4):
    import concurrent.futures
    import os
    print(f"Assigning cross sells using scoring algorithm (multiprocessing).")
    # If input is a DataFrame, use as is. If string, treat as filename and read/clean.
    if isinstance(df, str):
        input_file = df
        if not os.path.exists(input_file):
            print(f"❌ ERROR: Input file {input_file} not found.")
            sys.exit(1)
        df = pd.read_excel(input_file, dtype={SKU_FIELD: str})
        df = clean_df(df)
    else:
        df = clean_df(df)
    # Drop all excess columns before assignment for speed
    # Remove out-of-stock products before assignment so they never appear as cross-sells
    if 'Product Field 12' in df.columns:
        df = df[df['Product Field 12'].fillna('').str.strip().str.lower() != 'yes']
    df = df[[SKU_FIELD, PRODUCT_TYPE_FIELD, CATEGORY_FIELD, BRAND_FIELD, PAGES_FIELD, CROSS_SELL_FIELD, 'Subproducts', 'Product Field 12'] if 'Product Field 12' in df.columns else [SKU_FIELD, PRODUCT_TYPE_FIELD, CATEGORY_FIELD, BRAND_FIELD, PAGES_FIELD, CROSS_SELL_FIELD, 'Subproducts']]
    total = len(df)
    all_subproduct_skus = get_all_subproduct_skus(df)
    if not hasattr(assign_cross_sell, "num_threads"):
        assign_cross_sell.num_threads = 4

    def process_row(row_idx_row):
        row_idx, row = row_idx_row
        main_sku = str(row[SKU_FIELD])
        main_product_type = str(row[PRODUCT_TYPE_FIELD])
        main_category = str(row[CATEGORY_FIELD])
        main_brand = str(row[BRAND_FIELD])
        main_pages = set([p.strip() for p in str(row[PAGES_FIELD]).split("|") if p.strip()])
        if all([main_product_type == "", main_category == "", main_brand == "", not main_pages]):
            return ""
        candidates = df[~df[SKU_FIELD].isin(all_subproduct_skus)]
        candidates = candidates[candidates[SKU_FIELD] != main_sku]
        scores = []
        for _, crow in candidates.iterrows():
            score = 0
            if main_product_type != "" and str(crow[PRODUCT_TYPE_FIELD]) == main_product_type:
                score += SCORING_WEIGHTS[PRODUCT_TYPE_FIELD]
            if main_category != "" and str(crow[CATEGORY_FIELD]) == main_category:
                score += SCORING_WEIGHTS[CATEGORY_FIELD]
            if main_brand != "" and str(crow[BRAND_FIELD]) == main_brand:
                score += SCORING_WEIGHTS[BRAND_FIELD]
            candidate_pages = set([p.strip() for p in str(crow[PAGES_FIELD]).split("|") if p.strip()])
            shared_pages = main_pages & candidate_pages
            score += SCORING_WEIGHTS[PAGES_FIELD] * len(shared_pages)
            scores.append((str(crow[SKU_FIELD]), score))
        scores.sort(key=lambda x: x[1], reverse=True)
        top_16 = [sku for sku, s in scores if s > 0][:16]
        top_skus = random.sample(top_16, min(max_cross_sells, len(top_16))) if top_16 else []
        return "|".join(top_skus)

    import time
    cross_sells = [None] * total
    start_time = time.time()
    def update_progress(n):
        if n % 100 == 0 or n == total:
            elapsed = time.time() - start_time
            avg_time = elapsed / n if n > 0 else 0
            remaining = (total - n) * avg_time
            mins, secs = divmod(int(remaining), 60)
            print(f"Processed {n}/{total} products... Estimated time remaining: {mins}m {secs}s")

    rows = list(df.iterrows())
    for idx, (row_idx, row) in enumerate(rows):
        cross_sells[idx] = _process_row_mp((row_idx, row, df, all_subproduct_skus, max_cross_sells))
        update_progress(idx + 1)
    df[CROSS_SELL_FIELD] = cross_sells
    print(f"Finished assigning cross sells for {total} products.")
    # Output file should only contain SKU and Product Field 32
    return df[[SKU_FIELD, CROSS_SELL_FIELD]]

# Helper for multiprocessing: must be top-level for pickling
def _process_row_mp(args):
    row_idx, row, df, all_subproduct_skus, max_cross_sells = args
    NAME_FIELD = "Name"
    PRODUCT_TYPE_FIELD = "Product Field 25"
    CATEGORY_FIELD = "Product Field 24"
    BRAND_FIELD = "Product Field 16"
    PAGES_FIELD = "Product On Pages"
    CROSS_SELL_FIELD = "Product Cross Sell"
    SKU_FIELD = "SKU"
    SCORING_WEIGHTS = {
        PRODUCT_TYPE_FIELD: 4,
        CATEGORY_FIELD: 3,
        BRAND_FIELD: 1,
        PAGES_FIELD: 2
    }
    main_sku = str(row[SKU_FIELD])
    main_product_type = str(row[PRODUCT_TYPE_FIELD])
    main_category = str(row[CATEGORY_FIELD])
    main_brand = str(row[BRAND_FIELD])
    main_pages = set([p.strip() for p in str(row[PAGES_FIELD]).split("|") if p.strip()])
    if all([main_product_type == "", main_category == "", main_brand == "", not main_pages]):
        return ""
    candidates = df[~df[SKU_FIELD].isin(all_subproduct_skus)]
    if 'Product Field 12' in candidates.columns:
        candidates = candidates[candidates['Product Field 12'].str.strip().str.lower() != 'yes']
    candidates = candidates[candidates[SKU_FIELD] != main_sku]
    scores = []
    for _, crow in candidates.iterrows():
        score = 0
        if main_product_type != "" and str(crow[PRODUCT_TYPE_FIELD]) == main_product_type:
            score += SCORING_WEIGHTS[PRODUCT_TYPE_FIELD]
        if main_category != "" and str(crow[CATEGORY_FIELD]) == main_category:
            score += SCORING_WEIGHTS[CATEGORY_FIELD]
        if main_brand != "" and str(crow[BRAND_FIELD]) == main_brand:
            score += SCORING_WEIGHTS[BRAND_FIELD]
        candidate_pages = set([p.strip() for p in str(crow[PAGES_FIELD]).split("|") if p.strip()])
        shared_pages = main_pages & candidate_pages
        score += SCORING_WEIGHTS[PAGES_FIELD] * len(shared_pages)
        scores.append((str(crow[SKU_FIELD]), score))
    scores.sort(key=lambda x: x[1], reverse=True)
    top_16 = [sku for sku, s in scores if s > 0][:16]
    top_skus = random.sample(top_16, min(max_cross_sells, len(top_16))) if top_16 else []
    return "|".join(top_skus)
    df[CROSS_SELL_FIELD] = cross_sells
    print(f"Finished assigning cross sells for {total} products.")
    return df

def main(input_file):
    df = pd.read_excel(input_file, dtype={SKU_FIELD: str})
    df = clean_df(df)
    df = get_cleaned_parent_products(df)
    df_orig = df.copy()
    if hasattr(main, "benchmark") and main.benchmark:
        import time
        thread_options = [1, 2, 4, 8, 16]
        print("Benchmarking thread counts: ", thread_options)
        for threads in thread_options:
            print(f"\nTesting with {threads} threads...")
            assign_cross_sell.num_threads = threads
            df = df_orig.copy()
            start = time.time()
            assign_cross_sell(df)
            elapsed = time.time() - start
            mins, secs = divmod(int(elapsed), 60)
            print(f"Completed in {mins}m {secs}s with {threads} threads.")
        print("\nBenchmarking complete.")
    else:
        df = assign_cross_sell(df)
        output_file = "cross_sells_for_shopsite.xlsx"
        print(f"Saving ShopSite cross sell file: {output_file}")
        df[[SKU_FIELD, CROSS_SELL_FIELD]].to_excel(output_file, index=False)
        print(f"ShopSite cross sell file saved as {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python util/assign_cross_sell.py website.xlsx [num_threads|--benchmark]")
        sys.exit(1)
    input_file = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--benchmark":
        main.benchmark = True
        assign_cross_sell.num_threads = 4  # default for progress reporting
        main(input_file)
    else:
        # Default to 4 threads if not specified
        num_threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        assign_cross_sell.num_threads = num_threads
        main(input_file)
