"""
Import as:

import core.finance.portfolio_df_processing.binned_stats as cfpdpbist
"""
import logging

import numpy as np
import pandas as pd

import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def bin_prediction_annotated_portfolio_df(
    df: pd.DataFrame,
    proportion_of_data_per_bin: float,
    output_col: str,
    normalize_prediction_col_values: bool = False,
) -> pd.DataFrame:
    """
    Bin portfolio properties into bins determined by the prediction.

    It is assumed that the prediction is approximately standard normal.
    If the scale of the prediction is not on the unit scale, set
    `normalize_prediction_col_values=True` for better results.

    :param df: `portfolio_df` with "prediction" col, e.g., output of
        `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :param proportion_of_data_per_bin:
      - strictly between 0 and 1
      - always generates an odd number of bins symmetric bins based on
        the normal distribution, with the middle bin straddling zero
    :param output_col: "pnl", "pnl_in_bps", "sgn_corr", or "hit_rate"
    :param normalize_prediction_col_values: if `True`, divide the
        prediction col values by their standard deviation (across all
        times)
    """
    # Sanity-check dataframe.
    # TODO(Paul): Factor out this check.
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hpandas.dassert_index_is_datetime(df)
    hdbg.dassert_eq(df.columns.nlevels, 2)
    hdbg.dassert_is_subset(
        ["prediction", "pnl", "holdings_notional"],
        df.columns.levels[0].to_list(),
    )
    asset_ids = df.columns.levels[1].to_list()
    # Swap the column indices to facilitate analyzing portfolio data by name.
    swapped_df = df.swaplevel(i=0, j=1, axis=1)
    grouped = {}
    for asset_id in asset_ids:
        df_slice = swapped_df[asset_id]
        binned = _bin_annotated_portfolio_df_helper(
            df_slice,
            proportion_of_data_per_bin,
            output_col,
            normalize_prediction_col_values,
        )
        grouped[asset_id] = binned
    grouped = pd.concat(grouped, axis=1).swaplevel(axis=1).sort_index(axis=1)
    return grouped


def _bin_annotated_portfolio_df_helper(
    df: pd.DataFrame,
    proportion_of_data_per_bin: float,
    output_col: str,
    normalize_prediction_col_values: bool = False,
) -> pd.DataFrame:
    """
    Group `output_col` into bins determined by the prediction.
    """
    prediction = df["prediction"]
    pnl = df["pnl"]
    holdings_notional = df["holdings_notional"]
    if output_col == "pnl":
        df_to_group = pd.concat([prediction.shift(2), pnl], axis=1)
        grouped = costatis.group_by_bin(
            df_to_group,
            "prediction",
            proportion_of_data_per_bin,
            "pnl",
            normalize_prediction_col_values,
        )
    elif output_col == "pnl_in_bps":
        basis = holdings_notional.abs().shift(1)
        pnl_in_bps = 1e4 * pnl.divide(basis).replace(np.nan, 0).replace(
            [-np.inf, np.inf], np.nan
        )
        pnl_in_bps.name = "pnl_in_bps"
        df_to_group = pd.concat([prediction.shift(2), pnl_in_bps], axis=1)
        # This aggregation will be approximate, since we are arithmetically averaging bps.
        grouped = costatis.group_by_bin(
            df_to_group,
            "prediction",
            proportion_of_data_per_bin,
            "pnl_in_bps",
            normalize_prediction_col_values,
        )
    elif output_col == "sgn_corr":
        sgn_corr = np.sign(pnl).rename("sgn_corr")
        df_to_group = pd.concat([prediction.shift(2), sgn_corr], axis=1)
        grouped = costatis.group_by_bin(
            df_to_group,
            "prediction",
            proportion_of_data_per_bin,
            "sgn_corr",
            normalize_prediction_col_values,
        )
    elif output_col == "corr":
        corr = pnl.divide(pnl.std()).rename("corr")
        df_to_group = pd.concat([prediction.shift(2), corr], axis=1)
        grouped = costatis.group_by_bin(
            df_to_group,
            "prediction",
            proportion_of_data_per_bin,
            "corr",
            normalize_prediction_col_values,
        )
    elif output_col == "hit_rate":
        sgn_corr = np.sign(pnl).rename("sgn_corr")
        hits = np.round(0.5 * (1 + sgn_corr)).rename("hits")
        df_to_group = pd.concat([prediction.shift(2), hits], axis=1)
        grouped = costatis.group_by_bin(
            df_to_group,
            "prediction",
            proportion_of_data_per_bin,
            "hits",
            normalize_prediction_col_values,
        )
    else:
        raise ValueError(f"Invalid output_col `{output_col}`.")
    return grouped
