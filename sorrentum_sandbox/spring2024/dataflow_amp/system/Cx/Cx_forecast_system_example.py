"""
Import as:

import dataflow_amp.system.Cx.Cx_forecast_system_example as dtfasccfsex
"""

import datetime
from typing import Any, Dict, Optional, Union

import pandas as pd

import core.config as cconfig
import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import dataflow_amp.system.Cx.Cx_forecast_system as dtfasccfosy
import helpers.hdbg as hdbg

# #############################################################################
# Cx_NonTime_ForecastSystem_example
# #############################################################################


def get_Cx_NonTime_ForecastSystem_example(
    dag_builder_ctor_as_str: str,
    *dag_builder_args,
    train_test_mode: str,
    backtest_config: str,
    im_client_config: Dict[str, Any],
    # TODO(Grisha): P1, should become `**train_test_kwargs`.
    oos_start_date_as_str: Optional[str] = None,
    **dag_builder_kwargs,
) -> dtfsys.ForecastSystem:
    """
    Get `Cx_ForecastSystem` object for backtest simulation.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
    :param train_test_mode: same as in `Cx_NonTime_ForecastSystem`
    :param backtest_config: see `apply_backtest_config()`
    :param im_client_config: `ImClient` config
    :param oos_start_date_as_str: used only for train_test_mode="ins_oos",
        see `apply_ins_oos_backtest_config()`
    :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
    """
    # 1) Build a `System` object.
    system = dtfasccfosy.Cx_NonTime_ForecastSystem(
        dag_builder_ctor_as_str,
        *dag_builder_args,
        train_test_mode=train_test_mode,
        **dag_builder_kwargs,
    )
    # 2) Apply backtest config.
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # 3) Apply tile config.
    if train_test_mode in ["ins", "rolling"]:
        # TODO(Grisha): think how to apply the tile config when running
        # in the OOS mode.
        # Fill params that are specific of the tiled backtest.
        system = dtfsys.apply_backtest_tile_config(system)
    # 4) Apply train-test mode specific config.
    if train_test_mode == "rolling":
        # Fill rolling-specific backtest config parameters.
        system = dtfsys.apply_rolling_backtest_config(system)
    elif train_test_mode == "ins_oos":
        # Fill oos-specific backtest config parameters.
        system = dtfsys.apply_ins_oos_backtest_config(
            system, oos_start_date_as_str
        )
    # 5) Apply `ImClient` config.
    hdbg.dassert_in("universe_version", im_client_config)
    # Check that `ImClient` config universe version matches the one from backtest config.
    universe_str = system.config.get_and_mark_as_used(
        ("backtest_config", "universe_str")
    )
    # TODO(Grisha): move the logic to `parse_universe_str()` so that it returns,
    # vendor name universe version and top_n.
    # While `parse_universe_str()` returns universe version with a vendor name
    # (e.g., `ccxt_v7`), `ImClient` requires only the numeric version (i.e.
    # without a vendor name).
    universe_version, _ = cconfig.parse_universe_str(universe_str)
    universe_version = universe_version.split("_", 1)[-1].replace("_", ".")
    hdbg.dassert_eq(universe_version, im_client_config["universe_version"])
    system = dtfsys.apply_ImClient_config(system, im_client_config)
    # 6) Apply `MarketData` config.
    system = dtfsys.apply_MarketData_config(system)
    return system


# #############################################################################
# Cx_Time_ForecastSystem_example
# #############################################################################


def get_Cx_Time_ForecastSystem_example(
    dag_builder_ctor_as_str: str,
    *dag_builder_args,
    # `ReplayedMarketData` params.
    file_path: str,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
    delay_in_secs: int,
    # `RealtimeDagRunner` params.
    rt_timeout_in_secs_or_time: Union[int, datetime.time],
    **dag_builder_kwargs,
) -> dtfsys.System:
    """
    Build `Cx_Time_ForecastSystem`.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
    :param file_path: a path where data is stored
    :param replayed_delay_in_mins_or_timestamp: when the replayed wall-clock
        time starts
    :param delay_in_secs: represent how long it takes for the simulated system
        to respond
    :param rt_timeout_in_secs_or_time: for how long to execute the loop
    :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
    """
    # 1) Build a `System` object.
    system = dtfasccfosy.Cx_Time_ForecastSystem(
        dag_builder_ctor_as_str, *dag_builder_args, **dag_builder_kwargs
    )
    # 2) Apply `ReplayedMarketData_from_file` config.
    system = dtfsys.apply_ReplayedMarketData_from_file_config(
        system, file_path, replayed_delay_in_mins_or_timestamp, delay_in_secs
    )
    # 3) Apply `RealtimeDagRunner` config.
    system = dtfsys.apply_RealtimeDagRunner_config(
        system, rt_timeout_in_secs_or_time
    )
    return system


# TODO(Grisha): remove the function once the prod system is ported
# to the new style.
def apply_Cx_system_configs(
    system: dtfsys.System,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
    rt_timeout_in_secs_or_time: Union[int, datetime.time],
) -> dtfsys.System:
    """
    Apply configs common for all `Cx_Time_ForecastSystem`s.
    """
    system = dtfasccxbu.apply_Cx_MarketData_config(
        system, replayed_delay_in_mins_or_timestamp
    )
    system = dtfasccxbu.apply_Cx_DagRunner_config(
        system, rt_timeout_in_secs_or_time
    )
    system = dtfsys.apply_Portfolio_config(system)
    system = dtfsys.apply_ForecastEvaluatorFromPrices_config(system)
    return system


# #############################################################################
# Cx_Time_ForecastSystem_with_DataFramePortfolio_example
# #############################################################################


def get_Cx_Time_ForecastSystem_with_DataFramePortfolio_example1(
    dag_builder_ctor_as_str: str,
    *dag_builder_args,
    # `ReplayedMarketData` params.
    file_path: str,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
    delay_in_secs: int,
    # `RealtimeDagRunner` params.
    rt_timeout_in_secs_or_time: Union[int, datetime.time],
    **dag_builder_kwargs,
) -> dtfsys.System:
    """
    The system is used for the unit tests.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
    :param file_path: a path where data is stored
    :param replayed_delay_in_mins_or_timestamp: when the replayed wall-clock
        time starts
    :param delay_in_secs: represent how long it takes for the simulated system
        to respond
    :param rt_timeout_in_secs_or_time: for how long to execute the loop
    :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
    """
    # 1) Build a `System` object.
    system = dtfasccfosy.Cx_Time_ForecastSystem_with_DataFramePortfolio(
        dag_builder_ctor_as_str,
        *dag_builder_args,
        **dag_builder_kwargs,
    )
    system.config["trading_period"] = "5T"
    order_config = dtfasccxbu.get_Cx_order_config_instance1()
    #
    compute_target_positions_kwargs = {
        "bulk_frac_to_remove": 0.0,
        "bulk_fill_method": "zero",
        "target_gmv": 1e5,
    }
    optimizer_config = {
        "backend": "pomo",
        "asset_class": "crypto",
        "apply_cc_limits": False,
        "params": {
            "style": "cross_sectional",
            "kwargs": compute_target_positions_kwargs,
        },
    }
    #
    root_log_dir = None
    system = dtfasccxbu.apply_ProcessForecastsNode_config(
        system, order_config, optimizer_config, root_log_dir
    )
    # 2) Apply `ReplayedMarketData_from_file` config.
    system.config["market_data_config", "days"] = None
    system = dtfsys.apply_ReplayedMarketData_from_file_config(
        system, file_path, replayed_delay_in_mins_or_timestamp, delay_in_secs
    )
    # 3) Apply `RealtimeDagRunner` config.
    system = dtfsys.apply_RealtimeDagRunner_config(
        system, rt_timeout_in_secs_or_time
    )
    #
    system = dtfsys.apply_Portfolio_config(system)
    system = dtfsys.apply_ForecastEvaluatorFromPrices_config(system)
    return system


# #############################################################################
# Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example
# #############################################################################


def get_Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
    dag_builder_ctor_as_str: str,
    *dag_builder_args,
    # `RealtimeDagRunner` params.
    file_path: str,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
    delay_in_secs: int,
    # `RealtimeDagRunner` params.
    rt_timeout_in_secs_or_time: Union[int, datetime.time],
    **dag_builder_kwargs,
) -> dtfsys.System:
    """
    Build `Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor`
    and fill the `System.config`.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
    :param file_path: a path where data is stored
    :param replayed_delay_in_mins_or_timestamp: when the replayed wall-clock
        time starts
    :param delay_in_secs: represent how long it takes for the simulated system
        to respond
    :param rt_timeout_in_secs_or_time: for how long to execute the loop
    :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
    """
    # 1) Build a `System` object.
    system = dtfasccfosy.Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor(
        dag_builder_ctor_as_str,
        *dag_builder_args,
        **dag_builder_kwargs,
    )
    system.config["trading_period"] = "5T"
    order_config = dtfasccxbu.get_Cx_order_config_instance1()
    #
    compute_target_positions_kwargs = {
        "bulk_frac_to_remove": 0.0,
        "bulk_fill_method": "zero",
        "target_gmv": 1e5,
    }
    optimizer_config = {
        "backend": "pomo",
        "asset_class": "crypto",
        "apply_cc_limits": False,
        "params": {
            "style": "cross_sectional",
            "kwargs": compute_target_positions_kwargs,
        },
    }
    #
    root_log_dir = None
    system = dtfasccxbu.apply_ProcessForecastsNode_config(
        system, order_config, optimizer_config, root_log_dir
    )
    # 2) Apply `ReplayedMarketData_from_file` config.
    system.config["market_data_config", "days"] = None
    system = dtfsys.apply_ReplayedMarketData_from_file_config(
        system, file_path, replayed_delay_in_mins_or_timestamp, delay_in_secs
    )
    # 3) Apply `RealtimeDagRunner` config.
    system = dtfsys.apply_RealtimeDagRunner_config(
        system, rt_timeout_in_secs_or_time
    )
    #
    system = dtfsys.apply_Portfolio_config(system)
    system = dtfsys.apply_ForecastEvaluatorFromPrices_config(system)
    system = dtfsys.apply_OrderProcessor_config(system)
    return system
