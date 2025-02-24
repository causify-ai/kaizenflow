"""
Import as:

import core.signal_processing.decorrelation as csigdec
"""

import logging

import numpy as np
import pandas as pd
import scipy as sp
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def decorrelate_constant_correlation_df_rows(
    df: pd.DataFrame,
    corr: float,
) -> pd.DataFrame:
    """
    Decorrelate each row of `df` assuming constant correlation of `corr`.

    Decorrelation is handled row-by-row so as to effectively handle NaNs.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    decorr_rows = []
    for row in tqdm(df.iterrows(), total=df.shape[0]):
        decorr_row = decorrelate_constant_correlation(row[1], corr)
        decorr_rows.append(decorr_row)
    decorr_df = pd.concat(decorr_rows, axis=1).T
    return decorr_df


def decorrelate_constant_correlation(
    srs: pd.Series,
    corr: float,
) -> pd.DataFrame:
    """
    Decorrelate `srs` assuming constant correlation of `corr`.

    The decorrelation matrix depends upon the number of non-Nan elements.
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_lte(corr, 1)
    hdbg.dassert_lte(-1, corr)
    non_nan_idx = srs[~srs.isna()].index
    non_nan_srs = srs[non_nan_idx]
    dim = non_nan_idx.size
    if dim <= 1:
        return srs
    mat = get_constant_correlation_matrix(
        dim,
        corr,
        take_square_root=True,
        take_inverse=True,
    )
    mat.index = non_nan_idx
    mat.columns = non_nan_idx
    # Decorrelate the series.
    decorrelated_srs = non_nan_srs.dot(mat)
    # Index according to the original index.
    decorrelated_srs = decorrelated_srs.reindex(index=srs.index)
    return decorrelated_srs


# TODO(Paul): Consider adding caching.
def get_constant_correlation_matrix(
    dim: int,
    corr: float,
    take_square_root: bool = False,
    take_inverse: bool = False,
) -> pd.DataFrame:
    """
    Return a matrix with given dimension and constant correlation.

    Optionally, take the matrix square root and/or the matrix inverse.

    For large matrices, it is more efficient to compute the two unique
    values (the on-diagonal value and the off-diagonal value) directly.
    """
    hdbg.dassert_lt(0, dim)
    hdbg.dassert_lte(corr, 1)
    hdbg.dassert_lte(-1, corr)
    # Create a correlation matrix with constant correlation.
    id_matrix = np.identity(dim)
    ones = np.ones((dim, dim))
    mat = (1 - corr) * id_matrix + corr * ones
    # Optionally take the square root and/or the inverse.
    # Take the real part, since numerical instability may generate a spurious
    # nonzero complex component.
    if take_square_root:
        mat = sp.linalg.sqrtm(mat).real
    if take_inverse:
        mat = np.linalg.inv(mat).real
    # TODO(Paul): Consider allowing the user to pass an index, perhaps instead
    # of a dimension.
    # Convert to a dataframe.
    mat = pd.DataFrame(mat)
    return mat
