"""
Import as:

import dataflow.core.nodes.regression_models as dtfcnoremo
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import core.signal_processing as csigproc
import core.statistics as costatis
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Linear regression.
# #############################################################################


class LinearRegression(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    Fit and predict a linear regression model.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        x_vars: dtfcorutil.NodeColumnList,
        y_vars: dtfcorutil.NodeColumnList,
        steps_ahead: int,
        smoothing: float = 0,
        p_val_threshold: float = 1,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
        sample_weight_col: Optional[dtfcorutil.NodeColumnList] = None,
        feature_weights: Optional[List[float]] = None,
    ) -> None:
        super().__init__(nid)
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._fit_coefficients = None
        self._steps_ahead = steps_ahead
        self._smoothing = smoothing
        hdbg.dassert_lte(0, self._smoothing)
        self._p_val_threshold = p_val_threshold
        hdbg.dassert_lte(0, self._p_val_threshold)
        hdbg.dassert_lte(self._p_val_threshold, 1.0)
        hdbg.dassert_lte(
            0, self._steps_ahead, "Non-causal prediction attempted! Aborting..."
        )
        self._col_mode = col_mode or "replace_all"
        hdbg.dassert_in(self._col_mode, ["replace_all", "merge_all"])
        self._nan_mode = nan_mode or "raise"
        self._sample_weight_col = sample_weight_col
        if feature_weights is not None:
            hdbg.dassert_eq(len(feature_weights), len(x_vars))
            self._feature_weights = pd.Series(
                data=feature_weights, index=x_vars, name="feature_weights"
            )
        else:
            self._feature_weights = None

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_fit_coefficients": self._fit_coefficients,
            "_info['fit']": self._info["fit"],
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._fit_coefficients = fit_state["_fit_coefficients"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _fit_predict_helper(
        self, df_in: pd.DataFrame, fit: bool = True
    ) -> Dict[str, pd.DataFrame]:
        # Materialize names of x and y vars.
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        sample_weight_col = self._sample_weight_col
        # Package the sample weight column together with the x variables iff
        # `fit()` is called and a `sample_weight_col` that is not `None` is
        # provided.
        if fit and self._sample_weight_col is not None:
            x_vars_and_maybe_weight = x_vars + [self._sample_weight_col]
        else:
            x_vars_and_maybe_weight = x_vars
            sample_weight_col = None
        # Get x and forward y df.
        if fit:
            # NOTE: This df has no NaNs.
            df = dtfcorutil.get_x_and_forward_y_fit_df(
                df_in, x_vars_and_maybe_weight, y_vars, self._steps_ahead
            )
        else:
            # NOTE: This df has no `x_vars` NaNs.
            df = dtfcorutil.get_x_and_forward_y_predict_df(
                df_in, x_vars_and_maybe_weight, y_vars, self._steps_ahead
            )
        #
        # Handle presence of NaNs according to `nan_mode`.
        idx = df_in.index[: -self._steps_ahead] if fit else df_in.index
        self._handle_nans(idx, df.index)
        # Get the name of the forward y column.
        forward_y_cols = df.drop(
            x_vars_and_maybe_weight, axis=1
        ).columns.to_list()
        hdbg.dassert_eq(1, len(forward_y_cols))
        forward_y_col = forward_y_cols[0]
        # Regress `forward_y_col` on `x_vars` using `sample_weight_col` weights.
        # This performs one 1-variable regression per x variable.
        coefficients = costatis.compute_regression_coefficients(
            df, x_vars, forward_y_col, sample_weight_col=sample_weight_col,
        )
        if fit:
            self._fit_coefficients = coefficients.copy()
            # Initialize weights with `beta` values from regression.
            weights = self._fit_coefficients["beta"].copy()
            # Apply p-value thresholding.
            p_vals = self._fit_coefficients["p_val_2s"]
            weights[p_vals > self._p_val_threshold] = 0
            # Apply smoothing.
            smoothing = 1 / self._fit_coefficients["turn"] ** self._smoothing
            beta_norm = np.linalg.norm(weights)
            weights = beta_norm * csigproc.normalize(weights * smoothing)
            #
            self._fit_coefficients["weight"] = weights
            self._fit_coefficients["norm_weight"] = csigproc.normalize(weights)
            #
            hdbg.dassert(
                self._fit_coefficients is not None,
                "Model not found! Check if `fit()` has been run.",
            )
        # Generate predictions.
        # If the caller supplied `feature_weights`, use those for prediction.
        # Otherwise, use the learned weights.
        if self._feature_weights is not None:
            feature_weights = self._feature_weights
        else:
            feature_weights = self._fit_coefficients["weight"]
        forward_y_hat = df[x_vars].multiply(feature_weights).sum(axis=1)
        forward_y_hat_col = f"{forward_y_col}_hat"
        forward_y_hat = forward_y_hat.rename(forward_y_hat_col)
        # Populate `info`.
        info = collections.OrderedDict()
        info["fit_coefficients"] = self._fit_coefficients
        if not fit:
            info["predict_coefficients"] = coefficients
        df_out = df[[forward_y_col]].merge(
            forward_y_hat, how="outer", left_index=True, right_index=True
        )
        # Compute coefficients of forward y against its prediction.
        # NOTE: This does not use the sample weights.
        hat_coefficients = costatis.compute_regression_coefficients(
            df_out, [forward_y_hat_col], forward_y_col
        )
        info["hat_coefficients"] = hat_coefficients
        #
        df_out = df_out.reindex(idx)
        df_out = self._apply_col_mode(
            df_in,
            df_out,
            cols=y_vars,
            col_mode=self._col_mode,
        )
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        mode = "fit" if fit else "predict"
        self._set_info(mode, info)
        return {"df_out": df_out}

    def _handle_nans(
        self, idx: pd.DataFrame.index, non_nan_idx: pd.DataFrame.index
    ) -> None:
        if self._nan_mode == "raise":
            if idx.shape[0] != non_nan_idx.shape[0]:
                nan_idx = idx.difference(non_nan_idx)
                raise ValueError(f"NaNs detected at {nan_idx}")
        elif self._nan_mode == "drop":
            pass
        else:
            raise ValueError(f"Unrecognized nan_mode `{self._nan_mode}`")


# #############################################################################
# Multi-index linear regression.
# #############################################################################


class MultiindexLinearRegression(dtfconobas.FitPredictNode):
    """
    Fit and predict multiple linear regression models.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        x_vars: List[dtfcorutil.NodeColumn],
        y_vars: List[dtfcorutil.NodeColumn],
        steps_ahead: int,
        smoothing: float = 0.0,
        p_val_threshold: float = 1.0,
        nan_mode: Optional[str] = None,
        sample_weight_col: Optional[dtfcorutil.NodeColumnList] = None,
        feature_weights: Optional[List[float]] = None,
    ) -> None:
        """
        Params not listed are as in `ContinuousSkLearnModel`.

        :param in_col_groups: list of tuples, each having length
            `df_in.columns.nlevels - 1`. Leaf values become keys (e.g., they
            may be symbols), and the next-to-leaf level provides column names
            of the dataframe with the `x_vars` and `y_vars`.
        :param out_col_group: column level prefix of length
            `df_in.columns.nlevels - 2`. It may be an empty tuple.
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(in_col_groups, list)
        self._in_col_groups = in_col_groups
        self._out_col_group = out_col_group
        #
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._steps_ahead = steps_ahead
        self._smoothing = smoothing
        self._p_val_threshold = p_val_threshold
        self._nan_mode = nan_mode
        self._sample_weight_col = sample_weight_col
        self._feature_weights = feature_weights
        #
        self._key_fit_state: Dict[str, Any] = {}

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_key_fit_state": self._key_fit_state,
            "_info['fit']": self._info["fit"],
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._key_fit_state = fit_state["_key_fit_state"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _fit_predict_helper(
        self, df_in: pd.DataFrame, fit: bool
    ) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        dfs = dtfconobas.GroupedColDfToDfColProcessor.preprocess(
            df_in, self._in_col_groups
        )
        results = {}
        info = collections.OrderedDict()
        for key, df in dfs.items():
            lr = LinearRegression(
                "linear_regression",
                x_vars=self._x_vars,
                y_vars=self._y_vars,
                steps_ahead=self._steps_ahead,
                smoothing=self._smoothing,
                p_val_threshold=self._p_val_threshold,
                col_mode="replace_all",
                nan_mode=self._nan_mode,
                sample_weight_col=self._sample_weight_col,
                feature_weights=self._feature_weights,
            )
            if fit:
                df_out = lr.fit(df)["df_out"]
                info_out = lr.get_info("fit")
                self._key_fit_state[key] = lr.get_fit_state()
            else:
                hdbg.dassert_in(key, self._key_fit_state)
                lr.set_fit_state(self._key_fit_state[key])
                df_out = lr.predict(df)["df_out"]
                info_out = lr.get_info("predict")
            results[key] = df_out
            info[key] = info_out
        df_out = dtfconobas.GroupedColDfToDfColProcessor.postprocess(
            results, self._out_col_group
        )
        df_out = df_out.reindex(df_in.index)
        df_out = dtfcorutil.merge_dataframes(df_in, df_out)
        method = "fit" if fit else "predict"
        self._set_info(method, info)
        return {"df_out": df_out}
