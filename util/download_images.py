import os
import pandas as pd
from urllib.parse import urlparse
from image_util import download_image  # Make sure this function is implemented correctly

# Define the directory and filename of the Excel file
EXCEL_FILE = './util/image_urls.xlsx'
URL_COLUMN = 'Image_URL'  # Column name in the Excel file containing the image URLs

# Function to download images from the URLs in the Excel sheet
def download_images_from_excel(excel_file, url_column):
    # Read the Excel file
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"⚠️ Failed to read Excel file: {e}")
        return

    # Check if the specified column exists
    if url_column not in df.columns:
        print(f"⚠️ Column '{url_column}' not found in the Excel file.")
        return

    # Loop through the image URLs and download each image
    for idx, row in df.iterrows():
        img_url = row[url_column]
        if pd.notna(img_url):  # Check if the URL is not NaN (empty)
            print(f"🔽 Downloading image {idx + 1}: {img_url}")
            subdir = "purina"  # Directory to save images

            # Extract original file name from URL
            parsed_url = urlparse(img_url)
            file_name = os.path.basename(parsed_url.path)

            # Fallback if no file name is present in the URL
            if not file_name:
                file_name = f"image_{idx + 1}.jpg"

            # Download the image
            download_image(img_url, subdir, file_name, idx)

# Run the script to download images
if __name__ == '__main__':
    download_images_from_excel(EXCEL_FILE, URL_COLUMN)
