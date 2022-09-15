"""
Import as:

import dataflow_amp.system.mock1.mock1_forecast_system_example as dtfasmmfsex
"""
import datetime
from typing import Optional, Union

import pandas as pd

import core.config as cconfig
import dataflow.system as dtfsys
import dataflow_amp.system.mock1.mock1_forecast_system as dtfasmmfosy
import im_v2.common.data.client as icdc

# #############################################################################
# Mock1_NonTime_ForecastSystem_example
# #############################################################################


def get_Mock1_NonTime_ForecastSystem_for_simulation_example1(
    backtest_config: str,
) -> dtfsys.NonTime_ForecastSystem:
    """
    Get Mock1_NonTime_ForecastSystem object for backtest simulation.
    """
    system = dtfasmmfosy.Mock1_NonTime_ForecastSystem()
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # Fill pipeline-specific backtest config parameters.
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "10D"
    # Fill `MarketData` related config.
    system.config[
        "market_data_config", "im_client_ctor"
    ] = icdc.get_DataFrameImClient_example1
    system.config["market_data_config", "im_client_config"] = cconfig.Config()
    # Set the research PNL parameters.
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": "vwap",
            "volatility_col": "vwap.ret_0.vol",
            "prediction_col": "prediction",
        },
        "kwargs": {
            "target_gmv": 1e5,
            "liquidate_at_end_of_day": False,
        },
    }
    system.config[
        "research_forecast_evaluator_from_prices"
    ] = cconfig.Config.from_dict(forecast_evaluator_from_prices_dict)
    system = dtfsys.apply_market_data_config(system)
    return system


# #############################################################################
# Mock1_Time_ForecastSystem_with_DataFramePortfolio_example
# #############################################################################


def get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
    market_data_df: pd.DataFrame,
    rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]],
) -> dtfsys.System:
    """
    The System is used for the corresponding unit tests.
    """
    system = dtfasmmfosy.Mock1_Time_ForecastSystem_with_DataFramePortfolio()
    # Market data config.
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    system.config["market_data_config", "delay_in_secs"] = 5
    system.config["market_data_config", "replayed_delay_in_mins_or_timestamp"] = 5
    system.config["market_data_config", "asset_ids"] = [101]
    system.config["market_data_config", "data"] = market_data_df
    # Portfolio config.
    system = dtfsys.apply_Portfolio_config(system)
    # Dag runner config.
    system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    # PnL config.
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": "vwap",
            "volatility_col": "vwap.ret_0.vol",
            "prediction_col": "feature1",
        },
        "kwargs": {
            "target_gmv": 1e5,
            "liquidate_at_end_of_day": False,
        },
    }
    system.config[
        "research_forecast_evaluator_from_prices"
    ] = cconfig.Config.from_dict(forecast_evaluator_from_prices_dict)
    return system


# #############################################################################
# Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
# #############################################################################


def get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
    market_data_df: pd.DataFrame,
    rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]],
) -> dtfsys.System:
    """
    The System is used for the corresponding unit tests.
    """
    system = (
        dtfasmmfosy.Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor()
    )
    # Market data config.
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    system.config["market_data_config", "delay_in_secs"] = 5
    system.config["market_data_config", "replayed_delay_in_mins_or_timestamp"] = 5
    system.config["market_data_config", "asset_ids"] = [101]
    system.config["market_data_config", "data"] = market_data_df
    # Portfolio config.
    system = dtfsys.apply_Portfolio_config(system)
    # Dag runner config.
    system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    # PnL config.
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": "vwap",
            "volatility_col": "vwap.ret_0.vol",
            "prediction_col": "feature1",
        },
        "kwargs": {
            "target_gmv": 1e5,
            "liquidate_at_end_of_day": False,
        },
    }
    system.config[
        "research_forecast_evaluator_from_prices"
    ] = cconfig.Config.from_dict(forecast_evaluator_from_prices_dict)
    # If an order is not placed within a bar, then there is a timeout, so
    # we add extra 5 seconds to `bar_duration_in_secs` (which represents
    # the length of a trading bar) to make sure that the `OrderProcessor`
    # waits long enough before timing out.
    max_wait_time_for_order_in_secs = (
        system.config["dag_runner_config", "bar_duration_in_secs"] + 5
    )
    system.config[
        "order_processor_config", "max_wait_time_for_order_in_secs"
    ] = max_wait_time_for_order_in_secs
    # We add extra 5 seconds for the `OrderProcessor` to account for the first bar
    # that the DAG spends in fit mode.
    rt_timeout_in_secs_or_time = (
        system.config["dag_runner_config", "rt_timeout_in_secs_or_time"] + 5
    )
    system.config[
        "order_processor_config", "duration_in_secs"
    ] = rt_timeout_in_secs_or_time
    return system
