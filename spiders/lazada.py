import scrapy
import scrapy
from scrapy import signals
import pandas
import logging


class LazadaSpider(scrapy.Spider):
    name = 'lazada'
    allowed_domains = ['https://www.lazada.vn/']
    start_urls = ['http://https://www.lazada.vn//']
    products = []

    def start_requests(self):
        yield scrapy.Request(url=self.url, callback=self.get_category)
    
    def get_category(self, response):
        categories = response.css('a.item.item--seller::attr(href)').getall()

    def export_file(self):
        dfproduct = pandas.DataFrame(self.products)
        product_file_path = 'products_lazada.json'
        print(len(self.products))
        dfproduct.to_json(product_file_path, orient="records")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Summary
        Args:
            crawler (TYPE): Description
            *args: Description
            **kwargs: Description
        Returns:
            TYPE: Description
        """
        spider = super(QuotesSpider, cls).from_crawler(
            crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed,
                                signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        """Summary
        Args:
            spider (TYPE): Description
        """
        self.logger.info('START CLOSING SPIDER %s', spider.name)
        self.export_file()
