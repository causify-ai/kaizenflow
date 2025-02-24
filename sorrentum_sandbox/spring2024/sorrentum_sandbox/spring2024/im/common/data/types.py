"""
Import as:

import im.common.data.types as imcodatyp
"""
import enum


class AssetClass(enum.Enum):
    ETFs = "etfs"
    Forex = "forex"
    # TODO(*): -> futures
    Futures = "Futures"
    SP500 = "sp_500"
    Stocks = "stocks"


class Frequency(enum.Enum):
    Daily = "D"
    Hourly = "H"
    Minutely = "T"
    Tick = "tick"


class ContractType(enum.Enum):
    Continuous = "continuous"
    Expiry = "expiry"


# TODO(*): Is it still needed?
class Extension(enum.Enum):
    CSV = "csv"
    Parquet = "pq"
