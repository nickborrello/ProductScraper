import os
import pandas as pd
import time
from datetime import datetime
from threading import Lock
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.utils.scraping.scraping import get_standard_chrome_options

from scrapers.bradley_caldwell import scrape_bradley_caldwell
from scrapers.central_pet import scrape_central
from scrapers.orgill import scrape_orgill, login as login_orgill, is_logged_in as is_logged_in_orgill
from scrapers.phillips import scrape_phillips, login as login_phillips, is_logged_in as is_logged_in_phillips
from scrapers.petfoodex import scrape_petfood_experts, login as login_petfood, is_logged_in as is_logged_in_petfood

class DiscontinuedChecker:
    def __init__(self, input_file, output_file="discontinued_remaining.xlsx"):
        self.input_file = input_file
        self.output_file = output_file

        self.site_scrapers = {
            "Bradley Caldwell": scrape_bradley_caldwell,
            "Central Pet": scrape_central,
            "Orgill": scrape_orgill,
            "Phillips": scrape_phillips,
            "Pet Food Experts": scrape_petfood_experts,
        }

        self.login_required_sites = {
            "Orgill": {
                "login_func": login_orgill,
                "is_logged_in_func": is_logged_in_orgill
            },
            "Phillips": {
                "login_func": login_phillips,
                "is_logged_in_func": is_logged_in_phillips
            },
            "Pet Food Experts": {
                "login_func": login_petfood,
                "is_logged_in_func": is_logged_in_petfood
            }
        }

        self.headless = True
        self.site_locks = defaultdict(Lock)
        self.shared_browser_map = {}

    def init_browser(self, site):
        # Match master: use site-specific init_browser if available
        import threading
        thread_id = threading.current_thread().ident
        import time
        timestamp = int(time.time() * 1000)
        unique_profile = f"{site.replace(' ', '_')}_{thread_id}_{timestamp}"
        if site == "Orgill":
            from scrapers.orgill import init_browser as orgill_init_browser
            return orgill_init_browser(profile_suffix=unique_profile, headless=True)
        elif site == "Phillips":
            from scrapers.phillips import init_browser as phillips_init_browser
            return phillips_init_browser(profile_suffix=unique_profile, headless=True)
        elif site == "Pet Food Experts":
            from scrapers.petfoodex import init_browser as petfood_init_browser
            return petfood_init_browser(profile_suffix=unique_profile, headless=False)
        else:
            options = get_standard_chrome_options(headless=True, profile_suffix=unique_profile)
            user_data_dir = os.path.abspath(f"selenium_profiles/{unique_profile}")
            os.makedirs(user_data_dir, exist_ok=True)
            options.add_argument(f"--user-data-dir={user_data_dir}")
            return webdriver.Chrome(options=options)

    def check_and_handle_login(self, site, browser):
        if site not in self.login_required_sites:
            print(f"🔓 [{site}] No authentication required")
            return True
        login_info = self.login_required_sites[site]
        is_logged_in_func = login_info["is_logged_in_func"]
        login_func = login_info["login_func"]
        print(f"🔐 [{site}] Checking authentication status...")
        # Cookie loading removed - no longer necessary
        try:
            print(f"🔍 [{site}] Testing authentication status...")
            if is_logged_in_func(browser):
                print(f"✅ [{site}] Already authenticated - login session active")
                return True
            else:
                print(f"❌ [{site}] Not authenticated - login required")
        except Exception as e:
            print(f"⚠️ [{site}] Error checking login status: {str(e)[:50]}...")
            print(f"🔄 [{site}] Proceeding with login attempt...")
        max_login_attempts = 2
        for attempt in range(max_login_attempts):
            try:
                print(f"🔑 [{site}] Attempting login (attempt {attempt + 1}/{max_login_attempts})...")
                login_func(browser)
                time.sleep(2)
                try:
                    print(f"🔍 [{site}] Verifying login success...")
                    if is_logged_in_func(browser):
                        print(f"🎉 [{site}] Login successful! Authentication verified")
                        return True
                    else:
                        print(f"❌ [{site}] Login attempt failed - not authenticated after login")
                except Exception as verify_error:
                    print(f"⚠️ [{site}] Could not verify login status: {str(verify_error)[:50]}...")
                    print(f"🤔 [{site}] Assuming login succeeded (verification failed)")
                    return True
            except Exception as login_error:
                error_msg = str(login_error)
                print(f"❌ [{site}] Login attempt {attempt + 1} failed: {error_msg[:100]}...")
                if attempt < max_login_attempts - 1:
                    print(f"🔄 [{site}] Retrying login in 3 seconds...")
                    time.sleep(3)
        print(f"💀 [{site}] All login attempts failed - proceeding anyway (may cause scraping failures)")
        return False

    def login_sites(self):
        # Initialize and login to authentication-required sites first
        for site in self.site_scrapers:
            print(f"🔐 Initializing browser for {site}...")
            browser = self.init_browser(site)
            if site in self.login_required_sites:
                self.check_and_handle_login(site, browser)
            self.shared_browser_map[site] = browser


    def product_exists(self, sku, row):
        print("\n" + "=" * 70)
        print(f"🔎 Checking SKU: {sku}")
        print("=" * 70)

        def check_site(site, scraper):
            try:
                print(f"🔍 {sku} on {site}...")
                browser = self.shared_browser_map[site]
                with self.site_locks[site]:
                    result = scraper(sku, browser)
                if result and not result.get('flagged', False):
                    print(f"✅ Found {sku} on {site}!")
                    return True
            except Exception as e:
                print(f"❌ [{site}] Error processing SKU {sku}: {e}")
            return False

        with ThreadPoolExecutor(max_workers=len(self.site_scrapers)) as executor:
            futures = [
                executor.submit(check_site, site, scraper)
                for site, scraper in self.site_scrapers.items()
            ]
            for future in as_completed(futures):
                if future.result():
                    return True

        print(f"❌ Could Not Find {sku}")
        return False

    def run(self):
        print(f"📂 Loading {self.input_file}...")
        df = pd.read_excel(self.input_file, dtype=str)
        
        # Normalize column names
        if 'SKU_NO' in df.columns and 'SKU' not in df.columns:
            df["SKU"] = df["SKU_NO"].astype(str)
        elif 'SKU' in df.columns:
            df["SKU"] = df["SKU"].astype(str)

        # Pad SKUs to 12 digits
        def pad_sku(sku):
            sku = str(sku).strip()
            if sku.isdigit() and 10 <= len(sku) <= 12:
                return sku.zfill(12)
            return sku
        df["SKU"] = df["SKU"].apply(pad_sku)

        self.login_sites()

        not_found_rows = []
        processed_count = 0
        total_count = len(df)

        try:
            for idx, row in df.iterrows():
                sku = row["SKU"]
                print(f"Progress: {processed_count+1}/{total_count}")
                if len(sku) == 12 and sku.isdigit():
                    try:
                        found = self.product_exists(sku, row)
                        if not found:
                            not_found_rows.append(row)
                            pd.DataFrame(not_found_rows).to_excel(self.output_file, index=False)
                    except Exception as e:
                        print(f"❌ Failed to process {sku}: {e}")
                        not_found_rows.append(row)
                        pd.DataFrame(not_found_rows).to_excel(self.output_file, index=False)
                else:
                    print("SKU INVALID: " + sku)
                processed_count += 1
        except KeyboardInterrupt:
            print("🛑 Interrupted by user. Writing partial results...")
        finally:
            print(f"📄 Writing {len(not_found_rows)} not-found SKUs to {self.output_file}...")
            pd.DataFrame(not_found_rows).to_excel(self.output_file, index=False)

            for browser in self.shared_browser_map.values():
                try:
                    browser.quit()
                except:
                    pass

            print("✅ Done.")

if __name__ == "__main__":
    checker = DiscontinuedChecker("discontinuedlist080225.xlsx")
    checker.run()
