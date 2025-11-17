import json

from src.core.data_quality_scorer import (DataQualityScorer,
                                          is_product_high_quality)


def test_data_quality_gate():
    """
    Tests that the data quality scorer meets a minimum quality threshold.
    """
    with open("tests/fixtures/scraper_test_data.json", "r") as f:
        test_data = json.load(f)

    scorer = DataQualityScorer()
    total_records = 0
    high_quality_records = 0

    for scraper, data in test_data.items():
        if "test_skus" in data:
            for sku in data["test_skus"][:5]:  # Test first 5 SKUs per scraper
                # Mock record with SKU
                record = {
                    "SKU": sku,
                    "Name": f"Test {scraper} product",
                    "Price": "10.99",
                    "Images": "http://example.com/image.jpg",
                    "Weight": "1 lb",
                    "Product_Field_16": "Test Brand",
                    "Product_Field_24": "Test Category",
                    "Product_Field_25": "Test Product Type",
                }
                score, _ = scorer.score_record(record)
                total_records += 1
                if is_product_high_quality(record):
                    high_quality_records += 1

    quality_rate = high_quality_records / total_records if total_records > 0 else 0
    print(
        f"Quality validation: {high_quality_records}/{total_records} records pass quality gate ({quality_rate:.1%})"
    )

    # Quality gate: at least 60% of test records should pass (allowing for incomplete mock data)
    assert (
        quality_rate >= 0.6
    ), f"Quality gate failed: only {quality_rate:.1%} records pass validation"
