"""
Import as:

import dataflow_amp.system.mock3.mock3_forecast_system_example as dtfasmmfsex
"""


import pandas as pd

import core.config as cconfig
import core.finance.bid_ask as cfibiask
import dataflow.system as dtfsys
import dataflow.universe as dtfuniver
import dataflow_amp.system.mock3.mock3_forecast_system as dtfasmmfosy
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu


def get_Mock3_NonTime_ForecastSystem_example1(
    backtest_config: str,
) -> dtfsys.NonTime_ForecastSystem:
    """
    Build an example non-timed Mock3 System.

    The function configures OHLCV + Bid/Ask MarketData.
    """
    # - Build the System.
    system = dtfasmmfosy.Mock3_NonTime_ForecastSystem()
    # - Apply backtest config.
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # - Apply tile config.
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "1D"
    # - Get asset_ids and wall_clock_time.
    # TODO(Grisha): should it go to a `MarketData` builder?
    universe_str = system.config["backtest_config", "universe_str"]
    full_symbols = dtfuniver.get_universe(universe_str)
    asset_ids = list(
        ivcu.build_numerical_to_string_id_mapping(full_symbols).keys()
    )
    # Use the latest possible timestamp to guarantee that the data is in the past, i.e.
    # the System does not do future picking and all the data is available.
    wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
    # - Get OHLCV `MarketData` config.
    ohlcv_market_data_config = {
        # TODO(Grisha): do not use examples as they hide some params, use the class itself.
        "im_client_ctor": icdcl.get_CcxtHistoricalPqByTileClient_example1,
        "im_client_config": {
            "data_version": "v3",
            # Download universe version.
            "universe_version": "v7",
            "dataset": "ohlcv",
            "contract_type": "futures",
            # Data snapshot is not applicable for data version = "v3".
            "data_snapshot": "",
        },
        "asset_ids": asset_ids,
        "wall_clock_time": wall_clock_time,
        "columns": None,
        "column_remap": None,
        "filter_data_mode": "assert",
    }
    bid_ask_level = 1
    bid_ask_market_data_config = {
        # TODO(Grisha): do not use examples as they hide some params, use the class itself.
        "im_client_ctor": icdcl.ccxt_clients.CcxtHistoricalPqByTileClient,
        "im_client_config": {
            # Download universe version.
            "universe_version": "v7",
            "dataset": "bid_ask",
            "contract_type": "futures",
            # Data snapshot is not applicable for data version = "v3".
            "data_snapshot": "",
            # Data currently residing in the preprod bucket.
            "root_dir": "s3://cryptokaizen-data.preprod/v3/",
            "partition_mode": "by_year_month",
            "version": "v1_0_0",
            "download_universe_version": "v7",
            "tag": "resampled_1min",
            "aws_profile": "ck",
        },
        "asset_ids": asset_ids,
        "wall_clock_time": wall_clock_time,
        # TODO(Grisha): for some reason the current filtering mechanism filters out `asset_ids`
        # which makes it impossible to stitch the 2 market data dfs. So adding the necessary
        # columns manually.
        "columns": cfibiask.get_bid_ask_columns_by_level(bid_ask_level)
        + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
        "column_remap": None,
        "filter_data_mode": "assert",
    }
    market_data_config = {
        "asset_ids": asset_ids,
        "asset_id_col_name": "asset_id",
        "columns": None,
        "column_remap": None,
        # TODO(Grisha): check why it fails when the mode is `assert`.
        "filter_data_mode": "warn_and_trim",
        "ohlcv_market_data": ohlcv_market_data_config,
        "bid_ask_market_data": bid_ask_market_data_config,
    }
    system.config["market_data_config"] = cconfig.Config.from_dict(
        market_data_config
    )
    return system
