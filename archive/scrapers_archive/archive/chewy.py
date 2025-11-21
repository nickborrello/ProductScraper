import os
import re
import sys
import time
import traceback

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils.scraping.scraping import clean_string


def init_chewy_browser():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36"
    )
    options.add_argument("--user-data-dir=C:/temp/chewy-profile")
    return uc.Chrome(options=options, use_subprocess=True)


def scrape_chewy(product_name, original_sku):
    product_info = {
        "SKU": original_sku,
        "Name": "N/A",
        "Brand": "N/A",
        "Weight": "N/A",
        "Image URLs": [],
    }

    driver = init_chewy_browser()
    try:
        for attempt in range(2):
            try:
                driver.get("https://www.chewy.com")
                WebDriverWait(driver, 10).until(lambda d: "Chewy" in d.title)
                break
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                time.sleep(5)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search-autocomplete-desktop"))
        )
        search_input = driver.find_element(By.ID, "search-autocomplete-desktop")
        search_input.clear()
        search_input.send_keys(product_name)
        search_input.send_keys(Keys.RETURN)

        print("🧭 Please manually confirm the correct product page is loaded.")
        input("✅ Press ENTER to continue scraping...")

        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.TAG_NAME, "h1")))

        name_el = driver.find_element(By.TAG_NAME, "h1")
        product_info["Name"] = clean_string(name_el.text)

        try:
            brand_el = driver.find_element(
                By.CSS_SELECTOR, "span[data-testid='manufacture-name'] a"
            )
            product_info["Brand"] = clean_string(brand_el.text)
        except:
            try:
                brand_el = driver.find_element(By.CSS_SELECTOR, "span[data-testid='brand-name']")
                product_info["Brand"] = clean_string(brand_el.text)
            except:
                try:
                    alt_brand_el = driver.find_element(By.CSS_SELECTOR, "a[href*='/brands/']")
                    product_info["Brand"] = clean_string(alt_brand_el.text)
                except:
                    pass

        try:
            bullets = driver.find_elements(By.CSS_SELECTOR, "ul[data-testid='product-bullets'] li")
            for bullet in bullets:
                txt = bullet.text.lower()
                match = re.search(r"(\d+\.?\d*)\s*(oz|lb|lbs|pounds?)", txt)
                if match:
                    product_info["Weight"] = f"{match.group(1)} {match.group(2)}"
                    break
        except:
            pass

        try:
            image_urls = set()
            thumbs = driver.find_elements(By.CSS_SELECTOR, "img[data-testid='product-thumbnail']")
            for thumb in thumbs:
                src = thumb.get_attribute("src")
                if src and "data:image" not in src:
                    image_urls.add(src)

            try:
                carousel_imgs = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div[data-testid='product-carousel'] img.styles_mainCarouselImage__kiYyf",
                )
                for img in carousel_imgs:
                    src = img.get_attribute("src")
                    if src and "data:image" not in src and "customer-photos" not in src:
                        image_urls.add(src)
            except:
                pass

            product_info["Image URLs"] = list(image_urls)
        except Exception as e:
            print(f"⚠️ Image scrape error: {e}")

    except Exception:
        print("❌ Chewy scrape failed:")
        traceback.print_exc()
        print("🛑 Browser will remain open for debugging.")
        return None
    finally:
        try:
            driver.quit()
        except:
            pass

    # Flag product if it has any placeholders or missing images
    product_info["flagged"] = any(
        value == "N/A" for value in product_info.values() if isinstance(value, str)
    ) or not product_info.get("Image URLs")

    return product_info


if __name__ == "__main__":
    test_name = "earthborn holistic"
    print(f"🧪 Running test with query: '{test_name}'")
    result = scrape_chewy(test_name, original_sku="SAMPLE12345")
    if result:
        print("\n✅ Scraped product:")
        for k, v in result.items():
            if isinstance(v, list):
                print(f"{k}:")
                for img in v:
                    print(f" - {img}")
            else:
                print(f"{k}: {v}")
    else:
        print("❌ No product scraped.")
