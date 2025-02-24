"""
Import as:

import dataflow.core.nodes.sarimax_models as dtfcnosamo
"""

import collections
import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.iolib as siolib
from tqdm.autonotebook import tqdm

import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# ContinuousSarimaxModel
# #############################################################################


class ContinuousSarimaxModel(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    A dataflow node for continuous SARIMAX model.

    This is a wrapper around statsmodels SARIMAX with the following
    modifications:
      - We predict `y_t`, ... , `y_{t+n}` using `x_{t-n}`, ..., `x_{t-1}`,
        where `n` is `steps_ahead`, whereas in the classic implementation it is
        predicted using`x_t`, ... , `x_{t+n}`
      - When making predictions in the `fit` method, we treat the input data as
        out-of-sample. This allows making n-step-ahead predictions on a subset
        of exogenous data.

    See
    https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_stata.html
    for SARIMAX model examples.
    """

    # pylint: disable=too-many-ancestors

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        y_vars: dtfcorutil.NodeColumnList,
        steps_ahead: int,
        init_kwargs: Optional[Dict[str, Any]] = None,
        fit_kwargs: Optional[Dict[str, Any]] = None,
        x_vars: Optional[dtfcorutil.NodeColumnList] = None,
        add_constant: bool = False,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
        disable_tqdm: bool = False,
    ) -> None:
        """
        Initialize node for SARIMAX model.

        :param nid: node identifier
        :param y_vars: names of y variables. Only univariate predictions are
            supported
        :param steps_ahead: number of prediction steps
        :param init_kwargs: kwargs for initializing `sm.tsa.statespace.SARIMAX`
        :param fit_kwargs: kwargs for `fit` method of
            `sm.tsa.statespace.SARIMAX`
        :param x_vars: names of x variables
        :param add_constant: whether to add constant to exogenous dataset,
            default `False`. Note that adding a constant and specifying
            `trend="c"` is not the same
        :param col_mode: "replace_all" or "merge_all"
        :param nan_mode: "raise", "drop" or "leave_unchanged"
        :param disable_tqdm: whether to disable tqdm progress bar
        """
        super().__init__(nid)
        self._y_vars = y_vars
        # Zero-step prediction is not supported for autoregressive models.
        hdbg.dassert_lte(
            1, steps_ahead, "Non-causal prediction attempted! Aborting..."
        )
        self._steps_ahead = steps_ahead
        self._init_kwargs = init_kwargs
        self._fit_kwargs = fit_kwargs or {"disp": False}
        self._x_vars = x_vars
        self._add_constant = add_constant
        self._model = None
        self._model_results = None
        self._col_mode = col_mode or "merge_all"
        hdbg.dassert_in(self._col_mode, ["replace_all", "merge_all"])
        self._nan_mode = nan_mode or "raise"
        self._disable_tqdm = disable_tqdm

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        df = df_in.copy()
        idx = df.index
        # Get intersection of non-NaN `y` and `x`.
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        y_fit = df[y_vars]
        if self._nan_mode == "leave_unchanged":
            non_nan_idx = idx
        else:
            non_nan_idx = df[y_vars].dropna().index
        if self._x_vars is not None:
            x_fit = self._get_bkwd_x_df(df).dropna()
            x_fit_non_nan_idx = x_fit.index
            x_idx_extension = x_fit_non_nan_idx[-self._steps_ahead :]
            non_nan_idx = non_nan_idx.append(x_idx_extension)
            non_nan_idx = non_nan_idx.intersection(x_fit_non_nan_idx)
            idx = idx[self._steps_ahead :].append(x_idx_extension)
        else:
            x_fit = None
        x_fit = self._add_constant_to_x(x_fit)
        hdbg.dassert(not non_nan_idx.empty)
        # Handle presence of NaNs according to `nan_mode`.
        self._handle_nans(idx, non_nan_idx)
        y_fit = y_fit.reindex(non_nan_idx)
        # Fit the model.
        self._model = sm.tsa.statespace.SARIMAX(
            y_fit, exog=x_fit, **self._init_kwargs
        )
        self._model_results = self._model.fit(**self._fit_kwargs)
        # Get predictions.
        # Treat the fit data as out-of-sample to mimic the behavior in
        # `predict()`.
        fwd_y_hat = self._predict(y_fit, x_fit)
        # Package results.
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        forward_y_df = dtfcorutil.get_forward_cols(df, y_vars, self._steps_ahead)
        df_out = forward_y_df.merge(
            fwd_y_hat, how="outer", left_index=True, right_index=True
        )
        df_out = self._apply_col_mode(
            df,
            df_out,
            cols=dtfcorutil.convert_to_list(self._y_vars),
            col_mode=self._col_mode,
        )
        # Add info.
        # TODO(Julia): Maybe add model performance to info.
        info = collections.OrderedDict()
        info["model_summary"] = _remove_datetime_info_from_sarimax(
            _convert_sarimax_summary_to_dataframe(self._model_results.summary())
        )
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        df = df_in.copy()
        idx = df.index
        # Get intersection of non-NaN `y` and `x`.
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        hdbg.dassert_eq(len(y_vars), 1, "Only univariate `y` is supported")
        y_predict = df[y_vars]
        if self._x_vars is not None:
            x_predict = self._get_bkwd_x_df(df)
            x_predict = x_predict.dropna()
            y_predict = y_predict.reindex(x_predict.index)
            x_idx_extension = x_predict.index[-self._steps_ahead :]
            idx = idx[self._steps_ahead :].append(x_idx_extension)
        else:
            x_predict = None
        x_predict = self._add_constant_to_x(x_predict)
        # Handle presence of NaNs according to `nan_mode`.
        self._handle_nans(idx, y_predict.index)
        fwd_y_hat = self._predict(y_predict, x_predict)
        # Package results.
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        forward_y_df = dtfcorutil.get_forward_cols(df, y_vars, self._steps_ahead)
        df_out = forward_y_df.merge(
            fwd_y_hat, how="outer", left_index=True, right_index=True
        )
        df_out = self._apply_col_mode(
            df,
            df_out,
            cols=dtfcorutil.convert_to_list(self._y_vars),
            col_mode=self._col_mode,
        )
        # Add info.
        info = collections.OrderedDict()
        info["model_summary"] = _remove_datetime_info_from_sarimax(
            _convert_sarimax_summary_to_dataframe(self._model_results.summary())
        )
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        return {"df_out": df_out}

    # ///////////////////////////////////////////////////////////////////////////

    def _predict(
        self, y: pd.DataFrame, x: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Make n-step-ahead predictions.
        """
        preds = []
        if self._x_vars is not None:
            pred_range = len(y) - self._steps_ahead
            # TODO(Julia): Check this.
            pred_start = self._steps_ahead
        else:
            pred_range = len(y)
            pred_start = 1
        y_var = y.columns[0]
        for t in tqdm(
            range(pred_start, pred_range + 1),
            disable=self._disable_tqdm,
            desc="ContinuosSarimax predict",
        ):
            # If `t` is larger than `y`, this selects the whole `y`.
            y_past = y.iloc[:t]
            if x is not None:
                x_past = x.iloc[:t]
                x_step = x.iloc[t : t + self._steps_ahead]
            else:
                x_past = None
                x_step = None
            # Create a model with the same params as `self._model`, but make it
            # aware of the past values.
            model_predict = self._model.clone(y_past, exog=x_past)
            result_predict = model_predict.filter(self._model_results.params)
            # Make forecast.
            forecast = result_predict.forecast(
                steps=self._steps_ahead, exog=x_step
            )
            # Transform forecast into a row indexed by prediction time.
            forecast = forecast.to_frame(name=y_past.index[-1]).T
            forecast.columns = [
                f"{y_var}.shift_-{i+1}_hat" for i in range(self._steps_ahead)
            ]
            preds.append(forecast)
        preds = pd.concat(preds)
        return preds

    def _get_bkwd_x_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return dataframe of `steps_ahead - 1` backward x values.

        This way we predict `y_t` using `x_{t-n}`, ..., `x_{t-1}`, where `n` is
        `self._steps_ahead`.
        """
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        shift = self._steps_ahead
        # Shift index instead of series to extend the index.
        bkwd_x_df = df[x_vars].copy()
        bkwd_x_df.index = bkwd_x_df.index.shift(shift)
        mapper = lambda y: str(y) + "_bkwd_%i" % shift
        return bkwd_x_df.rename(columns=mapper)

    def _add_constant_to_x(self, x: pd.DataFrame) -> Optional[pd.DataFrame]:
        if not self._add_constant:
            return x
        if self._x_vars is not None:
            self._x_vars = dtfcorutil.convert_to_list(self._x_vars)
            hdbg.dassert_not_in(
                "const",
                self._x_vars,
                "A column name 'const' is already present, please rename column.",
            )
            self._x_vars.append("const")
            x = sm.add_constant(x)
            return x
        _LOG.warning("`add_constant=True` but no exog is provided.")
        return x

    def _handle_nans(
        self, idx: pd.DataFrame.index, non_nan_idx: pd.DataFrame.index
    ) -> None:
        if self._nan_mode == "raise":
            if idx.shape[0] != non_nan_idx.shape[0]:
                nan_idx = idx.difference(non_nan_idx)
                raise ValueError(f"NaNs detected at {nan_idx}")
        elif self._nan_mode == "drop" or self._nan_mode == "leave_unchanged":
            pass
        else:
            raise ValueError(f"Unrecognized nan_mode `{self._nan_mode}`")


# #############################################################################
# MultihorizonReturnsPredictionProcessor
# #############################################################################


class MultihorizonReturnsPredictionProcessor(dtfconobas.FitPredictNode):
    """
    Process multi-horizon returns prediction.

    In multi-horizon returns prediction problem, the output can take a form of
    single-step returns for each forecast step. To get returns from `t_0` to
    `t_n`, we need to:
      - (optional): undo z-scoring
      - accumulate returns for each step. The output is `cumret_t_1, ...,
        cumret_t_n` and `cumret_t_1_hat, ..., cumret_t_n_hat`
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        target_col: Any,
        prediction_cols: dtfcorutil.NodeColumnList,
        volatility_col: Any,
    ):
        """
        :param nid: node identifier
        :param target_col: name of the prediction target column which contains
            single-step returns, e.g. "ret_0_zscored"
        :param prediction_cols: name of columns with single-step returns
            predictions for each forecast step. The columns should be indexed
            by knowledge time and ordered by forecast step, e.g.
            `["ret_0_zscored.shift_-1_hat", "ret_0_zscored.shift_-2_hat",
            "ret_0_zscored.shift_-3_hat"]`
        :param volatility_col: name of a column containing one step ahead
            volatility forecast. If `None`, z-scoring is not inverted
        """
        super().__init__(nid)
        self._target_col = target_col
        self._prediction_cols = dtfcorutil.convert_to_list(prediction_cols)
        self._volatility_col = volatility_col
        self._max_steps_ahead = len(self._prediction_cols)

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        df_out = self._process(df_in)
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        df_out = self._process(df_in)
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        return {"df_out": df_out}

    def _process(self, df_in: pd.DataFrame) -> pd.DataFrame:
        cum_ret_hat = self._process_predictions(df_in)
        fwd_cum_ret = self._process_target(df_in)
        # TODO(Julia): Add `col_mode`.
        cum_y_yhat = fwd_cum_ret.join(cum_ret_hat, how="right")
        return cum_y_yhat

    def _process_predictions(self, df_in: pd.DataFrame) -> pd.DataFrame:
        """
        Invert z-scoring and accumulate predicted returns for each step.
        """
        predictions = df_in[self._prediction_cols]
        # Invert z-scoring.
        if self._volatility_col is not None:
            vol_1_hat = df_in[self._volatility_col]
            predictions = predictions.multiply(vol_1_hat, axis=0)
        # Accumulate predicted returns for each step.
        cum_ret_hats = []
        for i in range(1, self._max_steps_ahead + 1):
            cum_ret_hat_curr = predictions.iloc[:, :i].sum(axis=1, skipna=False)
            cum_ret_hats.append(
                cum_ret_hat_curr.to_frame(name=f"cumret.shift_-{i}_hat")
            )
        return pd.concat(cum_ret_hats, axis=1)

    def _process_target(self, df_in: pd.DataFrame) -> pd.Series:
        """
        Invert z-scoring and accumulate returns for each step.
        """
        target = df_in[self._target_col]
        # Invert z-scoring.
        if self._volatility_col is not None:
            vol_1_hat = df_in[self._volatility_col]
            vol_0_hat = vol_1_hat.shift(1)
            target = target * vol_0_hat
        # Accumulate target for each step.
        cum_rets = []
        for i in range(1, self._max_steps_ahead + 1):
            cum_ret_curr = (
                target.rolling(window=i).sum().rename(f"cumret.shift_-{i}")
            )
            cum_rets.append(cum_ret_curr)
        cum_rets = pd.concat(cum_rets, axis=1)
        fwd_cum_ret = cum_rets.shift(-self._max_steps_ahead)
        return fwd_cum_ret


# #############################################################################


def _convert_sarimax_summary_to_dataframe(
    summary: siolib.summary.Summary,
) -> Dict[str, pd.DataFrame]:
    """
    Convert SARIMAX model summary to dataframes.

    SARIMAX model summary consists of 3 tables:
        1) general info - 2 columns of pairs key-value
        2) coefs - a table with rows for every feature
        3) tests results - 2 columns of pairs key-value
    Function converts 1 and 3 tables to a dataframe with index-key, column-value,
    2 table - a dataframe with index-feature.
    """
    tables_dict = collections.OrderedDict()
    keys = ["info", "coefs", "tests"]
    for i, table in enumerate(summary.tables):
        table = np.array(table)
        if table.shape[1] == 4:
            # Process paired tables.
            table = np.vstack((table[:, :2], table[:, 2:]))
            df = pd.DataFrame(table)
            df = df.applymap(lambda x: str(x).strip(": ").lstrip(" "))
            if "Sample" in df[0].values:
                sample_index = df[0].tolist().index("Sample")
                df.iloc[sample_index, 0] = "Start Date"
                df.iloc[sample_index + 1, 0] = "End Date"
                df.iloc[sample_index + 1, 1] = df.iloc[
                    sample_index + 1, 1
                ].lstrip("- ")
            df = df[df[0] != ""]
            df = df.set_index(0)
            df.index.name = None
            df = df.iloc[:, 0]
        else:
            # Process coefs table.
            df = pd.DataFrame(table[1:, :])
            df = df.set_index(0)
            df.index.name = None
            df.columns = table[0, 1:]
        tables_dict[keys[i]] = df
    return tables_dict


def _remove_datetime_info_from_sarimax(
    summary: Dict[str, pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    """
    Remove date and time from model summary.
    """
    summary["info"] = summary["info"].drop(["Date", "Time"])
    return summary
