"""
Import as:

import dataflow.core.nodes.sklearn_models as dtfcnoskmo
"""

import collections
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import numpy as np
import pandas as pd
import sklearn as sklear

import core.data_adapters as cdatadap
import core.finance as cofinanc
import core.statistics as costatis
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# #############################################################################
# sklearn - supervised prediction models
# #############################################################################


class ContinuousSkLearnModel(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    Fit and predict an sklearn model.
    """

    # pylint: disable=too-many-ancestors

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        model_func: Callable[..., Any],
        x_vars: dtfcorutil.NodeColumnList,
        y_vars: dtfcorutil.NodeColumnList,
        steps_ahead: int,
        model_kwargs: Optional[Any] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
        sample_weight_col: Optional[dtfcorutil.NodeColumnList] = None,
    ) -> None:
        """
        Specify the data and sklearn modeling parameters.

        :param nid: unique node id
        :param model_func: an sklearn model
        :param x_vars: indexed by knowledge datetimes
            - `x_vars` may contain lags of `y_vars`
        :param y_vars: indexed by knowledge datetimes
            - e.g., in the case of returns, this would correspond to `ret_0`
        :param steps_ahead: number of steps ahead for which a prediction is
            to be generated. E.g.,
            - if `steps_ahead == 0`, then the predictions are
              are contemporaneous with the observed response (and hence
              inactionable)
            - if `steps_ahead == 1`, then the model attempts to predict
              `y_vars` for the next time step
            - The model is only trained to predict the target
              `steps_ahead` steps ahead (and not all intermediate steps)
        :param model_kwargs: parameters to forward to the sklearn model
            (e.g., regularization constants)
        :param col_mode: "merge_all" or "replace_all", as in
            `ColumnTransformer()`
        :param nan_mode: "drop" or "raise"
        :param sample_weight_col: column of relative weights to apply in `fit()`
        """
        super().__init__(nid)
        self._model_func = model_func
        self._model_kwargs = model_kwargs or {}
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._model: Optional[sklear.base.BaseEstimator] = None
        self._steps_ahead = steps_ahead
        hdbg.dassert_lte(
            0, self._steps_ahead, "Non-causal prediction attempted! Aborting..."
        )
        # NOTE: Set to "replace_all" for backward compatibility.
        self._col_mode = col_mode or "replace_all"
        hdbg.dassert_in(self._col_mode, ["replace_all", "merge_all"])
        self._nan_mode = nan_mode or "raise"
        self._sample_weight_col = sample_weight_col

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {"_model": self._model, "_info['fit']": self._info["fit"]}
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._model = fit_state["_model"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _fit_predict_helper(
        self, df_in: pd.DataFrame, fit: bool
    ) -> Dict[str, pd.DataFrame]:
        # Materialize names of x and y vars.
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        if fit and self._sample_weight_col is not None:
            sample_weight_col = dtfcorutil.convert_to_list(
                self._sample_weight_col
            )
            hdbg.dassert_eq(len(sample_weight_col), 1)
            x_vars_and_maybe_weight = x_vars + sample_weight_col
        else:
            x_vars_and_maybe_weight = x_vars
            sample_weight_col = None
        # Get x and forward y df.
        if fit:
            # This df has no NaNs.
            df = dtfcorutil.get_x_and_forward_y_fit_df(
                df_in, x_vars_and_maybe_weight, y_vars, self._steps_ahead
            )
        else:
            # This df has no `x_vars` NaNs.
            df = dtfcorutil.get_x_and_forward_y_predict_df(
                df_in, x_vars_and_maybe_weight, y_vars, self._steps_ahead
            )
        # Handle presence of NaNs according to `nan_mode`.
        idx = df_in.index[: -self._steps_ahead] if fit else df_in.index
        self._handle_nans(idx, df.index)
        # Isolate the forward y piece of `df`.
        forward_y_cols = df.drop(
            x_vars_and_maybe_weight, axis=1
        ).columns.to_list()
        forward_y_df = df[forward_y_cols]
        # Prepare x_vars in sklearn format.
        x_vals = cdatadap.transform_to_sklearn(df, x_vars)
        if fit:
            if sample_weight_col:
                # TODO(Paul): The `flatten()` is necessary here (but we do not
                # need it for the x or y vars). Consider updating
                # `transform_to_sklearn()` to handle this internally.
                sample_weights = cdatadap.transform_to_sklearn(
                    df, sample_weight_col
                ).flatten()
            else:
                sample_weights = None
            # Prepare forward y_vars in sklearn format.
            forward_y_fit = cdatadap.transform_to_sklearn(df, forward_y_cols)
            # Define and fit model.
            self._model = self._model_func(**self._model_kwargs)
            self._model = self._model.fit(
                x_vals, forward_y_fit, sample_weight=sample_weights
            )
        hdbg.dassert(
            self._model, "Model not found! Check if `fit()` has been run."
        )
        self._model = cast(sklear.base.BaseEstimator, self._model)
        # Generate predictions.
        forward_y_hat = self._model.predict(x_vals)
        # Generate dataframe from sklearn predictions.
        forward_y_hat_vars = [f"{y}_hat" for y in forward_y_cols]
        forward_y_hat = cdatadap.transform_from_sklearn(
            df.index, forward_y_hat_vars, forward_y_hat
        )
        score_idx = forward_y_df.index if fit else forward_y_df.dropna().index
        info = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        info["model_params"] = self._model.get_params()
        model_attribute_info = collections.OrderedDict()
        for k, v in vars(self._model).items():
            model_attribute_info[k] = v
        info["model_attributes"] = model_attribute_info
        info["model_score"] = self._score(
            forward_y_df.loc[score_idx],
            forward_y_hat.loc[score_idx],
        )
        df_out = forward_y_df.merge(
            forward_y_hat, how="outer", left_index=True, right_index=True
        )
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

    def _score(
        self,
        y_true: Union[pd.Series, pd.DataFrame],
        y_pred: Union[pd.Series, pd.DataFrame],
    ) -> Optional[float]:
        """
        Compute accuracy for classification or R^2 score for regression.
        """
        if sklear.base.is_classifier(self._model):
            metric = sklear.metrics.accuracy_score
        elif sklear.base.is_regressor(self._model):
            metric = sklear.metrics.r2_score
        else:
            return None
        # In `predict()` method, `y_pred` may exist for index where `y_true`
        # is already `NaN`.
        y_true = y_true.loc[: y_true.last_valid_index()]
        res = metric(y_true, y_pred.loc[y_true.index])
        return cast(float, res)


class MultiindexPooledSkLearnModel(dtfconobas.FitPredictNode):
    """
    Fit and predict multiple sklearn models.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        model_func: Callable[..., Any],
        x_vars: List[dtfcorutil.NodeColumn],
        y_vars: List[dtfcorutil.NodeColumn],
        steps_ahead: int,
        model_kwargs: Optional[Any] = None,
        nan_mode: Optional[str] = None,
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
        self._model_func = model_func
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._steps_ahead = steps_ahead
        self._model_kwargs = model_kwargs
        self._nan_mode = nan_mode
        #
        self._key_fit_state: Dict[str, Any] = {}

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_fit_state": self._fit_state,
            "_info['fit']": self._info["fit"],
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._fit_state = fit_state["_fit_state"]
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
        if fit:
            # TODO(Paul): compute the shifts first, then stack.
            for key, value in dfs.items():
                dfs[key] = dtfcorutil.get_x_and_forward_y_fit_df(
                    value, self._x_vars, self._y_vars, self._steps_ahead
                )
            stacked_df = dtfconobas.DfStacker.preprocess(dfs)
            forward_y_fit_cols = stacked_df.drop(
                columns=self._x_vars
            ).columns.to_list()
            sklm = SkLearnModel(
                "sklearn",
                model_func=self._model_func,
                x_vars=self._x_vars,
                y_vars=forward_y_fit_cols,
                model_kwargs=self._model_kwargs,
                col_mode="merge_all",
            )
            df_out = sklm.fit(stacked_df)["df_out"].drop(columns=self._x_vars)
            results = dtfconobas.DfStacker.postprocess(dfs, df_out)
            info = sklm.get_info("fit")
            self._fit_state = sklm.get_fit_state()
        else:
            csklm = ContinuousSkLearnModel(
                "sklearn",
                model_func=self._model_func,
                x_vars=self._x_vars,
                y_vars=self._y_vars,
                steps_ahead=self._steps_ahead,
                model_kwargs=self._model_kwargs,
                col_mode="replace_all",
                nan_mode=self._nan_mode,
            )
            # NOTE: we train with one type of sklearn node, predict with
            #     another
            csklm.set_fit_state(self._fit_state)
            for key, df in dfs.items():
                df_out = csklm.predict(df)["df_out"]
                info_out = csklm.get_info("predict")
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


class MultiindexSkLearnModel(dtfconobas.FitPredictNode):
    """
    Fit and predict multiple sklearn models.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        model_func: Callable[..., Any],
        x_vars: List[dtfcorutil.NodeColumn],
        y_vars: List[dtfcorutil.NodeColumn],
        steps_ahead: int,
        model_kwargs: Optional[Any] = None,
        nan_mode: Optional[str] = None,
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
        self._model_func = model_func
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._steps_ahead = steps_ahead
        self._model_kwargs = model_kwargs
        self._nan_mode = nan_mode
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
            csklm = ContinuousSkLearnModel(
                "sklearn",
                model_func=self._model_func,
                x_vars=self._x_vars,
                y_vars=self._y_vars,
                steps_ahead=self._steps_ahead,
                model_kwargs=self._model_kwargs,
                col_mode="replace_all",
                nan_mode=self._nan_mode,
            )
            if fit:
                df_drop_na = hpandas.dropna(df, how="all")
                if df_drop_na.empty:
                    # TODO(Grisha): come up with a better mechanism to handle
                    # empty data, maybe the fix should go to `ContinuousSkLearnModel`.
                    # Do not fit on NaN data.
                    _LOG.warning(
                        "No data found for key=%s, skipping the fit stage", key
                    )
                    continue
                df_out = csklm.fit(df)["df_out"]
                info_out = csklm.get_info("fit")
                self._key_fit_state[key] = csklm.get_fit_state()
            else:
                if key not in self._key_fit_state:
                    # TODO(Grisha): come up with a better mechanism to handle
                    # empty fit state, maybe the fix should go to `ContinuousSkLearnModel`.
                    _LOG.warning(
                        "No fit state found for key=%s, skipping the predict stage",
                        key,
                    )
                    continue
                csklm.set_fit_state(self._key_fit_state[key])
                df_out = csklm.predict(df)["df_out"]
                info_out = csklm.get_info("predict")
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


class SkLearnModel(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    Fit and predict an sklearn model.

    No NaN-handling or uniform sampling frequency requirement.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        x_vars: dtfcorutil.NodeColumnList,
        y_vars: dtfcorutil.NodeColumnList,
        model_func: Callable[..., Any],
        model_kwargs: Optional[Any] = None,
        col_mode: Optional[str] = None,
    ) -> None:
        super().__init__(nid)
        self._model_func = model_func
        self._model_kwargs = model_kwargs or {}
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._model: Optional[sklear.base.BaseEstimator] = None
        self._col_mode = col_mode or "replace_all"
        hdbg.dassert_in(self._col_mode, ["replace_all", "merge_all"])

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        SkLearnModel._validate_input_df(df_in)
        hdbg.dassert(
            df_in[df_in.isna().any(axis=1)].index.empty,
            "NaNs detected at index `%s`",
            str(df_in[df_in.isna().any(axis=1)].head().index),
        )
        df = df_in.copy()
        idx = df.index
        x_vars, x_fit, y_vars, y_fit = self._to_sklearn_format(df)
        self._model = self._model_func(**self._model_kwargs)
        self._model = self._model.fit(x_fit, y_fit)
        y_hat = self._model.predict(x_fit)
        #
        x_fit, y_fit, y_hat = self._from_sklearn_format(
            idx, x_vars, x_fit, y_vars, y_fit, y_hat
        )
        # TODO(Paul): Summarize model perf or make configurable.
        # TODO(Paul): Consider separating model eval from fit/predict.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        info["model_params"] = self._model.get_params()
        model_attribute_info = collections.OrderedDict()
        for k, v in vars(self._model).items():
            model_attribute_info[k] = v
        info["model_attributes"] = model_attribute_info
        # Return targets and predictions.
        y_hat = y_hat.reindex(idx)
        df_out = self._apply_col_mode(
            df, y_hat, cols=y_vars, col_mode=self._col_mode
        )
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        SkLearnModel._validate_input_df(df_in)
        df = df_in.copy()
        idx = df.index
        x_vars, x_predict, y_vars, y_predict = self._to_sklearn_format(df)
        hdbg.dassert_is_not(
            self._model, None, "Model not found! Check if `fit` has been run."
        )
        self._model = cast(sklear.base.BaseEstimator, self._model)
        y_hat = self._model.predict(x_predict)
        x_predict, y_predict, y_hat = self._from_sklearn_format(
            idx, x_vars, x_predict, y_vars, y_predict, y_hat
        )
        info = collections.OrderedDict()
        info["model_params"] = self._model.get_params()
        info["model_perf"] = self._model_perf(x_predict, y_predict, y_hat)
        # Return predictions.
        y_hat = y_hat.reindex(idx)
        df_out = self._apply_col_mode(
            df, y_hat, cols=y_vars, col_mode=self._col_mode
        )
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        return {"df_out": df_out}

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {"_model": self._model, "_info['fit']": self._info["fit"]}
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._model = fit_state["_model"]
        self._info["fit"] = fit_state["_info['fit']"]

    @staticmethod
    def _validate_input_df(df: pd.DataFrame) -> None:
        """
        Assert if df violates constraints, otherwise return `None`.
        """
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert_no_duplicates(df.columns)

    # TODO(Paul): Add type hints.
    @staticmethod
    def _model_perf(
        x: pd.DataFrame, y: pd.DataFrame, y_hat: pd.DataFrame
    ) -> collections.OrderedDict:
        _ = x
        info = collections.OrderedDict()
        # info["hitrate"] = pip._compute_model_hitrate(self.model, x, y)
        pnl_rets = y.multiply(y_hat.rename(columns=lambda x: x.strip("_hat")))
        info["pnl_rets"] = pnl_rets
        info["sr"] = costatis.compute_sharpe_ratio(
            cofinanc.resample(pnl_rets, rule="1B").sum(), time_scaling=252
        )
        return info

    @staticmethod
    def _from_sklearn_format(
        idx: pd.Index,
        x_vars: List[dtfcorutil.NodeColumn],
        x_vals: np.ndarray,
        y_vars: List[dtfcorutil.NodeColumn],
        y_vals: np.ndarray,
        y_hat: np.ndarray,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        x = cdatadap.transform_from_sklearn(idx, x_vars, x_vals)
        y = cdatadap.transform_from_sklearn(idx, y_vars, y_vals)
        y_h = cdatadap.transform_from_sklearn(
            idx, [f"{y}_hat" for y in y_vars], y_hat
        )
        return x, y, y_h

    def _to_sklearn_format(
        self, df: pd.DataFrame
    ) -> Tuple[
        List[dtfcorutil.NodeColumn],
        np.ndarray,
        List[dtfcorutil.NodeColumn],
        np.ndarray,
    ]:
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        x_vals, y_vals = cdatadap.transform_to_sklearn_old(df, x_vars, y_vars)
        return x_vars, x_vals, y_vars, y_vals
