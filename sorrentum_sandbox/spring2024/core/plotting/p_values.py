"""
Import as:

import core.plotting.p_values as cplpval
"""

import logging
from typing import Any, List, Optional, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import core.plotting.plotting_utils as cplpluti
import core.statistics as costatis

_LOG = logging.getLogger(__name__)


def multipletests_plot(
    pvals: pd.Series,
    threshold: float,
    adj_pvals: Optional[Union[pd.Series, pd.DataFrame]] = None,
    num_cols: Optional[int] = None,
    method: Optional[str] = None,
    suptitle: Optional[str] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
    **kwargs: Any,
) -> None:
    """
    Plot adjusted p-values and pass/fail threshold.

    :param pvals: unadjusted p-values
    :param threshold: threshold for adjusted p-values separating accepted and
        rejected hypotheses, e.g., "FWER", or family-wise error rate
    :param adj_pvals: adjusted p-values, if provided, will be used instead
        calculating inside the function
    :param num_cols: number of columns in multiplotting
    :param method: method for performing p-value adjustment, e.g., "fdr_bh"
    :param suptitle: overall title of all plots
    """
    if adj_pvals is None:
        pval_series = pvals.dropna().sort_values().reset_index(drop=True)
        adj_pvals = costatis.multipletests(pval_series, method=method).to_frame()
    else:
        pval_series = pvals.dropna()
        if isinstance(adj_pvals, pd.Series):
            adj_pvals = adj_pvals.to_frame()
    num_cols = num_cols or 1
    adj_pvals = adj_pvals.dropna(axis=1, how="all")
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(
            adj_pvals.shape[1],
            num_cols=num_cols,
            sharex=False,
            sharey=True,
            y_scale=5,
        )
        if not isinstance(axes, np.ndarray):
            axes = [axes]
        plt.suptitle(suptitle, x=0.5105, y=1.01, fontsize=15)
    for i, col in enumerate(adj_pvals.columns):
        mask = adj_pvals[col].notna()
        adj_pval = adj_pvals.loc[mask, col].sort_values().reset_index(drop=True)
        axes[i].plot(
            pval_series.loc[mask].sort_values().reset_index(drop=True),
            label="pvals",
            **kwargs,
        )
        axes[i].plot(adj_pval, label="adj pvals", **kwargs)
        # Show min adj p-val in text.
        min_adj_pval = adj_pval.iloc[0]
        axes[i].text(0.1, 0.7, "adj pval=%.3f" % min_adj_pval, fontsize=20)
        axes[i].text(
            0.1,
            0.6,
            weight="bold",
            fontsize=20,
            **(
                {"s": "PASS", "color": "g"}
                if min_adj_pval <= threshold
                else {"s": "FAIL", "color": "r"}
            ),
        )
        axes[i].set_title(col)
        axes[i].axhline(threshold, ls="--", c="k")
        axes[i].set_ylim(0, 1)
        axes[i].legend()
