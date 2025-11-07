# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductItem(scrapy.Item):
    """Scrapy Item for product data - matches your existing scraper format"""
    sku = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    brand = scrapy.Field()
    weight = scrapy.Field()
    image_urls = scrapy.Field()  # List of image URLs
    url = scrapy.Field()  # Source URL

    # Additional fields to match your existing format
    category = scrapy.Field()
    product_type = scrapy.Field()
    product_on_pages = scrapy.Field()
    special_order = scrapy.Field()
    product_cross_sell = scrapy.Field()
    product_disabled = scrapy.Field()
