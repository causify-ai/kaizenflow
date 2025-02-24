"""
Import as:

import im.ib.metadata.extract.ib_metadata_crawler.spiders.ibroker as imimeimcsi
"""

import csv
from typing import Generator, Union

import ib_metadata_crawler.items as it
import scrapy
import scrapy.http as http
import scrapy.linkextractors as le
import scrapy.loader as ldr
import scrapy.loader.processors as pr
import scrapy.signals as sig


class ExchangeLoader(ldr.ItemLoader):
    default_output_processor = pr.TakeFirst()

    products_in = pr.Join(",")
    hours_in = pr.Join(" ")


class SymbolLoader(ldr.ItemLoader):
    default_output_processor = pr.TakeFirst()


class IbrokerSpider(scrapy.Spider):
    name = "ibroker"
    allowed_domains = ["interactivebrokers.com"]
    start_urls = ["https://ndcdyn.interactivebrokers.com/en/index.php?f=1562"]
    exchange_header = ["region", "country", "market", "link", "products", "hours"]
    symbols_header = [
        "market",
        "product",
        "s_title",
        "ib_symbol",
        "symbol",
        "currency",
        "url",
    ]

    lx_regions = le.LinkExtractor(restrict_css="#toptabs ul.ui-tabs-nav")
    lx_products = le.LinkExtractor(
        restrict_css="#exchange-products div.row div.btn-selectors",
    )
    lx_pagination = le.LinkExtractor(
        restrict_css="#exchange-products ul.pagination li:not(li.disabled)"
    )

    @classmethod
    def from_crawler(
        cls, crawler: scrapy.Spider, *args, **kwargs
    ) -> scrapy.Spider:
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.init_feed, signal=sig.engine_started)
        return spider

    def init_feed(self) -> None:
        root = self.settings["OUTCOME_LOCATION"]
        with open(root / self.settings["EXCHANGE_FNAME"], "w") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(self.exchange_header)
        with open(root / self.settings["SYMBOLS_FNAME"], "w") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(self.symbols_header)

    def parse(
        self, response: http.HtmlResponse
    ) -> Generator[scrapy.Request, None, None]:
        for link in self.lx_regions.extract_links(response):
            yield scrapy.Request(
                link.url,
                self.parse_region,
                cb_kwargs={"region": link.text},
            )

    def parse_region(
        self, response: http.HtmlResponse, region: str
    ) -> Generator[scrapy.Request, None, None]:
        country = None
        table = response.css(
            "#exchange-listings div.col-xs-12 table.table tbody tr"
        )
        for t in table:
            exchange_meta = {"region": region}
            row = t.css("td")
            if row.attrib.get("rowspan"):
                country = row.css("td")[0].css("::text").get()
                row = row.css("td")[1:]
            exchange_meta["country"] = country
            exchange_meta["market"] = row[0].css("a::text").get()
            exchange_meta["products"] = row[1].css("td::text").getall() or "N/A"
            exchange_meta["hours"] = row[2].css("*::text").getall()
            url = response.urljoin(row[0].css("a").attrib["href"])
            self.logger.info(f"parse exchange: {url}")
            yield scrapy.Request(
                url,
                self.parse_exchange,
                cb_kwargs={"exchange_meta": exchange_meta},
            )

    def parse_exchange(
        self, response: http.HtmlResponse, exchange_meta: dict
    ) -> Generator[scrapy.Request, None, None]:
        exchange_meta["url"] = (
            response.xpath(
                '//*[@id="exchange-info"]/div/div/div/div[1]/table/tbody/tr/td[2]/a/@href'
            ).get()
            or "N/A"
        )
        eldr = ExchangeLoader(item=it.ExchangeItem())
        eldr.add_value("link", exchange_meta["url"])
        eldr.add_value("region", exchange_meta["region"])
        eldr.add_value("country", exchange_meta["country"])
        eldr.add_value("market", exchange_meta["market"])
        eldr.add_value("products", exchange_meta["products"])
        eldr.add_value("hours", exchange_meta["hours"])
        yield eldr.load_item()
        if self.lx_products.extract_links(response):
            for link in self.lx_products.extract_links(response):
                self.logger.info(
                    "Parse symbols of market %s, url %s",
                    exchange_meta["market"],
                    link.url,
                )
                yield scrapy.Request(
                    link.url,
                    self.parse_symbols,
                    cb_kwargs={"market": exchange_meta["market"]},
                )
        else:
            self.logger.info(
                "Parse symbols of market %s, url %s",
                exchange_meta["market"],
                response.url,
            )
            yield scrapy.Request(
                response.url,
                self.parse_symbols,
                cb_kwargs={"market": exchange_meta["market"]},
            )

    def parse_symbols(
        self, response: http.HtmlResponse, market: str
    ) -> Generator[Union[scrapy.Item, scrapy.Request], None, None]:
        product = (
            response.css(
                "#exchange-products div.btn-selectors p a.btn.btn-default.active::text"
            ).get()
            or "N/A"
        )
        symbol_title = response.css(
            "#exchange-products div.col-xs-12.col-sm-12 table.table tbody tr td a::text"
        )
        symbols = response.css("#exchange-products div.col-xs-12 tbody tr")
        for row in symbols:
            s_data = row.css("td::text").getall()
            if len(s_data) < 4:
                symbol_title = row.css("td a::text").get()
                s_data.insert(1, symbol_title)
            sldr = SymbolLoader(item=it.SymbolItem())
            sldr.add_value("market", market)
            sldr.add_value("product", product)
            sldr.add_value("s_title", s_data[1])
            sldr.add_value("ib_symbol", s_data[0])
            sldr.add_value("symbol", s_data[2])
            sldr.add_value("currency", s_data[3])
            sldr.add_value("url", response.url)
            yield sldr.load_item()

        pagination = self.lx_pagination.extract_links(response)
        if pagination and ">" in pagination[-1].text:
            yield scrapy.Request(
                pagination[-1].url,
                self.parse_symbols,
                cb_kwargs={"market": market},
            )
