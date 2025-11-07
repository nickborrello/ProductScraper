# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

class ProductPipeline:
    """
    Pipeline to process scraped product items and save them in format compatible
    with the existing ProductScraper system.
    """

    def __init__(self):
        self.items = []
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True)

    def process_item(self, item, spider):
        """Process each scraped item"""
        # Convert Scrapy item to dict
        product_dict = dict(item)

        # Ensure required fields exist with defaults
        product_dict.setdefault('Name', '')
        product_dict.setdefault('Price', '')
        product_dict.setdefault('Brand', '')
        product_dict.setdefault('Weight', '')
        product_dict.setdefault('Image URLs', [])

        # Convert to format expected by existing system
        formatted_product = {
            'SKU': product_dict.get('sku', ''),
            'Name': product_dict.get('name', ''),
            'Price': str(product_dict.get('price', '')),
            'Brand': product_dict.get('brand', ''),
            'Weight': str(product_dict.get('weight', '')),
            'Image URLs': product_dict.get('image_urls', []),
            'Category': product_dict.get('category', ''),
            'Product Type': product_dict.get('product_type', ''),
            'Product On Pages': product_dict.get('product_on_pages', ''),
            'Special Order': product_dict.get('special_order', ''),
            'Product Cross Sell': product_dict.get('product_cross_sell', ''),
            'ProductDisabled': product_dict.get('product_disabled', ''),
        }

        self.items.append(formatted_product)
        return item

    def close_spider(self, spider):
        """Called when spider finishes - save all collected items"""
        if not self.items:
            spider.logger.info("No products scraped")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON (for debugging/analysis)
        json_file = self.output_dir / f"scrapy_products_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, indent=2, ensure_ascii=False)
        spider.logger.info(f"Saved {len(self.items)} products to {json_file}")

        # Save as Excel (compatible with existing system)
        excel_file = self.output_dir / f"scrapy_products_{timestamp}.xlsx"
        df = pd.DataFrame(self.items)
        df.to_excel(excel_file, index=False)
        spider.logger.info(f"Saved {len(self.items)} products to {excel_file}")

        # Also save in the format expected by the main scraper system
        # This creates a file that can be imported by their existing database_import.py
        combined_file = Path('..') / 'data' / 'scrapy_output.xlsx'
        combined_file.parent.mkdir(exist_ok=True)

        # Map to ShopSite format for compatibility
        shopsite_format = []
        for product in self.items:
            shopsite_row = {
                'SKU': product['SKU'],
                'Name': product['Name'],
                'Product Description': product['Name'],
                'Price': product['Price'],
                'Weight': product['Weight'],
                'Product Field 16': product['Brand'],  # Brand
                'Product Field 24': product.get('Category', ''),  # Category
                'Product Field 25': product.get('Product Type', ''),  # Product Type
                'Product On Pages': product.get('Product On Pages', ''),
                'Product Field 32': product.get('Product Cross Sell', ''),  # Cross-sell
                'Product Field 11': product.get('Special Order', ''),  # Special Order
            }
            shopsite_format.append(shopsite_row)

        shopsite_df = pd.DataFrame(shopsite_format)
        shopsite_df.to_excel(combined_file, index=False)
        spider.logger.info(f"Saved ShopSite-compatible format to {combined_file}")

        spider.logger.info(f"Successfully processed {len(self.items)} products from {spider.name}")


class ScrapyProjectPipeline:
    """Legacy pipeline - kept for compatibility"""
    def process_item(self, item, spider):
        return item
