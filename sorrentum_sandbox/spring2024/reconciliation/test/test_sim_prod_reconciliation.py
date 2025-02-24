import os
import unittest.mock as umock
from typing import Any, Callable, Dict, Optional

import pandas as pd
import pytest

import core.config as cconfig
import dataflow.core as dtfcor
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hunit_test as hunitest
import reconciliation.sim_prod_reconciliation as rsiprrec


class Test_get_system_run_parameters(hunitest.TestCase):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield

    def set_up_test(self) -> None:
        """
        Create test dirs that have prod-like structure.

        E.g.:
        ```
        C1b\
            paper_trading\
                20230620_131000.20230621_130500\
                    system_log_dir.scheduled
                20230620_131000.20230621_130500\
                    system_log_dir.scheduled
        ...
        ```
        """
        self.setUp()
        self._prod_data_root_dir = self.get_scratch_space()
        self._dag_builder_name = "C1b"
        self._run_mode = "paper_trading"
        system_run_params = [
            ("20230720_131000", "20230721_130500", "scheduled"),
            ("20230721_131000", "20230722_130500", "manual"),
            ("20230722_131000", "20230723_130500", "scheduled"),
            ("20230723_131000", "20230724_130500", "manual"),
            ("20230724_131000", "20230725_130500", "scheduled"),
        ]
        for (
            start_timestamp_as_str,
            end_timestamp_as_str,
            mode,
        ) in system_run_params:
            # Create target dir.
            tag = ""
            target_dir = rsiprrec.get_target_dir(
                self._prod_data_root_dir,
                self._dag_builder_name,
                self._run_mode,
                start_timestamp_as_str,
                end_timestamp_as_str,
                tag=tag,
            )
            hio.create_dir(target_dir, incremental=True)
            # Create system log dir.
            system_log_dir = rsiprrec.get_prod_system_log_dir(mode)
            system_log_dir = os.path.join(target_dir, system_log_dir)
            hio.create_dir(system_log_dir, incremental=True)
        # Create multi-day test dirs.
        multiday_start_timestamp_as_str = "20230723_131000"
        multiday_end_timestamp_as_str = "20230730_130500"
        multiday_target_dir = rsiprrec.get_multiday_reconciliation_dir(
            self._prod_data_root_dir,
            self._dag_builder_name,
            self._run_mode,
            multiday_start_timestamp_as_str,
            multiday_end_timestamp_as_str,
        )
        hio.create_dir(multiday_target_dir, incremental=True)

    def check_helper(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        func: Callable,
        expected: str,
    ) -> None:
        """
        Compare the output with the expected result.
        """
        # Get system run parameters.
        tag = ""
        output = func(
            self._prod_data_root_dir,
            self._dag_builder_name,
            tag,
            self._run_mode,
            start_timestamp,
            end_timestamp,
        )
        # Check.
        actual = str(output)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test that system run parameters are returned in between
        `start_timestamp` and `end_timestamp`.
        """
        # Define params.
        start_timestamp = pd.Timestamp("2023-07-22 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2023-07-24 23:59:59+00:00")
        func = rsiprrec.get_system_run_parameters
        # Check.
        expected = [
            ("20230722_131000", "20230723_130500", "scheduled"),
            ("20230723_131000", "20230724_130500", "manual"),
            ("20230724_131000", "20230725_130500", "scheduled"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test2(self) -> None:
        """
        Test that returned system run parameters are filtered by
        `start_timestamp`.
        """
        # Define params.
        start_timestamp = pd.Timestamp("2023-07-21 00:00:00+00:00")
        end_timestamp = None
        func = rsiprrec.get_system_run_parameters
        # Check.
        expected = [
            ("20230721_131000", "20230722_130500", "manual"),
            ("20230722_131000", "20230723_130500", "scheduled"),
            ("20230723_131000", "20230724_130500", "manual"),
            ("20230724_131000", "20230725_130500", "scheduled"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test3(self) -> None:
        """
        Test that returned system run parameters are filtered by
        `end_timestamp`.
        """
        # Define params.
        start_timestamp = None
        end_timestamp = pd.Timestamp("2023-07-22 23:59:59+00:00")
        func = rsiprrec.get_system_run_parameters
        # Check.
        expected = [
            ("20230720_131000", "20230721_130500", "scheduled"),
            ("20230721_131000", "20230722_130500", "manual"),
            ("20230722_131000", "20230723_130500", "scheduled"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test4(self) -> None:
        """
        Test that system run parameters are returned for all available dirs
        when `start_timestamp` and `end_timestamp` are not defined.
        """
        # Define params.
        start_timestamp = None
        end_timestamp = None
        func = rsiprrec.get_system_run_parameters
        # Check.
        expected = [
            ("20230720_131000", "20230721_130500", "scheduled"),
            ("20230721_131000", "20230722_130500", "manual"),
            ("20230722_131000", "20230723_130500", "scheduled"),
            ("20230723_131000", "20230724_130500", "manual"),
            ("20230724_131000", "20230725_130500", "scheduled"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))


class Test_get_system_run_timestamps(Test_get_system_run_parameters):
    def test1(self) -> None:
        """
        Test that system run timestamps are returned in between
        `start_timestamp` and `end_timestamp`.
        """
        # Define params.
        start_timestamp = pd.Timestamp("2023-07-21 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2023-07-23 23:59:59+00:00")
        func = rsiprrec.get_system_run_timestamps
        # Check.
        expected = [
            ("20230721_131000", "20230722_130500"),
            ("20230722_131000", "20230723_130500"),
            ("20230723_131000", "20230724_130500"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test2(self) -> None:
        """
        Test that returned system run timestamps are filtered by
        `start_timestamp`.
        """
        # Define params.
        start_timestamp = pd.Timestamp("2023-07-22 00:00:00+00:00")
        end_timestamp = None
        func = rsiprrec.get_system_run_timestamps
        # Check.
        expected = [
            ("20230722_131000", "20230723_130500"),
            ("20230723_131000", "20230724_130500"),
            ("20230724_131000", "20230725_130500"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test3(self) -> None:
        """
        Test that returned system run timestamps are filtered by
        `end_timestamp`.
        """
        # Define params.
        start_timestamp = None
        end_timestamp = pd.Timestamp("2023-07-21 23:59:59+00:00")
        func = rsiprrec.get_system_run_timestamps
        # Check.
        expected = [
            ("20230720_131000", "20230721_130500"),
            ("20230721_131000", "20230722_130500"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))

    def test4(self) -> None:
        """
        Test that system run timestamps are returned for all available dirs
        when `start_timestamp` and `end_timestamp` are not defined.
        """
        # Define params.
        start_timestamp = None
        end_timestamp = None
        func = rsiprrec.get_system_run_timestamps
        # Check.
        expected = [
            ("20230720_131000", "20230721_130500"),
            ("20230721_131000", "20230722_130500"),
            ("20230722_131000", "20230723_130500"),
            ("20230723_131000", "20230724_130500"),
            ("20230724_131000", "20230725_130500"),
        ]
        self.check_helper(start_timestamp, end_timestamp, func, str(expected))


class Test_build_reconciliation_configs(hunitest.TestCase):
    @staticmethod
    def set_up_test(
        dst_root_dir: str,
        start_timestamp_as_str: str,
        end_timestamp_as_str: str,
        run_mode: str,
        mode: str,
    ) -> None:
        """
        Create dirs required for reconciliation configs building.

        Build a minimal config to extract `bar_duration_in_secs`.
        """
        prod_dir = os.path.join(
            dst_root_dir,
            f"Mock1/{run_mode}/{start_timestamp_as_str}.{end_timestamp_as_str}/prod/system_log_dir.{mode}",
        )
        sim_dir = os.path.join(
            dst_root_dir,
            f"Mock1/{run_mode}/{start_timestamp_as_str}.{end_timestamp_as_str}/simulation/system_log_dir.{mode}",
        )
        hio.create_dir(prod_dir, incremental=True)
        hio.create_dir(sim_dir, incremental=True)
        #
        config_dict = {
            "dag_runner_config": {
                "wake_up_timestamp": "2023-11-13 08:09:00-05:00",
                "rt_timeout_in_secs_or_time": 86400,
                "bar_duration_in_secs": 300,
            },
        }
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(prod_dir, tag)

    def test1(self) -> None:
        """
        Check that reconciliation config is being built correctly.
        """
        # Define params.
        dst_root_dir = self.get_scratch_space()
        dag_builder_ctor_as_str = (
            "dataflow_amp.pipelines.mock1.mock1_pipeline.Mock1_DagBuilder"
        )
        start_timestamp_as_str = "20230802_154500"
        end_timestamp_as_str = "20230802_160000"
        run_mode = "prod"
        mode = "scheduled"
        tag = ""
        # Create required dirs and config files in scratch space.
        self.set_up_test(
            dst_root_dir,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
        )
        # Run.
        config = rsiprrec.build_reconciliation_configs(
            dst_root_dir,
            dag_builder_ctor_as_str,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
            tag=tag,
        )
        actual = str(config)
        self.check_string(actual, purify_text=True)

    def test2(self) -> None:
        """
        Check that reconciliation config is being built correctly.

        `set_config_values` is passed to override default values.
        """
        # Define params.
        dst_root_dir = self.get_scratch_space()
        dag_builder_ctor_as_str = (
            "dataflow_amp.pipelines.mock1.mock1_pipeline.Mock1_DagBuilder"
        )
        start_timestamp_as_str = "20230802_154500"
        end_timestamp_as_str = "20230802_160000"
        run_mode = "prod"
        mode = "scheduled"
        tag = ""
        set_config_values = '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(1.0), "prediction_abs_threshold": float(0.3)})'
        # Create required dirs and config files in scratch space.
        self.set_up_test(
            dst_root_dir,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
        )
        # Run.
        config = rsiprrec.build_reconciliation_configs(
            dst_root_dir,
            dag_builder_ctor_as_str,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
            tag=tag,
            set_config_values=set_config_values,
        )
        actual = str(config)
        self.check_string(actual, purify_text=True)

    def test3(self) -> None:
        """
        Check that reconciliation config is being built correctly with backend
        as `batch_optimizer`.

        `set_config_values` is passed to override default values.
        """
        dst_root_dir = self.get_scratch_space()
        dag_builder_ctor_as_str = (
            "dataflow_amp.pipelines.mock1.mock1_pipeline.Mock1_DagBuilder"
        )
        start_timestamp_as_str = "20230802_154500"
        end_timestamp_as_str = "20230802_160000"
        run_mode = "prod"
        mode = "scheduled"
        tag = ""
        set_config_values = """("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","backend"),(str("batch_optimizer"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params"),({"dollar_neutrality_penalty": float(0.0), "constant_correlation": float(0.85), "constant_correlation_penalty": float(1.0), "relative_holding_penalty": float(0.0), "relative_holding_max_frac_of_gmv": float(0.6), "target_gmv": float(1500.0), "target_gmv_upper_bound_penalty": float(0.0), "target_gmv_hard_upper_bound_multiple": float(1.0), "transaction_cost_penalty": float(0.1), "solver": str("ECOS")})"""
        # Create required dirs and config files in scratch space.
        self.set_up_test(
            dst_root_dir,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
        )
        # Run.
        config = rsiprrec.build_reconciliation_configs(
            dst_root_dir,
            dag_builder_ctor_as_str,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
            tag=tag,
            set_config_values=set_config_values,
        )
        actual = str(config)
        self.check_string(actual, purify_text=True)

    def test4(self) -> None:
        """
        Check that reconciliation config is being built correctly when no
        optimizer overrides are present.

        `set_config_values` is passed to override default values.
        """
        # Define params.
        dst_root_dir = self.get_scratch_space()
        dag_builder_ctor_as_str = (
            "dataflow_amp.pipelines.mock1.mock1_pipeline.Mock1_DagBuilder"
        )
        start_timestamp_as_str = "20230802_154500"
        end_timestamp_as_str = "20230802_160000"
        run_mode = "prod"
        mode = "scheduled"
        tag = ""
        # Config overrides don't have any optimizer overrides.
        set_config_values = '("market_data_config","days"),(pd.Timedelta(str("150T")));("trading_period"),(str("3T"))'
        # Create required dirs and config files in scratch space.
        self.set_up_test(
            dst_root_dir,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
        )
        # Run.
        config = rsiprrec.build_reconciliation_configs(
            dst_root_dir,
            dag_builder_ctor_as_str,
            start_timestamp_as_str,
            end_timestamp_as_str,
            run_mode,
            mode,
            tag=tag,
            set_config_values=set_config_values,
        )
        actual = str(config)
        self.check_string(actual, purify_text=True)


class Test_Extract_Bar_Duration_from_pkl_Config(hunitest.TestCase):
    @staticmethod
    def helper(config_dict, dst_dir):
        """
        Save text and pickled config file in `dst_dir`.
        """
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(dst_dir, tag)

    def test1(self) -> None:
        """
        Test the function when the `bar_duration_in_secs` appears at the
        beginning of the `DagRunner` config.
        """
        config_dict = {
            "dag_runner_config": {
                "bar_duration_in_secs": 300,
                "fit_at_beginning": False,
                "rt_timeout_in_secs_or_time": 3600,
            }
        }
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        self.helper(config_dict, dst_dir)
        actual = rsiprrec.extract_bar_duration_from_pkl_config(dst_dir)
        expected = "5T"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        """
        Test the function when the `bar_duration_in_secs` appears at the end of
        the `DagRunner` config.
        """
        config_dict = {
            "dag_runner_config": {
                "wake_up_timestamp": "2023-11-13 08:09:00-05:00",
                "rt_timeout_in_secs_or_time": 86400,
                "bar_duration_in_secs": 300,
            }
        }
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        self.helper(config_dict, dst_dir)
        actual = rsiprrec.extract_bar_duration_from_pkl_config(dst_dir)
        expected = "5T"
        self.assert_equal(actual, expected)

    def test3(self) -> None:
        """
        Test that the function raises exception when the `bar_duration_in_secs`
        is not present in `DagRunner` config.
        """
        config_dict = {
            "dag_runner_config": {
                "wake_up_timestamp": "2023-11-13 08:09:00-05:00",
                "rt_timeout_in_secs_or_time": 86400,
            }
        }
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        self.helper(config_dict, dst_dir)
        with self.assertRaises(ValueError) as v:
            rsiprrec.extract_bar_duration_from_pkl_config(dst_dir)
        # Check output.
        actual = str(v.exception)
        expected = "Cannot parse `bar_duration_in_secs` from the config"
        self.assert_equal(actual, expected)


# #############################################################################
# Check `extract_price_column_name_from_pkl_config()`.
# #############################################################################


class Test_extract_price_column_name_from_pkl_config(hunitest.TestCase):
    """
    Check that `extract_price_column_name_from_pkl_config()` works correctly.
    """

    def save_config_to_file(self, config_dict: Dict[str, Any]) -> None:
        """
        Save text and pickled config file in `dst_dir`.
        """
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(dst_dir, tag)

    def test1(self) -> None:
        """
        Test the function when the `mark_to_market_col` appears at the
        beginning of the `portfolio_config` config.
        """
        config_dict = {
            "portfolio_config": {
                "mark_to_market_col": "close",
            }
        }
        self.save_config_to_file(config_dict)
        dst_dir = self.get_scratch_space()
        actual = rsiprrec.extract_price_column_name_from_pkl_config(dst_dir)
        expected = "close"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        """
        Test that the function raises exception when the `mark_to_market_col`
        is not present in `portfolio_config` config.
        """
        config_dict = {"portfolio_config": {}}
        self.save_config_to_file(config_dict)
        dst_dir = self.get_scratch_space()
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.extract_price_column_name_from_pkl_config(dst_dir)
        # Check output.
        actual = str(cm.exception)
        self.check_string(actual, purify_text=True)


# #############################################################################
# Check `extract_universe_version_from_pkl_config()`.
# #############################################################################


class Test_extract_universe_version_from_pkl_config(hunitest.TestCase):
    """
    Check that `extract_universe_version_from_pkl_config()` works correctly.
    """

    def save_config_to_file(self, config_dict: Dict[str, Any]) -> None:
        """
        Save text and pickled config file in `dst_dir`.
        """
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(dst_dir, tag)

    def check_universe_version(self, expected: str) -> None:
        """
        Check that the universe version returned from function is same as
        expected.

        :param dst_dir: dir with config files
        :param expected: expected output
        """
        # Dir to get config files.
        dst_dir = self.get_scratch_space()
        actual = rsiprrec.extract_universe_version_from_pkl_config(dst_dir)
        self.assert_equal(actual, expected)

    def test1(self) -> None:
        """
        Test the function when the `universe_version` appears at the beginning
        of the `market_data_config` config.
        """
        config_dict = {
            "market_data_config": {
                "universe_version": "v7.4",
                "asset_ids": [3303714233, 1467591036],
                "asset_id_col_name": "asset_id",
            }
        }
        self.save_config_to_file(config_dict)
        expected = "v7.4"
        self.check_universe_version(expected)

    def test2(self) -> None:
        """
        Test the function when the `universe_version` appears at the end of the
        `market_data_config` config.
        """
        config_dict = {
            "market_data_config": {
                "asset_ids": [3303714233, 1467591036],
                "asset_id_col_name": "asset_id",
                "universe_version": "v7.4",
            }
        }
        self.save_config_to_file(config_dict)
        expected = "v7.4"
        self.check_universe_version(expected)

    def test3(self) -> None:
        """
        Test that the function raises exception when the `universe_version` is
        not present in `market_data_config` config.
        """
        config_dict = {
            "market_data_config": {
                "asset_ids": [3303714233, 1467591036],
                "asset_id_col_name": "asset_id",
            }
        }
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        self.save_config_to_file(config_dict)
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.extract_universe_version_from_pkl_config(dst_dir)
        # Check output.
        actual = str(cm.exception)
        self.check_string(actual, purify_text=True)


# #############################################################################
# Check `extract_table_name_from_pkl_config()`.
# #############################################################################


class Test_extract_table_name_from_pkl_config(hunitest.TestCase):
    """
    Check that `extract_table_name_from_pkl_config()` works correctly.
    """

    def save_config_to_file(self, config_dict: Dict[str, Any]) -> None:
        """
        Save text and pickled config file for the test.
        """
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        # Build Config.
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(dst_dir, tag)

    def test1(self) -> None:
        """
        Test the function when the `table_name` is present in
        `market_data_config` config.
        """
        config_dict = {
            "market_data_config": {
                "universe_version": "v7.4",
                "asset_ids": [3303714233, 1467591036],
                "asset_id_col_name": "asset_id",
                "im_client_config": {
                    "table_name": "ccxt_ohlcv_futures",
                },
            }
        }
        self.save_config_to_file(config_dict)
        dst_dir = self.get_scratch_space()
        actual = rsiprrec.extract_table_name_from_pkl_config(dst_dir)
        expected = "ccxt_ohlcv_futures"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        """
        Test that the function raises exception when the `table_name` is not
        present in `market_data_config` config.
        """
        config_dict = {
            "market_data_config": {
                "universe_version": "v7.4",
                "asset_ids": [3303714233, 1467591036],
                "asset_id_col_name": "asset_id",
            }
        }
        self.save_config_to_file(config_dict)
        dst_dir = self.get_scratch_space()
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.extract_table_name_from_pkl_config(dst_dir)
        # Check output.
        actual = str(cm.exception)
        self.check_string(actual, purify_text=True)


# #############################################################################
# Check `extract_execution_freq_from_pkl_config()`.
# #############################################################################


class Test_extract_execution_freq_from_pkl_config(hunitest.TestCase):
    """
    Check that `extract_execution_freq_from_pkl_config()` works correctly.
    """

    def test1(self) -> None:
        """
        Test the function when the `execution_frequency` appears at the
        beginning of the `process_forecasts_node_dict` config.
        """
        config_dict = {
            "process_forecasts_node_dict": {
                "execution_frequency": "1T",
                "prediction_col": "feature",
                "volatility_col": "garman_klass_vol",
            }
        }
        self._save_config_to_file(config_dict)
        expected = "1T"
        self._check_execution_freq(expected)

    def test2(self) -> None:
        """
        Test the function when the `execution_frequency` appears at the end of
        the `process_forecasts_node_dict` config.
        """
        config_dict = {
            "process_forecasts_node_dict": {
                "prediction_col": "feature",
                "volatility_col": "garman_klass_vol",
                "execution_frequency": "1T",
            }
        }
        self._save_config_to_file(config_dict)
        expected = "1T"
        self._check_execution_freq(expected)

    def test3(self) -> None:
        """
        Test that the function raises exception when the `execution_frequency`
        is not present in `process_forecasts_node_dict` config.
        """
        config_dict = {
            "process_forecasts_node_dict": {
                "prediction_col": "feature",
                "volatility_col": "garman_klass_vol",
            }
        }
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        self._save_config_to_file(config_dict)
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.extract_execution_freq_from_pkl_config(dst_dir)
        # Check output.
        actual = str(cm.exception)
        self.check_string(actual, purify_text=True)

    def _save_config_to_file(self, config_dict: Dict[str, Any]) -> None:
        """
        Save text and pickled config file in `dst_dir`.
        """
        # Dir to store config files.
        dst_dir = self.get_scratch_space()
        config = cconfig.Config.from_dict(config_dict)
        tag = "system_config.output"
        # Save config to `txt` and `pkl` file.
        config.save_to_file(dst_dir, tag)

    def _check_execution_freq(self, expected: str) -> None:
        """
        Check that the universe version returned from function is same as
        expected.

        :param dst_dir: dir with config files
        :param expected: expected output
        """
        # Dir to get config files.
        dst_dir = self.get_scratch_space()
        actual = rsiprrec.extract_execution_freq_from_pkl_config(dst_dir)
        self.assert_equal(actual, expected)


class Test_get_dag_output_path(hunitest.TestCase):
    """
    Check that `get_dag_output_path()` returns a correct path.
    """

    def create_dag_output_dirs(self) -> Dict[str, str]:
        """
        Create dirs required for returning the dag data path.
        """
        # Define params.
        dst_root_dir = self.get_scratch_space()
        mode = "scheduled"
        # Get system log dir based on mode.
        system_log_dir = rsiprrec.get_prod_system_log_dir(mode)
        prod_dir = os.path.join(dst_root_dir, "Mock1/prod", system_log_dir)
        sim_dir = os.path.join(dst_root_dir, "Mock1/simulation", system_log_dir)
        dag_path_dict = {}
        dag_path_dict["prod"] = rsiprrec.get_data_type_system_log_path(
            prod_dir, "dag_data"
        )
        dag_path_dict["sim"] = rsiprrec.get_data_type_system_log_path(
            sim_dir, "dag_data"
        )
        for dir in dag_path_dict.values():
            # Create dag dirs.
            hio.create_dir(dir, incremental=True)
            # Make the dirs non-empty.
            file_name = "data.txt"
            file_path = os.path.join(dir, file_name)
            data = "hello"
            hio.to_file(file_path, data)
        return dag_path_dict

    def test1(self) -> None:
        """
        Test when mode is `automatic` and both the dir exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        mode = "automatic"
        # Get absolute path of `amp` dir.
        # Used when tests are ran from orange.
        amp_path = hgit.get_amp_abs_path()
        # Check output.
        actual = rsiprrec.get_dag_output_path(dag_path_dict, mode)
        expected = os.path.join(
            amp_path,
            "reconciliation/test/outcomes/Test_get_dag_output_path.test1/tmp.scratch/Mock1/prod/system_log_dir.scheduled/dag/node_io/node_io.data",
        )
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        """
        Test when mode is `automatic` and prod dir doesn't exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        # Make prod dir non-existant.
        dag_path_dict["prod"] = "prod/dir"
        mode = "automatic"
        # Get absolute path of `amp` dir.
        # Used when tests are ran from orange.
        amp_path = hgit.get_amp_abs_path()
        # Check output.
        actual = rsiprrec.get_dag_output_path(dag_path_dict, mode)
        expected = os.path.join(
            amp_path,
            "reconciliation/test/outcomes/Test_get_dag_output_path.test2/tmp.scratch/Mock1/simulation/system_log_dir.scheduled/dag/node_io/node_io.data",
        )
        self.assert_equal(actual, expected)

    def test3(self) -> None:
        """
        Test when mode is `prod` and prod dir exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        mode = "prod"
        # Get absolute path of `amp` dir.
        # Used when tests are ran from orange.
        amp_path = hgit.get_amp_abs_path()
        # Check output.
        actual = rsiprrec.get_dag_output_path(dag_path_dict, mode)
        expected = os.path.join(
            amp_path,
            "reconciliation/test/outcomes/Test_get_dag_output_path.test3/tmp.scratch/Mock1/prod/system_log_dir.scheduled/dag/node_io/node_io.data",
        )
        self.assert_equal(actual, expected)

    def test4(self) -> None:
        """
        Test when mode is `prod` and prod dir doesn't exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        # Make prod dir non-existant.
        dag_path_dict["prod"] = "prod/dir"
        mode = "prod"
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.get_dag_output_path(dag_path_dict, mode)
        # Check output.
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        Dir '/app/prod/dir' doesn't exist
        mode=prod and dir prod/dir doesn't exist.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test5(self) -> None:
        """
        Test when mode is `sim` and sim dir exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        mode = "sim"
        # Get absolute path of `amp` dir.
        # Used when tests are ran from orange.
        amp_path = hgit.get_amp_abs_path()
        # Check output.
        actual = rsiprrec.get_dag_output_path(dag_path_dict, mode)
        expected = os.path.join(
            amp_path,
            "reconciliation/test/outcomes/Test_get_dag_output_path.test5/tmp.scratch/Mock1/simulation/system_log_dir.scheduled/dag/node_io/node_io.data",
        )
        self.assert_equal(actual, expected)

    def test6(self) -> None:
        """
        Test when mode is `sim` and sim dir doesn't exists.
        """
        # Get prod and sim dag dirs.
        dag_path_dict = self.create_dag_output_dirs()
        # Make sim dir non-existant.
        dag_path_dict["sim"] = "sim/dir"
        mode = "sim"
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.get_dag_output_path(dag_path_dict, mode)
        # Check output.
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        Dir '/app/sim/dir' doesn't exist
        mode=sim and dir sim/dir doesn't exist.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test7(self) -> None:
        """
        Test if both dir doesn't exists.
        """
        # Create non-existant prod and sim dirs.
        dag_path_dict = {"prod": "dummy/dir", "sim": "dummy/dir_2"}
        mode = "automatic"
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.get_dag_output_path(dag_path_dict, mode)
        # Check output.
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        cond=False
        Both prod dir=dummy/dir and sim dir=dummy/dir_2 doesn't exists.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test8(self) -> None:
        """
        Test if the mode is unknown.
        """
        # Keep prod and sim dag dirs empty as not needed in the test.
        dag_path_dict = {}
        mode = "unknown"
        with self.assertRaises(AssertionError) as cm:
            rsiprrec.get_dag_output_path(dag_path_dict, mode)
        # Check output.
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        'unknown' in '['automatic', 'prod', 'sim']'
        Invalid mode=unknown. The mode should be 'automatic', 'prod', 'sim'.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_get_system_log_paths(hunitest.TestCase):
    """
    Check that `get_system_log_paths()` works correctly.
    """

    def create_target_output_dirs(self, create_all_dirs: bool) -> Dict[str, str]:
        """
        Create dirs required for returning the system log path.

        :param create_all_dirs: toggle to create complete or incomplete
            test paths.
        """
        # Create path where at least one of the path does exist.
        scratch_dir = self.get_scratch_space()
        prod_dir = rsiprrec.get_prod_dir(scratch_dir)
        data_type = "dag_data"
        prod_system_log_path = rsiprrec.get_data_type_system_log_path(
            prod_dir, data_type
        )
        hio.create_dir(prod_system_log_path, incremental=True)
        simulation_dir = rsiprrec.get_simulation_dir(scratch_dir)
        simulation_system_log_path = rsiprrec.get_data_type_system_log_path(
            simulation_dir, data_type
        )
        if create_all_dirs:
            # Create a dir to run a test when all DAG outputs dirs exist;
            # because we might not have one of DAG output dirs in some experiments.
            hio.create_dir(simulation_system_log_path, incremental=True)
        return {"prod": prod_dir, "sim": simulation_dir}

    def check_output(
        self, expected: str, only_warning: bool, create_all_dirs: bool
    ) -> None:
        """
        Validate the log paths returned by the function with the given set of
        parameters.

        :param expected: the expected output with the given parameters
        :param only_warning: issue a warning instead of aborting when
            one of system log dir paths don't exist
        :param create_all_dirs: toggle to create complete or incomplete
            test paths.
        """
        target_dir = self.create_target_output_dirs(create_all_dirs)
        data_type = "dag_data"
        # Check. Function should return log paths.
        actual = str(
            rsiprrec.get_system_log_paths(
                target_dir, data_type, only_warning=only_warning
            )
        )
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test when `only_warning = True` and all dirs exist.
        """
        # Initialize parameters as per the test requirements.
        only_warning = True
        create_all_dirs = True
        expected = r"""
        {'prod': '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test1/tmp.scratch/prod/dag/node_io/node_io.data', 'sim': '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test1/tmp.scratch/simulation/dag/node_io/node_io.data'}
        """
        self.check_output(expected, only_warning, create_all_dirs)

    def test2(self) -> None:
        """
        Test when `only_warning = True` and one of the dirs is missing.
        """
        # Initialize parameters as per the test requirements.
        only_warning = True
        create_all_dirs = False
        expected = r"""
        {'prod': '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test2/tmp.scratch/prod/dag/node_io/node_io.data', 'sim': ''}
        """
        self.check_output(expected, only_warning, create_all_dirs)

    def test3(self) -> None:
        """
        Test when `only_warning = False` and all dirs exist.
        """
        # Initialize parameters as per the test requirements.
        only_warning = False
        create_all_dirs = True
        expected = r"""
        {'prod': '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test3/tmp.scratch/prod/dag/node_io/node_io.data', 'sim': '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test3/tmp.scratch/simulation/dag/node_io/node_io.data'}
        """
        self.check_output(expected, only_warning, create_all_dirs)

    def test4(self) -> None:
        """
        Test when `only_warning = False` and one of the dirs is missing.
        """
        # Initialize parameters as per the test requirements.
        only_warning = False
        create_all_dirs = False
        target_dir = self.create_target_output_dirs(create_all_dirs)
        data_type = "dag_data"
        # Check. Function should raise Assertion Error.
        with self.assertRaises(AssertionError) as e:
            _ = rsiprrec.get_system_log_paths(
                target_dir, data_type, only_warning=only_warning
            )
        actual = str(e.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        Dir '$GIT_ROOT/reconciliation/test/outcomes/Test_get_system_log_paths.test4/tmp.scratch/simulation/dag/node_io/node_io.data' doesn't exist
        ################################################################################
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)


class Test_reconcile_create_dirs(hunitest.TestCase):
    """
    Check that `reconcile_create_dirs()` works correctly.
    """

    def check_reconcile_create_dirs(
        self,
        backup_dir_if_exists: bool,
        create_dir: bool,
        expected: str,
    ) -> None:
        """
        Verify output.

        :param backup_dir_if_exists: see `hio.create_dir()`
        :param create_dir: toggle to create dir
        :param expected: the expected output for the test
        """
        # Create path for the test output.
        dst_root_dir = self.get_scratch_space()
        # Initialize mock variables.
        dag_builder_ctor_as_str = (
            "dataflow_orange.pipelines.Mock1.Mock1_pipeline.Mock1_DagBuilder"
        )
        dag_builder_name = dtfcor.get_DagBuilder_name_from_string(
            dag_builder_ctor_as_str
        )
        run_mode = "paper_trading"
        start_timestamp_as_str = "20230828_130500"
        end_timestamp_as_str = "20230829_131000"
        tag = ""
        abort_if_exists = False
        # Create the existing dir for the test.
        if create_dir:
            existing_dir = rsiprrec.get_target_dir(
                dst_root_dir,
                dag_builder_name,
                run_mode,
                start_timestamp_as_str,
                end_timestamp_as_str,
                tag=tag,
            )
            existing_dir = os.path.join(existing_dir, "mock_dir")
            hio.create_dir(existing_dir, incremental=False)
        # Invoke the function.
        rsiprrec.reconcile_create_dirs(
            dag_builder_ctor_as_str,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            dst_root_dir,
            abort_if_exists,
            backup_dir_if_exists,
            tag=tag,
        )
        # Check.
        actual_dirs = sorted(
            hio.listdir(
                dst_root_dir,
                pattern="*",
                only_files=False,
                use_relative_paths=True,
            )
        )
        actual = str(actual_dirs)
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(os.path, "getmtime")
    def test1(
        self,
        mock_getmtime: umock.MagicMock,
    ) -> None:
        """
        Test when `backup_dir_if_exists = True` and dir that should be created
        already exists.
        """
        backup_dir_if_exists = True
        create_existing_dir = True
        expected = r"""
        ['.', 'Mock1', 'Mock1/paper_trading', 'Mock1/paper_trading/20230828_130500.20230829_131000', 'Mock1/paper_trading/20230828_130500.20230829_131000.20240201_182954', 'Mock1/paper_trading/20230828_130500.20230829_131000.20240201_182954/mock_dir', 'Mock1/paper_trading/20230828_130500.20230829_131000/prod', 'Mock1/paper_trading/20230828_130500.20230829_131000/reconciliation_notebook', 'Mock1/paper_trading/20230828_130500.20230829_131000/simulation']
        """
        # Mock the timestamp so that the test is not dependent on real time. The
        # function uses current timestamp in the backed up dir name.
        mock_getmtime.return_value = 1706812194.4668508
        self.check_reconcile_create_dirs(
            backup_dir_if_exists, create_existing_dir, expected
        )

    def test2(self) -> None:
        """
        Test when `backup_dir_if_exists = True` and dir that should be created
        does not exist.
        """
        backup_dir_if_exists = True
        create_existing_dir = False
        expected = r"""
        ['.', 'Mock1', 'Mock1/paper_trading', 'Mock1/paper_trading/20230828_130500.20230829_131000', 'Mock1/paper_trading/20230828_130500.20230829_131000/prod', 'Mock1/paper_trading/20230828_130500.20230829_131000/reconciliation_notebook', 'Mock1/paper_trading/20230828_130500.20230829_131000/simulation']
        """
        self.check_reconcile_create_dirs(
            backup_dir_if_exists, create_existing_dir, expected
        )

    def test3(self) -> None:
        """
        Test when `backup_dir_if_exists = False` and dir that should be created
        does not exist.
        """
        backup_dir_if_exists = False
        create_existing_dir = False
        expected = r"""
        ['.', 'Mock1', 'Mock1/paper_trading', 'Mock1/paper_trading/20230828_130500.20230829_131000', 'Mock1/paper_trading/20230828_130500.20230829_131000/prod', 'Mock1/paper_trading/20230828_130500.20230829_131000/reconciliation_notebook', 'Mock1/paper_trading/20230828_130500.20230829_131000/simulation']
        """
        self.check_reconcile_create_dirs(
            backup_dir_if_exists, create_existing_dir, expected
        )

    def test4(self) -> None:
        """
        Test when `backup_dir_if_exists = False` and dir that should be created
        already exists.
        """
        backup_dir_if_exists = False
        create_existing_dir = True
        expected = r"""
        ['.', 'Mock1', 'Mock1/paper_trading', 'Mock1/paper_trading/20230828_130500.20230829_131000', 'Mock1/paper_trading/20230828_130500.20230829_131000/mock_dir', 'Mock1/paper_trading/20230828_130500.20230829_131000/prod', 'Mock1/paper_trading/20230828_130500.20230829_131000/reconciliation_notebook', 'Mock1/paper_trading/20230828_130500.20230829_131000/simulation']
        """
        self.check_reconcile_create_dirs(
            backup_dir_if_exists, create_existing_dir, expected
        )


class Test_get_universe_version_from_config_overrides(hunitest.TestCase):
    """
    Check that `get_universe_version_from_config_overrides()` works correctly.
    """

    def test1(self) -> None:
        """
        Check that the universe version is returned from config override
        string.
        """
        set_config_values = '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal"));("market_data_config", "universe_version"),(str("v7.3"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(1.0)})'
        actual = rsiprrec.get_universe_version_from_config_overrides(
            set_config_values
        )
        expected = "v7.3"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        """
        Check that None is returned if universe version is not defined in
        config override string.
        """
        set_config_values = '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(1.0)})'
        actual = rsiprrec.get_universe_version_from_config_overrides(
            set_config_values
        )
        actual = str(actual)
        expected = "None"
        self.assert_equal(actual, expected)
