"""
Import as:

import market_data.stitched_market_data as mdstmada
"""

import logging
from typing import Any, List, Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# import im_lime.eg as imlimeg
import market_data.abstract_market_data as mdabmada
import market_data.im_client_market_data as mdimcmada

# import market_data_lime.eg_real_time_market_data as mdlertmda

_LOG = logging.getLogger(__name__)


# TODO(gp): These normalization operations should be done by the ImClient. The
#  invariant is that the output of each ImClient is mostly consistent. We might
#  need to do some renaming in IgStitchedMarketData.
def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df.index.name = "end_time"
    df.index = df.index.tz_convert("America/New_York")
    return df


def normalize_rt_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a df from the RT data.
    """
    df.index = df.index.tz_convert("America/New_York")
    df.drop(columns=["timestamp_db"], inplace=True)
    return df


def normalize_historical_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a df from the historical data.
    """
    df.rename(columns={"asset_ids": "asset_id"}, inplace=True)
    return df


# #############################################################################
# IgStitchedMarketData
# #############################################################################


# TODO(gp): Create a general StitchedMarketData class that accepts an Historical and
#  a RealTime ImClient. Then derive IgStitchedMarketData from it customizing the
#  columns to read from each ImClient.
# TODO(gp): Add tests using MarketData_TestCase.
class IgStitchedMarketData(mdabmada.MarketData):
    """
    Accept a RealTimeImClient and an historical ImClient, and.
    """

    def __init__(
        self,
        asset_ids: List[Any],
        get_wall_clock_time: hdateti.GetWallClockTime,
        # TODO(gp): Can we accept two ImClient?
        eg_rt_market_data,  #: mdlertmda.IgRealTimeMarketData,
        eg_historical_im_client,  #: imlimeg.IgHistoricalPqByDateTaqBarClient,
        # TODO(gp): It should accept two column remapping and then support another
        #  remapping after the merge?
        **kwargs: Any,
    ):
        self._ig_rt_market_data = eg_rt_market_data
        self._ig_historical_im_client = eg_historical_im_client
        asset_id_col = "asset_id"
        start_time_col_name = "start_time"
        end_time_col_name = "end_time"
        # Real-time columns.
        columns = [
            start_time_col_name,
            end_time_col_name,
            asset_id_col,
            "close",
            "volume",
            "timestamp_db",
            "bid_price",
            "ask_price",
            "bid_num_trade",
            "ask_num_trade",
            "day_spread",
            "day_num_spread",
        ]
        # Rename columns from real-time fields to historical fields.
        column_remap = {
            # TODO(gp): Some pipelines call volume "vol", which could be
            # confused with volatility. We should be explicit and call it
            # "volume".
            # "volume": "vol",
            "ask_price": "good_ask",
            "bid_price": "good_bid",
            "bid_num_trade": "sided_bid_count",
            "ask_num_trade": "sided_ask_count",
        }
        super().__init__(
            asset_id_col,
            asset_ids,
            start_time_col_name,
            end_time_col_name,
            columns,
            get_wall_clock_time,
            column_remap=column_remap,
            **kwargs,
        )

    def get_data_for_last_period(
        self,
        timedelta: pd.Timedelta,
        *,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Return data for the given `timedelta`.

        The data from current wall clock time to the previous midnight is retrieved
        from the RT market data source.
        The data from midnight to X - 1 days is retrieved from the historical IM client.
        """
        _LOG.debug(hprint.to_str("timedelta"))
        # Parse the `timedelta`.
        hpandas.dassert_is_days(timedelta, min_num_days=2)
        # Retrieve the wall clock time.
        get_wall_clock_time = self._ig_rt_market_data.get_wall_clock_time
        # The last day is retrieved from the RT MarketData.
        # rt_timedelta = pd.Timedelta("1D")
        wall_clock_time = get_wall_clock_time()
        historical_market_data_end_ts = wall_clock_time.replace(
            hour=0, minute=0, second=0
        )
        rt_timedelta = wall_clock_time - historical_market_data_end_ts
        _LOG.debug("rt_timedelta=%s", rt_timedelta)
        rt_market_data_df = self._ig_rt_market_data.get_data_for_last_period(
            rt_timedelta,
        )
        _LOG.debug(
            hpandas.df_to_str(
                rt_market_data_df, tag="==> rt_market_data_df", print_dtypes=True
            )
        )
        # rt_market_data_df=
        #                                          start_time   asset_id  close  volume               timestamp_db  good_bid  good_ask  sided_bid_count  sided_ask_count  day_spread  day_num_spread
        # end_time
        # 2022-01-10 09:01:00-05:00 2022-01-10 09:00:00-05:00  17085    NaN       0 2022-01-10 14:01:04.805855    169.27    169.30                0                0        1.82              59
        # 2022-01-10 09:02:00-05:00 2022-01-10 09:01:00-05:00  17085    NaN       0 2022-01-10 14:02:03.021451    169.29    169.31                0                0        3.17             119
        # 2022-01-10 09:03:00-05:00 2022-01-10 09:02:00-05:00  17085    NaN       0 2022-01-10 14:03:02.915018    169.16    169.18                0                0        4.85             179
        #
        hdbg.dassert_lte(1, rt_market_data_df.shape[0])
        # The rest of the data comes from the historical MarketData.
        # wall_clock_time = get_wall_clock_time()
        # historical_market_data_end_ts = wall_clock_time.replace(
        #     hour=0, minute=0, second=0
        # )
        hdbg.dassert_lte(2, timedelta.days)
        historical_timedelta = pd.Timedelta(days=(timedelta.days - 1))
        _LOG.debug("historical_timedelta=%s", historical_timedelta)
        historical_market_data_start_ts = (
            historical_market_data_end_ts - historical_timedelta
        )
        _LOG.debug(
            "historical_market_data=[%s,%s]",
            historical_market_data_start_ts,
            historical_market_data_end_ts,
        )
        full_symbol_col_name = "asset_ids"
        # TODO(gp): timestamp_db is not in the historical bar data. Hopefully
        #  it is in the archived bar data.
        columns = "end_time start_time asset_id close volume good_bid good_ask sided_bid_count sided_ask_count day_spread day_num_spread"
        #
        columns = columns.split()
        # TODO(gp): Call the proper function to convert asset_ids to full_symbols.
        full_symbols = list(map(str, self._asset_ids))
        filter_data_mode = "assert"
        historical_market_data_df = self._ig_historical_im_client.read_data(
            full_symbols,
            historical_market_data_start_ts,
            historical_market_data_end_ts,
            columns,
            filter_data_mode,
            full_symbol_col_name=full_symbol_col_name,
        )
        _LOG.debug(
            hpandas.df_to_str(
                historical_market_data_df,
                tag="==> historical_market_data_df",
                print_dtypes=True,
            )
        )
        # historical_market_data_df=
        #                                          start_time    asset_ids  close  volume  good_bid  good_ask  sided_bid_count  sided_ask_count  day_spread  day_num_spread
        # timestamp
        # 2022-01-03 14:01:00+00:00 2022-01-03 14:00:00+00:00  17085.0    NaN     0.0    177.65    177.74              0.0              0.0        2.76            59.0
        # 2022-01-03 14:02:00+00:00 2022-01-03 14:01:00+00:00  17085.0    NaN     0.0    177.55    177.56              0.0              0.0        6.23           119.0
        # 2022-01-03 14:03:00+00:00 2022-01-03 14:02:00+00:00  17085.0    NaN     0.0    177.63    177.66              0.0              0.0       11.74           179.0
        #
        hdbg.dassert_lte(1, historical_market_data_df.shape[0])
        # Align the columns names.
        # TODO(gp): Clean up this.
        rt_market_data_df = normalize_rt_df(rt_market_data_df)
        rt_market_data_df = normalize_df(rt_market_data_df)
        historical_market_data_df = normalize_historical_df(
            historical_market_data_df
        )
        historical_market_data_df = normalize_df(historical_market_data_df)
        # Merge.
        # hdbg.dassert_set_eq(
        #    rt_market_data_df.columns, historical_market_data_df.columns
        # )
        df = pd.concat([rt_market_data_df, historical_market_data_df], axis=0)
        df.sort_index(ascending=True, inplace=True)
        # _LOG.debug(
        #    hpandas.df_to_str(
        #        df, print_shape_info=True, print_dtypes=True, tag="==> df"
        #    )
        # )
        # df["asset_id"] = df["asset_id"].astype(int)
        # _LOG.debug(
        #    hpandas.df_to_str(
        #        df, print_shape_info=True, print_dtypes=True, tag="==> df"
        #    )
        # )
        # TODO(gp): There should be a single row for each (timestamp, EG id).
        # hpandas.dassert_strictly_increasing_index(df)
        return df

    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        return self._ig_rt_market_data.should_be_online(wall_clock_time)

    def _get_data(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> pd.DataFrame:
        # TODO(gp): Check that we are asking for data that comes from the RT part.
        df = self._ig_rt_market_data._get_data(*args, **kwargs)
        return df

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        return self._ig_rt_market_data._get_last_end_time()


# #############################################################################
# HorizontalStitchedMarketData
# #############################################################################


class HorizontalStitchedMarketData(mdabmada.MarketData):
    """
    Stitch together 2 `ImClientMarketData` objects horizontally.

    Input df1:
    ```
                          end_ts    asset_id        full_symbol      open      high       low     close    volume        vwap  number_of_trades        twap              knowledge_timestamp
    0  2022-04-30 20:01:00-04:00  1464553467  binance::ETH_USDT   2726.62   2727.16   2724.99   2725.59   648.179   2725.8408               618   2725.7606 2022-06-20 09:49:40.140622+00:00
    1  2022-04-30 20:01:00-04:00  1467591036  binance::BTC_USDT  37635.00  37635.60  37603.70  37626.80   168.216  37619.4980              1322  37619.8180 2022-06-20 09:48:46.910826+00:00
    2  2022-04-30 20:02:00-04:00  1464553467  binance::ETH_USDT   2725.59   2730.42   2725.59   2730.04  1607.265   2728.7821              1295   2728.3652 2022-06-20 09:49:40.140622+00:00
    ```

    Input df2:
    ```
                          end_ts    asset_id        full_symbol                   start_ts     bid_price  bid_size     ask_price  ask_size
    0  2022-04-30 20:01:00-04:00  1464553467  binance::ETH_USDT  2022-04-30 20:00:00-04:00   2725.493716  1035.828   2725.731107  1007.609
    1  2022-04-30 20:01:00-04:00  1467591036  binance::BTC_USDT  2022-04-30 20:00:00-04:00  37620.402680   120.039  37622.417898   107.896
    2  2022-04-30 20:02:00-04:00  1464553467  binance::ETH_USDT  2022-04-30 20:01:00-04:00   2728.740700   732.959   2728.834137  1293.961
    ```

    Output df:
    ```
                                 asset_id        full_symbol      open      high       low     close    volume        vwap  number_of_trades        twap              knowledge_timestamp                  start_ts     bid_price  bid_size     ask_price  ask_size
    end_ts
    2022-04-30 20:01:00-04:00  1464553467  binance::ETH_USDT   2726.62   2727.16   2724.99   2725.59   648.179   2725.8408               618   2725.7606 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:00:00-04:00   2725.493716  1035.828   2725.731107  1007.609
    2022-04-30 20:01:00-04:00  1467591036  binance::BTC_USDT  37635.00  37635.60  37603.70  37626.80   168.216  37619.4980              1322  37619.8180 2022-06-20 09:48:46.910826+00:00 2022-04-30 20:00:00-04:00  37620.402680   120.039  37622.417898   107.896
    2022-04-30 20:02:00-04:00  1464553467  binance::ETH_USDT   2725.59   2730.42   2725.59   2730.04  1607.265   2728.7821              1295   2728.3652 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:01:00-04:00   2728.740700   732.959   2728.834137  1293.961
    ```
    """

    def __init__(
        self,
        *args: Any,
        im_client_market_data1: mdabmada.MarketData,
        im_client_market_data2: mdabmada.MarketData,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        hdbg.dassert_isinstance(
            im_client_market_data1, mdimcmada.ImClientMarketData
        )
        hdbg.dassert_isinstance(
            im_client_market_data2, mdimcmada.ImClientMarketData
        )
        self._im_client_market_data1 = im_client_market_data1
        self._im_client_market_data2 = im_client_market_data2

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
        market_data_df1 = self._im_client_market_data1._get_data(
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            left_close,
            right_close,
            limit,
            ignore_delay,
        )
        market_data_df2 = self._im_client_market_data2._get_data(
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            left_close,
            right_close,
            limit,
            ignore_delay,
        )
        # TODO(Grisha): @Dan If the data is coming from the same data source,
        # then we merge on `full_symbol` and `asset_id`. If the data is coming
        # from different data sets then the merge should be done on
        # `full_symbol` and not `asset_id`.
        cols_to_merge_on = [
            self._end_time_col_name,
            self._asset_id_col,
            # TODO(Grisha): get the name from the ImClient.
            "full_symbol",
            self._start_time_col_name,
        ]
        #
        pd_merge_kwargs = {}
        pd_merge_kwargs["how"] = "outer"
        pd_merge_kwargs["on"] = cols_to_merge_on
        pd_merge_kwargs["suffixes"] = ("_df1", "_df2")
        # TODO(Grisha): do not hard-wire column name, pass via interface instead.
        knowledge_timestamp_column_name = "knowledge_timestamp"
        # TODO(Grisha): consider factoring out and extending for other columns, e.g.,
        # `end_download_timestamp`.
        if (
            knowledge_timestamp_column_name in market_data_df1.columns
            and knowledge_timestamp_column_name in market_data_df2.columns
        ):
            # Allow to have `knowledge_timestamp` in both dataframes.
            intersecting_columns = [knowledge_timestamp_column_name]
        else:
            intersecting_columns = None
        # Merge dataframes.
        market_data_df = hpandas.merge_dfs(
            market_data_df1,
            market_data_df2,
            self._end_time_col_name,
            intersecting_columns=intersecting_columns,
            **pd_merge_kwargs,
        )
        # TODO(Grisha): consider factoring out and extending for other columns, e.g.,
        # `end_download_timestamp`.
        if intersecting_columns is not None:
            hdbg.dassert_eq(len(pd_merge_kwargs["suffixes"]), 2)
            # Keep the latest knowledge_timestamp of the two.
            knowledge_timestamp_column_name_df1 = (
                knowledge_timestamp_column_name + pd_merge_kwargs["suffixes"][0]
            )
            knowledge_timestamp_column_name_df2 = (
                knowledge_timestamp_column_name + pd_merge_kwargs["suffixes"][1]
            )
            market_data_df[knowledge_timestamp_column_name] = market_data_df[
                [
                    knowledge_timestamp_column_name_df1,
                    knowledge_timestamp_column_name_df2,
                ]
            ].max(axis=1)
            # Drop the repeating columns.
            market_data_df = market_data_df.drop(
                columns=[
                    knowledge_timestamp_column_name_df1,
                    knowledge_timestamp_column_name_df2,
                ]
            )
        return market_data_df

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        """
        Get the last end time for the both input clients.
        """
        last_end_time1 = self._im_client_market_data1.get_last_end_time()
        last_end_time2 = self._im_client_market_data2.get_last_end_time()
        #
        if last_end_time1 is None:
            ret = last_end_time2
        elif last_end_time2 is None:
            ret = last_end_time1
        else:
            ret = max(last_end_time1, last_end_time2)
        return ret
