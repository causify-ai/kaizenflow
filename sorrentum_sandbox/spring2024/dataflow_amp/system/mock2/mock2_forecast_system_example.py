"""
Import as:

import dataflow_amp.system.mock2.mock2_forecast_system_example as dasmmfsex
"""

import core.config as cconfig
import dataflow.system as dtfsys
import dataflow_amp.system.mock2.mock2_forecast_system as dasmmfosy
import im_v2.common.data.client.historical_pq_clients as imvcdchpcl


def _get_Mock2_NonTime_ForecastSystem(
    backtest_config: str, root_dir: str
) -> dtfsys.NonTime_ForecastSystem:
    """
    Get `Mock2_NonTime_ForecastSystem` object.

    :param backtest_config: backtest_config, e.g.,
        `bloomberg_v1-top1.5T.2023-08-01_2023-08-31`
    :param root_dir: a root dir where data is stored
    """
    system = dasmmfosy.Mock2_NonTime_ForecastSystem()
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # Fill pipeline-specific backtest config parameters.
    # TODO(Grisha): Generalize and re-use `apply_backtest_tile_config()`.
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "1D"
    # Fill `MarketData` related config.
    system.config[
        "market_data_config", "im_client_ctor"
    ] = imvcdchpcl.HistoricalPqByCurrencyPairTileClient
    im_client_config_dict = {
        "vendor": "bloomberg",
        "universe_version": "v1",
        "root_dir": root_dir,
        "partition_mode": "by_year_month",
        "dataset": "ohlcv",
        "contract_type": "spot",
        "data_snapshot": "",
        "download_mode": "manual",
        "downloading_entity": "",
        "aws_profile": "ck",
        "resample_1min": False,
        "version": "v1_0_0",
        "download_universe_version": "v1",
        "tag": "resampled_1min",
    }
    system.config[
        "market_data_config", "im_client_config"
    ] = cconfig.Config().from_dict(im_client_config_dict)
    # Add research Portfolio configuration.
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
    system = dtfsys.apply_MarketData_config(system)
    return system


def get_Mock2_NonTime_ForecastSystem_example1(
    backtest_config: str,
) -> dtfsys.NonTime_ForecastSystem:
    """
    Get `Mock2_NonTime_ForecastSystem` object for backtesting.
    """
    root_dir = "s3://cryptokaizen-data-test/v3/bulk"
    system = _get_Mock2_NonTime_ForecastSystem(backtest_config, root_dir)
    return system


def get_Mock2_NonTime_ForecastSystem_example2(
    backtest_config: str,
) -> dtfsys.NonTime_ForecastSystem:
    """
    Get `Mock2_NonTime_ForecastSystem` object for unit testing.

    The only difference from `get_Mock2_NonTime_ForecastSystem_example1()`
    is the `root_dir`.
    """
    root_dir = "s3://cryptokaizen-unit-test/v3/bulk"
    system = _get_Mock2_NonTime_ForecastSystem(backtest_config, root_dir)
    return system
