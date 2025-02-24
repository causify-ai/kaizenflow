"""
Import as:

import market_data.im_client_market_data as mdimcmada
"""

import logging
from typing import Any, List, Optional, cast

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu
import market_data.abstract_market_data as mdabmada

_LOG = logging.getLogger(__name__)


class ImClientMarketData(mdabmada.MarketData):
    """
    Implement a `MarketData` that uses a `ImClient` as backend.
    """

    def __init__(
        self, *args: Any, im_client: icdc.ImClient, **kwargs: Any
    ) -> None:
        """
        Build object.
        """
        super().__init__(*args, **kwargs)
        hdbg.dassert_isinstance(im_client, icdc.ImClient)
        self._im_client = im_client

    def get_last_price(
        self,
        col_name: str,
        asset_ids: List[int],
    ) -> pd.DataFrame:
        """
        Override parent method in `MarketData`.

        In contrast with specific `MarketData` backends,
        `ImClientMarketData` uses the end of interval for date
        filtering.
        """
        last_end_time = self.get_last_end_time()
        _LOG.info("last_end_time=%s", last_end_time)
        # Get the data.
        df = self.get_data_at_timestamp(
            last_end_time,
            self._end_time_col_name,
            asset_ids,
        )
        # Convert the df of data into a series.
        hdbg.dassert_in(col_name, df.columns)
        last_price = df[[col_name, self._asset_id_col]]
        # TODO(gp): Print if there are nans.
        return last_price

    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        """
        See the parent class.
        """
        # TODO(gp): It should delegate to the ImClient.
        return True

    def _get_data(
        self,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        left_close: bool,
        right_close: bool,
        limit: Optional[int],
        ignore_delay: bool,
    ) -> pd.DataFrame:
        """
        See the parent class.
        """
        _LOG.debug(
            hprint.to_str(
                "start_ts end_ts ts_col_name asset_ids left_close right_close limit ignore_delay"
            )
        )
        # This is used only in ReplayedMarketData.
        _ = ignore_delay
        if not left_close:
            if start_ts is not None:
                # Add one millisecond to not include the left boundary.
                start_ts += pd.Timedelta(1, "ms")
        if not right_close:
            if end_ts is not None:
                # Subtract one millisecond not to include the right boundary.
                end_ts -= pd.Timedelta(1, "ms")
        if asset_ids is None:
            # If asset ids are not provided, get universe as full symbols.
            full_symbols = self._im_client.get_universe()
        else:
            # Convert asset ids to full symbols to read `im` data.
            full_symbols = self._im_client.get_full_symbols_from_asset_ids(
                asset_ids
            )
        # Load the data using `im_client`.
        ivcu.dassert_valid_full_symbols(full_symbols)
        #
        # TODO(gp): im_client should always return the name of the column storing
        #  the asset_id as "full_symbol" instead we access the class to see what
        #  is the name of that column.
        full_symbol_col_name = self._im_client._get_full_symbol_col_name(None)
        if self._columns is not None:
            # Exclude columns specific of `MarketData` when querying `ImClient`.
            columns_to_exclude_in_im = [
                self._asset_id_col,
                self._start_time_col_name,
                self._end_time_col_name,
            ]
            query_columns = [
                col
                for col in self._columns
                if col not in columns_to_exclude_in_im
            ]
            if full_symbol_col_name not in query_columns:
                # Add full symbol column to the query if its name wasn't passed
                # since it is necessary for asset id column generation.
                query_columns.insert(0, full_symbol_col_name)
        else:
            query_columns = cast(List[str], self._columns)
        # Read data.
        market_data = self._im_client.read_data(
            full_symbols,
            start_ts,
            end_ts,
            query_columns,
            self._filter_data_mode,
        )
        _LOG.debug(
            "-> df after _im_client.read_data=\n%s",
            hpandas.df_to_str(market_data),
        )
        # Add `asset_id` column.
        _LOG.debug("asset_id_col=%s", self._asset_id_col)
        _LOG.debug("full_symbol_col_name=%s", full_symbol_col_name)
        _LOG.debug("market_data.columns=%s", sorted(list(market_data.columns)))
        hdbg.dassert_in(full_symbol_col_name, market_data.columns)
        transformed_asset_ids = self._im_client.get_asset_ids_from_full_symbols(
            market_data[full_symbol_col_name].tolist()
        )
        if self._asset_id_col in market_data.columns:
            _LOG.debug(
                "Overwriting column '%s' with asset_ids", self._asset_id_col
            )
            market_data[self._asset_id_col] = transformed_asset_ids
        else:
            market_data.insert(
                0,
                self._asset_id_col,
                transformed_asset_ids,
            )
        if self._columns is not None:
            # Drop full symbol column if it was not in the sepcified columns.
            if full_symbol_col_name not in self._columns:
                market_data = market_data.drop(full_symbol_col_name, axis=1)
        hdbg.dassert_in(self._asset_id_col, market_data.columns)
        if limit:
            # Keep only top N records.
            hdbg.dassert_lte(1, limit)
            market_data = market_data.head(limit)
        # Prepare data for normalization by the parent class.
        market_data = self._convert_data_for_normalization(market_data)
        _LOG.debug(
            "-> df after _convert_data_for_normalization=\n%s",
            hpandas.df_to_str(market_data),
        )
        return market_data

    def _convert_data_for_normalization(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert data to format required by normalization in parent class.

        :param df: IM data to transform
        ```
                                  full_symbol     close     volume
                      index
        2021-07-26 13:42:00  binance:BTC_USDT  47063.51  29.403690
        2021-07-26 13:43:00  binance:BTC_USDT  46946.30  58.246946
        2021-07-26 13:44:00  binance:BTC_USDT  46895.39  81.264098
        ```
        :return: transformed data
        ```
                        end_ts       full_symbol     close     volume             start_ts
        idx
        0  2021-07-26 13:42:00  binance:BTC_USDT  47063.51  29.403690  2021-07-26 13:41:00
        1  2021-07-26 13:43:00  binance:BTC_USDT  46946.30  58.246946  2021-07-26 13:42:00
        2  2021-07-26 13:44:00  binance:BTC_USDT  46895.39  81.264098  2021-07-26 13:43:00
        ```
        """
        # Move the index to the end ts column.
        df.index.name = "index"
        df = df.reset_index()
        hdbg.dassert_not_in(self._end_time_col_name, df.columns)
        df = df.rename(columns={"index": self._end_time_col_name})
        # `IM` data is assumed to have 1 minute frequency.
        hdbg.dassert_not_in(self._start_time_col_name, df.columns)
        # hdbg.dassert_eq(df.index.freq, "1T")
        df[self._start_time_col_name] = df[
            self._end_time_col_name
        ] - pd.Timedelta(minutes=1)
        return df

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        # We need to find the last timestamp before the current time. If don't have data
        # for an asset for the past hour it does not make any sense to compute further.
        # TODO(Grisha): should be a function of `bar_length_in_minutes`, e.g.,
        # `bar_length_in_minutes * 2`. In order not to complicate the interface
        #  use 15T (the longest bar length) * 2.
        timedelta = pd.Timedelta("30T")
        df = self.get_data_for_last_period(timedelta)
        _LOG.debug(
            hpandas.df_to_str(
                df, print_shape_info=True, tag="after get_data_for_last_period"
            )
        )
        if df.empty:
            wall_clock_time = self.get_wall_clock_time()
            _LOG.warning(
                "No data found near wall_clock_time=%s", wall_clock_time
            )
            ret = None
        else:
            # The latest timestamp is min timestamp across max timestamps
            # across all assets. In other words, data is ready when data is
            # ready for every asset.
            # E.g., we have 3 assets and their data timestamps are the following:
            # asset1: 15:58, 15:59, 16:00
            # asset2: 15:58, 15:59
            # asset3: 15:58, 15:59, 16:00, 16:01
            # We are looking for end timestamp that is present for all the assets.
            # In this case, it is 15:59 because at 16:00 the data is available
            # only for `asset1` and `asset3`.
            df_max_ts_per_asset = (
                df.reset_index()
                .groupby(by=[self._asset_id_col])
                .max()[self._end_time_col_name]
            )
            _LOG.debug(
                hpandas.df_to_str(
                    df_max_ts_per_asset,
                    print_shape_info=True,
                    tag="latest timestamp per asset",
                )
            )
            ret = df_max_ts_per_asset.min()
        _LOG.debug("-> ret=%s", ret)
        return ret
