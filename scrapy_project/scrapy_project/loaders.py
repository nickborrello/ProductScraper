"""
Item loaders for Scrapy spiders.

These loaders provide data cleaning and processing for scraped items.
"""

from itemloaders.processors import TakeFirst, MapCompose, Join
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
import re

class ProductLoader(ItemLoader):
    """
    Item loader for product data with built-in cleaning processors.
    """

    # Default processor: take first item
    default_output_processor = TakeFirst()

    # Clean text fields (remove extra whitespace, HTML tags)
    name_in = MapCompose(remove_tags, str.strip)
    brand_in = MapCompose(remove_tags, str.strip)
    category_in = MapCompose(remove_tags, str.strip)
    product_type_in = MapCompose(remove_tags, str.strip)
    special_order_in = MapCompose(remove_tags, str.strip)

    # Clean and normalize price
    price_in = MapCompose(
        remove_tags,
        str.strip,
        lambda x: re.sub(r'[^\d.,]', '', x),  # Remove non-numeric except decimal
        lambda x: x.replace(',', ''),  # Remove commas
        lambda x: float(x) if x else None,
        lambda x: f"${x:.2f}" if x else None
    )

    # Clean and normalize weight
    weight_in = MapCompose(
        remove_tags,
        str.strip,
        lambda x: x.upper() if x else x,
        # Extract numeric value and unit
        lambda x: re.search(r'(\d+(?:\.\d+)?)\s*(LB|OZ|KG|G|POUNDS|OUNCES|KILOGRAMS?|GRAMS?)', x, re.I),
        lambda x: (float(x.group(1)), x.group(2).upper()) if x else None,
        # Convert to pounds
        lambda x: x[0] / 16.0 if x and x[1] in ['OZ', 'OUNCES'] else
                  x[0] * 2.20462 if x and x[1] in ['KG', 'KILOGRAMS'] else
                  x[0] / 453.592 if x and x[1] in ['G', 'GRAMS'] else
                  x[0] if x else None,
        lambda x: f"{x:.2f} LB" if x else None
    )

    # Handle image URLs (keep as list)
    image_urls_out = lambda x: list(x)

    # Join multiple text fields with separator
    product_on_pages_out = Join('|')
    product_field_32_out = Join('|')  # Cross-sell relationships