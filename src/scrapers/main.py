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
    
    # Load SKUs from Excel file
    update_status("Loading SKUs from Excel file...")
    try:
        from src.scrapers.sku_loader import SKULoader
        
        loader = SKULoader()
        skus = loader.load(file_path)
        log(f"📊 Loaded {len(skus)} SKUs from {file_path}", "INFO")
        
        if not skus:
            log("❌ No SKUs found in Excel file", "ERROR")
            return
            
    except Exception as e:
        log(f"❌ Failed to load Excel file: {e}", "ERROR")
        return
    
    # Load scraper configurations
    update_status("Loading scraper configurations...")
    from src.scrapers.parser import ScraperConfigParser
    from src.scrapers.executor.workflow_executor import WorkflowExecutor
    from src.scrapers.result_storage import ResultStorage
    
    parser = ScraperConfigParser()
    storage = ResultStorage()
    configs = []
    
    for site_name in available_sites:
        # Convert site name back to filename
        config_filename = site_name.lower().replace(" ", "_") + ".yaml"
        config_path = os.path.join(config_dir, config_filename)
        
        if os.path.exists(config_path):
            try:
                config = parser.load_from_file(config_path)
                configs.append(config)
                log(f"✅ Loaded config: {config.name}", "INFO")
            except Exception as e:
                log(f"⚠️ Failed to load {config_filename}: {e}", "WARNING")
        else:
            log(f"⚠️ Config file not found: {config_filename}", "WARNING")
    
    if not configs:
        log("❌ No valid scraper configurations loaded", "ERROR")
        return
    
    # Execute scraping
    total_operations = len(configs) * len(skus)
    completed_operations = 0
    successful_results = 0
    failed_results = 0
    
    log(f"🚀 Starting scraping: {len(configs)} scrapers × {len(skus)} SKUs = {total_operations} operations", "INFO")
    
    for config in configs:
        log(f"\n{'='*60}", "INFO")
        log(f"📌 Starting scraper: {config.name}", "INFO")
        log(f"{'='*60}", "INFO")
        
        update_status(f"Running {config.name} scraper...")
        
        # Initialize executor for this scraper
        try:
            executor = WorkflowExecutor(config, headless=True)
        except Exception as e:
            log(f"❌ Failed to initialize {config.name}: {e}", "ERROR")
            failed_results += len(skus)
            completed_operations += len(skus)
            continue
        
        # Process each SKU
        for idx, sku in enumerate(skus, 1):
            update_status(f"{config.name}: Processing SKU {idx}/{len(skus)} ({sku})")
            log(f"\n[{config.name}] Processing SKU {idx}/{len(skus)}: {sku}", "INFO")
            
            try:
                # Execute workflow with SKU context
                result = executor.execute_workflow(
                    context={"sku": sku},
                    quit_browser=False  # Reuse browser for efficiency
                )
                
                if result.get("success"):
                    extracted_data = result.get("results", {})
                    
                    # Save to database
                    if storage.save(sku, config.name, extracted_data):
                        successful_results += 1
                        log(f"✅ [{config.name}] Successfully scraped and saved SKU: {sku}", "INFO")
                    else:
                        failed_results += 1
                        log(f"⚠️ [{config.name}] Scraped but failed to save SKU: {sku}", "WARNING")
                else:
                    failed_results += 1
                    log(f"❌ [{config.name}] Failed to scrape SKU: {sku}", "ERROR")
                    
            except Exception as e:
                failed_results += 1
                log(f"❌ [{config.name}] Error scraping SKU {sku}: {e}", "ERROR")
            
            # Update progress
            completed_operations += 1
            if progress_callback:
                progress_pct = int((completed_operations / total_operations) * 100)
                try:
                    progress_callback.emit(progress_pct)
                except AttributeError:
                    progress_callback(progress_pct)
        
        # Cleanup browser for this scraper
        try:
            if executor.browser:
                executor.browser.quit()
        except Exception as e:
            log(f"⚠️ Error closing browser for {config.name}: {e}", "WARNING")
        
        log(f"✅ Completed scraper: {config.name}", "INFO")
    
    # Final summary
    log(f"\n{'='*60}", "INFO")
    log(f"🏁 SCRAPING COMPLETE", "INFO")
    log(f"{'='*60}", "INFO")
    log(f"📊 Total operations: {total_operations}", "INFO")
    log(f"✅ Successful: {successful_results}", "INFO")
    log(f"❌ Failed: {failed_results}", "INFO")
    log(f"📈 Success rate: {(successful_results/total_operations*100):.1f}%", "INFO")
    
    update_status("Scraping complete!")


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
