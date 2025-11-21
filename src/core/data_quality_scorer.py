"""
Data Quality Scoring Module

This module provides algorithms to score the quality of scraped product data.
It evaluates completeness, accuracy, and consistency against validation criteria.
"""

import re
from typing import Any
from urllib.parse import urlparse


class DataQualityScorer:
    """
    Class for scoring data quality of product records.
    """

    REQUIRED_FIELDS = [
        "SKU",
        "Name",
        "Price",
        "Images",
        "Weight",
        "Product_Field_16",  # Brand
        "Product_Field_24",  # Category
        "Product_Field_25",  # Product Type
    ]

    INVALID_VALUES = {"", "N/A", "null", "NULL", None}

    # Weight conversion factors to LB
    WEIGHT_UNITS = {
        "lb": 1.0,
        "lbs": 1.0,
        "oz": 1 / 16.0,
        "kg": 2.20462,
        "g": 0.00220462,
        "gram": 0.00220462,
        "grams": 0.00220462,
    }

    def __init__(self):
        pass

    def score_record(self, record: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        """
        Score a single product record.

        Args:
            record: Dictionary containing product data

        Returns:
            Tuple of (overall_score, details_dict)
        """
        completeness_score, completeness_details = self._score_completeness(record)
        accuracy_score, accuracy_details = self._score_accuracy(record)
        consistency_score, consistency_details = self._score_consistency(record)

        # Weighted overall score: 40% completeness, 40% accuracy, 20% consistency
        overall_score = 0.4 * completeness_score + 0.4 * accuracy_score + 0.2 * consistency_score

        details = {
            "completeness": {
                "score": completeness_score,
                "details": completeness_details,
            },
            "accuracy": {"score": accuracy_score, "details": accuracy_details},
            "consistency": {"score": consistency_score, "details": consistency_details},
            "overall": overall_score,
        }

        return overall_score, details

    def is_high_quality(self, score: float, threshold: float = 85.0) -> bool:
        """
        Check if score meets high quality threshold.

        Args:
            score: Quality score (0-100)
            threshold: Minimum threshold (default 85%)

        Returns:
            True if score >= threshold
        """
        return score >= threshold

    def _score_completeness(self, record: dict[str, Any]) -> tuple[float, Any]:
        """
        Score completeness: Check if required fields are present and valid.

        Returns:
            Tuple of (score_0_100, details_dict)
        """
        total_fields = len(self.REQUIRED_FIELDS)
        valid_fields = 0
        details = {}

        for field in self.REQUIRED_FIELDS:
            value = record.get(field)
            is_valid = self._is_field_valid(value, field)
            details[field] = {"present": value is not None, "valid": is_valid}
            if is_valid:
                valid_fields += 1

        score = (valid_fields / total_fields) * 100
        return score, details

    def _score_accuracy(self, record: dict[str, Any]) -> tuple[float, Any]:
        """
        Score accuracy: Check weight normalization, URL validity, etc.

        Returns:
            Tuple of (score_0_100, details_dict)
        """
        score_components = []
        details = {}

        # Weight accuracy
        weight_value = record.get("Weight", "")
        weight_score, weight_details = self._score_weight_accuracy(weight_value)
        score_components.append(weight_score)
        details["weight"] = weight_details

        # Image URLs accuracy
        images_value = record.get("Images", "")
        images_score, images_details = self._score_images_accuracy(images_value)
        score_components.append(images_score)
        details["images"] = images_details

        # Price accuracy (basic numeric check)
        price_value = record.get("Price", "")
        price_score, price_details = self._score_price_accuracy(price_value)
        score_components.append(price_score)
        details["price"] = price_details

        # Average of components
        overall_score = sum(score_components) / len(score_components) if score_components else 0
        return overall_score, details

    def _score_consistency(self, record: dict[str, Any]) -> tuple[float, Any]:
        """
        Score consistency: Check formats and patterns.

        Returns:
            Tuple of (score_0_100, details_dict)
        """
        score_components = []
        details = {}

        # SKU format (alphanumeric, reasonable length)
        sku_value = record.get("SKU", "")
        sku_consistent = self._is_sku_consistent(sku_value)
        score_components.append(100 if sku_consistent else 0)
        details["sku_format"] = sku_consistent

        # Name format (not just numbers, reasonable length)
        name_value = record.get("Name", "")
        name_consistent = self._is_name_consistent(name_value)
        score_components.append(100 if name_consistent else 0)
        details["name_format"] = name_consistent

        # Brand/Category/Product Type consistency (not empty, reasonable)
        brand_value = record.get("Product_Field_16", "")
        category_value = record.get("Product_Field_24", "")
        product_type_value = record.get("Product_Field_25", "")

        brand_consistent = self._is_text_field_consistent(brand_value)
        category_consistent = self._is_text_field_consistent(category_value)
        product_type_consistent = self._is_text_field_consistent(product_type_value)

        score_components.extend(
            [
                100 if brand_consistent else 0,
                100 if category_consistent else 0,
                100 if product_type_consistent else 0,
            ]
        )

        details.update(
            {
                "brand_format": brand_consistent,
                "category_format": category_consistent,
                "product_type_format": product_type_consistent,
            }
        )

        overall_score = sum(score_components) / len(score_components) if score_components else 0
        return overall_score, details

    def _is_field_valid(self, value: Any, field_name: str = "") -> bool:
        """Check if a field value is valid (not invalid and has meaningful content)."""
        if value in self.INVALID_VALUES:
            return False
        if isinstance(value, str):
            stripped = value.strip()
            if stripped in self.INVALID_VALUES:
                return False
            # Additional checks for meaningless content
            if stripped.lower() in {"invalid", "not-a-url", "n/a", "none", "null"}:
                return False
            # For price, check if it contains digits
            if field_name.lower() == "price" and not any(c.isdigit() for c in stripped):
                return False
            # For images, check if it contains http
            if field_name.lower() == "images" and "http" not in stripped.lower():
                return False
        return True

    def _score_weight_accuracy(self, weight_str: str) -> tuple[float, dict[str, Any]]:
        """Score weight field accuracy and normalization."""
        if not weight_str or weight_str.strip() in self.INVALID_VALUES:
            return 0, {"normalized": None, "valid": False}

        try:
            normalized_lb = self._normalize_weight_to_lb(weight_str)
            if normalized_lb is not None and normalized_lb > 0:
                return 100, {"normalized": f"{normalized_lb:.2f} lb", "valid": True}
            else:
                return 0, {"normalized": None, "valid": False}
        except:
            return 0, {"normalized": None, "valid": False}

    def _normalize_weight_to_lb(self, weight_str: str) -> float | None:
        """Parse weight string and convert to LB."""
        weight_str = weight_str.strip().lower()

        # Match patterns like "5 lb", "10.5 oz", "2 kg"
        match = re.match(r"^(\d+(?:\.\d+)?)\s*(lb|lbs|oz|kg|g|gram|grams)?$", weight_str)
        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2) or "lb"  # Default to lb if no unit

        if unit in self.WEIGHT_UNITS:
            return value * self.WEIGHT_UNITS[unit]
        return None

    def _score_images_accuracy(self, images_str: str) -> tuple[float, Any]:
        """Score images field accuracy (valid URLs)."""
        if not images_str or images_str.strip() in self.INVALID_VALUES:
            return 0, {"valid_urls": 0, "total_urls": 0, "percentage": 0}

        urls = [url.strip() for url in images_str.split(",") if url.strip()]
        if not urls:
            return 0, {"valid_urls": 0, "total_urls": 0, "percentage": 0}

        valid_count = sum(1 for url in urls if self._is_valid_url(url))
        percentage = (valid_count / len(urls)) * 100

        return percentage, {
            "valid_urls": valid_count,
            "total_urls": len(urls),
            "percentage": percentage,
        }

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid HTTP/HTTPS."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except:
            return False

    def _score_price_accuracy(self, price_str: str) -> tuple[float, Any]:
        """Score price field accuracy (numeric format)."""
        if not price_str or price_str.strip() in self.INVALID_VALUES:
            return 0, {"numeric": False, "value": None}

        try:
            # Remove currency symbols and commas
            clean_price = re.sub(r"[^\d.]", "", price_str)
            price_value = float(clean_price)
            return 100 if price_value >= 0 else 0, {
                "numeric": True,
                "value": price_value,
            }
        except:
            return 0, {"numeric": False, "value": None}

    def _is_sku_consistent(self, sku: str) -> bool:
        """Check SKU format consistency."""
        if not sku or sku in self.INVALID_VALUES:
            return False
        # Alphanumeric, dashes, underscores, reasonable length
        return bool(re.match(r"^[A-Za-z0-9\-_]{1,50}$", sku))

    def _is_name_consistent(self, name: str) -> bool:
        """Check name format consistency."""
        if not name or name in self.INVALID_VALUES:
            return False
        # Not just numbers, reasonable length
        if re.match(r"^\d+$", name):
            return False
        return 1 <= len(name) <= 200

    def _is_text_field_consistent(self, value: str) -> bool:
        """Check text field consistency."""
        if not value or value in self.INVALID_VALUES:
            return False
        return 1 <= len(value.strip()) <= 100


# Convenience functions
def score_product_data(record: dict[str, Any]) -> tuple[float, Any]:
    """
    Score a single product record using DataQualityScorer.

    Args:
        record: Product data dictionary

    Returns:
        Tuple of (score, details)
    """
    scorer = DataQualityScorer()
    return scorer.score_record(record)


def is_product_high_quality(record: dict[str, Any], threshold: float = 85.0) -> bool:
    """
    Check if product data meets quality threshold.

    Args:
        record: Product data dictionary
        threshold: Quality threshold (default 85%)

    Returns:
        True if high quality
    """
    score, _ = score_product_data(record)
    return score >= threshold
