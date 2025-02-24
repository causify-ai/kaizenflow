"""
Download data from Crypto-Chassis: https://github.com/crypto-chassis.

Import as:

import im_v2.crypto_chassis.data.extract.extractor as imvccdexex
"""
# import logging
# from typing import Any, Dict, List, Optional

# import pandas as pd
# import requests
# import tqdm

# import helpers.hdatetime as hdateti
# import helpers.hdbg as hdbg
# import im_v2.common.data.extract.extractor as ivcdexex

# _LOG = logging.getLogger(__name__)


# class CryptoChassisExtractor(ivcdexex.Extractor):
#     """
#     Access exchange data from Crypto-Chassis through REST API.
#     """

#     def __init__(self, contract_type: str) -> None:
#         """
#         Construct CrytoChassis extractor.

#         :param contract_type: spot or futures contracts to extract
#         """
#         super().__init__()
#         hdbg.dassert_in(contract_type, ["spot", "futures"])
#         self.contract_type = contract_type
#         self._endpoint = "https://api.cryptochassis.com/v1"
#         self.vendor = "crypto_chassis"

#     @staticmethod
#     def coerce_to_numeric(
#         data: pd.DataFrame, float_columns: Optional[List[str]] = None
#     ):
#         """
#         Coerce given DataFrame to numeric data type.

#         :param data: data to transform
#         :param float_columns: columns to enforce float data type
#         :return: DataFrame with numeric data.
#         """
#         # Convert data to numeric.
#         data = data.apply(pd.to_numeric)
#         # Enforce float type for certain columns.
#         if float_columns:
#             data[float_columns] = data[float_columns].astype(float)
#         return data

#     def convert_currency_pair(
#         self,
#         currency_pair: str,
#         exchange_id: str = None,
#     ) -> str:
#         """
#         Convert currency pair used for getting data from exchange.

#         The transformation is dependent on the provided
#         contract types and exchange_id.

#         :param currency_pair: extracted asset, e.g. "BTC_USDT"
#         """
#         if exchange_id == "okx" or self.contract_type == "spot":
#             # Replace separators with '-', e.g.
#             # 'BTC/USDT' -> 'btc-usdt'.
#             replace = [("/", "-"), ("_", "-")]
#         elif self.contract_type == "futures":
#             # Remove separator for futures contracts, e.g.
#             #  'BTC/USDT' -> 'btcusdt'
#             replace = [("/", ""), ("_", "")]

#         for old, new in replace:
#             currency_pair = currency_pair.replace(old, new).lower()
#         return currency_pair

#     @staticmethod
#     def _build_query_url(base_url: str, **kwargs: Any) -> str:
#         """
#         Combine base API URL and query parameters.

#         :param base_url: base URL of CryptoChassis API
#         Additional parameters that can be passed as **kwargs:
#           - depth: int - allowed values: 1 to 10. Defaults to 1.
#           - interval: str, e.g. `1m`, `3m`, `5m` etc.
#           - startTime: pd.Timestamp
#           - endTime: pd.Timestamp
#           - includeRealTime: 0, 1. If set to 1, request rate limit on this
#             endpoint is 1 request per second per public IP.
#         :return: query URL with parameters
#         """
#         params = []
#         for pair in kwargs.items():
#             if pair[1] is not None:
#                 # Check whether the parameter is not empty.
#                 # Convert value to string and join query parameters.
#                 joined = "=".join([pair[0], str(pair[1])])
#                 params.append(joined)
#         joined_params = "&".join(params)
#         query_url = f"{base_url}?{joined_params}"
#         return query_url

#     def _transform_raw_bid_ask_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
#         """
#         Transform raw bid ask data as received from the API into our
#         representation.

#         Example:

#         Raw data:

#         time_seconds,bid_price_bid_size|...,ask_price_ask_size|...
#         1668384000,0.3296_28544|0.3295_34010,0.3297_19228|0.3298_91197

#         Transformed:

#         timestamp,bid_price_l1,bid_size_l1,bid_price_l2,bid_size_l2,ask_price_l2...
#         1668384000,0.3296,28544,0.3295,34010,0.3297

#         :param raw_data: data loaded from CC API.
#         :return formatted bid/ask data, example above.
#         """
#         # When data contains more than order book level 1 the returned
#         #  bid/ask columns are named "bid_price_bid_size|...",
#         #  "ask_price_ask_size|..." so we translate the names.
#         raw_data.columns = [
#             "timestamp",
#             "bid_price&bid_size",
#             "ask_price&ask_size",
#         ]
#         # Separate bid/ask data columns by levels.
#         price_size_levels = []
#         for ob_column in ["bid_price&bid_size", "ask_price&ask_size"]:
#             price_size_composite = raw_data[ob_column].str.split("|", expand=True)
#             for level in price_size_composite.columns:
#                 # Start counting the levels from 1.
#                 str_level = str(int(level) + 1)
#                 single_price_size = price_size_composite[level].str.split(
#                     "_", expand=True
#                 )
#                 # Transform bid_price&bid_size at level 1 into
#                 #  bid_price_l1 and bid_size_l1
#                 single_price_size.columns = list(
#                     map(lambda x: x + f"_l{str_level}", ob_column.split("&"))
#                 )
#                 price_size_levels.append(single_price_size)
#         price_size_levels = pd.concat(price_size_levels, axis=1)
#         # Remove deprecated columns.
#         raw_data = raw_data.drop(
#             columns=["bid_price&bid_size", "ask_price&ask_size"]
#         )
#         bid_ask_cols = list(price_size_levels.columns)
#         transformed_data = pd.concat([raw_data, price_size_levels], axis=1)
#         transformed_data = self.coerce_to_numeric(
#             transformed_data, float_columns=bid_ask_cols
#         )
#         return transformed_data

#     def _download_bid_ask(
#         self,
#         exchange_id: str,
#         currency_pair: str,
#         start_timestamp: pd.Timestamp,
#         end_timestamp: pd.Timestamp,
#         *,
#         depth: int,
#     ) -> pd.DataFrame:
#         """
#         Download snapshot data on bid/ask.

#             timestamp     bid_price     bid_size     ask_price     ask_size
#         0     1641686400     41678.35     0.017939     41686.97     1.69712319
#         1     1641686401     41678.35     0.017939     41690.58     0.04

#         :param exchange_id: the name of exchange, e.g. `binance`, `coinbase`
#         :param currency_pair: the pair of currency to exchange, e.g. `btc-usd`
#         :param start_timestamp: start of processing
#         :param depth: depth of the orderbook to download, 1 to 10
#         :return: bid/ask data
#         """
#         hdbg.dassert_isinstance(
#             start_timestamp,
#             pd.Timestamp,
#         )
#         hdbg.dassert_isinstance(
#             end_timestamp,
#             pd.Timestamp,
#         )
#         hdbg.dassert_lte(start_timestamp, end_timestamp)
#         currency_pair = self.convert_currency_pair(currency_pair, exchange_id)
#         # Verify that date parameters are of correct format.
#         if depth:
#             hdbg.dassert_lgt(1, depth, 10, True, True)
#             depth = str(depth)
#         # Set an exchange ID for futures, if applicable.
#         if self.contract_type == "futures":
#             hdbg.dassert_in(
#                 exchange_id,
#                 ["binance", "okex"],
#                 msg="Only binance and okex futures are supported",
#             )
#             if exchange_id == "binance":
#                 if currency_pair.endswith("usd"):
#                     # Change exchange and currency format to COIN-M futures.
#                     currency_pair = currency_pair + "_perp"
#                     exchange_id = "binance-coin-futures"
#                 else:
#                     # Change exchange ID to USDS futures.
#                     exchange_id = "binance-usds-futures"
#         # Build base URL.
#         core_url = self._build_base_url(
#             data_type="market-depth",
#             exchange=exchange_id,
#             currency_pair=currency_pair,
#         )
#         date_range = pd.date_range(start_timestamp, end_timestamp, freq="d")
#         all_days_data = []
#         for timestamp in tqdm.tqdm(date_range):
#             timestamp = timestamp.strftime("%Y-%m-%dT%XZ")
#             # Build URL with specified parameters.
#             query_url = self._build_query_url(
#                 core_url, startTime=timestamp, depth=depth
#             )
#             _LOG.info(query_url)
#             # Request the data.
#             r = requests.get(query_url)
#             # Retrieve raw data.
#             data_json = r.json()
#             if not data_json.get("urls"):
#                 # Return empty dataframe if there are no results.
#                 _LOG.warning("No data at %s", query_url)
#                 df_csv = pd.DataFrame()
#             else:
#                 df_csv = data_json["urls"][0]["url"]
#                 # Convert CSV into dataframe.
#                 df_csv = pd.read_csv(df_csv, compression="gzip")
#             all_days_data.append(df_csv)
#         bid_ask = pd.concat(all_days_data)
#         if bid_ask.empty:
#             _LOG.warning("No data found for given query parameters.")
#             return pd.DataFrame()
#         df = self._transform_raw_bid_ask_data(bid_ask)
#         # Drop duplicates as a safety net in case the data is faulty.
#         df = df.drop_duplicates()
#         # The API does not respect the specified timestamps
#         #  precisely.
#         # Return data only in the originally specified interval
#         #  to avoid confusion.
#         start_ts_unix = hdateti.convert_timestamp_to_unix_epoch(
#             start_timestamp, unit="s"
#         )
#         end_ts_unix = hdateti.convert_timestamp_to_unix_epoch(
#             end_timestamp, unit="s"
#         )
#         _LOG.info("DataFrame shape before timestamp filter: " + str(df.shape))
#         df = df[df["timestamp"] >= start_ts_unix]
#         df = df[df["timestamp"] <= end_ts_unix]
#         _LOG.info("DataFrame shape after timestamp filter: " + str(df.shape))
#         return df

#     def _download_ohlcv(
#         self,
#         exchange_id: str,
#         currency_pair: str,
#         start_timestamp: Optional[pd.Timestamp],
#         end_timestamp: Optional[pd.Timestamp],
#         *,
#         interval: Optional[str] = "1m",
#         include_realtime: bool = False,
#         **kwargs: Dict[str, Any],
#     ) -> pd.DataFrame:
#         """
#         Download snapshot of ohlcv.

#             timestamp     open         high         low         close        volume  vwap  number_of_trades     twap
#         0     1634011620     56775.59     56799.51     56775.59     56799.51     0.184718     56781.6130     9     56783.3033
#         1     1634011680     56822.35     56832.25     56815.59     56815.59     0.363495     56828.9840     16     56828.9512

#         :param exchange_id: the name of exchange, e.g. `binance`, `coinbase`
#         :param currency_pair: the pair of currency to download, e.g. `btc-usd`
#         :param start_timestamp: timestamp of start
#         :param end_timestamp: timestamp of end
#         :param interval: interval between data points in one bar, e.g. `1m` (default), `5h`, `2d`
#         :param include_realtime: 0 (default) or 1. If set to 1, request rate limit on this
#             endpoint is 1 request per second per public IP.
#         :return: ohlcv data
#         """
#         # Verify that date parameters are of correct format.
#         if start_timestamp:
#             hdbg.dassert_isinstance(
#                 start_timestamp,
#                 pd.Timestamp,
#             )
#             # Convert datetime to unix time, e.g. `2022-01-09T00:00:00` -> `1641686400`.
#             start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
#                 start_timestamp, unit="s"
#             )
#         if end_timestamp:
#             hdbg.dassert_isinstance(
#                 end_timestamp,
#                 pd.Timestamp,
#             )
#             end_timestamp = hdateti.convert_timestamp_to_unix_epoch(
#                 end_timestamp, unit="s"
#             )
#         currency_pair = self.convert_currency_pair(currency_pair, exchange_id)
#         # Set an exchange ID for futures, if applicable.
#         if self.contract_type == "futures":
#             hdbg.dassert_eq(
#                 exchange_id, "binance", msg="Only binance futures are supported"
#             )
#             if currency_pair.endswith("usd"):
#                 currency_pair = currency_pair + "_perp"
#                 exchange_id = "binance-coin-futures"
#             else:
#                 exchange_id = "binance-usds-futures"
#             _LOG.info("currency pair %s", currency_pair)
#         # Build base URL.
#         core_url = self._build_base_url(
#             data_type="ohlc",
#             exchange=exchange_id,
#             currency_pair=currency_pair,
#         )
#         _LOG.info("core_url %s", core_url)
#         # Convert include_realtime to CryptoChassis-compatible
#         #  format.
#         include_realtime_as_str = "1" if include_realtime else "0"
#         # Build URL with specified parameters.
#         query_url = self._build_query_url(
#             core_url,
#             startTime=start_timestamp,
#             endTime=end_timestamp,
#             interval=interval,
#             includeRealTime=include_realtime_as_str,
#         )
#         # Request the data.
#         _LOG.info("Downloading from %s", query_url)
#         r = requests.get(query_url)
#         # Retrieve raw data.
#         data_json = r.json()
#         # Get OHLCV data.
#         data = []
#         if data_json.get("historical") is not None:
#             # Process historical data.
#             df_csv = data_json["historical"]["urls"][0]["url"]
#             # Convert CSV into dataframe.
#             historical_data = pd.read_csv(df_csv, compression="gzip")
#             data.append(historical_data)
#         if data_json.get("recent") is not None:
#             # Process recent data.
#             columns = data_json["recent"]["fields"].split(", ")
#             # Build Dataframe.
#             recent_data = pd.DataFrame(
#                 columns=columns, data=data_json["recent"]["data"]
#             )
#             data.append(recent_data)
#         # Combine historical and recent Dataframes.
#         if not data:
#             # Return empty Dataframe if there is no data.
#             return pd.DataFrame()
#         ohlcv = pd.concat(data)
#         # Coerce principal data columns to numeric dtype.
#         ohlcv_columns = ["open", "high", "low", "close", "volume"]
#         ohlcv = self.coerce_to_numeric(ohlcv, float_columns=ohlcv_columns)
#         # Filter the time period since Crypto Chassis doesn't provide this functionality.
#         # (CmTask #1887).
#         if start_timestamp:
#             ohlcv = ohlcv[(ohlcv["time_seconds"] >= start_timestamp)]
#         if end_timestamp:
#             ohlcv = ohlcv[(ohlcv["time_seconds"] <= end_timestamp)]
#         # Rename time column.
#         ohlcv = ohlcv.rename(columns={"time_seconds": "timestamp"})
#         return ohlcv

#     def _download_trades(
#         self,
#         exchange_id: str,
#         currency_pair: str,
#         *,
#         start_timestamp: Optional[pd.Timestamp] = None,
#         **kwargs: Any,
#     ) -> pd.DataFrame:
#         """
#         Download snapshot of trade data.

#             timestamp     price         size        is_buyer_maker
#         0     1641686404     41692.50     0.012473     0
#         1     1641686441     41670.00     0.001194     0

#         :param exchange_id: the name of exchange, e.g. `binance`, `coinbase`
#         :param currency_pair: the pair of currency to download, e.g. `btc-usd`
#         :param start_timestamp: timestamp of start. The API ignores the times section
#          of the argument and instead return the day's worth of data (in UTC):
#          e.g. start_timestamp=2022-12-11T00:10:01+00:00 returns data in interval
#          [2022-12-11T00:00:00+00:00, 2022-12-11T23:59:59+00:00]
#         :return: trade data
#         """
#         # Verify that date parameters are of correct format.
#         if start_timestamp:
#             hdbg.dassert_isinstance(
#                 start_timestamp,
#                 pd.Timestamp,
#             )
#             start_timestamp = start_timestamp.strftime("%Y-%m-%dT%XZ")
#         currency_pair = self.convert_currency_pair(currency_pair, exchange_id)
#         # Set an exchange ID for futures, if applicable.
#         if self.contract_type == "futures":
#             hdbg.dassert_in(
#                 exchange_id,
#                 ["binance", "okex", "okx"],
#                 msg="Only binance and okex futures are supported",
#             )
#             if exchange_id == "binance":
#                 exchange_id = "binance-usds-futures"
#         # Build base URL.
#         core_url = self._build_base_url(
#             data_type="trade",
#             exchange=exchange_id,
#             currency_pair=currency_pair,
#         )
#         # Build URL with specified parameters.
#         query_url = self._build_query_url(core_url, startTime=start_timestamp)
#         # Request the data.
#         # TODO(Vlad): There is a bug in the Chassis API that causes it to return
#         #  a wrong dates for the data. For example, if we request data for
#         #  2023-01-01, it returns data for 2022-12-31.
#         #  Needs to be catch and inform the user.
#         r = requests.get(query_url)
#         # Retrieve raw data.
#         try:
#             data_json = r.json()
#         except requests.exceptions.JSONDecodeError as e:
#             _LOG.error(
#                 "Unable to retrieve data for %s" " message=%s",
#                 currency_pair,
#                 r.text,
#             )
#             raise e
#         # If there is no `urls` key or there is one but the value is an empty list.
#         if not data_json.get("urls"):
#             _LOG.info(
#                 f"Unable to retrieve data for {currency_pair} "
#                 + f"and start_timestamp={start_timestamp}"
#             )
#             # Return empty dataframe if there is no results.
#             return pd.DataFrame()
#         df_csv = data_json["urls"][0]["url"]
#         # Convert CSV into dataframe.
#         trade = pd.read_csv(df_csv, compression="gzip")
#         # Rename time column.
#         trade = trade.rename(
#             columns={"time_seconds": "timestamp", "size": "amount"}
#         )
#         # Convert milliseconds timestamp to integer.
#         trade["timestamp"] = trade["timestamp"] * 1000
#         trade["timestamp"] = trade["timestamp"].astype(int)
#         # Limit columns to those that are required.
#         trade["side"] = trade["is_buyer_maker"].map({1: "buy", 0: "sell"})
#         columns = ["timestamp", "price", "amount", "side"]
#         trade = trade[columns]
#         return trade

#     def _build_base_url(
#         self,
#         data_type: str,
#         exchange: str,
#         currency_pair: str,
#     ) -> str:
#         """
#         Build valid URL to send request to CryptoChassis API.

#         :param data_type: the type of data source, `market-depth`, `trade` or `ohlc`
#         :param exchange: the exchange type, e.g. 'binance'
#         :param currency_pair: the pair of currency to exchange, e.g. `btc-usd`
#         :return: base URL of CryptoChassis API
#         """
#         # Make-do solution because chassis uses different name for OKX.
#         if exchange == "okx":
#             exchange = "okex"
#         # Build main API URL.
#         core_url = f"{self._endpoint}/{data_type}/{exchange}/{currency_pair}"
#         return core_url

#     def _download_websocket_ohlcv(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _download_websocket_bid_ask(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _download_websocket_trades(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _subscribe_to_websocket_ohlcv(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _subscribe_to_websocket_bid_ask(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _subscribe_to_websocket_trades(
#         self, exchange_id: str, currency_pair: str, **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )

#     def _subscribe_to_websocket_bid_ask_multiple_symbols(
#         self, exchange_id: str, currency_pair: List[str], **kwargs: Any
#     ) -> Dict:
#         raise NotImplementedError(
#             "This method is not implemented for CryptoChassis vendor yet."
#         )
