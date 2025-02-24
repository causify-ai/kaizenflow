"""
Import as:

import dataflow_amp.system.Cx.utils as dtfasycxut
"""

import logging
import os

import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import im_v2.common.universe as ivcu
import market_data as mdata

_LOG = logging.getLogger(__name__)


# TODO(Grisha): consider moving to `dataflow`, maybe `dataflow/core/utils.py`,
# there is nothing specific to Cx.
# #############################################################################
# Load and resample OHLCV data
# #############################################################################


def load_market_data(
    market_data: mdata.MarketData,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
) -> pd.DataFrame:
    """
    Load market data.

    :param market_data: `MarketData` backed by the production DB
    :param start_timestamp: the earliest date timestamp to load data for
    :param end_timestamp: the latest date timestamp to load data for
    """
    nid = "read_data"
    timestamp_col_name = "end_timestamp"
    multiindex_output = True
    col_names_to_remove = None
    # This is similar to what `RealTimeDataSource` does in production
    # but allows to query data in the past.
    historical_data_source = dtfsys.HistoricalDataSource(
        nid,
        market_data,
        timestamp_col_name,
        multiindex_output,
        col_names_to_remove=col_names_to_remove,
    )
    # Convert to the DataFlow `Intervals` format.
    fit_intervals = [(start_timestamp, end_timestamp)]
    _LOG.info("fit_intervals=%s", fit_intervals)
    historical_data_source.set_fit_intervals(fit_intervals)
    market_data_df = historical_data_source.fit()["df_out"]
    return market_data_df


def resample_ohlcv_data(
    ohlcv_df: pd.DataFrame,
    resampling_frequency: str,
) -> pd.DataFrame:
    """
    Resample OHLCV to a target frequency.

    :param ohlcv_df: OHLCV dataframe
    :param resampling_frequency: resampling frequency
    :return: resampled OHLCV dataframe
    """
    df_columns = ohlcv_df.columns.get_level_values(0).tolist()
    hdbg.dassert_is_subset(["close", "high", "low", "open", "volume"], df_columns)
    resampling_node = dtfcore.GroupedColDfToDfTransformer(
        "resample",
        transformer_func=cofinanc.resample_bars,
        **{
            "in_col_groups": [
                ("open",),
                ("high",),
                ("low",),
                ("close",),
                ("volume",),
            ],
            "out_col_group": (),
            "transformer_kwargs": {
                "rule": resampling_frequency,
                "resampling_groups": [
                    ({"close": "close"}, "last", {}),
                    ({"high": "high"}, "max", {}),
                    ({"low": "low"}, "min", {}),
                    ({"open": "open"}, "first", {}),
                    (
                        {"volume": "volume"},
                        "sum",
                        {"min_count": 1},
                    ),
                    (
                        {
                            "close": "twap",
                        },
                        "mean",
                        {},
                    ),
                ],
                "vwap_groups": [
                    ("close", "volume", "vwap"),
                ],
            },
            "reindex_like_input": False,
            "join_output_with_input": False,
        },
    )
    resampled_ohlcv = resampling_node.fit(ohlcv_df)["df_out"]
    return resampled_ohlcv


def load_and_resample_ohlcv_data(
    market_data: mdata.MarketData,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    bar_duration: str,
) -> pd.DataFrame:
    """
    Load market data and resample it.

    :param market_data: same as in `load_market_data()`
    :param start_timestamp: same as in `load_market_data()`
    :param end_timestamp: same as in `load_market_data()`
    :param bar_duration: bar duration as pandas string
    :return: resampled market data dataframe
    """
    market_data_df = load_market_data(market_data, start_timestamp, end_timestamp)
    resampled_data = resample_ohlcv_data(market_data_df, bar_duration)
    return resampled_data


# TODO(Grisha): consider passing `MarketData` object to interface and moving to
# a more general lib.
# TODO(Grisha): -> `save_market_data()`?
# TODO(Grisha): does it support saving to S3? `to_csv()` usage below hints that
# it does not.
def dump_market_data_from_db(
    dst_file_path: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    db_stage: str,
    table_name: str,
    universe_version: str,
) -> None:
    """
    Save market data from the DB to a file.

    :param dst_file_path: file name with full path to save market data
    :param start_timestamp_as_str: string representation of start
        timestamp e.g., "20230906_101000"
    :param end_timestamp_as_str: string representation of end timestamp
        e.g., "20230906_101000"
    :param db_stage: stage of the database to use, e.g., "prod"
    :param universe_version: version of the universe e.g., "v7.1"
    """
    dst_dir, _ = os.path.split(dst_file_path)
    hdbg.dassert_dir_exists(dst_dir)
    # We add timezone info to `start_timestamp_as_str` and `end_timestamp_as_str`
    # because they are passed in the "UTC" timezone.
    # TODO(Grisha): factor out in a function `system_timestaps_str_to_timestamp()`.
    tz = "UTC"
    datetime_format = "%Y%m%d_%H%M%S"
    start_timestamp = hdateti.str_to_timestamp(
        start_timestamp_as_str, tz, datetime_format=datetime_format
    )
    end_timestamp = hdateti.str_to_timestamp(
        end_timestamp_as_str, tz, datetime_format=datetime_format
    )
    # We need to use exactly the same data that the prod system ran against
    # in production.
    vendor = "CCXT"
    mode = "trade"
    asset_ids = ivcu.get_vendor_universe_as_asset_ids(
        universe_version, vendor, mode
    )
    market_data = dtfasccxbu.get_Cx_RealTimeMarketData_prod_instance1(
        asset_ids, db_stage, table_name=table_name
    )
    # Convert timestamps to a timezone in which `MarketData` operates.
    market_data_tz = market_data._timezone
    start_timestamp = start_timestamp.tz_convert(market_data_tz)
    end_timestamp = end_timestamp.tz_convert(market_data_tz)
    # Save data.
    # Dump data for the last 7 days.
    history_start_timestamp = start_timestamp - pd.Timedelta("7D")
    # TODO(Grisha): a bit weird that we should pass `_start_time_col_name` twice, i.e.
    # when we initialize `MarketData` and in `get_data_for_interval()`.
    timestamp_col_name = market_data._start_time_col_name
    data = market_data.get_data_for_interval(
        history_start_timestamp,
        end_timestamp,
        timestamp_col_name,
        asset_ids,
        right_close=True,
    )
    # TODO(Grisha): extend `save_market_data()` so that it accepts a starting point.
    data.to_csv(dst_file_path, compression="gzip", index=True)
    _LOG.info("Saving in '%s' done", dst_file_path)
