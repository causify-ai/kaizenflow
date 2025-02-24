"""
Import as:

import core.statistics.correlation as cstacorr
"""

import collections
import logging

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_distance_matrix(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the distance matrix of `df`, treating rows as samples.

    :param df: numeric n x m dataframe (n samples of m dimensions)
    :return: n x n distance matrix
    """
    if isinstance(df, pd.Series):
        df = df.to_frame()
    hdbg.dassert_isinstance(df, pd.DataFrame)
    idx = df.index
    distance_matrix = sp.spatial.distance_matrix(df, df)
    out_df = pd.DataFrame(distance_matrix, idx, idx.to_list())
    return out_df


def compute_doubly_centered_distance_matrix(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the "doubly centered" distance matrix.

    :param df: as in `compute_distance_matrix()`
    :return: return distance matrix re-centered row-wise and column-wise.
    """
    if isinstance(df, pd.Series):
        df = df.to_frame()
    distance_matrix_df = compute_distance_matrix(df)
    #
    col_mean = distance_matrix_df.mean(axis=0)
    row_mean = distance_matrix_df.mean(axis=1)
    grand_mean = col_mean.mean()
    #
    centered = distance_matrix_df
    centered = centered.subtract(col_mean, axis=0)
    centered = centered.subtract(row_mean, axis=1)
    centered = centered + grand_mean
    return centered


def compute_distance_covariance(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
) -> float:
    """
    Compute the "distance covariance" (Szekely, Rizzo, Bakirov).

    :param df1: numeric n x m_1 dataframe
    :param df2: numeric n x m_2 dataframe
    :return: distance covariance
    """
    if isinstance(df1, pd.Series):
        df1 = df1.to_frame()
    if isinstance(df2, pd.Series):
        df2 = df2.to_frame()
    hdbg.dassert_isinstance(df1, pd.DataFrame)
    hdbg.dassert_isinstance(df2, pd.DataFrame)
    n_samples_1 = df1.shape[0]
    n_samples_2 = df2.shape[0]
    hdbg.dassert_eq(n_samples_1, n_samples_2)
    #
    doubly_centered_distance_matrix_1 = compute_doubly_centered_distance_matrix(
        df1
    )
    doubly_centered_distance_matrix_2 = compute_doubly_centered_distance_matrix(
        df2
    )
    #
    hadamard_product = doubly_centered_distance_matrix_1.multiply(
        doubly_centered_distance_matrix_2
    )
    distance_covariance = hadamard_product.mean().mean()
    return distance_covariance


def compute_distance_correlation(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the "distance correlation" (Szekely, Rizzo, Bakirov).

    This is a number in [0, 1].

    :param df1: numeric n x m_1 dataframe
    :param df2: numeric n x m_2 dataframe
    :return: distance covariance
    """
    distance_covariance = compute_distance_covariance(df1, df2)
    distance_variance_1 = compute_distance_covariance(df1, df1)
    distance_variance_2 = compute_distance_covariance(df2, df2)
    distance_correlation = distance_covariance / np.sqrt(
        distance_variance_1 * distance_variance_2
    )
    return distance_correlation


def compute_mean_pearson_correlation(df: pd.DataFrame):
    """
    Compute the mean Pearson correlation of cols of `df`.
    """
    corr = df.corr()
    # Get upper triangular part without the main diagonal.
    ut_indices = np.triu_indices_from(corr.values, 1)
    ut_part = corr.values[ut_indices]
    # Take a Fisher transformation.
    fisher = np.arctanh(ut_part)
    # Average and undo the Fisher transformation.
    mean_corr = np.tanh(fisher.mean())
    return mean_corr


def compute_mean_pearson_correlation_by_group(
    df: pd.DataFrame,
    level: int,
) -> pd.DataFrame:
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_eq(df.columns.nlevels, 2)
    hdbg.dassert_is_integer(level)
    hdbg.dassert_is_subset([level], [0, 1])
    groups = df.columns.levels[level].to_list()
    corrs = collections.OrderedDict()
    for group in groups:
        group_df = df.T.xs(group, level=level).T
        corrs[group] = group_df.corr()
    # TODO(Paul): Consider performing a Fisher transformation before taking the mean.
    mean_corr = pd.concat(corrs).groupby(level=1).mean()
    return mean_corr


def compute_correlation_confidence_density_approximation(
    rho: float,
    n_samples: int,
    *,
    grid_size: float = 0.0001,
) -> pd.Series:
    """
    Compute an approximate posterior density for correlation.

    For more context and some discussion on the (relatively high) accuracy
    of this approximation, see
      Taraldsen, G. The Confidence Density for Correlation. Sankhya A 85,
      600–616 (2023). https://doi.org/10.1007/s13171-021-00267-y

    :param rho: empirical correlation
    :param n_samples: number of samples used to compute the correlation
    :param grid_size: granularity of density approximation
    :return: series with correlation grid points as index (on original, not
        Fisher-transformed scale) and pdf density as values.
    """
    # Ensure the correlation `rho` is between -1 and 1.
    hdbg.dassert_lte(-1.0, rho)
    hdbg.dassert_lte(rho, 1.0)
    # Ensure there are sufficiently many samples.
    hdbg.dassert_lte(4, n_samples, msg="At least 4 samples are required.")
    # Take the Fisher transformation.
    loc = np.arctanh(rho)
    _LOG.debug("Fisher transformation of correlation `rho` equals %.5f" % loc)
    # Set the degrees of freedom assuming unknown mean.
    nu = n_samples - 1
    dof = nu - 2
    _LOG.debug("Degrees of freedom (assuming unknown mean) equals %d" % dof)
    scale = 1 / np.sqrt(dof)
    _LOG.debug(
        "Standard deviation of transformed correlation distribution is %.5f"
        % scale
    )
    # Compute the density.
    x_vals = np.linspace(
        sp.stats.norm.ppf(grid_size, loc=loc, scale=scale),
        sp.stats.norm.ppf(1 - grid_size, loc=loc, scale=scale),
        int(np.ceil(1 / grid_size)),
    )
    c1 = np.sqrt((nu - 2) / (2 * np.pi))
    vals = [
        c1
        * (1 / (1 - x**2))
        * np.exp(
            ((2 - nu) / 8)
            * (np.log((1 + x) * (1 - rho) / ((1 - x) * (1 + rho)))) ** 2
        )
        for x in np.tanh(x_vals)
    ]
    # Undo the transformation.
    confidence_density = pd.Series(
        vals, index=np.tanh(x_vals), name="confidence_density"
    )
    return confidence_density
