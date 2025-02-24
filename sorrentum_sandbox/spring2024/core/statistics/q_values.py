"""
Import as:

import core.statistics.q_values as cstqval
"""

import logging
from typing import Optional, Union

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def estimate_q_values(
    p_values: Union[pd.Series, pd.DataFrame],
    n_experiments: Optional[int] = None,
    pi0: Optional[float] = None,
) -> pd.Series:
    """
    Estimate q-values from p-values.

    See https://github.com/nfusi/qvalue for reference.

    :param p_values: p-values of test statistics of experiments
    :param n_experiments: number of experiments; by default, this is set to the
        number of p-values
    :param pi0: estimate of proportion of true null hypotheses
    :return: estimated q-values
    """
    # TODO(Paul): Relax the NaN constraint.
    hdbg.dassert(not p_values.isna().any().any())
    # Each p-value must lie in [0, 1].
    hdbg.dassert_lte(0, p_values.min().min())
    hdbg.dassert_lte(p_values.max().max(), 1)
    #
    pv = p_values.values.ravel()
    #
    n_experiments = n_experiments or len(pv)
    # Estimate the proportion of true null hypotheses.
    if pi0 is not None:
        # Use `pi0` if the caller provided one.
        pi0 = pi0
    elif n_experiments < 100:
        # Use the most conservative estimate if `n_experiments` is small.
        pi0 = 1.0
    else:
        # Follow the estimation procedure in Storey and Tibshirani (2003).
        pi0 = []
        lambdas = np.arange(0, 0.9, 0.01)
        counts = np.array([(pv > i).sum() for i in lambdas])
        for k in range(len(lambdas)):
            pi0.append(counts[k] / (n_experiments * (1 - lambdas[k])))
        #
        pi0 = np.array(pi0)
        # Fit natural cubic spline.
        tck = sp.interpolate.splrep(lambdas, pi0, k=3)
        pi0 = sp.interpolate.splev(lambdas[-1], tck)
        _LOG.info("pi0=%.3f (estimated proportion of null features)" % pi0)
        if pi0 > 1:
            _LOG.info("pi0 > 1 (%.3f), clipping to 1" % pi0)
            pi0 = 1.0
    hdbg.dassert_lte(0, pi0)
    hdbg.dassert_lte(pi0, 1)
    #
    p_ordered = np.argsort(pv)
    pv = pv[p_ordered]
    # Initialize q-values.
    q_values = pi0 * n_experiments / len(pv) * pv
    q_values[-1] = min(q_values[-1], 1.0)
    # Iteratively compute q-values.
    for i in range(len(pv) - 2, -1, -1):
        q_values[i] = min(
            pi0 * n_experiments * pv[i] / (i + 1.0), q_values[i + 1]
        )
    # Reorder q-values.
    qv_temp = q_values.copy()
    qv = np.zeros_like(q_values)
    qv[p_ordered] = qv_temp
    #
    qv = qv.reshape(p_values.shape)
    #
    if isinstance(p_values, pd.Series):
        q_values = pd.Series(index=p_values.index, data=qv, name="q_val")
    else:
        q_values = pd.DataFrame(
            index=p_values.index, data=qv, columns=p_values.columns
        )
    return q_values
