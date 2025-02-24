"""
Import as:

import core.signal_processing.incremental_pca as csprinpc
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import core.signal_processing.special_functions as csprspfu
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_ipca(
    df: pd.DataFrame,
    num_pc: int,
    tau: float,
) -> Tuple[pd.DataFrame, List[pd.DataFrame]]:
    """
    Incremental PCA.

    The dataframe should already be centered.

    https://ieeexplore.ieee.org/document/1217609
    https://www.cse.msu.edu/~weng/research/CCIPCApami.pdf

    :param num_pc: number of principal components to calculate
    :param tau: parameter used in (continuous) compute_ema and compute_ema-derived kernels. For
        typical ranges it is approximately but not exactly equal to the
        center-of-mass (com) associated with an compute_ema kernel.
    :return:
      - df of eigenvalue series (col 0 correspond to max eigenvalue, etc.).
      - list of dfs of unit eigenvectors (0 indexes df eigenvectors
        corresponding to max eigenvalue, etc.).
    """
    hdbg.dassert_isinstance(
        num_pc, int, msg="Specify an integral number of principal components."
    )
    hdbg.dassert_lt(
        num_pc,
        df.shape[0],
        msg="Number of time steps should exceed number of principal components.",
    )
    hdbg.dassert_lte(
        num_pc,
        df.shape[1],
        msg="Dimension should be greater than or equal to the number of principal components.",
    )
    hdbg.dassert_lt(0, tau)
    com = csprspfu.calculate_com_from_tau(tau)
    alpha = 1.0 / (com + 1.0)
    _LOG.debug("com = %0.2f", com)
    _LOG.debug("alpha = %0.2f", alpha)
    # TODO(Paul): Consider requiring that the caller do this instead.
    # Fill NaNs with zero.
    df.fillna(0, inplace=True)
    lambdas: Dict[int, list] = {k: [] for k in range(num_pc)}
    # V's are eigenvectors with norm equal to corresponding eigenvalue.
    vs: Dict[int, list] = {k: [] for k in range(num_pc)}
    unit_eigenvecs: Dict[int, list] = {k: [] for k in range(num_pc)}
    step = 0
    for n in df.index:
        # Initialize u(n).
        u = df.loc[n].copy()
        for i in range(min(num_pc, step + 1)):
            # Initialize ith eigenvector.
            if i == step:
                v = u.copy()
                if np.linalg.norm(v):
                    _LOG.debug("Initializing eigenvector %s...", i)
                    step += 1
            else:
                # Main update step for eigenvector i.
                u, v = _compute_ipca_step(u, vs[i][-1], alpha)
            # Bookkeeping.
            v.name = n
            vs[i].append(v)
            norm = np.linalg.norm(v)
            lambdas[i].append(norm)
            unit_eigenvecs[i].append(v / norm)
    _LOG.debug("Completed %s steps of incremental PCA.", len(df))
    # Convert lambda dict of lists to list of series.
    # Convert unit_eigenvecs dict of lists to list of dataframes.
    lambdas_srs = []
    unit_eigenvec_dfs = []
    for i in range(num_pc):
        lambdas_srs.append(
            pd.Series(index=df.index[-len(lambdas[i]) :], data=lambdas[i])
        )
        unit_eigenvec_dfs.append(pd.concat(unit_eigenvecs[i], axis=1).transpose())
    lambda_df = pd.concat(lambdas_srs, axis=1)
    return lambda_df, unit_eigenvec_dfs


def _compute_ipca_step(
    u: pd.Series, v: pd.Series, alpha: float
) -> Tuple[pd.Series, pd.Series]:
    """
    Single step of incremental PCA.

    At each point, the norm of v is the eigenvalue estimate (for the component
    to which u and v refer).

    :param u: residualized observation for step n, component i
    :param v: unnormalized eigenvector estimate for step n - 1, component i
    :param alpha: compute_ema-type weight (choose in [0, 1] and typically < 0.5)

    :return: (u_next, v_next), where
      * u_next is residualized observation for step n, component i + 1
      * v_next is unnormalized eigenvector estimate for step n, component i
    """
    if np.linalg.norm(v) == 0:
        v_next = v * 0
        u_next = u.copy()
    else:
        v_next = (1 - alpha) * v + alpha * u * np.dot(u, v) / np.linalg.norm(v)
        u_next = u - np.dot(u, v) * v / (np.linalg.norm(v) ** 2)
    return u_next, v_next


def compute_unit_vector_angular_distance(df: pd.DataFrame) -> pd.Series:
    """
    Calculate the angular distance between unit vectors.

    Accepts a df of unit vectors (each row a unit vector) and returns a series
    of consecutive angular distances indexed according to the later time point.

    The angular distance lies in [0, 1].
    """
    vecs = df.values
    # If all of the vectors are unit vectors, then
    # np.diag(vecs.dot(vecs.T)) should return an array of all 1.'s.
    cos_sim = np.diag(vecs[:-1, :].dot(vecs[1:, :].T))
    ang_dist = np.arccos(cos_sim) / np.pi
    srs = pd.Series(index=df.index[1:], data=ang_dist, name="angular change")
    return srs


def compute_eigenvector_diffs(eigenvecs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Take a list of eigenvectors and return a df of angular distances.
    """
    ang_chg = []
    for i, vec in enumerate(eigenvecs):
        srs = compute_unit_vector_angular_distance(vec)
        srs.name = i
        ang_chg.append(srs)
    df = pd.concat(ang_chg, axis=1)
    return df
