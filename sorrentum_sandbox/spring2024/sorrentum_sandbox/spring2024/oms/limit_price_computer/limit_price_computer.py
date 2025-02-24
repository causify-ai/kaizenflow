"""
Import as:

import oms.limit_price_computer.limit_price_computer as olpclprco
"""
import abc
import logging
from typing import Any, Dict

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


class AbstractLimitPriceComputer(abc.ABC, hobject.PrintableMixin):
    """
    Abstract class for calculating limit price.
    """

    def __init__(self) -> None:
        """
        Constructor.
        """

    @staticmethod
    def get_latest_timestamps_from_bid_ask_data(
        bid_ask_price_data: pd.DataFrame,
    ) -> Dict[str, pd.Timestamp]:
        """
        Get timestamp data related to the bid/ask price.

        The target timestamps are:
        - "binance_timestamp" timestamp of the bid/ask provided by the exchange.
        - "knowledge_timestamp": when the data was loaded into the DB
        - "end_download_timestamp": when the data was downloaded by the extractor.

        :param bid_ask_price_data: bid/ask prices for a certain asset
            For the example of bid/ask data see `_calculate_limit_price()`
        :return: dictionary of target timestamp values
        """
        # Add number of data points present in the bid/ask data.
        num_data_points = bid_ask_price_data.shape[0]
        # Get the latest data point.
        latest_bid_ask = bid_ask_price_data.iloc[-1]
        # Extract all timestamps related to the price data.
        end_download_timestamp_col = "end_download_timestamp"
        knowledge_timestamp_col = "knowledge_timestamp"
        #
        end_download_timestamp = latest_bid_ask[end_download_timestamp_col]
        knowledge_timestamp = latest_bid_ask[knowledge_timestamp_col]
        #
        exchange_timestamp = latest_bid_ask.name
        # Create a mapping to include in the output.
        out_data = {
            "num_data_points": num_data_points,
            "exchange_timestamp": exchange_timestamp,
            "knowledge_timestamp": knowledge_timestamp,
            "end_download_timestamp": end_download_timestamp,
        }
        return out_data

    @staticmethod
    def get_latest_size_from_bid_ask_data(
        bid_ask_data: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        Extract latest bid/ask size data.

        The data is retrieved from the DB and is expected to be
        normalized with `normalize_bid_ask_data` method.
        """
        bid_size_col = "bid_size_l1"
        ask_size_col = "ask_size_l1"
        # Verify that data contains numeric values for size.
        for col in [bid_size_col, ask_size_col]:
            hdbg.dassert_in(col, bid_ask_data.columns)
            hdbg.dassert_type_is(float(bid_ask_data.iloc[0][col]), float)
        # Validate that the data has a valid datetime index.
        hpandas.dassert_time_indexed_df(
            bid_ask_data, allow_empty=False, strictly_increasing=True
        )
        # Get latest size data.
        bid_size_latest, ask_size_latest = bid_ask_data[
            [bid_size_col, ask_size_col]
        ].iloc[-1]
        size_dict = {
            "latest_bid_size": bid_size_latest,
            "latest_ask_size": ask_size_latest,
        }
        return size_dict

    def to_dict(self) -> Dict[str, Any]:
        """
        Get dict representation of the object, e.g.

        ```
        {
            'object_type': 'LimitPriceComputerUsingSpread',
            'passivity_factor': 0.55,
            'max_deviation': 0.01
        }
        ```
        """
        obj_dict = {}
        # Save the class name.
        obj_dict["object_type"] = self.__class__.__name__
        # Save the attributes of an instance.
        obj_dict.update(self.__dict__)
        return obj_dict

    @abc.abstractmethod
    def calculate_limit_price(
        self,
        bid_ask_data: pd.DataFrame,
        side: str,
        price_precision: int,
        execution_freq: pd.Timedelta,
        wave_id: int,
    ) -> Dict[str, Any]:
        """
        Return limit price and price data such as latest/mean bid/ask price.

        :param bid_ask_data: bid/ask prices for a single asset
            Example of input bid ask data (levels 3-10 omitted for readability):

                                         currency_pair exchange_id           end_download_timestamp              knowledge_timestamp  bid_size_l1  bid_size_l2  ... bid_price_l1  bid_price_l2   ...  ask_size_l1  ask_size_l2  ...  ask_price_l1  ask_price_l2 ...   ccxt_symbols    asset_id
        timestamp
        2023-08-11 12:49:52.835000+00:00      GMT_USDT     binance 2023-08-11 12:49:52.975836+00:00 2023-08-11 12:49:53.205151+00:00      38688.0     279499.0  ...        0.2033        0.2032  ...     232214.0     244995.0  ...       0.2034        0.2035  ...  GMT/USDT:USDT  1030828978
        2023-08-11 12:49:52.835000+00:00      GMT_USDT     binance 2023-08-11 12:49:53.482785+00:00 2023-08-11 12:49:55.324804+00:00      38688.0     279499.0  ...        0.2033        0.2032  ...     232214.0     244995.0  ...       0.2034        0.2035  ...  GMT/USDT:USDT  1030828978
        :param side: "buy" or "sell"
        :param price_precision: precision (number of decimal places) required
            by the exchange for setting limit prices, which may vary depending
            on the specific asset. Use `price_precision` to round the calculated
            limit price to meet the exchange's precision requirements
        :param wave_id: number of the TWAP child order wave
            Required for dynamic change of calculation parameters wave to wave.
        :param execution_freq: frequency of child order wave submission
        :return: limit price of the single asset (additional keys are permitted)
            Example output schema :
            ```
            {
                'limit_price': float,
            }
            ```
        """

    def normalize_bid_ask_data(self, bid_ask_data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and normalize the bid ask data.

        :param bid_ask_data: bid/ask prices for a single asset
            Example of input data see `calculate_limit_price().`
        :return: normalized bid_ask_data

            Example of normalized bid ask data:
                                                            end_download_timestamp              knowledge_timestamp    bid_price_l1  ask_price_l1
            timestamp
            2023-08-11 12:49:52.835000+00:00      2023-08-11 12:49:52.975836+00:00 2023-08-11 12:49:53.205151+00:00      0.2033        0.2032
            2023-08-11 12:49:52.835000+00:00      2023-08-11 12:49:53.482785+00:00 2023-08-11 12:49:55.324804+00:00      0.2033        0.2032
        """
        # Validate that data contains numeric columns for prices
        # and quantities.
        bid_price_col = "bid_price_l1"
        ask_price_col = "ask_price_l1"
        for col in [bid_price_col, ask_price_col]:
            hdbg.dassert_in(col, bid_ask_data.columns)
            hdbg.dassert_type_is(float(bid_ask_data.iloc[0][col]), float)
        # Validate that the data contains timestamp columns.
        end_download_timestamp_col = "end_download_timestamp"
        knowledge_timestamp_col = "knowledge_timestamp"
        for col in [end_download_timestamp_col, knowledge_timestamp_col]:
            hdbg.dassert_in(col, bid_ask_data.columns)
            hdbg.dassert_type_is(
                pd.Timestamp(bid_ask_data.iloc[0][col]), pd.Timestamp
            )
        # Validate that the data has a valid datetime index.
        hpandas.dassert_time_indexed_df(
            bid_ask_data, allow_empty=False, strictly_increasing=True
        )
        # Validate if the data is of single asset.
        hdbg.dassert_eq(1, len(bid_ask_data["asset_id"].unique()))
        hdbg.dassert_lt(0, len(bid_ask_data))
        bid_ask_price_data = bid_ask_data[
            [
                bid_price_col,
                ask_price_col,
                end_download_timestamp_col,
                knowledge_timestamp_col,
            ]
        ]
        return bid_ask_price_data
