"""
Result Collector Module

Collects and stores scraper results as JSON files for later consolidation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ResultCollector:
    """Utility class to collect and store scraper results as JSON."""

    def __init__(self, output_dir: str | Path | None = None):
        """
        Initialize result collector.

        Args:
            output_dir: Directory to save result JSON files. If None, uses default.
        """
        if output_dir is None:
            # Default to project data/scraper_results/
            project_root = Path(__file__).parent.parent.parent
            output_dir = project_root / "data" / "scraper_results"

        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session results
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results: dict[str, dict[str, Any]] = {}  # {scraper_name: {sku: result}}

    def add_result(self, sku: str, scraper_name: str, result_data: dict[str, Any]) -> None:
        """
        Add a scraper result to the collection.

        Args:
            sku: Product SKU
            scraper_name: Name of scraper that produced the result
            result_data: Dictionary of extracted fields
        """
        if scraper_name not in self.results:
            self.results[scraper_name] = {}
        
        self.results[scraper_name][sku] = {
            "sku": sku,
            "scraper": scraper_name,
            "timestamp": datetime.now().isoformat(),
            "data": result_data
        }

    def save_session(self) -> Path:
        """
        Save current session results to JSON file.

        Returns:
            Path to the saved JSON file
        """
        output_file = self.output_dir / f"scrape_session_{self.session_id}.json"
        
        # Prepare output structure
        output_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "scrapers": list(self.results.keys()),
            "total_results": sum(len(skus) for skus in self.results.values()),
            "results": self.results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return output_file

    def get_results_by_sku(self, sku: str) -> dict[str, Any]:
        """
        Get all scraper results for a specific SKU.

        Args:
            sku: Product SKU to lookup

        Returns:
            Dictionary mapping scraper names to their results for this SKU
        """
        sku_results = {}
        for scraper_name, scraper_skus in self.results.items():
            if sku in scraper_skus:
                sku_results[scraper_name] = scraper_skus[sku]
        return sku_results

    def get_all_skus(self) -> set[str]:
        """
        Get set of all unique SKUs across all scrapers.

        Returns:
            Set of SKU strings
        """
        all_skus = set()
        for scraper_skus in self.results.values():
            all_skus.update(scraper_skus.keys())
        return all_skus

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about collected results.

        Returns:
            Dictionary with stats
        """
        all_skus = self.get_all_skus()
        
        # Count how many scrapers found each SKU
        sku_coverage = {}
        for sku in all_skus:
            sku_results = self.get_results_by_sku(sku)
            sku_coverage[sku] = len(sku_results)
        
        return {
            "total_unique_skus": len(all_skus),
            "total_results": sum(len(skus) for skus in self.results.values()),
            "scrapers_used": list(self.results.keys()),
            "skus_found_on_multiple_sites": sum(1 for count in sku_coverage.values() if count > 1),
            "skus_not_found": sum(1 for count in sku_coverage.values() if count == 0)
        }
