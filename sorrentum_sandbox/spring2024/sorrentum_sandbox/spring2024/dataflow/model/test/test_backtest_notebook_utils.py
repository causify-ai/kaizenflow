import logging
import os
from typing import List, Optional

import pandas as pd

import core.config as cconfig
import dataflow.model.backtest_notebook_utils as dtfmbanout
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_build_research_backtest_analyzer_config_dict(hunitest.TestCase):
    def get_config(self, sweep_values: Optional[List[float]]) -> cconfig.Config:
        """
        Get default config for testing.
        """
        config_dict = {
            "asset_id_col": "asset_id",
            "pnl_resampling_frequency": "D",
            "rule": "6T",
            "annotate_forecasts_kwargs": {
                "style": "longitudinal",
                "quantization": 30,
                "liquidate_at_end_of_day": False,
                "initialize_beginning_of_day_trades_to_zero": False,
                "burn_in_bars": 3,
                "compute_extended_stats": True,
                "target_dollar_risk_per_name": 1.0,
                "modulate_using_prediction_magnitude": False,
                "prediction_abs_threshold": 0.3,
            },
        }
        if sweep_values is not None:
            config_dict["sweep_param"] = {
                "keys": (
                    "annotate_forecasts_kwargs",
                    "target_dollar_risk_per_name",
                ),
                "values": sweep_values,
            }
        config = cconfig.Config().from_dict(config_dict)
        return config

    def test_sweep_param_one_value(self) -> None:
        """
        Test with one value in `sweep_param` field.
        """
        config_dict = self.get_config(sweep_values=[0.7])
        actual = dtfmbanout.build_research_backtest_analyzer_config_sweep(
            config_dict
        )
        self.check_string(str(actual))

    def test_sweep_param_multiple_values(self) -> None:
        """
        Test with multiple values in `sweep_param` field.
        """
        config = self.get_config(sweep_values=[0.25, 0.5, 1])
        actual = dtfmbanout.build_research_backtest_analyzer_config_sweep(config)
        self.check_string(str(actual))

    def test_no_sweep_param(self) -> None:
        """
        Test without `sweep_param` field.
        """
        config = self.get_config(sweep_values=None)
        actual = dtfmbanout.build_research_backtest_analyzer_config_sweep(config)
        self.check_string(str(actual))


class Test_resample_with_weights_ohlcv_bars(hunitest.TestCase):
    def test_resample_with_weights_ohlcv_bars(self) -> None:
        """
        Test resampling OHLCV bars with weights.
        """
        # Prepare data.
        df_ohlcv = self.load_ohlcv_data()
        price_col = "close"
        bar_duration = "6T"
        weights = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        # Run.
        actual = dtfmbanout.resample_with_weights_ohlcv_bars(
            df_ohlcv, price_col, bar_duration, weights
        )
        # Check.
        df_str = hpandas.df_to_str(actual)
        self.check_string(df_str)

    def load_ohlcv_data(self) -> pd.DataFrame:
        """
        Get OHLCV data for testing.

        OHLCV data consists of:
          - named index `end_ts`: pd.DatetimeIndex
          - columns: pd.MultiIndex:
            - level 0: `close`, `high`, `low`, `open`, `twap`, `volume`, `vwap`
            - level 1: asset ids, e.g. 1464553467, 1464553468, 1464553469

        To generate new test data:
          - run the `Master_research_backtest_analyzer` notebook
          - save the first 10 rows of `ohlcv_data` variable to a CSV file
          - upload the CSV file to the S3 bucket
        """
        # Copy test data from S3 to scratch space.
        aws_profile = "ck"
        s3_input_dir = self.get_s3_input_dir(use_only_test_class=True)
        scratch_dir = self.get_scratch_space()
        hs3.copy_data_from_s3_to_local_dir(s3_input_dir, scratch_dir, aws_profile)
        # Get the path to the OHLCV data.
        oms_child_order_path = os.path.join(
            scratch_dir,
            "ohlcv_data.csv",
        )
        # Load the data.
        df_ohlcv = pd.read_csv(oms_child_order_path, header=[0, 1], index_col=0)
        df_ohlcv.index = pd.to_datetime(df_ohlcv.index)
        df_ohlcv.index.freq = "T"
        return df_ohlcv


class Test_load_backtest_tiles(hunitest.TestCase):
    def test_load_backtest_tiles1(self) -> None:
        """
        Loading backtest tiles to memory.
        """
        # Run.
        load_all_tiles_in_memory = None
        # Run.
        actual = self.helper(load_all_tiles_in_memory)
        # Check the shape.
        self.assertEqual((11161, 6), actual.shape)
        # Check the last 3 rows.
        tail = actual.tail(3)
        tail_str = hpandas.df_to_str(tail)
        self.check_string(tail_str)

    def helper(self, load_all_tiles_in_memory: Optional[int]) -> pd.DataFrame:
        """
        Helper function to test loading backtest tiles.
        """
        # Prepare data.
        log_dir = self.get_log_dir()
        start_date = pd.Timestamp("2024-01-01")
        end_date = pd.Timestamp("2024-02-01")
        asset_id_col = "asset_id"
        cols = ["open", "garman_klass_vol", "feature"]
        # Run.
        actual = dtfmbanout.load_backtest_tiles(
            log_dir, start_date, end_date, cols, asset_id_col
        )
        return actual

    def get_log_dir(self) -> str:
        """
        Get the path to the backtest log directory.

        To generate new test data:
          - run the `Master_research_backtest_analyzer` notebook
          - save the backtest log files to a directory
          - upload the directory to the S3 bucket
        """
        # Copy test data from S3 to scratch space.
        aws_profile = "ck"
        s3_input_dir = self.get_s3_input_dir(use_only_test_class=True)
        scratch_dir = self.get_scratch_space()
        hs3.copy_data_from_s3_to_local_dir(s3_input_dir, scratch_dir, aws_profile)
        return scratch_dir
