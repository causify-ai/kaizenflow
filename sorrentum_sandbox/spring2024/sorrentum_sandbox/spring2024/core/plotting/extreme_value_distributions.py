"""
Import as:

import core.plotting.extreme_value_distributions as cpevd
"""

import logging
from typing import Dict

import pandas as pd
import scipy as sp

import core.statistics as costatis

_LOG = logging.getLogger(__name__)


def fit_and_plot_extreme_value_distributions(
    srs: pd.Series,
    alpha: float = 0.05,
    weibull_min_kwargs: Dict[str, float] = {},
    gumbel_r_kwargs: Dict[str, float] = {},
    lognormal_kwargs: Dict[str, float] = {},
) -> pd.DataFrame:
    """
    Compare ECDF to common EV distributions.

    :param srs: observations
    :param alpha: as in `costatis.compute_empirical_cdf_with_bounds()`
    :param weibull_min_kwargs:
      - loc
      - scale
    :param gumbel_r_kwargs:
    """
    data_list = []
    sorted_vals = srs.sort_values().dropna().values
    # Compute empirical cdf.
    ecdf_with_bounds = costatis.compute_empirical_cdf_with_bounds(srs, alpha)
    data_list.append(ecdf_with_bounds)
    # Fit Weibull.
    weibull_params = sp.stats.weibull_min.fit(
        sorted_vals,
        **weibull_min_kwargs,
    )
    _LOG.info("Weibull fit params=%s", weibull_params)
    weibull_cdf = sp.stats.weibull_min.cdf(
        sorted_vals,
        *weibull_params,
    )
    weibull_srs = pd.Series(
        weibull_cdf,
        sorted_vals,
        name="weibull_cdf",
    )
    data_list.append(weibull_srs)
    # Fit Gumbel.
    gumbel_params = sp.stats.gumbel_r.fit(
        sorted_vals,
        **gumbel_r_kwargs,
    )
    _LOG.info("Gumbel fit params=%s", gumbel_params)
    gumbel_cdf = sp.stats.gumbel_r.cdf(
        sorted_vals,
        *gumbel_params,
    )
    gumbel_srs = pd.Series(
        gumbel_cdf,
        sorted_vals,
        name="gumbel_cdf",
    )
    data_list.append(gumbel_srs)
    # Fit Lognormal.
    lognormal_params = sp.stats.lognorm.fit(
        sorted_vals,
        **lognormal_kwargs,
    )
    _LOG.info("Lognormal fit params=%s", lognormal_params)
    lognormal_cdf = sp.stats.lognorm.cdf(
        sorted_vals,
        *lognormal_params,
    )
    lognormal_srs = pd.Series(
        lognormal_cdf,
        sorted_vals,
        name="lognormal_cdf",
    )
    data_list.append(lognormal_srs)
    #
    df = pd.concat(data_list, axis=1)
    df.plot()
    return df
