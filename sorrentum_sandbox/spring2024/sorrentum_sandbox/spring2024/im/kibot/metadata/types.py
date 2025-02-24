"""
Import as:

import im.kibot.metadata.types as imkimetyp
"""

import dataclasses
import enum

# TODO(Amr): add doc strings to these classes with examples.
from typing import Union

import pandas as pd


class KibotContractType(enum.Enum):
    Daily = "Daily"
    OneMin = "1Min"
    TickBidAsk = "TickBidAsk"
    Continuos = "Continuous"


@dataclasses.dataclass
class ContractMetadata:
    Symbol: str
    Link: str
    Description: str


@dataclasses.dataclass
class TickBidAskContractMetadata:
    SymbolBase: str
    Symbol: str
    StartDate: str
    Size: str
    Description: str
    Exchange: str


@dataclasses.dataclass
class Adjustment:
    Date: str
    Symbol: str
    Company: str
    Action: str
    Description: str
    EventDate: str


@dataclasses.dataclass
class Ticker:
    Symbol: str
    StartDate: str
    Size: str
    Description: str
    Exchange: str
    Industry: str
    Sector: str


# TODO(*): Move up, maybe even in helpers.
DATE_TYPE = Union[str, "pandas.Timestamp", "datetime.datetime"]


@dataclasses.dataclass
class Expiry:
    month: str
    year: str


@dataclasses.dataclass
class ContractLifetime:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
