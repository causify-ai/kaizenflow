"""
Import as:

import core.finance.target_position_generation as cftapoge
"""

import logging
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

import core.signal_processing as sigproc
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(Paul): Consider changing the config to a list of kwargs.
def compute_target_positions_cross_sectionally(
    prediction: pd.DataFrame,
    volatility: pd.DataFrame,
    *,
    bulk_frac_to_remove: float = 0.0,
    bulk_fill_method: str = "zero",
    target_gmv: Union[float, pd.Series] = 1e6,
    volatility_lower_bound: float = 1e-5,
) -> pd.DataFrame:
    """
    Compute target dollar positions based on forecasts, basic constraints.

    :param prediction: dataframe of (t + 1, t + 2] returns forecasts
    :param volatility: dataframe of volatility forecasts
    :param bulk_frac_to_remove: applied to predictions, as in
        `csigproc.gaussian_rank()`
    :param bulk_fill_method: applied to predictions, as in
        `csigproc.gaussian_rank()`
    :param target_gmv: a float (constant target GMV) or else a
        `datetime.time` indexed `pd.Series` of GMVs (e.g., to simulate
        intraday ramp-up/ramp-down
    :param volatility_lower_bound: threshold for volatility clipping
    :return: dataframe of t + 1 target positions
    """
    # TODO(Paul): Some callers compute at a single time step with an
    # integer-indexed dataframe. Either update the callers to use a timestamp
    # or relax constraints uniformly in this file.
    # hpandas.dassert_time_indexed_df(
    #     prediction, allow_empty=True, strictly_increasing=True
    # )
    # hpandas.dassert_time_indexed_df(
    #     volatility, allow_empty=True, strictly_increasing=True
    # )
    hpandas.dassert_axes_equal(prediction, volatility)
    if prediction.columns.size > 1:
        gaussian_ranked = sigproc.gaussian_rank(
            prediction,
            bulk_frac_to_remove=bulk_frac_to_remove,
            bulk_fill_method=bulk_fill_method,
        )
    else:
        _LOG.warning(
            "Predictions provided for one asset; skipping Gaussian ranking."
        )
        gaussian_ranked = prediction
    _LOG.debug(
        "gaussian_ranked=\n%s",
        hpandas.df_to_str(gaussian_ranked, num_rows=10),
    )
    target_position_signs = np.sign(gaussian_ranked)
    _LOG.debug(
        "target_position_signs=\n%s",
        hpandas.df_to_str(target_position_signs, num_rows=10),
    )
    _LOG.debug(
        "position count=\n%s",
        hpandas.df_to_str(target_position_signs.abs().sum(axis=1)),
    )
    _LOG.debug(
        "position sign imbalance=\n%s",
        hpandas.df_to_str(target_position_signs.sum(axis=1)),
    )
    volatility = volatility.clip(lower=volatility_lower_bound)
    target_positions = target_position_signs.divide(volatility**2)
    _LOG.debug(
        "target_positions prior to gmv scaling=\n%s",
        hpandas.df_to_str(target_positions, num_rows=10),
    )
    target_positions = _apply_gmv_scaling(target_positions, target_gmv)
    _LOG.debug(
        "gmv-scaled target_positions=\n%s",
        hpandas.df_to_str(target_positions, num_rows=10),
    )
    hdbg.dassert_isinstance(target_positions, pd.DataFrame)
    return target_positions


# TODO(Paul): Rename with cross-sectional.
def _apply_gmv_scaling(
    target_positions: pd.DataFrame,
    target_gmv: Union[float, pd.Series],
) -> pd.DataFrame:
    l1_norm = target_positions.abs().sum(axis=1, min_count=1)
    if isinstance(target_gmv, float):
        hdbg.dassert_lt(0, target_gmv)
        scale_factors = l1_norm / target_gmv
    elif isinstance(target_gmv, pd.Series):
        hdbg.dassert_lte(0, target_gmv.min())
        # TODO(Paul): Perform an index comparison.
        scale_factors = l1_norm.divide(target_gmv, axis=0).replace(
            [-np.inf, np.inf], 0.0
        )
    else:
        raise ValueError("`target_gmv` type=%s not supported", type(target_gmv))
    _LOG.debug("`scale_factors`=\n%s", hpandas.df_to_str(scale_factors))
    target_positions = target_positions.divide(scale_factors, axis=0).replace(
        [-np.inf, np.inf], 0.0
    )
    return target_positions


def compute_target_positions_longitudinally(
    prediction: pd.DataFrame,
    volatility: pd.DataFrame,
    *,
    prediction_abs_threshold: float = 0.0,
    volatility_to_spread_threshold: float = 0.0,
    volatility_lower_bound: float = 1e-4,
    gamma: float = 0.0,
    fill_method: str = "zero",
    target_dollar_risk_per_name: float = 1e2,
    spread_lower_bound: float = 1e-4,
    spread: Optional[pd.DataFrame] = None,
    modulate_using_prediction_magnitude: bool = False,
    constant_decorrelation_coefficient: float = 0.0,
) -> pd.DataFrame:
    """
    Compute target dollar positions based on forecasts, basic constraints.

    :param prediction: dataframe of (t + 1, t + 2] returns forecasts
    :param volatility: dataframe of volatility forecasts
    :param prediction_abs_threshold: threshold below which predictions are
        interpreted as a flat signal
    :param volatility_to_spread_threshold: threshold below which predictions
        are interpreted as a flat signal
    :param volatility_lower_bound: threshold for volatility clipping
    :param gamma: prediction.abs() * vol_to_spread threshold; larger is more
        relaxed
    :param fill_method: forward fill to apply to predictions after masking
    :param target_dollar_risk_per_name: target dollar risk to have on a
        name (not a target notional)
    :param spread_lower_bound: minimum allowable spread estimate
    :param spread: optional dataframe of spread forecasts; if `None`, then
        impute `spread_lower_bound`.
    :param modulate_using_prediction_magnitude: if `False`, using only the
        sign of the prediction (after any thresholding) and volatility for
        determining position size; if `True`, perform a final multiplication
        by the position magnitude.
    :param constant_decorrelation_coefficient: must be >=0. If equal to zero,
        this is a no-op; if greater than zero, preprocess predictions by
        decorrelating under the assumption of constant correlation.
    """
    # TODO(Paul): Some callers compute at a single time step with an
    #  integer-indexed dataframe. Either update the callers to use a timestamp
    #  or relax constraints uniformly in this file.
    # hpandas.dassert_time_indexed_df(
    #     prediction, allow_empty=True, strictly_increasing=True
    # )
    # hpandas.dassert_time_indexed_df(
    #     volatility, allow_empty=True, strictly_increasing=True
    # )
    hpandas.dassert_axes_equal(prediction, volatility)
    #
    dassert_is_nonnegative_float(prediction_abs_threshold)
    dassert_is_nonnegative_float(volatility_to_spread_threshold)
    dassert_is_nonnegative_float(volatility_lower_bound)
    dassert_is_nonnegative_float(gamma)
    dassert_is_nonnegative_float(target_dollar_risk_per_name)
    dassert_is_nonnegative_float(spread_lower_bound)
    dassert_is_nonnegative_float(constant_decorrelation_coefficient)
    # Initialize spread.
    if spread is None:
        _LOG.info(
            "spread is `None`; imputing spread_lower_bound=%f", spread_lower_bound
        )
        spread = pd.DataFrame(
            spread_lower_bound, prediction.index, prediction.columns
        )
    hpandas.dassert_axes_equal(prediction, spread)
    spread = spread.clip(lower=spread_lower_bound)
    _LOG.debug(
        "spread=\n%s",
        hpandas.df_to_str(spread),
    )
    #
    idx = prediction.index
    prediction = prediction.dropna(how="all")
    if constant_decorrelation_coefficient > 0:
        prediction = sigproc.decorrelate_constant_correlation_df_rows(
            prediction,
            constant_decorrelation_coefficient,
        )
        _LOG.debug(
            "decorrelated predictions=\n%s",
            hpandas.df_to_str(prediction),
        )
    non_nan_idx = prediction.index
    volatility_to_spread = volatility.divide(spread)
    _LOG.debug(
        "volatility_to_spread=\n%s",
        hpandas.df_to_str(volatility_to_spread),
    )
    pred_term = (prediction.abs() - prediction_abs_threshold).clip(lower=0.0)
    vol_to_spread_term = (
        volatility_to_spread - volatility_to_spread_threshold
    ).clip(lower=0.0)
    mask = pred_term.multiply(vol_to_spread_term) <= gamma
    prediction = prediction[~mask]
    prediction = prediction.reindex(index=non_nan_idx)
    # TODO(Paul): This can arise if nothing is masked out. Revisit and test.
    # if not prediction[mask].isnull().all().all():
    #     prediction[mask] = 0.0
    if fill_method == "nan":
        pass
    elif fill_method == "zero":
        prediction = prediction.fillna(0.0)
    elif fill_method == "ffill":
        prediction = prediction.ffill()
    else:
        raise ValueError("Unrecognized `fill_method`=%s" % fill_method)
    # Add back the all-NaN rows.
    prediction = prediction.reindex(index=idx)
    #
    _LOG.debug(
        "prediction=\n%s",
        hpandas.df_to_str(prediction),
    )
    #
    target_position_signs = np.sign(prediction)
    _LOG.debug(
        "target_position_signs=\n%s",
        hpandas.df_to_str(target_position_signs),
    )
    _LOG.debug(
        "position count=\n%s",
        hpandas.df_to_str(target_position_signs.abs().sum(axis=1)),
    )
    _LOG.debug(
        "position sign imbalance=\n%s",
        hpandas.df_to_str(target_position_signs.sum(axis=1)),
    )
    #
    volatility = volatility.clip(lower=volatility_lower_bound)
    target_capital = target_dollar_risk_per_name / volatility
    _LOG.debug(
        "target_capital=\n%s",
        hpandas.df_to_str(target_capital),
    )
    target_positions = target_position_signs.multiply(target_capital)
    if modulate_using_prediction_magnitude:
        target_positions = target_positions.multiply(prediction.abs())
    _LOG.debug("target_positions=\n%s", hpandas.df_to_str(target_positions))
    #
    hdbg.dassert_isinstance(target_positions, pd.DataFrame)
    return target_positions


def dassert_is_nonnegative_float(val: Any) -> None:
    hdbg.dassert_isinstance(val, float)
    hdbg.dassert_lte(0.0, val)
