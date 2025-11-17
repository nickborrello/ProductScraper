import os
import re
import requests
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

PLACEHOLDER_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSFUAfyVe3Easiycyh3isP9wDQTYuSmGPsPQvLIJdEYvQ_DsFq5Ez2Nh_QjiS3oZ3B8ZPfK9cZQyIStmQMV1lDPLw"


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def init_selenium_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)


def process_image(content, img_name):
    img = Image.open(BytesIO(content))

    # Convert transparent PNGs to RGB with white background
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
        img = background
    else:
        img = img.convert("RGB")  # Ensure compatibility with JPEG

    width, height = img.size

    if width > height:
        new_width = 1000
        new_height = int((height / width) * 1000)
    else:
        new_height = 1000
        new_width = int((width / height) * 1000)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    new_img = Image.new("RGB", (1000, 1000), (255, 255, 255))
    paste_x = (1000 - new_width) // 2
    paste_y = (1000 - new_height) // 2
    new_img.paste(img, (paste_x, paste_y))
    new_img.save(img_name, "JPEG", quality=95)


def download_image(img_url, subdir, file_name, idx, results_folder=None):
    if results_folder:
        # Use session-specific results folder
        folder_path = os.path.join(results_folder, "images", subdir)
    else:
        # Fallback to old behavior
        folder_path = os.path.join(PROJECT_ROOT, "data", "images", subdir)
    os.makedirs(folder_path, exist_ok=True)

    sanitized_file_name = sanitize_filename(file_name)
    if len(sanitized_file_name) > 255:
        sanitized_file_name = sanitized_file_name[:255]

    if idx == 0:
        img_name = os.path.join(folder_path, sanitized_file_name)
    else:
        name, ext = os.path.splitext(sanitized_file_name)
        img_name = os.path.join(folder_path, f"{name}-{idx}.jpg")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    try:
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()
        process_image(response.content, img_name)
        return
    except Exception as e:
        print(f"⚠️ Failed to download image directly: {e}")

    # Selenium fallback
    try:
        print("🕸️ Trying Selenium fallback...")
        driver = init_selenium_driver()
        driver.get(img_url)
        time.sleep(3)
        img_element = driver.find_element("tag name", "img")
        src = img_element.get_attribute("src")
        driver.quit()

        if not src.startswith("http"):
            raise ValueError("Selenium image src not valid")

        fallback_response = requests.get(src, headers=headers, timeout=10)
        fallback_response.raise_for_status()
        process_image(fallback_response.content, img_name)
        return
    except Exception as se:
        print(f"⚠️ Selenium also failed: {se}")

    # Placeholder fallback
    try:
        print("🧩 Using placeholder image instead.")
        placeholder_response = requests.get(PLACEHOLDER_URL, timeout=10)
        placeholder_response.raise_for_status()
        process_image(placeholder_response.content, img_name)
    except Exception as pe:
        print(f"❌ Failed to fetch placeholder image: {pe}")
