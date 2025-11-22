"""
SKU Loader Module

Loads SKUs from Excel files for scraping operations.
"""

import pandas as pd
from pathlib import Path


class SKULoader:
    """Utility class to load SKUs from Excel files."""

    def __init__(self, sku_column: str = "SKU"):
        """
        Initialize SKU loader.

        Args:
            sku_column: Name of the column containing SKUs
        """
        self.sku_column = sku_column

    def load(self, file_path: str | Path) -> list[str]:
        """
        Load SKUs from an Excel file.

        Args:
            file_path: Path to Excel file (.xlsx, .xls)

        Returns:
            List of SKU strings

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If SKU column not found or file is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        try:
            # Read Excel file
            df = pd.read_excel(file_path)

            # Check if SKU column exists
            if self.sku_column not in df.columns:
                available_cols = ", ".join(df.columns)
                raise ValueError(
                    f"SKU column '{self.sku_column}' not found. Available columns: {available_cols}"
                )

            # Extract SKUs and convert to strings
            skus = df[self.sku_column].dropna().astype(str).tolist()

            # Remove any empty strings
            skus = [sku.strip() for sku in skus if sku.strip()]

            return skus

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to load Excel file: {e}") from e

    def load_with_context(self, file_path: str | Path) -> list[dict[str, str]]:
        """
        Load SKUs with additional context columns from Excel.

        Args:
            file_path: Path to Excel file

        Returns:
            List of dicts with SKU and any other columns as context

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If SKU column not found or file is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        try:
            # Read Excel file
            df = pd.read_excel(file_path)

            # Check if SKU column exists
            if self.sku_column not in df.columns:
                available_cols = ", ".join(df.columns)
                raise ValueError(
                    f"SKU column '{self.sku_column}' not found. Available columns: {available_cols}"
                )

            # Convert to list of dicts
            records = df.to_dict("records")

            # Filter out rows without SKU
            records = [r for r in records if pd.notna(r.get(self.sku_column))]

            # Convert all values to strings and strip whitespace
            for record in records:
                for key, value in record.items():
                    if pd.notna(value):
                        record[key] = str(value).strip()
                    else:
                        record[key] = ""

            return records

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to load Excel file: {e}") from e
