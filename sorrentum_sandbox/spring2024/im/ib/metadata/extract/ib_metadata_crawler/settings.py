"""
Import as:

import im.ib.metadata.extract.ib_metadata_crawler.settings as imimeimcse
"""

import datetime as dt

import environs

# 20210723-205200
ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S%f")
env = environs.Env()

ITEM_PIPELINES = {
    "ib_metadata_crawler.pipelines.ExchangeUniquePipeline": 100,
    "ib_metadata_crawler.pipelines.CSVPipeline": 200,
}

BOT_NAME = "ib_metadata_crawler"
SPIDER_MODULES = ["ib_metadata_crawler.spiders"]
NEWSPIDER_MODULE = "ib_metadata_crawler.spiders"
ROBOTSTXT_OBEY = False
LOG_LEVEL = env.log_level("LOG_LEVEL", "INFO")
OUTCOME_LOCATION = env.path("OUTCOME_LOCATION", "/outcome")
EXCHANGE_FNAME = f"exchanges-{ts}.csv"
SYMBOLS_FNAME = f"symbols-{ts}.csv"
