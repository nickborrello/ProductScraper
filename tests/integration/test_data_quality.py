import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.core.data_quality_scorer import (DataQualityScorer,
                                          is_product_high_quality)


def get_available_scrapers():
    """Get list of available scraper names from configs."""
    configs_dir = PROJECT_ROOT / "src" / "scrapers" / "configs"
    scrapers = []
    if configs_dir.exists():
        for config_file in configs_dir.glob("*.yaml"):
            if config_file.is_file():
                scrapers.append(config_file.stem)
    return sorted(scrapers)


def get_test_skus(scraper_name: str):
    """Get test SKUs for a scraper from its YAML config."""
    config_path = PROJECT_ROOT / "src" / "scrapers" / "configs" / f"{scraper_name}.yaml"
    if not config_path.exists():
        return ["035585499741"]  # Default fallback

    parser = ScraperConfigParser()
    config = parser.load_from_file(config_path)
    return config.test_skus or ["035585499741"]


import pytest


def test_data_quality_gate():
    """
    Tests that the data quality scorer meets a minimum quality threshold.
    """
    scorer = DataQualityScorer()
    total_records = 0
    high_quality_records = 0

    scrapers = get_available_scrapers()

    for scraper_name in scrapers:
        test_skus = get_test_skus(scraper_name)
        for sku in test_skus[:5]:  # Test first 5 SKUs per scraper
            # Mock record with SKU
            record = {
                "SKU": sku,
                "Name": f"Test {scraper_name} product",
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


def test_scraper_config_validation():
    """
    Test that all scraper configurations can be loaded and have required fields.
    """
    parser = ScraperConfigParser()
    configs_dir = PROJECT_ROOT / "src" / "scrapers" / "configs"

    for config_file in configs_dir.glob("*.yaml"):
        scraper_name = config_file.stem
        print(f"\n📊 {scraper_name.upper()}")
        print("-" * 30)

        # Should not raise exception
        config = parser.load_from_file(config_file)

        # Basic validation
        assert config.base_url, f"Scraper {scraper_name} missing base_url"
        assert config.workflows, f"Scraper {scraper_name} missing workflows"
        assert isinstance(config.test_skus, list), f"Scraper {scraper_name} test_skus should be list"

        print(f"Test SKUs: {len(config.test_skus or [])} configured")
        print(f"Base URL: {config.base_url}")
        print(f"Timeout: {config.timeout}s")
