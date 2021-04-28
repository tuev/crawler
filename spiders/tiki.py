import scrapy
from scrapy import signals
import pandas
import logging


class TikiSpider(scrapy.Spider):
    name = "tiki"
    url = 'https://tiki.vn/'
    categoryURLList = []
    sellerList = []
    products = []

    def start_requests(self):
        yield scrapy.Request(url=self.url, callback=self.get_category)

    def get_category(self, response):
        categoryURL = response.css('a.menu-link::attr(href)').getall()
        for category in categoryURL:
            if category != '#':
                self.categoryURLList.append(category)
                yield scrapy.Request(category, self.get_seller_url)

    def get_seller_url(self, response):
        sellerURL = response.css('a.item.item--seller::attr(href)').getall()
        for seller in sellerURL:
            sellerId = self.get_seller_id(seller)
            if sellerId not in self.sellerList:
                self.sellerList.append(sellerId)
                self.get_product_seller(sellerId)
                seller_uri = 'https://tiki.vn/api/v2/products?limit=200&page=1&seller=%s' % sellerId
                yield scrapy.Request(seller_uri, callback=self.paging_seller_url(sellerId))

    def paging_seller_url(self, seller):
        def request_product(response):
            data = response.json()
            self.add_product(response)
            for key in data:
                if key == 'paging':
                    for page in range(2, data[key]['last_page']):
                        seller_uri = 'https://tiki.vn/api/v2/products?limit=200&page=%s&seller=%s' % (
                            page, seller)
                        yield scrapy.Request(seller_uri, callback=self.add_product)
        return request_product

    def get_seller_id(self, seller_url):
        seller_parts = seller_url.split("seller=")
        seller_parts.reverse()
        return seller_parts[0].split("&")[0]

    def get_product_seller(self, seller=1, page=1, limit=200):
        seller_uri = 'https://tiki.vn/api/v2/products?limit=%s&page=%s&seller=%s' % (
            limit, page, seller)
        request = scrapy.Request(seller_uri)
        request.callback = self.add_product
        yield request

    def add_product(self, response):
        data = response.json()
        print(len(data['data']))
        self.products.extend(data['data'])

    def export_file(self):
        dfCategory = pandas.DataFrame(self.categoryURLList)
        category_file_path = 'categoryURL.json'
        dfCategory.to_json(category_file_path, orient="values")

        dfseller = pandas.DataFrame(self.sellerList)
        seller_file_path = 'sellerList.json'
        dfseller.to_json(seller_file_path, orient="values")

        dfproduct = pandas.DataFrame(self.products)
        product_file_path = 'products_tiki.json'
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
        spider = super(TikiSpider, cls).from_crawler(
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
