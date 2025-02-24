"""
Import as:

import core.signal_processing.cross_sectional as csprcrse
"""

import logging

import numpy as np
import pandas as pd
import scipy as sp
import sklearn.preprocessing as skp

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# Add options to:
# - NaN out values below a threshold (pre-transformation)
# - standardize
# - remove bulk based on a stdev cutoff, then replace bulk with
#   - zero
#   - nan
#   - ffill


def gaussian_rank(
    df: pd.DataFrame,
    *,
    bulk_frac_to_remove: float = 0.0,
    bulk_fill_method: str = "nan",
    n_quantiles: int = 1001,
) -> pd.DataFrame:
    """
    Perform row-wise Gaussian ranking.
    """
    hdbg.dassert_lte(0.0, bulk_frac_to_remove)
    hdbg.dassert_lt(bulk_frac_to_remove, 1.0)
    hdbg.dassert_isinstance(bulk_fill_method, str)
    hdbg.dassert_isinstance(df, pd.DataFrame)
    quantile_transformer = skp.QuantileTransformer(
        n_quantiles=n_quantiles,
        output_distribution="normal",
    )
    gaussian_ranking = quantile_transformer.fit_transform(df.T.values).T
    df = pd.DataFrame(
        gaussian_ranking,
        df.index,
        df.columns,
    )
    if bulk_frac_to_remove > 0:
        threshold = sp.stats.norm.ppf(0.5 * (1 + bulk_frac_to_remove))
        idx = df.index
        # Drop all-NaN rows.
        df = df.dropna(how="all")
        non_nan_idx = df.index
        # TODO(Paul): Check strict/non-strict.
        mask = df.abs() < threshold
        df = df[~mask]
        df = df.reindex(index=non_nan_idx)
        if bulk_fill_method == "nan":
            pass
        elif bulk_fill_method == "zero":
            df[mask] = 0.0
        elif bulk_fill_method == "ffill":
            df = df.ffill()
        else:
            raise ValueError("Unrecognized `bulk_fill_method`=%s" % bulk_fill_method)
        # Add back the all-NaN rows.
        df = df.reindex(index=idx)
    return df


def uniform_rank(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rank rows uniformly and map to [-1, +1].
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Rank each row. Each non-NaN element is mapped to an integer between zero
    # and the number of non-NaN elements in the element's row.
    ranked = df.rank(axis=1)
    # Do not rank rows with fewer than two non-NaN elements.
    counts = df.count(axis=1).replace([0, 1], np.nan)
    # Map each row to [-1, +1].
    multiplier = 2 / (counts - 1)
    translation = -(counts + 1) / (counts - 1)
    ranked = (ranked.multiply(multiplier, axis=0)).add(translation, axis=0)
    return ranked
