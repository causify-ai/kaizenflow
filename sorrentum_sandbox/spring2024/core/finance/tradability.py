"""
Import as:

import core.finance.tradability as cfintrad
"""


import logging
import random
from typing import Dict

import numpy as np
import pandas as pd
import statsmodels
from numpy.typing import ArrayLike

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def process_df(df: pd.DataFrame, freq_mins: int) -> pd.DataFrame:
    rics = df["ric"].unique()
    hdbg.dassert_eq(len(rics), 1, "Found more than one ric: %s", rics)
    ric = rics[0]
    #
    egids = df["egid"].unique()
    hdbg.dassert_eq(len(egids), 1, "Found more than one egid: %s", egids)
    egid = egids[0]
    #
    out_df = pd.DataFrame()
    out_df["close"] = df["close"].resample(f"{freq_mins}T").last()
    out_df["ric"] = ric
    out_df["egid"] = egid
    out_df["volume"] = df["volume"].resample(f"{freq_mins}T").sum()
    # # TODO(gp): This should be VWAP.
    out_df["bid"] = df["bid"].resample(f"{freq_mins}T").mean()
    out_df["ask"] = df["ask"].resample(f"{freq_mins}T").mean()
    out_df = out_df.dropna()
    # #
    out_df["ret_0"] = out_df["close"].pct_change()
    out_df["spread_usd"] = out_df["ask"] - out_df["bid"]
    out_df["spread_bps"] = (out_df["ask"] - out_df["bid"]) / out_df["close"]
    out_df["trad"] = out_df["ret_0"].abs() / out_df["spread_bps"]
    out_df = out_df.dropna()
    return out_df


def compute_stats(df: pd.DataFrame) -> pd.Series:
    rics = df["ric"].unique()
    hdbg.dassert_eq(len(rics), 1, "Found more than 1 future: %s", rics)
    ric = rics[0]
    srs = {
        "ric": ric,
        "close.mean": df["close"].mean(),
        "ret_0.mad": df["ret_0"].mad(),
        "spread_usd.median": df["spread_usd"].median(),
        "spread_bps.median": df["spread_bps"].median(),
        "trad": df["trad"].median(),
    }
    srs = pd.Series(srs)
    return srs


# #############################################################################


def get_predictions(
    df: pd.DataFrame, ret_col: str, hit_rate: float, seed: int
) -> pd.Series:
    """
    :param df: desired sample with OHLCV data and calculated returns
    :param hit_rate: desired percantage of successful predictions
    :param seed: experiment stance
    """
    hdbg.dassert_lte(0, hit_rate)
    hdbg.dassert_lte(hit_rate, 1)
    random.seed(seed)
    n = df.shape[0]
    rets = df[ret_col].values
    # Mask contains 1 for a desired hit and -1 for a miss.
    num_hits = int((1 - hit_rate) * n)
    mask = ([-1] * num_hits) + ([1] * (n - num_hits))
    # print(len(mask))
    mask = np.asarray(mask)
    # Randomize the location of the outcomes.
    random.shuffle(mask)
    # Construct predictions using the sign of the actual returns.
    pred = pd.Series(np.sign(rets) * mask)
    # Change the index for easy attachment to initial DataFrame.
    pred.index = df.index
    return pred


# TODO(Grisha): dup of `calculate_hit_rate()`?
def calculate_confidence_interval(
    hit_series: pd.Series, alpha: float, method: str
) -> None:
    """
    :param hit_series: boolean series with hit values
    :param alpha: significance level
    :param method: "normal", "agresti_coull", "beta", "wilson", "binom_test"
    """
    point_estimate = hit_series.mean()
    hit_lower, hit_upper = statsmodels.stats.proportion.proportion_confint(
        count=hit_series.sum(),
        nobs=hit_series.count(),
        alpha=alpha,
        method=method,
    )
    result_values_pct = [100 * point_estimate, 100 * hit_lower, 100 * hit_upper]
    conf_alpha = (1 - alpha / 2) * 100
    print(f"hit_rate: {result_values_pct[0]}")
    print(f"hit_rate_lower_CI_({conf_alpha}%): {result_values_pct[1]}")
    print(f"hit_rate_upper_CI_({conf_alpha}%): {result_values_pct[2]}")


def get_predictions_and_hits(df, ret_col, hit_rate, seed):
    """
    Calculate hits from the predictions and show confidence intervals.

    :param df: desired sample with OHLCV data and calculated returns
    :param ret_col: name of the column with returns
    :param hit_rate: desired percentage of successful predictions
    :param seed: experiment stance
    """
    df = df.copy()
    df["predictions"] = get_predictions(df, ret_col, hit_rate, seed)
    # Specify necessary columns.
    df = df[[ret_col, "predictions"]]
    # Attach `hit` column (boolean).
    df = df.copy()
    df["hit"] = df[ret_col] * df["predictions"] >= 0
    # Exclude NaNs for the better analysis (at least one in the beginning because of `pct_change()`)
    df = hpandas.dropna(df, report_stats=False)
    return df


def compute_bar_pnl(
    df: pd.DataFrame, rets_col: str, prediction_col: str
) -> pd.Series:
    """
    Compute PnL (profits and losses) for each bar.

    :param df: dataframe containing returns and predictions (aligned)
    :param rets_col: name of the column with returns
    :param prediction_col: name of the column with predictions
    :return: bar PnL
    """
    hdbg.dassert_in(rets_col, df.columns)
    _LOG.debug("rets_col=%s, prediction_col=%s", rets_col, prediction_col)
    hdbg.dassert_in(prediction_col, df.columns)
    bar_pnl = df[prediction_col] * df[rets_col]
    bar_pnl.name = "bar_pnl"
    return bar_pnl


# TODO(Grisha): maybe pass 2 pd.Series?
def compute_total_pnl(
    df: pd.DataFrame, rets_col: str, prediction_col: str
) -> float:
    """
    Compute PnL.
    """
    bar_pnl = compute_bar_pnl(df, rets_col, prediction_col)
    pnl = bar_pnl.sum()
    return pnl


def simulate_pnls_for_set_of_hit_rates(
    df: pd.DataFrame,
    rets_col: str,
    prediction_col: str,
    hit_rates: ArrayLike,
    n_experiment: int,
) -> Dict[float, float]:
    """
    For the set of various pre-defined `hit_rates` values iterate several
    generations for the actual PnL.

    :param df: desired sample with calculated returns
    :param rets_col: name of the column with returns
    :param hit_rates: set of hit rates for the experiment
    :param n_experiment: number of iterations for each `hit_rate`
    :return: corresponding `PnL` for each `hit_rate`
    """
    # Every seed corresponds to a different "model".
    seed = random.randint(0, 100)
    # Placeholder for the results.
    results = {}
    # Each value of hit rate is making its own PnL value.
    for hit_rate in hit_rates:
        # For each value of hit rate produce `n_experiment` iterations.
        for i in range(n_experiment):
            # Generate predictions and hits for a given `hit_rate`.
            df_tmp = get_predictions_and_hits(df, rets_col, hit_rate, seed)
            # The actual `hit_rate`.
            hit_rate = df_tmp["hit"].mean()
            # The actual `PnL`.
            pnl = compute_total_pnl(df_tmp, rets_col, prediction_col)
            # Attach corresponding `hit_rate` and `PnL` to the dictionary.
            results[hit_rate] = pnl
            # Reassign seed value.
            seed += 1
    return results


# TODO(gp): Move to hpandas.
def plot_without_gaps(df):
    # df.plot(x=df.index.astype(str))
    df = df.copy()
    df.index = df.index.to_series().dt.strftime("%Y-%m-%d")
    df.plot()
