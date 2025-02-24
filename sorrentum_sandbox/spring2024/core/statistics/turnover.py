"""
Import as:

import core.statistics.turnover as cstaturn
"""

import logging
from typing import Callable, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy as sp

import core.statistics.entropy as cstaentr
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_turnover_and_bias(
    volume: pd.Series,
    bias: pd.Series,
) -> pd.Series:
    """
    Computes turnover and bias in units of input.
    """
    hdbg.dassert_isinstance(volume, pd.Series)
    hdbg.dassert_lte(0, volume.min())
    hdbg.dassert_isinstance(bias, pd.Series)
    hdbg.dassert(volume.index.equals(bias.index))
    srs = pd.Series(
        {
            "turnover_mean": volume.mean(),
            "turnover_stdev": volume.std(),
            "market_bias_mean": bias.mean(),
            "market_bias_stdev": bias.std(),
        }
    )
    srs.name = "turnover_and_bias"
    return srs


def compute_turnover(
    pos: pd.Series, unit: Optional[str] = None, nan_mode: Optional[str] = None
) -> pd.Series:
    """
    Compute turnover for a sequence of positions.

    :param pos: sequence of positions
    :param unit: desired output unit (e.g. 'B', 'W', 'M', etc.)
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :return: turnover
    """
    hdbg.dassert_isinstance(pos, pd.Series)
    nan_mode = nan_mode or "drop"
    pos = hdatafr.apply_nan_mode(pos, mode=nan_mode)
    numerator = pos.diff().abs()
    denominator = (pos.abs() + pos.shift().abs()) / 2
    if unit:
        numerator = numerator.resample(
            rule=unit,
            closed="right",
            label="right",
        ).sum()
        denominator = denominator.resample(
            rule=unit,
            closed="right",
            label="right",
        ).sum()
    turnover = numerator / denominator
    # Raise if we upsample.
    if len(turnover) > len(pos):
        raise ValueError("Upsampling is not allowed.")
    return turnover


def compute_average_holding_period(
    pos: pd.Series, unit: Optional[str] = None, nan_mode: Optional[str] = None
) -> float:
    """
    Compute average holding period for a sequence of positions.

    :param pos: sequence of positions
    :param unit: desired output unit (e.g. 'B', 'W', 'M', etc.)
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :return: average holding period in specified units
    """
    unit = unit or "B"
    hdbg.dassert_isinstance(pos, pd.Series)
    # TODO(Paul): Determine how to deal with no `freq`.
    hdbg.dassert(pos.index.freq)
    pos_freq_in_year = hdatafr.infer_sampling_points_per_year(pos)
    unit_freq_in_year = hdatafr.infer_sampling_points_per_year(
        pos.resample(rule=unit, closed="right", label="right").sum()
    )
    hdbg.dassert_lte(
        unit_freq_in_year,
        pos_freq_in_year,
        msg=f"Upsampling pos freq={pd.infer_freq(pos.index)} to unit freq={unit} is not allowed",
    )
    nan_mode = nan_mode or "drop"
    pos = hdatafr.apply_nan_mode(pos, mode=nan_mode)
    unit_coef = unit_freq_in_year / pos_freq_in_year
    average_holding_period = (
        pos.abs().mean() / pos.diff().abs().mean()
    ) * unit_coef
    return average_holding_period


def compute_avg_turnover_and_holding_period(
    pos: pd.Series,
    unit: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute average turnover and holding period for a sequence of positions.

    :param pos: pandas series of positions
    :param unit: desired output holding period unit (e.g. 'B', 'W', 'M', etc.)
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: average turnover, holding period and index frequency
    """
    hdbg.dassert_isinstance(pos, pd.Series)
    hdbg.dassert(pos.index.freq)
    pos_freq = pos.index.freq
    unit = unit or pos_freq
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    result_index = [
        prefix + "avg_turnover_(%)",
        prefix + "turnover_frequency",
        prefix + "avg_holding_period",
        prefix + "holding_period_units",
    ]
    avg_holding_period = compute_average_holding_period(
        pos=pos, unit=unit, nan_mode=nan_mode
    )
    avg_turnover = 100 * (1 / avg_holding_period)
    #
    result_values = [avg_turnover, unit, avg_holding_period, unit]
    res = pd.Series(data=result_values, index=result_index, name=pos.name)
    return res


def apply_smoothing_parameters(
    rho: pd.Series, turn: pd.Series, parameters: List[float]
) -> pd.DataFrame:
    """
    Estimate smoothing effects.

    :param parameters: corresponds to (inverse) exponent of `turn`
    """
    rhos = []
    turns = []
    tsq = turn**2
    for param in parameters:
        rho_num = np.square(np.linalg.norm(tsq.pow(-1 * param / 4).multiply(rho)))
        # TODO(Paul): Cross-check.
        turn_num = np.linalg.norm(tsq.pow(0.5 - 2 * param / 4).multiply(rho))
        denom = np.linalg.norm(tsq.pow(-2 * param / 4).multiply(rho))
        rhos.append(rho_num / denom)
        turns.append(turn_num / denom)
    rho_srs = pd.Series(index=parameters, data=rhos, name="rho")
    rho_frac = (rho_srs / rho_srs.max()).rename("rho_frac")
    turn_srs = pd.Series(index=parameters, data=turns, name="turn")
    rho_to_turn = (rho_srs / turn_srs).rename("rho_to_turn")
    df = pd.concat([rho_srs, rho_frac, turn_srs, rho_to_turn], axis=1)
    return df


def compute_turn(df: pd.DataFrame) -> float:
    """
    Compute turnover from weighted components.

    :param df: dataframe with (signal) variance, turnover, and weight
        columns
    :return: turnover, normalized to lie in [-2, 2]
    """
    _df_has_var_turn(df)
    hdbg.dassert_in("weight", df.columns)
    # Signal variance.
    var = df["var"]
    # -2 <= turn <=2 (1.0 == 100%).
    turn_sq = np.square(df["turn"])
    # Signal weight.
    weight_sq = np.square(df["weight"])
    # Compute.
    numerator = weight_sq.dot(var * turn_sq)
    denominator = weight_sq.dot(var)
    return np.sqrt(numerator / denominator)


def maximize_weight_entropy(
    df: pd.DataFrame,
    turnover: float,
) -> pd.Series:
    """
    Generate maximum entropy weights targeting `turnover`.
    """
    return _optimize_weights(
        df,
        turnover,
        lambda x: -1 * cstaentr.compute_entropy(pd.Series(np.sqrt(x)), 1),
    )


def maximize_weight_sr(
    df: pd.DataFrame,
    turnover: float,
) -> pd.Series:
    """
    Generate weights maximizing SR targeting `turnover`.
    """
    _df_has_var_turn(df)
    vec = np.sqrt(df["var"])
    if "rho" in df.columns:
        rho = df["rho"]
        hdbg.dassert_lte(0, rho.min())
        vec = vec * rho
    return _optimize_weights(
        df,
        turnover,
        lambda x: -1 * np.sqrt(x).dot(vec.values),
    )


def _optimize_weights(
    df: pd.DataFrame,
    turnover: float,
    fun: Callable,
) -> pd.Series:
    _df_has_var_turn(df)
    # TODO(Paul): Consider allowing the user to pass in `x0`.
    # Initialize starting point and create orthant bounds.
    x0 = np.ones(df.shape[0])
    bounds = sp.optimize.Bounds(0, np.inf)
    # Generate subspace constraint.
    A_eq = _get_turnover_constraint_matrix(df)
    b_eq = pd.Series([np.square(turnover), 1]).values
    constraints = {"type": "eq", "fun": lambda x: A_eq @ x - b_eq}
    # Optimize.
    result = sp.optimize.minimize(
        fun=fun,
        x0=x0,
        bounds=bounds,
        constraints=constraints,
    )
    _LOG.debug("result=%s", result)
    hdbg.dassert(result["success"])
    optimum = np.sqrt(result["x"])
    # l1 normalize the weights and turn into a series.
    weights = pd.Series(
        optimum / np.linalg.norm(optimum, 1), df.index, name="weight"
    )
    # Ensure that all weights are nonnegative.
    hdbg.dassert_lte(0, weights.min())
    return weights


def get_isoturnover_affine_space(
    df: pd.DataFrame,
    turnover: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the isoturnover affine space in terms of squared weights.
    """
    _df_has_var_turn(df)
    mat = _get_turnover_constraint_matrix(df)
    # Generator projection matrix (onto the orthogonal complement).
    proj = mat.T @ np.linalg.inv(mat @ mat.T) @ mat
    b_vec = pd.Series([np.square(turnover), 1]).values
    x0 = np.linalg.pinv(mat).dot(b_vec)
    return proj, x0


# TODO(Paul): This does not take into account the scale invariance of
#  the weights (but should).
def compute_distance_to_isoturnover_plane(
    df: pd.DataFrame,
    turnover: float,
) -> float:
    """
    Compute distance of squared weights to isoturnover plane of squared
    weights.
    """
    hdbg.dassert_in("weight", df.columns)
    weight_sq = np.square(df["weight"])
    proj, x0 = get_isoturnover_affine_space(df, turnover)
    dist = np.linalg.norm(proj.dot(weight_sq.values - x0))
    return dist


# TODO(Paul): This does not take into account the scale invariance of
#  the weights (but should).
def project_onto_isoturnover_plane(
    df: pd.DataFrame,
    turnover: float,
) -> pd.Series:
    """
    Orthogonally project weights onto isoturnover plane in squared weight
    space.

    Raises if a projected (squared) component is negative.

    :return: l1-normalized weights (in original space)
    """
    hdbg.dassert_in("weight", df.columns)
    proj, x0 = get_isoturnover_affine_space(df, turnover)
    weight_sq = np.square(df["weight"])
    proj_vec = proj.dot(x0 - weight_sq.values) + weight_sq.values
    proj_vec_root = np.sqrt(proj_vec)
    weights = pd.Series(proj_vec_root, df.index, name="weight")
    return weights


def find_nearest_affine_point(
    df: pd.DataFrame,
    turnover: float,
) -> pd.DataFrame:
    """
    Find the point in isoturnover space closest to the squared weight line.
    """
    hdbg.dassert_in("weight", df.columns)
    weight_sq = np.square(df["weight"])
    proj, x0 = get_isoturnover_affine_space(df, turnover)
    # Find the scaling factor for `weight_sq` that minimizes its distance to
    # the affine space.
    lambda_ = (
        proj.dot(weight_sq.values).dot(proj.dot(x0))
        / np.linalg.norm(proj.dot(weight_sq.values)) ** 2
    )
    _LOG.debug("lambda_=%0.2f", lambda_)
    # Project the rescaled weights.
    df = df.copy()
    df["weight"] = np.sqrt(lambda_) * df["weight"]
    projection = project_onto_isoturnover_plane(df, turnover)
    # Normalize the project weights.
    normalized_weights = projection / np.linalg.norm(projection, 1)
    return normalized_weights


def _df_has_var_turn(df):
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_is_subset(["var", "turn"], df.columns)
    hdbg.dassert_lte(0, df["var"].min())
    hdbg.dassert_lte(-2, df["turn"].min())
    hdbg.dassert_lte(df["turn"].max(), 2)


def _get_turnover_constraint_matrix(df: pd.DataFrame) -> np.ndarray:
    _df_has_var_turn(df)
    row1 = df["var"] * np.square(df["turn"])
    row2 = df["var"]
    matrix = pd.concat([row1, row2], axis=1).T.values
    return matrix
