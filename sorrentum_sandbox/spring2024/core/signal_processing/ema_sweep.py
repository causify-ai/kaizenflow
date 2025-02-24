"""
Import as:

import core.signal_processing.ema_sweep as csprema
"""

import logging
from typing import List

import pandas as pd
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def sweep_horizon_and_com(
    signal_df: pd.DataFrame,
    target_df: pd.DataFrame,
    time_horizons: List[int],
    coms: List[float],
    *,
    horizon_unit: str = "T",
    delay: int = 1,
) -> pd.DataFrame:
    """
    Sweep time horizons and ema filterings of signal.

    :param signal_df: knowledge-time indexed signal
    :param target_df: knowledge-time index target
    :param time_horizons: list of forecast horizons
    :param coms: list of centers of mass to use for ema
    :param horizon_unit: unit of `time_horizon`
    :param delay: delay in units of `horizon_unit`
    :return: correlation dataframe, with index of coms and columns consisting
        of time horizons
    """
    # Check types and compatibility.
    hdbg.dassert_isinstance(signal_df, pd.DataFrame)
    hpandas.dassert_strictly_increasing_index(signal_df)
    hdbg.dassert_isinstance(target_df, pd.DataFrame)
    hpandas.dassert_strictly_increasing_index(target_df)
    hpandas.dassert_indices_equal(
        signal_df,
        target_df,
        only_warning=True,
    )
    hdbg.dassert_container_type(
        time_horizons,
        list,
        int,
        "Time horizons must be expressed as a list of ints.",
    )
    hdbg.dassert_container_type(
        coms,
        list,
        float,
        "Centers of mass must be expressed as a list of floats.",
    )
    hdbg.dassert_isinstance(horizon_unit, str)
    # TODO(Paul): Add a check on `delay`, but not a hard inequality (we want
    #   to warn on future peeking but allow it in exploratory research as a
    #   check).
    # Perform outer sweep over time horizons.
    corrs = []
    item_ids = signal_df.columns.to_list()
    for time_horizon in tqdm(time_horizons, desc="time_horizon"):
        com_sweep = {}
        # Perform inner sweep over centers of mass.
        for com in tqdm(coms, desc="com"):
            corr_vals = []
            # Perform the sweep independently for each item.
            for item_id in item_ids:
                smoothed_signal = signal_df[item_id].ewm(com).mean()
                # Resample smoothed signal to latest and shift by `delay`.
                smoothed_signal = (
                    smoothed_signal.resample(str(time_horizon) + horizon_unit)
                    .last()
                    .shift(delay)
                )
                # Resample target by averaging over time horizon.
                target = (
                    target_df[item_id]
                    .resample(str(time_horizon) + horizon_unit)
                    .mean()
                )
                corr = smoothed_signal.corr(target)
                corr_vals.append(corr)
            corr_vals = pd.Series(corr_vals)
            # Approximate typical correlation across items by mean of correlations.
            com_sweep[com] = corr_vals.mean()
        com_sweep = pd.Series(com_sweep, name=time_horizon)
        corrs.append(com_sweep)
    corrs = pd.concat(corrs, axis=1)
    return corrs
