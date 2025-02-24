"""
Contain functions used by Master_research_backtest_analyzer notebook.

Import as:

import dataflow.model.backtest_notebook_utils as dtfmbanout
"""

import datetime
import logging
from typing import Any, Dict, List

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.model.abstract_forecast_evaluator as dtfmabfoev
import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
import dataflow.model.parquet_tile_analyzer as dtfmpatian
import dataflow.model.tiled_flows as dtfmotiflo
import helpers.hdbg as hdbg
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

_LOG = logging.getLogger(__name__)


# #############################################################################
# Backtest analysis configs
# #############################################################################


def build_research_backtest_analyzer_config_sweep(
    default_config: cconfig.Config,
) -> Dict[str, cconfig.Config]:
    """
    Build a dict of configs to run a backtest sweep.

    :param default_config: config for the backtest analysis
    :return: dict of configs to run the backtest analysis
    """
    if "sweep_param" in default_config:
        hdbg.dassert_isinstance(default_config["sweep_param"], cconfig.Config)
        # Set param values to sweep and corressponding config keys.
        sweep_param_keys = default_config["sweep_param", "keys"]
        hdbg.dassert_isinstance(sweep_param_keys, tuple)
        sweep_param_values = default_config["sweep_param", "values"]
        hdbg.dassert_isinstance(sweep_param_values, list)
        # Build config dict.
        config_dict = {}
        for val in sweep_param_values:
            # Update new config value.
            config = default_config.copy()
            config.update_mode = "overwrite"
            config[sweep_param_keys] = val
            config.update_mode = "assert_on_overwrite"
            # Set updated config key for config dict.
            config_dict_key = ":".join(sweep_param_keys)
            config_dict_key = " = ".join([config_dict_key, str(val)])
            # Add new config to the config dict.
            config_dict[config_dict_key] = config
    else:
        # Put single input config to a dict.
        config_dict = {"default_config": default_config}
    return config_dict


# #############################################################################
# Resampling and param sweeping
# #############################################################################


def resample_with_weights_ohlcv_bars(
    df_ohlcv: pd.DataFrame,
    price_col: str,
    bar_duration: str,
    weights: List[float],
) -> pd.DataFrame:
    """
    Resample 1-minute data to `bar_duration` with weights.

    :param df_ohlcv: input OHLCV data
    :param price_col: price column
    :param bar_duration: bar duration
    :param weights: weights for resampling
    :return: resampled OHLCV data
    """
    resampling_node = dtfcore.GroupedColDfToDfTransformer(
        "resample",
        transformer_func=cofinanc.resample_with_weights,
        **{
            "in_col_groups": [
                (price_col,),
            ],
            "out_col_group": (),
            "transformer_kwargs": {
                "rule": bar_duration,
                "col": price_col,
                "weights": weights,
            },
            "reindex_like_input": False,
            "join_output_with_input": False,
        },
    )
    resampled_ohlcv = resampling_node.fit(df_ohlcv)["df_out"]
    return resampled_ohlcv


# #############################################################################
# ForecastEvaluator
# #############################################################################


def get_forecast_evaluator(
    forecast_evaluator_class_name: str, **kwargs: Dict[str, Any]
) -> dtfmabfoev.AbstractForecastEvaluator:
    """
    Get the forecast evaluator for the backtest analysis.

    :param forecast_evaluator_class_name: name of the ForecastEvaluator
        as str, e.g. "ForecastEvaluatorFromPrices",
        "ForecastEvaluatorWithOptimizer" :param **kwargs: kwargs for
        ctor of the provided ForecastEvaluator class
    :return: ForecastEvaluator object
    """
    # Choose the class based on the label.
    if forecast_evaluator_class_name == "ForecastEvaluatorFromPrices":
        forecast_evaluator_class = dtfmfefrpr.ForecastEvaluatorFromPrices
    #
    elif forecast_evaluator_class_name == "ForecastEvaluatorWithOptimizer":
        forecast_evaluator_class = ofevwiop.ForecastEvaluatorWithOptimizer
    #
    else:
        raise ValueError(
            f"Unsupported forecast_evaluator_class_name: {forecast_evaluator_class_name}"
        )
    # Construct the object.
    forecast_evaluator = forecast_evaluator_class(**kwargs)
    return forecast_evaluator


# #############################################################################
# Tiles loading
# #############################################################################


def load_backtest_tiles(
    src_dir: str,
    start_date: datetime.date,
    end_date: datetime.date,
    cols: List[str],
    asset_id_col: str,
) -> pd.DataFrame:
    """
    Load backtest tiles from the log directory.

    The tiles are loaded for all assets present in the parquet dataset
    and trimmed to the precise date range.

    :param src_dir: directory with backtest log files
    :param start_date: start date
    :param end_date: end date
    :param cols: columns to load from asset tiles
    :param asset_id_col: asset_id column
    :return: backtest tiles
    """
    # Get tile asset_ids.
    parquet_tile_analyzer = dtfmpatian.ParquetTileAnalyzer()
    parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
        src_dir
    )
    asset_ids = parquet_tile_metadata.index.levels[0].to_list()
    #
    tile_df = next(
        dtfmotiflo.yield_processed_parquet_tiles_by_year(
            src_dir, start_date, end_date, asset_id_col, cols, asset_ids=asset_ids
        )
    )
    # Trim tile to the specified time interval.
    tile_df = tile_df[
        (tile_df.index >= pd.Timestamp(start_date, tz="UTC"))
        & (tile_df.index <= pd.Timestamp(end_date, tz="UTC"))
    ]
    return tile_df


def assert_nans_in_price_df(price_df: pd.DataFrame) -> None:
    """
    Check NaNs in the price df.

    Since the Optimizer cannot work with NaN values in the price column,
    check the presence of NaN values and return the first and last date
    where NaNs are encountered.
    """
    try:
        hdbg.dassert_eq(price_df.isna().sum().sum(), 0)
    except AssertionError as e:
        min_nan_idx = price_df[price_df.isnull().any(axis=1)].index.min()
        max_nan_idx = price_df[price_df.isnull().any(axis=1)].index.max()
        _LOG.warning(
            "NaN values found between %s and %s", min_nan_idx, max_nan_idx
        )
        raise e
