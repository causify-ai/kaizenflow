"""
Import as:

import dataflow_amp.system.mock1.mock1_forecast_system_example as dtfasmmfsex
"""
import datetime
from typing import Optional, Union

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.system as dtfsys
import dataflow_amp.system.mock1.mock1_forecast_system as dtfasmmfosy
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

# #############################################################################
# Mock1_NonTime_ForecastSystem_example
# #############################################################################


def get_Mock1_NonTime_ForecastSystem_for_simulation_example1(
    backtest_config: str,
) -> dtfsys.NonTime_ForecastSystem:
    """
    Get Mock1_NonTime_ForecastSystem object for backtesting.
    """
    system = dtfasmmfosy.Mock1_NonTime_ForecastSystem()
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # Fill pipeline-specific backtest config parameters.
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "10D"
    # Fill `MarketData` related config.
    vendor = "mock1"
    mode = "trade"
    universe = ivcu.get_vendor_universe(
        vendor, mode, version="v1", as_full_symbol=True
    )
    df = cofinanc.get_MarketData_df6(universe)
    system.config[
        "market_data_config", "im_client_ctor"
    ] = icdc.get_DataFrameImClient_example1
    system.config[
        "market_data_config", "im_client_config"
    ] = cconfig.Config().from_dict({"df": df})
    # Set the research PNL parameters.
    dag_builder = system.config["dag_builder_object"]
    price_col = dag_builder.get_column_name("price")
    volatility_col = dag_builder.get_column_name("volatility")
    # TODO(Dan): Investigate why passing with `DagBuilder` leads to test breaks.
    prediction_col = "prediction"
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": price_col,
            "volatility_col": volatility_col,
            "prediction_col": prediction_col,
        },
        "kwargs": {
            "target_gmv": 1e5,
            "liquidate_at_end_of_day": False,
        },
    }
    system.config[
        "research_forecast_evaluator_from_prices"
    ] = cconfig.Config.from_dict(forecast_evaluator_from_prices_dict)
    system = dtfsys.apply_MarketData_config(system)
    return system


# #############################################################################
# Mock1_Time_ForecastSystem_with_DataFramePortfolio_example
# #############################################################################


def get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
    market_data_df: pd.DataFrame,
    rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]],
) -> dtfsys.System:
    """
    Build a System used for the corresponding unit tests.
    """
    system = dtfasmmfosy.Mock1_Time_ForecastSystem_with_DataFramePortfolio()
    system.config["trading_period"] = "5T"
    # Market data config.
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    system.config["market_data_config", "delay_in_secs"] = 5
    system.config[
        "market_data_config", "replayed_delay_in_mins_or_timestamp"
    ] = pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York")
    system.config["market_data_config", "asset_ids"] = [101]
    system.config["market_data_config", "data"] = market_data_df
    system.config["market_data_config", "history_lookback"] = pd.Timedelta(days=7)
    # Portfolio config.
    system = dtfsys.apply_Portfolio_config(system)
    # Dag runner config.
    system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    # PnL config.
    # TODO(Grisha): use `apply_ForecastEvaluatorFromPrices_config()` instead.
    dag_builder = system.config["dag_builder_object"]
    price_col = dag_builder.get_column_name("price")
    volatility_col = dag_builder.get_column_name("volatility")
    prediction_col = dag_builder.get_column_name("prediction")
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": price_col,
            "volatility_col": volatility_col,
            "prediction_col": prediction_col,
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
    Build a System is used for the corresponding unit tests.
    """
    system = (
        dtfasmmfosy.Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor()
    )
    system.config["trading_period"] = "5T"
    # Market data config.
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    system.config["market_data_config", "delay_in_secs"] = 5
    system.config[
        "market_data_config", "replayed_delay_in_mins_or_timestamp"
    ] = pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York")
    system.config["market_data_config", "asset_ids"] = [101]
    # TODO(gp): Use a file to pass the data instead of a df.
    system.config["market_data_config", "data"] = market_data_df
    system.config["market_data_config", "history_lookback"] = pd.Timedelta(days=7)
    # Portfolio config.
    system = dtfsys.apply_Portfolio_config(system)
    # Dag runner config.
    system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    # PnL config.
    # TODO(Grisha): use `apply_ForecastEvaluatorFromPrices_config()` instead.
    dag_builder = system.config["dag_builder_object"]
    price_col = dag_builder.get_column_name("price")
    volatility_col = dag_builder.get_column_name("volatility")
    prediction_col = dag_builder.get_column_name("prediction")
    forecast_evaluator_from_prices_dict = {
        "style": "cross_sectional",
        "init": {
            "price_col": price_col,
            "volatility_col": volatility_col,
            "prediction_col": prediction_col,
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


# #############################################################################
# Mock1_NonTime_ForecastSystem_example1
# #############################################################################


def get_Mock1_NonTime_ForecastSystem_example1(
    backtest_config: str,
) -> dtfsys.ForecastSystem:
    """
    Build Mock1_ForecastSystem and fill the `System.config`.
    """
    system = dtfasmmfosy.Mock1_NonTime_ForecastSystem()
    #
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # Fill pipeline-specific backtest config parameters.
    # TODO(gp): These 2 params should go inside apply_backtest_config.
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "10D"
    # Fill `MarketData` related config.
    vendor = "mock1"
    mode = "trade"
    universe = ivcu.get_vendor_universe(
        vendor, mode, version="v1", as_full_symbol=True
    )
    df = cofinanc.get_MarketData_df6(universe)
    system.config[
        "market_data_config", "im_client_ctor"
    ] = icdc.get_DataFrameImClient_example1
    im_client_config = cconfig.Config().from_dict({"df": df})
    system.config["market_data_config", "im_client_config"] = im_client_config
    #
    system = dtfsys.apply_MarketData_config(system)
    # TODO(Grisha): No need to set research PNL parameters, deprecate.
    # Set the research PNL parameters.
    dag_builder = system.config["dag_builder_object"]
    price_col = dag_builder.get_column_name("price")
    volatility_col = dag_builder.get_column_name("volatility")
    prediction_col = dag_builder.get_column_name("prediction")
    system.config["research_pnl", "price_col"] = price_col
    system.config["research_pnl", "volatility_col"] = volatility_col
    system.config["research_pnl", "prediction_col"] = prediction_col
    return system


# #############################################################################
# Mock1_Time_ForecastSystem_example1
# #############################################################################


# TODO(Nina): Factor out the examples to pass params into it.
def get_Mock1_Time_ForecastSystem_example1() -> dtfsys.ForecastSystem:
    """
    Build a System is used for the corresponding unit tests.
    """
    system = dtfasmmfosy.Mock1_Time_ForecastSystem()
    #
    # The test decides when to start the execution.
    # The data inside the market data starts at 2000-01-01 09:31:00-05:00.
    # We want to have 10 minutes of burn in for the model.
    system.config[
        "market_data_config", "replayed_delay_in_mins_or_timestamp"
    ] = pd.Timestamp("2000-01-01 09:41:00-05:00", tz="America/New_York")
    # Market takes 10 seconds to send the bar.
    system.config["market_data_config", "delay_in_secs"] = 10
    system.config["market_data_config", "days"] = 1
    #
    # Exercise the system for 3 5-minute intervals.
    system.config["dag_runner_config", "rt_timeout_in_secs_or_time"] = 60 * 5 * 3
    # Duration of the bar is 5 minutes.
    system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
    return system
