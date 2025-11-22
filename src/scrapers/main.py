"""
New Modular Scraper System Entry Point

This module provides the main entry point for the new YAML-based modular scraper system.
It replaces the legacy archived scraper system.
"""

import os
import sys
import warnings

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import os

from src.core.database.refresh import refresh_database_from_xml


def run_scraping(file_path: str, selected_sites: list[str] | None = None, log_callback=None, status_callback=None, progress_callback=None, **kwargs) -> None:
    """
    Run scraping using the new modular scraper system.

    Args:
        file_path: Path to Excel file containing SKUs to scrape
        selected_sites: List of site names to scrape (optional)
        log_callback: Optional callback for logging messages
        status_callback: Optional callback for status updates
        progress_callback: Optional callback for progress updates
        **kwargs: Additional arguments passed to individual scrapers
    """
    print("🚀 Starting scraping with new modular scraper system...")

    # Helper for logging
    def log(msg, level="INFO"):
        print(f"[{level}] {msg}")
        if log_callback:
            try:
                log_callback.emit(msg, level)
            except AttributeError:
                log_callback(msg, level)
            
    # Helper for status updates
    def update_status(msg):
        if status_callback:
            try:
                status_callback.emit(msg)
            except AttributeError:
                status_callback(msg)

    # Load available scraper configurations
    config_dir = os.path.join(project_root, "src", "scrapers", "configs")
    available_sites = []

    if selected_sites:
        # Use user-selected sites
        available_sites = selected_sites
    else:
        if os.path.exists(config_dir):
            for filename in os.listdir(config_dir):
                if filename.endswith((".yaml", ".yml")) and filename != "sample_config.yaml":
                    site_name = (
                        filename.replace(".yaml", "").replace(".yml", "").replace("_", " ").title()
                    )
                    available_sites.append(site_name)

    if not available_sites:
        log("❌ No scraper configurations found or selected.", "ERROR")
        return

    log(f"📋 Available scrapers: {', '.join(available_sites)}")
    
    # TODO: Implement actual scraping logic here
    # The modular YAML-based scraper system needs to:
    # 1. Load scraper configs from config_dir
    # 2. Read SKUs from the Excel file at file_path
    # 3. Execute scrapers on those SKUs
    # 4. Save results to database
    
    log("⚠️ Scraping implementation pending - modular system not yet complete", "WARNING")
    log(f"Would scrape file: {file_path}", "INFO")
    log(f"Using scrapers: {', '.join(available_sites)}", "INFO")


# Legacy compatibility - these functions are deprecated
def run_scraping_legacy(*args, **kwargs):
    """Legacy function - redirects to new system with deprecation warning."""
    warnings.warn(
        "run_scraping_legacy is deprecated. Use run_scraping from the new modular system.",
        DeprecationWarning,
        stacklevel=2,
    )
    return run_scraping(*args, **kwargs)


def run_db_refresh(progress_callback=None, log_callback=None) -> tuple[bool, str]:
    """
    Refresh the database from XML file.

    Args:
        progress_callback: Optional callback for progress updates
        log_callback: Optional callback for logging

    Returns:
        Tuple of (success, message)
    """
    # Find the XML file path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    xml_path = os.path.join(project_root, "data", "databases", "shopsite_products_cleaned.xml")

    if progress_callback:
        try:
            progress_callback.emit(10)
        except AttributeError:
            progress_callback(10)

    if log_callback:
        try:
            log_callback.emit("💾 Refreshing database from XML file...")
        except AttributeError:
            log_callback("💾 Refreshing database from XML file...")

    if progress_callback:
        try:
            progress_callback.emit(30)
        except AttributeError:
            progress_callback(30)

    if log_callback:
        try:
            log_callback.emit("🔄 Processing XML and updating database...")
        except AttributeError:
            log_callback("🔄 Processing XML and updating database...")

    # Call the actual refresh function
    success, message = refresh_database_from_xml(xml_path)

    if progress_callback:
        try:
            progress_callback.emit(90)
        except AttributeError:
            progress_callback(90)

    if success and log_callback:
        try:
            log_callback.emit("💡 Database updated successfully.")
        except AttributeError:
            log_callback("💡 Database updated successfully.")

    return success, message
