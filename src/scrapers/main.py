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
        formatted_msg = f"[{level}] {msg}"
        print(formatted_msg)
        if log_callback:
            try:
                log_callback.emit(formatted_msg)
            except AttributeError:
                log_callback(formatted_msg)
            
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
        records = loader.load_with_context(file_path)
        skus = [r["SKU"] for r in records]
        
        # Extract Price metadata for preservation
        price_metadata = {}
        for record in records:
            sku = record.get("SKU", "")
            # Check for Price in various column names
            price = record.get("Price", record.get("LIST_PRICE", record.get("price", "")))
            if price:
                price_metadata[sku] = price
        
        log(f"📊 Loaded {len(skus)} SKUs from {file_path}", "INFO")
        if price_metadata:
            log(f"💰 Found prices for {len(price_metadata)} products", "INFO")
        
        if not skus:
            log("❌ No SKUs found in Excel file", "ERROR")
            return
            
    except Exception as e:
        log(f"❌ Failed to load Excel file: {e}", "ERROR")
        return
    
    # Load scraper configurations
    update_status("Loading scraper configurations...")
    from src.scrapers.executor.workflow_executor import WorkflowExecutor
    from src.scrapers.parser import ScraperConfigParser
    from src.scrapers.result_collector import ResultCollector
    
    parser = ScraperConfigParser()
    collector = ResultCollector()  # Collect results instead of saving to DB
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
    
    import math
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.core.settings_manager import settings
    
    max_workers = settings.get("max_workers", 2)
    log(f"⚙️ Using max {max_workers} concurrent workers", "INFO")
    
    # Determine execution strategy
    tasks = []
    
    # Strategy 1: Single Site + Multiple Workers = Split SKUs (Risky but fast)
    if len(configs) == 1 and max_workers > 1:
        config = configs[0]
        chunk_size = math.ceil(len(skus) / max_workers)
        sku_chunks = [skus[i:i + chunk_size] for i in range(0, len(skus), chunk_size)]
        
        log(f"⚠️ ENABLED SKU-LEVEL PARALLELISM for {config.name}", "WARNING")
        log(f"⚠️ Splitting {len(skus)} SKUs into {len(sku_chunks)} chunks across {max_workers} workers.", "WARNING")
        log(f"⚠️ CAUTION: This will trigger {len(sku_chunks)} concurrent logins to the same account.", "WARNING")
        
        for i, chunk in enumerate(sku_chunks):
            tasks.append((config, chunk, f"Worker-{i+1}"))
            
    # Strategy 2: Multiple Sites or Single Worker = One task per site (Safe)
    else:
        for config in configs:
            tasks.append((config, skus, "Main"))

    def process_scraper(args):
        """Process a scraper configuration with a specific list of SKUs."""
        config, target_skus, worker_id = args
        scraper_success = 0
        scraper_failed = 0
        
        prefix = f"[{config.name}:{worker_id}]"
        
        log(f"\n{'='*60}", "INFO")
        log(f"📌 Starting scraper: {config.name} ({worker_id}) - {len(target_skus)} SKUs", "INFO")
        log(f"{'='*60}", "INFO")
        
        update_status(f"Running {config.name} ({worker_id})...")
        
        # Initialize executor for this scraper
        try:
            executor = WorkflowExecutor(config, headless=True)
        except Exception as e:
            log(f"❌ {prefix} Failed to initialize: {e}", "ERROR")
            return 0, len(target_skus)
        
        # Process each SKU
        batch_size = 10
        for idx, sku in enumerate(target_skus, 1):
            # Check for cancellation
            stop_event = kwargs.get("stop_event")
            if stop_event and stop_event.is_set():
                log(f"🛑 {prefix} Cancellation requested. Stopping...", "WARNING")
                break

            # Restart browser every batch_size items
            if idx > 1 and (idx - 1) % batch_size == 0:
                log(f"🔄 {prefix} Restarting browser (batch limit {batch_size} reached)...", "INFO")
                try:
                    if executor.browser:
                        executor.browser.quit()
                    # Re-initialize executor (which creates new browser)
                    executor = WorkflowExecutor(config, headless=True)
                except Exception as e:
                    log(f"❌ {prefix} Failed to restart browser: {e}", "ERROR")
                    pass

            update_status(f"{config.name} ({worker_id}): Processing SKU {idx}/{len(target_skus)} ({sku})")
            
            try:
                # Execute workflow with SKU context
                result = executor.execute_workflow(
                    context={"sku": sku},
                    quit_browser=False  # Reuse browser for efficiency
                )
                
                if result.get("success"):
                    extracted_data = result.get("results", {})
                    
                    # Check if we actually found product data (not just "no results")
                    has_data = any(extracted_data.get(field) for field in ["Name", "Brand", "Price", "Weight"])
                    
                    if has_data:
                        # Add to collector (JSON storage)
                        collector.add_result(sku, config.name, extracted_data)
                        scraper_success += 1
                        
                        # Log product details (Price is from input file, not scraped)
                        name = extracted_data.get("Name", "N/A")
                        brand = extracted_data.get("Brand", "N/A")
                        weight = extracted_data.get("Weight", "N/A")
                        log(f"✅ {prefix} Found: {name} | Brand: {brand} | Weight: {weight}", "INFO")
                    else:
                        # SKU not found on this site - skip (per user requirement #4)
                        log(f"⚠️ {prefix} No data found for SKU: {sku}", "WARNING")
                        scraper_failed += 1
                else:
                    scraper_failed += 1
                    log(f"❌ {prefix} Failed to scrape SKU: {sku}", "ERROR")
                    
            except Exception as e:
                scraper_failed += 1
                log(f"❌ {prefix} Error scraping SKU {sku}: {e}", "ERROR")
            
            # Update progress (thread-safe way needed ideally, but simple increment works for rough progress)
            nonlocal completed_operations
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
            log(f"⚠️ {prefix} Error closing browser: {e}", "WARNING")
        
        log(f"✅ Completed task: {config.name} ({worker_id})", "INFO")
        return scraper_success, scraper_failed

    # Run scrapers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as thread_executor:
        # Submit all tasks
        futures = [thread_executor.submit(process_scraper, task) for task in tasks]
        
        for future in as_completed(futures):
            try:
                s_success, s_failed = future.result()
                successful_results += s_success
                failed_results += s_failed
            except Exception as exc:
                log(f"❌ Scraper task generated an exception: {exc}", "ERROR")
    
    # Save results to JSON file
    log("\n💾 Saving results to JSON file...", "INFO")
    try:
        json_file = collector.save_session(metadata={"price": price_metadata})
        log(f"✅ Results saved to: {json_file}", "INFO")
        
        # Display collection stats
        stats = collector.get_stats()
        log("\n📊 Results Summary:", "INFO")
        log(f"   Unique SKUs found: {stats['total_unique_skus']}", "INFO")
        log(f"   Total scraper results: {stats['total_results']}", "INFO")
        log(f"   SKUs found on multiple sites: {stats['skus_found_on_multiple_sites']}", "INFO")
    except Exception as e:
        log(f"❌ Failed to save results: {e}", "ERROR")
    
    # Final summary
    log(f"\n{'='*60}", "INFO")
    log("🏁 SCRAPING COMPLETE", "INFO")
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
