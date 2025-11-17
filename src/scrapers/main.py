"""
New Modular Scraper System Entry Point

This module provides the main entry point for the new YAML-based modular scraper system.
It replaces the legacy archived scraper system.
"""

import os
import sys
import warnings
from typing import List, Optional

# Ensure project root is in path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import os

from src.core.database.refresh import refresh_database_from_xml
from src.scrapers.executor.workflow_executor import WorkflowExecutor
from src.scrapers.models.config import ScraperConfig
from src.scrapers.parser.yaml_parser import ScraperConfigParser


def run_scraping(
    file_path: str, selected_sites: Optional[List[str]] = None, **kwargs
) -> None:
    """
    Run scraping using the new modular scraper system.

    Args:
        file_path: Path to Excel file containing SKUs to scrape
        selected_sites: List of site names to scrape (optional)
        **kwargs: Additional arguments passed to individual scrapers
    """
    print("🚀 Starting scraping with new modular scraper system...")

    # Load available scraper configurations
    config_dir = os.path.join(project_root, "src", "scrapers", "configs")
    available_sites = []

    if os.path.exists(config_dir):
        for filename in os.listdir(config_dir):
            if (
                filename.endswith((".yaml", ".yml"))
                and filename != "sample_config.yaml"
            ):
                site_name = (
                    filename.replace(".yaml", "")
                    .replace(".yml", "")
                    .replace("_", " ")
                    .title()
                )
                available_sites.append(site_name)

    if not available_sites:
        print("❌ No scraper configurations found in src/scrapers/configs/")
        return

    print(f"📋 Available scrapers: {', '.join(available_sites)}")

    # Filter to selected sites if specified
    if selected_sites:
        available_sites = [
            site
            for site in available_sites
            if site.lower().replace(" ", "")
            in [s.lower().replace(" ", "") for s in selected_sites]
        ]
        if not available_sites:
            print(f"❌ None of the selected sites are available: {selected_sites}")
            return

    print(f"🎯 Will scrape sites: {', '.join(available_sites)}")

    # TODO: Implement Excel file processing and scraping execution
    # This is a placeholder - full implementation would require integrating with
    # the existing Excel processing logic from the archived system

    print("✅ New modular scraper system initialized")
    print("📖 See docs/SCRAPER_CONFIGURATION_GUIDE.md for configuration details")


def get_available_scrapers() -> List[str]:
    """
    Get list of available scraper configurations.

    Returns:
        List of scraper names
    """
    config_dir = os.path.join(project_root, "src", "scrapers", "configs")
    scrapers = []

    if os.path.exists(config_dir):
        for filename in os.listdir(config_dir):
            if (
                filename.endswith((".yaml", ".yml"))
                and filename != "sample_config.yaml"
            ):
                site_name = (
                    filename.replace(".yaml", "")
                    .replace(".yml", "")
                    .replace("_", " ")
                    .title()
                )
                scrapers.append(site_name)

    return scrapers


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
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    xml_path = os.path.join(
        project_root, "data", "databases", "shopsite_products_cleaned.xml"
    )

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
