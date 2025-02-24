import logging
import os

import pandas as pd
import pytest

import core.config as cconfig
import core.finance.bid_ask as cfibiask
import dev_scripts.notebooks as dsnrn
import helpers.hgit as hgit
import helpers.hserver as hserver

_LOG = logging.getLogger(__name__)


def build_test_universe_analysis_config() -> cconfig.ConfigList:
    """
    Default config builder for testing the Master_universe_analysis notebook.
    """
    universe_version = "v8.1"
    wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
    config = {
        "universe": {
            "vendor": "CCXT",
            "mode": "trade",
            "version": universe_version,
            "as_full_symbol": True,
        },
        "ohlcv_data": {
            "start_timestamp": pd.Timestamp("2024-02-29T00:00:00+00:00"),
            "end_timestamp": pd.Timestamp("2024-02-29T23:59:00+00:00"),
            "im_client_config": {
                "vendor": "ccxt",
                "universe_version": universe_version,
                "root_dir": "s3://cryptokaizen-unit-test/v3",
                "resample_1min": False,
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "futures",
                "data_snapshot": "",
                "aws_profile": "ck",
                "version": "v1_0_0",
                "download_universe_version": "v8",
                "tag": "downloaded_1min",
                "download_mode": "periodic_daily",
                "downloading_entity": "airflow",
            },
            "market_data_config": {
                "columns": None,
                "column_remap": None,
                "wall_clock_time": wall_clock_time,
            },
            "column_names": {
                "close": "close",
                "volume": "volume",
            },
        },
        "bid_ask_data": {
            "start_timestamp": pd.Timestamp("2024-02-18T00:00:00+00:00"),
            "end_timestamp": pd.Timestamp("2024-02-19T00:00:00+00:00"),
            "im_client_config": {
                "universe_version": "v8",
                "root_dir": "s3://cryptokaizen-unit-test/v3",
                "partition_mode": "by_year_month",
                "dataset": "bid_ask",
                "contract_type": "futures",
                "data_snapshot": "",
                "version": "v2_0_0",
                "download_universe_version": "v8",
                "tag": "resampled_1min",
                "aws_profile": "ck",
            },
            "market_data_config": {
                "columns": cfibiask.get_bid_ask_columns_by_level(1)
                + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
                "column_remap": None,
                "wall_clock_time": wall_clock_time,
                "filter_data_mode": "assert",
            },
            "rolling_window": 30,
            "column_names": {
                "timestamp": "timestamp",
                "full_symbol": "full_symbol",
                "close": "close",
                "volume": "volume",
                "volume_notional": "volume_notional",
                "ask_price": "level_1.ask_price.close",
                "bid_price": "level_1.bid_price.close",
                "bid_ask_midpoint": "level_1.bid_ask_midpoint.close",
                "half_spread": "level_1.half_spread.close",
            },
        },
        "liquidity_metrics": {
            "half_spread_bps_mean": "half_spread_bps_mean",
            "ask_vol_bps_mean": "ask_vol_bps_mean",
            "bid_vol_bps_mean": "bid_vol_bps_mean",
            "bid_vol_to_half_spread_mean": "bid_vol_to_half_spread_mean",
            "bid_vol_to_half_spread_bucket": "bid_vol_to_half_spread_bucket",
            "half_spread_bucket": "half_spread_bucket",
        },
        "US_equities_tz": "America/New_York",
        "plot_kwargs": {
            "kind": "barh",
            "logx": True,
            "figsize": (20, 100),
        },
        "partition_universe": False,
    }
    config = cconfig.Config().from_dict(config)
    config_list = cconfig.ConfigList([config])
    return config_list


@pytest.mark.skipif(
    hserver.is_inside_ci(),
    reason="The prod database is not available via GH actions",
)
class Test_run_master_universe_analysis_notebook(
    dsnrn.Test_Run_Notebook_TestCase
):
    @pytest.mark.superslow("~97 seconds.")
    def test1(self) -> None:
        """
        Run `im_v2/common/universe/notebooks/Master_universe_analysis.ipynb`
        notebook end-to-end.
        """
        amp_dir = hgit.get_amp_abs_path()
        notebook_path = (
            "im_v2/common/universe/notebooks/Master_universe_analysis.ipynb"
        )
        notebook_path = os.path.join(amp_dir, notebook_path)
        #
        config_builder = "im_v2.common.universe.test.test_notebooks.build_test_universe_analysis_config()"
        self._test_run_notebook(notebook_path, config_builder)
