#!/usr/bin/env python

import datetime
import logging
import os
from typing import Any, Dict, Optional

import pandas as pd

import core.config as cconfig
import dataflow.model.backtest_notebook_utils as dtfmbanout
import oms.broker.ccxt.ccxt_utils as obccccut

_LOG = logging.getLogger(__name__)


def get_run_backtest_analysis_config(
    tiles_dir: str,
    start_date: datetime.date,
    end_date: datetime.date,
    forecast_evaluator_class_name: str,
    *,
    optimizer_config_dict: Optional[Dict[str, Any]] = None,
    sweep_param: Optional[Dict[str, Any]] = None,
) -> cconfig.Config:
    output_dir_name = os.path.join(
        tiles_dir.rstrip("tiled_results"),
        "portfolio_dfs",
        pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S"),
    )
    if not sweep_param:
        sweep_param = {}
    backtest_analysis_config_dict: Dict[str, Any] = {
        "dir_name": tiles_dir,
        "output_dir_name": output_dir_name,
        "forecast_evaluator_class_name": forecast_evaluator_class_name,
        "start_date": start_date,
        "end_date": end_date,
        "asset_id_col": "asset_id",
        "pnl_resampling_frequency": "D",
        "rule": "6T",
        "im_client_config": {
            "vendor": "ccxt",
            "universe_version": "v8.1",
            "root_dir": "s3://cryptokaizen-data.preprod/v3",
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
            "resample_1min": False,
        },
        "annotate_forecasts_kwargs": {
            "style": "longitudinal",
            "quantization": 30,
            "liquidate_at_end_of_day": False,
            "initialize_beginning_of_day_trades_to_zero": False,
            "burn_in_bars": 3,
            "compute_extended_stats": True,
            "target_dollar_risk_per_name": 1.0,
            "modulate_using_prediction_magnitude": True,
            "prediction_abs_threshold": 0.0,
        },
        "forecast_evaluator_kwargs": {
            "price_col": "open",
            "volatility_col": "garman_klass_vol",
            "prediction_col": "feature",
        },
        "bin_annotated_portfolio_df_kwargs": {
            "proportion_of_data_per_bin": 0.2,
            "normalize_prediction_col_values": False,
        },
    }
    # Add 'asset_id_to_share_decimals' based on the `quantization` parameter:
    if not backtest_analysis_config_dict["annotate_forecasts_kwargs"][
        "quantization"
    ]:
        asset_id_to_share_decimals = obccccut.get_asset_id_to_share_decimals()
        backtest_analysis_config_dict["annotate_forecasts_kwargs"][
            "asset_id_to_share_decimals"
        ] = asset_id_to_share_decimals
    else:
        backtest_analysis_config_dict["annotate_forecasts_kwargs"][
            "asset_id_to_share_decimals"
        ] = None
    # Add `optimizer_config_dict` to the
    if optimizer_config_dict:
        backtest_analysis_config_dict["forecast_evaluator_kwargs"][
            "optimizer_config_dict"
        ] = optimizer_config_dict
    if sweep_param:
        backtest_analysis_config_dict["sweep_param"] = sweep_param

    # Build config from dict.
    backtest_analysis_config = cconfig.Config().from_dict(
        backtest_analysis_config_dict
    )
    return backtest_analysis_config


def main() -> None:
    # Provide parameters for building the backtest analysis config.
    tiles_dir = "/shared_data/backtest.danya/build_tile_configs.C11a.ccxt_v8_1-all.5T.2023-08-01_2024-03-31.ins.run0/tiled_results"
    start_date = datetime.date(2023, 8, 1)
    end_date = datetime.date(2024, 1, 31)
    forecast_evaluator_class_name = "ForecastEvaluatorWithOptimizer"
    optimizer_config_dict: Dict[str, Any] = {
        "dollar_neutrality_penalty": 0.0,
        "constant_correlation": 0.5,
        "constant_correlation_penalty": 50.0,
        "relative_holding_penalty": 0.0,
        "relative_holding_max_frac_of_gmv": 0.1,
        "target_gmv": 1000,
        "target_gmv_upper_bound_penalty": 0.0,
        "target_gmv_hard_upper_bound_multiple": 1.05,
        "transaction_cost_penalty": 1.2,
        "solver": "ECOS",
        "verbose": False,
    }
    sweep_param: Dict[str, Any] = {}
    #
    backtest_analysis_config = get_run_backtest_analysis_config(
        tiles_dir,
        start_date,
        end_date,
        forecast_evaluator_class_name,
        optimizer_config_dict=optimizer_config_dict,
        sweep_param=sweep_param,
    )

    # #########################################################################
    # Load tile df.
    # #########################################################################
    backtest_tiles_cols = [
        backtest_analysis_config["forecast_evaluator_kwargs"]["price_col"],
        backtest_analysis_config["forecast_evaluator_kwargs"]["volatility_col"],
        backtest_analysis_config["forecast_evaluator_kwargs"]["prediction_col"],
    ]
    tile_df = dtfmbanout.load_backtest_tiles(
        backtest_analysis_config["dir_name"],
        backtest_analysis_config["start_date"],
        backtest_analysis_config["end_date"],
        backtest_tiles_cols,
        backtest_analysis_config["asset_id_col"],
    )

    # #########################################################################
    # Assertion for tiles.
    # #########################################################################

    # Check NaNs in the price column.
    price_col = backtest_analysis_config["forecast_evaluator_kwargs"]["price_col"]
    price_df = tile_df[price_col]
    dtfmbanout.assert_nans_in_price_df(price_df)
    # Check NaNs in the feature column.
    # If NaNs in the feature column are found, replace them with 0.
    feature_col = backtest_analysis_config["forecast_evaluator_kwargs"][
        "prediction_col"
    ]
    feature_col_nans = tile_df[feature_col].isna().sum()
    if feature_col_nans.sum():
        _LOG.warning("NaN values in the feature column:\n%s", feature_col_nans)
        tile_df[feature_col] = tile_df[feature_col].fillna(0)

    # #########################################################################
    # Compute and save portfolio
    # #########################################################################

    # Get configs sweeping over parameter.
    config_dict = dtfmbanout.build_research_backtest_analyzer_config_sweep(
        backtest_analysis_config
    )
    #
    for key, config in config_dict.items():
        fep = dtfmbanout.get_forecast_evaluator(
            config["forecast_evaluator_class_name"],
            **config["forecast_evaluator_kwargs"].to_dict(),
        )
        # Create a subdirectory for the current config, e.g.
        # "optimizer_config_dict:constant_correlation_penalty=1".
        experiment_dir = os.path.join(
            config["output_dir_name"], key.replace(" ", "")
        )
        _LOG.warning("Saving portfolio in experiment_dir=%s", experiment_dir)
        _ = fep.save_portfolio(
            tile_df,
            experiment_dir,
            **config["annotate_forecasts_kwargs"].to_dict(),
        )


if __name__ == "__main__":
    main()
