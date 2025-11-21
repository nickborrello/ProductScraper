"""
Scraper output validation utilities for testing and debugging.
"""

import re
from typing import Any

import pandas as pd


class ScraperValidator:
    """Validates scraper output data format and content."""

    def __init__(self, test_data_path: str | None = None):
        """Initialize validator with test data configuration."""
        # Define common validation rules internally
        self.common_rules = {
            "required_fields": ["SKU", "Name"],
            "weight_unit": "LB",
            "image_format": "list_of_urls",
            "price_format": "string",
            "invalid_values": ["N/A", "n/a", "NA", "null", "NULL", ""],
        }

        # Define expected fields for each scraper
        self.expected_fields = {
            "amazon": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "bradley": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "central_pet": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "coastal": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "mazuri": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "petfoodex": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "phillips": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
            "orgill": ["SKU", "Name", "Brand", "Weight", "Image URLs"],
        }

    def validate_product_data(self, products: list[dict], scraper_name: str) -> dict[str, Any]:
        """
        Validate a list of product dictionaries from a scraper.

        Args:
            products: List of product dictionaries
            scraper_name: Name of the scraper

        Returns:
            Dict with validation results and any errors found
        """
        results = {
            "scraper": scraper_name,
            "total_products": len(products),
            "valid_products": 0,
            "invalid_products": 0,
            "errors": [],
            "warnings": [],
            "field_coverage": {},
            "data_quality_score": 0.0,
        }

        if not products:
            results["errors"].append("No products returned")
            return results

        expected_fields = self.expected_fields.get(scraper_name, [])

        # Track field coverage
        field_counts = {field: 0 for field in expected_fields}

        for i, product in enumerate(products):
            if not isinstance(product, dict):
                results["errors"].append(f"Product {i}: Not a dictionary (type: {type(product)})")
                results["invalid_products"] += 1
                continue

            product_valid = True
            product_errors = []
            product_warnings = []

            # Check required fields
            for field in self.common_rules.get("required_fields", []):
                if field not in product or product[field] is None:
                    product_errors.append(f"Missing required field: {field}")
                    product_valid = False
                elif str(product[field]).strip() in self.common_rules.get("invalid_values", []):
                    product_errors.append(
                        f"Invalid value for required field {field}: '{product[field]}'"
                    )
                    product_valid = False
                # Note: field_counts increment moved to expected fields loop below

            # Check expected fields
            for field in expected_fields:
                if field in product:
                    field_counts[field] += 1

                    # Field-specific validation
                    if field == "SKU" and not self._validate_sku(product[field]):
                        product_warnings.append(f"SKU format may be invalid: {product[field]}")

                    elif field == "Price" and not self._validate_price(product[field]):
                        product_warnings.append(f"Price format may be invalid: {product[field]}")

                    elif field == "Images" and not self._validate_images(product[field]):
                        product_warnings.append(f"Images format may be invalid: {product[field]}")

                    elif field == "Weight" and not self._validate_weight(product[field]):
                        product_warnings.append(f"Weight format may be invalid: {product[field]}")

            if product_valid:
                results["valid_products"] += 1
            else:
                results["invalid_products"] += 1
                results["errors"].extend([f"Product {i}: {err}" for err in product_errors])

            if product_warnings:
                results["warnings"].extend([f"Product {i}: {warn}" for warn in product_warnings])

        # Calculate field coverage percentages
        results["field_coverage"] = {
            field: (
                (count / results["total_products"]) * 100 if results["total_products"] > 0 else 0
            )
            for field, count in field_counts.items()
        }

        # Calculate data quality score (0-100)
        if results["total_products"] > 0:
            valid_ratio = results["valid_products"] / results["total_products"]
            field_coverage_avg = (
                sum(results["field_coverage"].values()) / len(results["field_coverage"])
                if results["field_coverage"]
                else 0
            )
            results["data_quality_score"] = valid_ratio * 0.6 + (field_coverage_avg / 100) * 0.4

        return results

    def validate_dataframe_output(self, df: pd.DataFrame, scraper_name: str) -> dict[str, Any]:
        """
        Validate pandas DataFrame output from scraper.

        Args:
            df: Pandas DataFrame with product data
            scraper_name: Name of the scraper

        Returns:
            Dict with validation results
        """
        results = {
            "scraper": scraper_name,
            "dataframe_shape": df.shape,
            "columns": list(df.columns),
            "errors": [],
            "warnings": [],
        }

        if df.empty:
            results["errors"].append("DataFrame is empty")
            return results

        expected_fields = self.expected_fields.get(scraper_name, [])

        # Check for expected columns
        missing_columns = set(expected_fields) - set(df.columns)
        if missing_columns:
            results["warnings"].append(f"Missing expected columns: {list(missing_columns)}")

        # Check for required columns
        required_fields = self.common_rules.get("required_fields", [])
        missing_required = set(required_fields) - set(df.columns)
        if missing_required:
            results["errors"].append(f"Missing required columns: {list(missing_required)}")

        # Validate each row
        for idx, row in df.iterrows():
            row_errors = []
            for field in required_fields:
                if field in df.columns:
                    value = row[field]
                    if pd.isna(value) or str(value).strip() in self.common_rules.get(
                        "invalid_values", []
                    ):
                        row_errors.append(f"Row {idx}: Invalid {field} value: '{value}'")

            if row_errors:
                results["errors"].extend(row_errors)

        return results

    def _validate_sku(self, sku: Any) -> bool:
        """Validate SKU format."""
        if not sku:
            return False
        sku_str = str(sku).strip()
        # Basic SKU validation - not empty and reasonable length
        return 1 <= len(sku_str) <= 50

    def _validate_price(self, price: Any) -> bool:
        """Validate price format."""
        if not price:
            return False
        price_str = str(price).strip()
        # Allow various price formats: $10.99, 10.99, 10, etc.
        price_pattern = r"^\$?\d+(\.\d{1,2})?$"
        return bool(re.match(price_pattern, price_str))

    def _validate_images(self, images: Any) -> bool:
        """Validate images format (list of URLs)."""
        if not images:
            return False

        # Handle both "Images" and "Image URLs" field names
        if isinstance(images, list):
            image_list = images
        elif isinstance(images, str):
            # If it's a string, it might be comma-separated
            image_list = [url.strip() for url in images.split(",") if url.strip()]
        else:
            return False

        if not image_list:
            return False

        # Check that all items are valid URLs
        url_pattern = r"^https?://[^\s,]+$"
        return all(re.match(url_pattern, str(url)) for url in image_list if url)

    def _validate_weight(self, weight: Any) -> bool:
        """Validate weight format (should be in LB units)."""
        if not weight:
            return False
        weight_str = str(weight).strip().upper()

        # Check for LB unit
        if "LB" not in weight_str and "POUND" not in weight_str:
            return False

        # Extract numeric part
        weight_match = re.search(r"(\d+(?:\.\d+)?)", weight_str)
        if not weight_match:
            return False

        weight_value = float(weight_match.group(1))
        # Reasonable weight range for pet products
        return 0.01 <= weight_value <= 1000.0

    def print_validation_report(self, results: dict[str, Any]) -> None:
        """Print a formatted validation report."""
        print(f"\n{'=' * 60}")
        print(f"VALIDATION REPORT: {results['scraper'].upper()}")
        print(f"{'=' * 60}")

        print(f"Total Products: {results['total_products']}")
        print(f"Valid Products: {results['valid_products']}")
        print(f"Invalid Products: {results['invalid_products']}")
        print(f"Data Quality Score: {results['data_quality_score']:.1f}")

        if results.get("dataframe_shape"):
            print(f"DataFrame Shape: {results['dataframe_shape']}")

        if results["field_coverage"]:
            print("\nField Coverage:")
            for field, coverage in results["field_coverage"].items():
                print(f"  {field}: {coverage:.1f}%")

        if results["errors"]:
            print(f"\n❌ ERRORS ({len(results['errors'])}):")
            for error in results["errors"][:10]:  # Show first 10 errors
                print(f"  • {error}")
            if len(results["errors"]) > 10:
                print(f"  ... and {len(results['errors']) - 10} more errors")

        if results["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
            for warning in results["warnings"][:10]:  # Show first 10 warnings
                print(f"  • {warning}")
            if len(results["warnings"]) > 10:
                print(f"  ... and {len(results['warnings']) - 10} more warnings")

        # Overall assessment
        if results["errors"]:
            print("\n❌ VALIDATION FAILED - Fix errors before deployment")
        elif results["warnings"]:
            print("\n⚠️  VALIDATION PASSED WITH WARNINGS - Review warnings")
        else:
            print("\n✅ VALIDATION PASSED - Ready for deployment")

        print(f"{'=' * 60}\n")
