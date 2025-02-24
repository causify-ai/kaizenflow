import logging
from typing import Any

import pandas as pd

import core.config as cconfig

# TODO(gp): Reuse cconfig
import core.config.config_list_builder as cccolibu
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _check_config_list(
    self_: Any, config_list: cconfig.ConfigList, expected_num_configs: int
) -> None:
    actual_output = str(config_list)
    self_.check_string(actual_output, fuzzy_match=True, purify_text=True)
    self_.assertEqual(len(config_list.configs), expected_num_configs)


# #############################################################################
# Test_build_config_list_varying_tiled_periods1
# #############################################################################


class Test_build_config_list_varying_tiled_periods1(hunitest.TestCase):
    """
    Cover period of times with different tiles.
    """

    def cover_with_monthly_tiles(
        self,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        expected_num_configs: int,
    ) -> None:
        # Prepare inputs.
        # Create a Config with `overwrite` mode to support item reassignment.
        update_mode = "overwrite"
        config = cconfig.Config(update_mode=update_mode)
        config_list = cconfig.ConfigList([config])
        freq_as_pd_str = "1M"
        lookback_as_pd_str = "10D"
        # Run.
        config_list = cccolibu.build_config_list_varying_tiled_periods(
            config_list,
            start_timestamp,
            end_timestamp,
            freq_as_pd_str,
            lookback_as_pd_str,
        )
        # Check.
        _check_config_list(self, config_list, expected_num_configs)

    # //////////////////////////////////////////////////////////////////////////////

    def test_1tile_1(self) -> None:
        """
        Cover [2020-01-01, 2020-01-31] with 1 monthly tile.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-01 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-01-31 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 1
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )

    def test_1tile_2(self) -> None:
        """
        Cover [2020-01-01, 2020-01-30] with 1 monthly tile.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-01 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-01-30 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 1
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )

    def test_1tile_3(self) -> None:
        """
        Cover [2020-01-02, 2020-01-30] with 1 monthly tile.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-02 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-01-30 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 1
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_2tiles_1(self) -> None:
        """
        Cover [2020-01-02, 2020-02-01] with 2 monthly tiles.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-02 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-02-01 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 2
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )

    def test_2tiles_2(self) -> None:
        """
        Cover [2020-01-07, 2020-02-29] with 2 monthly tiles.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-07 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-02-29 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 2
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_3tiles_1(self) -> None:
        """
        Cover [2020-01-07, 2020-03-15] with 3 monthly tiles.
        """
        # Inputs.
        start_timestamp = pd.Timestamp("2020-01-07 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2020-03-31 00:00:00+0000", tz="UTC")
        # Expected output.
        expected_num_configs = 3
        # Run.
        self.cover_with_monthly_tiles(
            start_timestamp, end_timestamp, expected_num_configs
        )


# #############################################################################
# Test_build_config_list_with_tiled_universe
# #############################################################################


class Test_build_config_list_with_tiled_universe(hunitest.TestCase):
    def test1(self) -> None:
        # Prepare inputs.
        config = cconfig.Config()
        config_list = cconfig.ConfigList([config])
        asset_ids = [13684, 10971]
        # Run.
        config_list = cccolibu.build_config_list_with_tiled_universe(
            config_list, asset_ids
        )
        # Check.
        expected_num_configs = 1
        _check_config_list(self, config_list, expected_num_configs)


# #############################################################################
# Test_build_config_list_with_tiled_universe_and_periods
# #############################################################################


# TODO(gp): @all Add a test using a SystemConfigList, instead of a ConfigList.
class Test_build_config_list_with_tiled_universe_and_periods(hunitest.TestCase):
    def test1(self) -> None:
        # Prepare inputs.
        # Create a Config with `overwrite` mode to support item reassignment.
        system_config = cconfig.Config(update_mode="overwrite")
        system_config[
            "backtest_config", "time_interval_str"
        ] = "2020-01-01_2020-03-01"
        system_config["backtest_config", "freq_as_pd_str"] = "M"
        system_config["backtest_config", "lookback_as_pd_str"] = "90D"
        system_config["market_data_config", "asset_ids"] = [13684, 10971]
        config_list = cconfig.ConfigList([system_config])
        # Run.
        config_list = cccolibu.build_config_list_with_tiled_universe_and_periods(
            config_list
        )
        # Check.
        expected_num_configs = 2
        _check_config_list(self, config_list, expected_num_configs)
