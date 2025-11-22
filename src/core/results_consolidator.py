import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

@dataclass
class ScraperResult:
    """Represents a single result from a specific scraper for a SKU."""
    scraper_name: str
    timestamp: str
    data: Dict[str, Any]
    
    @property
    def price(self) -> Optional[float]:
        """Extract price as float if possible."""
        raw_price = self.data.get("Price")
        if not raw_price:
            return None
        try:
            # Remove currency symbols and whitespace
            clean_price = str(raw_price).replace("$", "").replace(",", "").strip()
            return float(clean_price)
        except ValueError:
            return None

@dataclass
class ConsolidatedProduct:
    """Represents a product with results from multiple scrapers."""
    sku: str
    results: Dict[str, ScraperResult] = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get the best available name."""
        # Return the first non-empty name found
        for res in self.results.values():
            name = res.data.get("Name")
            if name:
                return str(name)
        return "Unknown Product"
    
    @property
    def sites_found(self) -> List[str]:
        """List of sites where this product was found."""
        return list(self.results.keys())
    
    @property
    def price_range(self) -> str:
        """Get formatted price range."""
        prices = [res.price for res in self.results.values() if res.price is not None]
        if not prices:
            return "N/A"
        min_p = min(prices)
        max_p = max(prices)
        if min_p == max_p:
            return f"${min_p:.2f}"
        return f"${min_p:.2f} - ${max_p:.2f}"

class ResultsConsolidator:
    """Manages loading and consolidating scraper results."""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        
    def get_available_sessions(self) -> List[Dict[str, Any]]:
        """List all available scrape sessions."""
        sessions = []
        if not self.results_dir.exists():
            return sessions
            
        for f in self.results_dir.glob("scrape_session_*.json"):
            try:
                # Parse filename for timestamp if needed, or just read file stats
                # scrape_session_YYYYMMDD_HHMMSS.json
                timestamp_str = f.stem.replace("scrape_session_", "")
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                sessions.append({
                    "id": timestamp_str,
                    "path": str(f),
                    "display": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "filename": f.name
                })
            except Exception:
                continue
                
        # Sort by new
        return sorted(sessions, key=lambda x: x["id"], reverse=True)
        
    def load_and_consolidate(self, session_paths: List[str]) -> List[ConsolidatedProduct]:
        """Load specified session files and consolidate by SKU."""
        consolidated: Dict[str, ConsolidatedProduct] = {}
        
        for path in session_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Handle session format
                if "results" in data and isinstance(data["results"], dict):
                    # Structure: results -> scraper_name -> sku -> data
                    for scraper_name, scraper_results in data["results"].items():
                        for sku, details in scraper_results.items():
                            if sku not in consolidated:
                                consolidated[sku] = ConsolidatedProduct(sku=sku)
                                
                            result_data = details.get("data", {})
                            timestamp = details.get("timestamp", "")
                            
                            result = ScraperResult(
                                scraper_name=scraper_name,
                                timestamp=timestamp,
                                data=result_data
                            )
                            
                            consolidated[sku].results[scraper_name] = result
                            
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue
                
        return list(consolidated.values())
