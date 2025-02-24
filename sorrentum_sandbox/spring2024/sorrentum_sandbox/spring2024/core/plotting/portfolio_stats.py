"""
Import as:

import core.plotting.portfolio_stats as cplposta
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import core.finance as cofinanc
import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def plot_portfolio_stats(
    df: pd.DataFrame,
    *,
    freq: Optional[str] = None,
    y_scale: Optional[float] = 5,
) -> None:
    """
    Plots stats of a portfolio bar metrics dataframe, possibly multiindex.

    :param df: `df` should be of the form
                                      pnl  gross_volume  net_volume        gmv     nmv
        2022-01-03 09:30:00-05:00  125.44         49863      -31.10  1000000.0     NaN
        2022-01-03 09:40:00-05:00  174.18        100215       24.68  1000000.0   12.47
        2022-01-03 09:50:00-05:00  -21.52        100041      -90.39  1000000.0  -55.06
        2022-01-03 10:00:00-05:00  -16.82         50202       99.19  1000000.0  167.08

        if singly indexed. If multiindexed, column level zero should contain the
        portfolio name.
    :param freq: resampling frequency. `None` means no resampling.
    :param y_scale: controls the size of the figures
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Handle resampling if `freq` is provided.
    if freq is not None:
        hdbg.dassert_isinstance(freq, str)
        df = cofinanc.resample_portfolio_bar_metrics(
            df,
            freq,
        )
    # Make the `df` a df with a two-level column index.
    if df.columns.nlevels == 1:
        df = pd.concat([df], axis=1, keys=["strategy"])
    hdbg.dassert_eq(df.columns.nlevels, 2)
    # Define plot axes.
    _, axes = cplpluti.get_multiple_plots(12, 2, y_scale=y_scale)
    # PnL.
    pnl = df.T.xs("pnl", level=1).T
    pnl.plot(ax=axes[0], title="Bar PnL", ylabel="dollars")
    #
    gmv = df.T.xs("gmv", level=1).T
    # Zero-GMV "bars" lead to noise in some plots. Remove these.
    gmv = gmv.replace(0, np.nan)
    rolling_gmv = gmv.expanding().mean()
    #
    gross_volume = df.T.xs("gross_volume", level=1).T
    gross_volume = gross_volume.replace(0, np.nan)
    # TODO(Paul): Make the unit configurable.
    pnl_rel_volume = pnl.divide(gross_volume)
    (1e4 * pnl_rel_volume).plot(
        ax=axes[1], title="Bar PnL/Gross Volume", ylabel="bps"
    )
    # Cumulative PnL.
    pnl.cumsum().plot(ax=axes[2], title="Cumulative PnL", ylabel="dollars")
    # TODO(Paul): Make this a GMV-weighted average.
    (1e2 * pnl.cumsum().divide(rolling_gmv)).plot(
        ax=axes[3], title="Cumulative PnL/GMV", ylabel="%"
    )
    # Volume/turnover.
    gross_volume.cumsum().ffill().plot(
        ax=axes[4],
        title="Cumulative Gross Volume",
        ylabel="dollars",
    )
    #
    turnover = 100 * gross_volume.divide(rolling_gmv)
    turnover.plot(ax=axes[5], title="Bar Turnover", ylabel="% GMV")
    # Net volume/imbalance.
    net_volume = df.T.xs("net_volume", level=1).T
    net_volume.cumsum().ffill().plot(
        ax=axes[6],
        title="Cumulative Net Volume",
        ylabel="dollars",
    )
    imbalance = 100 * net_volume.divide(gmv)
    imbalance.plot(ax=axes[7], title="Bar Net Volume", ylabel="% GMV")
    # GMV.
    gmv.plot(ax=axes[8], title="GMV", ylabel="dollars")
    (gmv / rolling_gmv).plot(
        ax=axes[9], title="GMV deviation from expanding mean", ylabel="ratio"
    )
    # NMV.
    nmv = df.T.xs("nmv", level=1).T
    nmv.plot(ax=axes[10], title="NMV", ylabel="dollars")
    nmv_rel = 100 * nmv.divide(gmv)
    nmv_rel.plot(ax=axes[11], title="NMV", ylabel="% GMV")
