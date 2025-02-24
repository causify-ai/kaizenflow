"""
Import as:

import im.ib.metadata.extract.ib_metadata_crawler.pipelines as imimeimcpi
"""

import csv
import pathlib
from typing import Union

import ib_metadata_crawler.items as it
import ib_metadata_crawler.spiders.ibroker as ib
import scrapy
import scrapy.exceptions as ex


class ExchangeUniquePipeline:
    seen = set()

    def process_item(
        self, item: scrapy.Item, spider: ib.IbrokerSpider
    ) -> Union[scrapy.Item, ex.DropItem]:
        if isinstance(item, it.ExchangeItem):
            if item["market"] in self.seen:
                raise ex.DropItem("Market already parsed")
            self.seen.add(item["market"])
        return item


class CSVPipeline:
    def __init__(
        self, root: pathlib.Path, exchange_fname: str, symbol_fname: str
    ) -> None:
        self.root_dir = root
        self.exchange = exchange_fname
        self.symbol = symbol_fname

    @classmethod
    def from_crawler(cls, crawler: scrapy.Spider) -> scrapy.Spider:
        return cls(
            root=crawler.settings.get("OUTCOME_LOCATION"),
            exchange_fname=crawler.settings.get("EXCHANGE_FNAME"),
            symbol_fname=crawler.settings.get("SYMBOLS_FNAME"),
        )

    def open_spider(self, spider: ib.IbrokerSpider) -> None:
        self.exchange_f = open(self.root_dir / self.exchange, "a")
        self.symbol_f = open(self.root_dir / self.symbol, "a")
        self.exchange_csv = csv.writer(self.exchange_f, delimiter="\t")
        self.symbol_csv = csv.writer(self.symbol_f, delimiter="\t")

    def close_spider(self, spider: ib.IbrokerSpider) -> None:
        self.exchange_f.close()
        self.symbol_f.close()

    def process_item(
        self, item: scrapy.Item, spider: ib.IbrokerSpider
    ) -> scrapy.Item:
        if isinstance(item, it.ExchangeItem):
            return self._process_exchange(item, spider.exchange_header)
        if isinstance(item, it.SymbolItem):
            return self._process_symbol(item, spider.symbols_header)

    def _process_exchange(self, item: scrapy.Item, header: list) -> scrapy.Item:
        self.exchange_csv.writerow([item[x] for x in header])
        return item

    def _process_symbol(self, item: scrapy.Item, header: list) -> scrapy.Item:
        self.symbol_csv.writerow([item[x] for x in header])
        return item
