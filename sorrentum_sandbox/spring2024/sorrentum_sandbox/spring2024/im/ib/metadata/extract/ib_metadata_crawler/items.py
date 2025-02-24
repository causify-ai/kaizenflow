"""
Import as:

import im.ib.metadata.extract.ib_metadata_crawler.items as imimeimcit
"""

import scrapy


class ExchangeItem(scrapy.Item):
    region = scrapy.Field()
    country = scrapy.Field()
    market = scrapy.Field()
    link = scrapy.Field()
    products = scrapy.Field()
    hours = scrapy.Field()


class SymbolItem(scrapy.Item):
    market = scrapy.Field()
    product = scrapy.Field()
    s_title = scrapy.Field()
    ib_symbol = scrapy.Field()
    symbol = scrapy.Field()
    currency = scrapy.Field()
    url = scrapy.Field()
