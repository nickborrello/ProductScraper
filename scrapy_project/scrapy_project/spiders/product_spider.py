import scrapy
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
from w3lib.html import remove_tags
import re
from ..items import ProductItem
from urllib.parse import urljoin
from typing import List, Dict, Any

class ProductLoader(ItemLoader):
    """Item loader with processors for cleaning data"""
    default_item_class = ProductItem
    default_output_processor = TakeFirst()

    # Clean and extract price
    price_in = MapCompose(
        remove_tags,
        lambda x: re.search(r'[\d,]+\.?\d*', str(x)),
        lambda x: x.group(0) if x else None,
        lambda x: float(x.replace(',', '')) if x else None
    )

    # Clean weight
    weight_in = MapCompose(
        remove_tags,
        lambda x: re.search(r'(\d+(?:\.\d+)?)\s*(?:lb|oz|kg|g)', str(x), re.I),
        lambda x: x.group(1) if x else None,
        lambda x: float(x) if x else None
    )

    # Extract image URLs
    image_urls_out = lambda x: list(x)  # Keep as list

class ProductSpider(scrapy.Spider):
    """
    Generic product spider that can scrape products by SKU from various sites.

    This spider demonstrates how to convert from Selenium-based scraping to Scrapy.
    For sites requiring JavaScript execution, you would need Scrapy-Splash.
    """

    name = 'product_spider'

    # Default settings - can be overridden in settings.py or via command line
    custom_settings = {
        'DOWNLOAD_DELAY': 1,  # Be respectful
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'USER_AGENT': 'ProductScraper/1.0 (+https://github.com/your-repo)',
        'ROBOTSTXT_OBEY': True,
    }

    def __init__(self, skus=None, site_url=None, search_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Parse SKUs from command line argument
        self.skus = []
        if skus:
            if isinstance(skus, str):
                self.skus = [sku.strip() for sku in skus.split(',') if sku.strip()]
            elif isinstance(skus, list):
                self.skus = skus

        # Site-specific URLs - these would be configured per site
        self.site_url = site_url or 'https://example.com'
        self.search_url = search_url or 'https://example.com/search?q={query}'

        self.logger.info(f"Initialized ProductSpider with {len(self.skus)} SKUs to scrape")

    def start_requests(self):
        """Generate initial requests for each SKU."""
        if not self.skus:
            self.logger.warning("No SKUs provided to scrape")
            return

        for sku in self.skus:
            # Try direct product URL first (if we know the pattern)
            product_url = self._get_product_url(sku)
            if product_url:
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={'sku': sku, 'source': 'direct'},
                    errback=self.handle_error
                )
            else:
                # Fall back to search
                search_url = self.search_url.format(query=sku)
                yield scrapy.Request(
                    url=search_url,
                    callback=self.parse_search_results,
                    meta={'sku': sku, 'source': 'search'},
                    errback=self.handle_error
                )

    def _get_product_url(self, sku: str) -> str:
        """
        Generate direct product URL from SKU.

        This method should be overridden for each specific site.
        Returns None if direct URL pattern is not known.
        """
        # Example patterns for different sites:
        # Amazon: https://www.amazon.com/dp/{sku}
        # Walmart: https://www.walmart.com/ip/{sku}
        # Target: https://www.target.com/p/{sku}

        # For now, return None to force search
        return None

    def parse_search_results(self, response):
        """Parse search results page to find product links."""
        sku = response.meta['sku']

        # Extract product links from search results
        # This is highly site-specific and would need customization per site
        product_links = response.css('a.product-link::attr(href)').getall()

        if not product_links:
            self.logger.warning(f"No product links found for SKU {sku}")
            return

        # Take the first result (could be improved with better matching)
        product_url = urljoin(response.url, product_links[0])

        yield scrapy.Request(
            url=product_url,
            callback=self.parse_product,
            meta={'sku': sku, 'source': 'search_result'},
            errback=self.handle_error
        )

    def parse_product(self, response):
        """Parse individual product page."""
        sku = response.meta['sku']
        source = response.meta.get('source', 'unknown')

        self.logger.info(f"Parsing product page for SKU {sku} (source: {source})")

        # Use ItemLoader for robust data extraction
        loader = ProductLoader(response=response)
        loader.add_value('sku', sku)

        # Extract product data - these selectors are examples and would need
        # to be customized for each specific site
        loader.add_css('name', 'h1.product-title::text, .product-name::text')
        loader.add_css('price', '.price::text, .product-price::text')
        loader.add_css('brand', '.brand::text, .manufacturer::text')
        loader.add_css('weight', '.weight::text, .product-weight::text')
        loader.add_css('image_urls', 'img.product-image::attr(src), .gallery img::attr(src)')

        # Additional fields that might be available
        loader.add_css('category', '.breadcrumb a::text, .category::text')
        loader.add_css('product_type', '.item-type::text, .product-type::text')
        loader.add_css('special_order', '.special-order::text, .availability::text')

        # Load the item
        item = loader.load_item()

        # Add metadata
        item['product_on_pages'] = response.url
        item['last_updated'] = None  # Will be set by pipeline

        # Clean and validate the data
        item = self._clean_product_data(item)

        if self._validate_product(item):
            yield item
        else:
            self.logger.warning(f"Product validation failed for SKU {sku}")

    def _clean_product_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize product data."""
        # Remove extra whitespace
        for key, value in item.items():
            if isinstance(value, str):
                item[key] = value.strip()

        # Normalize price (remove currency symbols, etc.)
        if 'price' in item and item['price']:
            # Remove non-numeric characters except decimal point
            price_clean = re.sub(r'[^\d.]', '', str(item['price']))
            try:
                item['price'] = f"${float(price_clean):.2f}"
            except ValueError:
                pass

        # Normalize weight to consistent format
        if 'weight' in item and item['weight']:
            item['weight'] = self._normalize_weight(str(item['weight']))

        return item

    def _normalize_weight(self, weight_str: str) -> str:
        """Normalize weight to consistent LB format."""
        if not weight_str:
            return ''

        # Convert common weight formats to LB
        weight_str = weight_str.upper()

        # Handle pounds
        if 'LB' in weight_str or 'POUND' in weight_str:
            return weight_str

        # Handle ounces to pounds
        if 'OZ' in weight_str or 'OUNCE' in weight_str:
            oz_match = re.search(r'(\d+(?:\.\d+)?)', weight_str)
            if oz_match:
                oz = float(oz_match.group(1))
                lb = oz / 16.0
                return f"{lb:.2f} LB"

        # Handle kilograms to pounds
        if 'KG' in weight_str or 'KILOGRAM' in weight_str:
            kg_match = re.search(r'(\d+(?:\.\d+)?)', weight_str)
            if kg_match:
                kg = float(kg_match.group(1))
                lb = kg * 2.20462
                return f"{lb:.2f} LB"

        # Return as-is if no conversion needed
        return weight_str

    def _validate_product(self, item: Dict[str, Any]) -> bool:
        """Validate that product has required fields."""
        required_fields = ['sku', 'name']
        return all(item.get(field) for field in required_fields)

    def handle_error(self, failure):
        """Handle request failures."""
        sku = failure.request.meta.get('sku', 'unknown')
        self.logger.error(f"Request failed for SKU {sku}: {failure.value}")

# Example of how to create site-specific spiders
class AmazonSpider(ProductSpider):
    """Spider specifically for Amazon products."""

    name = 'amazon_spider'

    def __init__(self, *args, **kwargs):
        super().__init__(
            site_url='https://www.amazon.com',
            search_url='https://www.amazon.com/s?k={query}',
            *args, **kwargs
        )

    def _get_product_url(self, sku: str) -> str:
        """Generate Amazon product URL from ASIN/SKU."""
        return f"https://www.amazon.com/dp/{sku}"

    def parse_product(self, response):
        """Parse Amazon product page with site-specific selectors."""
        loader = ProductLoader(response=response)
        loader.add_value('sku', response.meta['sku'])

        # Amazon-specific selectors
        loader.add_css('name', '#productTitle::text')
        loader.add_css('price', '.a-price .a-offscreen::text, #priceblock_ourprice::text')
        loader.add_css('brand', '#bylineInfo::text, .a-brand::text')
        loader.add_css('weight', '.a-size-base .a-text-bold + span::text')

        # Amazon product images
        loader.add_css('image_urls', '#imgTagWrapperId img::attr(src), .image img::attr(src)')

        item = loader.load_item()
        item['product_on_pages'] = response.url

        yield item