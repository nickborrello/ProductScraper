# Scrapy settings for ProductScraper project
#
# Optimized for respectful web scraping of e-commerce sites

BOT_NAME = "ProductScraper"

SPIDER_MODULES = ["scrapy_project.spiders"]
NEWSPIDER_MODULE = "scrapy_project.spiders"

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "ProductScraper/1.0 (+https://github.com/your-repo)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling settings - be respectful to avoid being blocked
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2  # 2 second delay between requests

# Disable cookies for simple scraping (enable if needed for sessions)
COOKIES_ENABLED = False

# Override the default request headers to look more like a real browser
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Configure item pipelines
ITEM_PIPELINES = {
    "scrapy_project.pipelines.ProductPipeline": 300,
}

# Enable and configure the AutoThrottle extension for respectful scraping
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable HTTP caching to avoid re-downloading pages during development
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # 1 hour
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [404, 500, 502, 503, 504]

# Feed exports - save results in multiple formats
FEEDS = {
    'output/products_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf-8',
        'indent': 2,
    },
    'output/products_%(time)s.csv': {
        'format': 'csv',
        'encoding': 'utf-8',
    },
}

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
