import scrapy
from scrapy import signals
import pandas
import logging
import math
import json
from scrapy_splash import SplashRequest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER
LOGGER.setLevel(logging.WARNING)


class element_has_css_class(object):
    """An expectation for checking that an element has a particular css class.

    locator - used to find the element
    returns the WebElement once it has the particular css class
    """

    def __init__(self, locator, css_class):
        self.locator = locator
        self.css_class = css_class

    def __call__(self, driver):
        # Finding the referenced element
        element = driver.find_element(*self.locator)
        if self.css_class in element.get_attribute("class"):
            return element
        else:
            return False


class ShopeeSpider(scrapy.Spider):
    name = "shopee"
    url = 'https://shopee.vn'
    categoryList = []
    indexCat = 5

    categoryURLList = {}
    sellerList = []
    products = []
    currentCategory = ''
    total = 0
    limit = 100
    tempMaxPage = 0
    driver = None
    isProgess = False
    currentUrl = ''
    testUrl = 'https://shopee.vn/N%C6%B0%E1%BB%9Bc-lau-s%C3%A0n-Sunlight-1kg-chai-i.31765605.2729032540'

    productsDetail = []

    def start_requests(self):
        yield scrapy.Request(url=self.testUrl, callback=self.getProduct)

    def get_category(self, response):
        self.startHeadlessBrowser()
        self.driver.get(self.url)
        # Implicit wait
        self.wait_in_seconds(100)
        categoryNextBtn = self.driver.find_element_by_css_selector(
            '.section-category-list .shopee-header-section__content .carousel-arrow.carousel-arrow--next.carousel-arrow--hint')
        self.execute_click(categoryNextBtn)

        # Explicit wait
        categories = self.driver.find_elements_by_css_selector(
            "a.home-category-list__category-grid")
        print('[CATEGORY]: count', len(categories))
        for category in categories:
            title = category.find_element_by_css_selector(
                'div > div:nth-child(2) > div').get_attribute('innerHTML')
            url = category.get_attribute('href')
            self.categoryList.append(title)
            if title in self.categoryURLList:
                self.categoryURLList[title].append(url)
            else:
                self.categoryURLList[title] = [url]

        self.currentCategory = self.categoryList[self.indexCat]
        self.getProduct(self.currentCategory)

    def getProduct(self, category):
        self.driver.get(self.categoryURLList[category][0])
        self.wait_in_seconds(100)

        while self.driver.current_url != self.currentUrl:
            next_btn = self.driver.find_element_by_css_selector(
                '.shopee-page-controller .shopee-icon-button--right ')
            items = self.driver.find_elements_by_css_selector(
                "div.shopee-search-item-result__item.col-xs-2-4 a")

            for item in items:
                self.products.append(item.get_attribute('href'))
            self.currentUrl = self.driver.current_url
            self.execute_click(next_btn)

    def getProductDetail(self):
        for item in self.products:
            self.driver.get(item)
            self.wait_in_seconds(100)
            self.extractProductInfo()

    def extractProductInfo(self):
        productBrief = self.driver.find_element_by_css_selector(
            '.product-briefing')
        img = productBrief.find_element_by_css_selector('img')
        print(img)

    def closeChromeDriver(self):
        if self.driver != None:
            self.driver.quit()

    def execute_click(self, element):
        self.driver.execute_script("arguments[0].click();", element)
        self.wait_in_seconds(100)

    def wait_in_seconds(self, seconds):
        if self.driver == None:
            self.startHeadlessBrowser()
        self.driver.implicitly_wait(seconds)

    def driver_wait_until(self):
        if self.driver == None:
            self.startHeadlessBrowser()
        return WebDriverWait(self.driver, 10)

    def startHeadlessBrowser(self):
        if self.driver == None:
            options = webdriver.ChromeOptions()
            options.add_argument("headless")
            desired_capabilities = options.to_capabilities()
            self.driver = webdriver.Chrome(
                desired_capabilities=desired_capabilities)
            self.driver.set_window_size(3024, 3768)
        return self.driver

    def export_file(self):
        dfCategory = pandas.DataFrame.from_dict(
            self.categoryURLList, orient='index')
        category_file_path = 'categoryList_shopee.json'
        dfCategory.to_json(category_file_path)

        dfseller = pandas.DataFrame(self.products)
        print(self.indexCat, 'ON', len(self.categoryList))
        print('TOTAL', len(self.products))

        seller_file_path = f'products_shopee-{self.currentCategory}.json'
        dfseller.to_json(seller_file_path, orient="records")

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
        spider = super(ShopeeSpider, cls).from_crawler(
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
        self.closeChromeDriver()

    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f'quotes-{page}.html'
        with open(filename, 'wb') as f:
            f.write(response.body)
