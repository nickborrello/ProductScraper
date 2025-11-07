import scrapy


class ExampleSpiderSpider(scrapy.Spider):
    name = "example_spider"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]

    def parse(self, response):
        pass
