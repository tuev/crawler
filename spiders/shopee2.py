import scrapy
from scrapy import signals
import pandas
import logging
import math
import json
import re
import urllib.parse
from scrapy_splash import SplashRequest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER
from scrapy.utils.curl import curl_to_request_kwargs
import random

LOGGER.setLevel(logging.WARNING)
user_agent_list = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:39.0) Gecko/20100101 Firefox/39.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; WOW64; Trident/6.0)',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.146 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.146 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20140205 Firefox/24.0 Iceweasel/24.3.0',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:28.0) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2',
]


class ShopeeSpider2(scrapy.Spider):
    name = "shopee2"
    url = 'https://shopee.vn/api/v2/category_list/get'
    categoryList = []
    categoryURLList = []
    sellerList = []
    products = []
    total = 0
    limit = 50
    tempItemCount = 0
    currentCategory = {}
    driver = None
    isProgess = False
    userAgent = user_agent_list[0]

    headers = {
        'authority': 'shopee.vn',
        'sec-ch-ua': '"Google Chrome";v="87", " Not;A Brand";v="99", "Chromium";v="87"',
        'x-shopee-language': 'vi',
        'x-requested-with': 'XMLHttpRequest',
        'if-none-match-': '55b03-dc7d0f3cf5037f420066316fe898fbd8',
        'sec-ch-ua-mobile': '?0',
        'x-api-source': 'pc',
        'accept': '*/*',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'if-none-match': '8c5f6005ed8aa323ef9e311385cbe253',
    }

    def start_requests(self):
        yield scrapy.Request(url=self.url, callback=self.get_category)

    def get_category(self, response):
        data = json.loads(response.body)
        self.categoryList = data['data']['category_list']
        for category in self.categoryList:
            categoryId = category['catid']
            self.isProgess = True
            if categoryId == 12938:
                self.currentCategory = category
                while self.isProgess == True:
                    referrer = self.getReferrer()
                    category_uri = f"https://shopee.vn/api/v2/search_items/?by=relevancy&limit=50&match_id={categoryId}&newest={self.tempItemCount}&order=desc&page_type=search&version=2"
                    self.headers['referer'] = referrer
                    self.headers['user-agent'] = random.choice(user_agent_list)
                    request = scrapy.Request(
                        category_uri, self.getCatProduct, headers=self.headers)
                    yield request

    def getCatProduct(self, response):
        try:
            data = json.loads(response.body)
            if data['total_count'] == None:
                print("END -ERROR")
                self.isProgess = False
                self.tempItemCount = 0
            else:
                print(len(data['items']), '-',
                      self.tempItemCount, data['total_count'])
                self.products.extend(data['items'])
                self.tempItemCount += self.limit
        except ValueError:  # includes simplejson.decoder.JSONDecodeError
            print("GET -ERROR")
            self.tempItemCount += self.limit

    def getReferrer(self):
        base = 'https://shopee.vn/'
        categoryName = re.sub(
            r'[\&]', '', self.currentCategory['display_name'])
        categoryRef = re.sub('--', '-', re.sub(
            '%20', '-', urllib.parse.quote(categoryName)))

        categoryId = self.currentCategory['catid']
        currentPage = self.tempItemCount//self.limit
        if currentPage == 0:
            return f'{base}{categoryRef}-cat.{categoryId}'
        return f'{base}{categoryRef}-cat.{categoryId}?page={currentPage}'

    def getProduct(self, category):
        def extractProduct(response):
            if response == None:
                return
            try:
                data = response.json()
                print(data['total_count'], 'totla')
                if data == None:
                    return
                if data['adjust'] != None:
                    self.isProgess = False
                else:
                    self.tempMaxPage = math.ceil(
                        data['total_count']/self.limit)
                    print(len(data['items']), 'items', self.tempMaxPage)
                    # self.products = self.products[category].extend(
                    #     data['items'])
            except TypeError:
                self.isProgess = False

        return extractProduct

    def export_file(self):
        dfCategory = pandas.DataFrame(self.categoryList)
        category_file_path = 'categoryList_shopee.json'
        dfCategory.to_json(category_file_path, orient="values")

        dfseller = pandas.DataFrame(self.products)
        seller_file_path = 'products_shopee.json'
        print(len(self.products))
        dfseller.to_json(seller_file_path, orient="values")

    @ classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Summary
        Args:
            crawler (TYPE): Description
            *args: Description
            **kwargs: Description
        Returns:
            TYPE: Description
        """
        spider = super(ShopeeSpider2, cls).from_crawler(
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
        if self.driver != None:
            self.driver.Dispose()

    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f'quotes-{page}.html'
        with open(filename, 'wb') as f:
            f.write(response.body)
