"""
Import as:

import dataflow.core.nodes.volatility_models as dtfcnovomo
"""

import collections
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy as sp
import sklearn as sklear

import core.config as cconfig
import core.data_adapters as cdatadap
import core.signal_processing as csigproc
import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.nodes.sources as dtfconosou
import dataflow.core.nodes.transformers as dtfconotra
import dataflow.core.utils as dtfcorutil
import dataflow.core.visitors as dtfcorvisi
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class SmaModel(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    Fit and predict a smooth moving average (SMA) model.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        col: dtfcorutil.NodeColumnList,
        steps_ahead: int,
        tau: Optional[float] = None,
        min_tau_periods: Optional[float] = 2,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        Specify the data and SMA modeling parameters.

        :param nid: unique node id
        :param col: name of column to model
        :param steps_ahead: as in `ContinuousSkLearnModel`
        :param tau: as in `csigproc.compute_smooth_moving_average`. If `None`,
            learn this parameter. Will be re-learned on each `fit` call.
        :param min_tau_periods: similar to `min_periods` as in
            `csigproc.compute_smooth_moving_average`, but expressed in units of
            tau
        :param col_mode: `merge_all` or `replace_all`, as in `ColumnTransformer()`
        :param nan_mode: as in `ContinuousSkLearnModel`
        """
        super().__init__(nid)
        self._col = dtfcorutil.convert_to_list(col)
        hdbg.dassert_eq(len(self._col), 1)
        self._steps_ahead = steps_ahead
        hdbg.dassert_lte(
            0, self._steps_ahead, "Non-causal prediction attempted! Aborting..."
        )
        if nan_mode is None:
            self._nan_mode = "raise"
        else:
            self._nan_mode = nan_mode
        self._col_mode = col_mode or "replace_all"
        hdbg.dassert_in(self._col_mode, ["replace_all", "merge_all"])
        # Smooth moving average model parameters to learn.
        self._must_learn_tau = tau is None
        self._tau = tau
        self._min_tau_periods = min_tau_periods or 0
        self._min_depth = 1
        self._max_depth = 1
        self._metric = sklear.metrics.mean_absolute_error

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        idx = df_in.index[: -self._steps_ahead]
        x_vars = self._col
        y_vars = self._col
        df = dtfcorutil.get_x_and_forward_y_fit_df(
            df_in, x_vars, y_vars, self._steps_ahead
        )
        forward_y_cols = df.drop(x_vars, axis=1).columns
        # Handle presence of NaNs according to `nan_mode`.
        self._handle_nans(idx, df.index)
        # Define and fit model.
        if self._must_learn_tau:
            forward_y_df = df[forward_y_cols]
            # Prepare forward y_vars in sklearn format.
            forward_y_fit = cdatadap.transform_to_sklearn(
                forward_y_df, forward_y_df.columns.tolist()
            )
            # Prepare `x_vars` in sklearn format.
            x_fit = cdatadap.transform_to_sklearn(df, self._col)
            self._tau = self._learn_tau(x_fit, forward_y_fit)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("tau=%s", self._tau)
        return self._predict_and_package_results(df_in, idx, df.index, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        df = df_in.copy()
        idx = df.index
        # Restrict to times where col has no NaNs.
        non_nan_idx = df.loc[idx][self._col].dropna().index
        # Handle presence of NaNs according to `nan_mode`.
        self._handle_nans(idx, non_nan_idx)
        # Use trained model to generate predictions.
        hdbg.dassert_is_not(
            self._tau,
            None,
            "Parameter tau not found! Check if `fit` has been run.",
        )
        return self._predict_and_package_results(
            df_in, idx, non_nan_idx, fit=False
        )

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {"_tau": self._tau, "_info['fit']": self._info["fit"]}
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        self._tau = fit_state["_tau"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _predict_and_package_results(
        self,
        df_in: pd.DataFrame,
        idx: pd.Index,
        non_nan_idx: pd.Index,
        fit: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        data = cdatadap.transform_to_sklearn(df_in.loc[non_nan_idx], self._col)
        fwd_y_hat = self._predict(data)
        forward_y_df = dtfcorutil.get_forward_cols(
            df_in, self._col, self._steps_ahead
        )
        forward_y_df = forward_y_df.loc[non_nan_idx]
        # Put predictions in dataflow dataframe format.
        fwd_y_hat_vars = [f"{y}_hat" for y in forward_y_df.columns]
        fwd_y_hat = cdatadap.transform_from_sklearn(
            non_nan_idx, fwd_y_hat_vars, fwd_y_hat
        )
        # Return targets and predictions.
        df_out = forward_y_df.reindex(idx).merge(
            fwd_y_hat.reindex(idx), left_index=True, right_index=True
        )
        hdbg.dassert_no_duplicates(df_out.columns)
        # Select columns for output.
        df_out = self._apply_col_mode(
            df_in, df_out, cols=self._col, col_mode=self._col_mode
        )
        # Update `info`.
        info = collections.OrderedDict()
        info["tau"] = self._tau
        info["min_periods"] = self._get_min_periods(self._tau)
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        method = "fit" if fit else "predict"
        self._set_info(method, info)
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
        elif self._nan_mode == "leave_unchanged":
            pass
        else:
            raise ValueError(f"Unrecognized nan_mode `{self._nan_mode}`")

    def _learn_tau(self, x: np.array, y: np.array) -> float:
        def score(tau: float) -> float:
            x_srs = pd.DataFrame(x.flatten())
            sma = csigproc.compute_smooth_moving_average(
                x_srs,
                tau=tau,
                min_periods=0,
                min_depth=self._min_depth,
                max_depth=self._max_depth,
            )
            min_periods = self._get_min_periods(tau)
            return self._metric(sma[min_periods:], y[min_periods:])

        tau_lb, tau_ub = 1, 1000
        # Satisfy 2 * tau_ub * min_tau_periods = len(x).
        # This ensures that no more than half of the `fit` series is burned.
        if self._min_tau_periods > 0:
            tau_ub = int(len(x) / (2 * self._min_tau_periods))
        opt_results = sp.optimize.minimize_scalar(
            score, method="bounded", bounds=[tau_lb, tau_ub]
        )
        return opt_results.x

    def _get_min_periods(self, tau: float) -> int:
        """
        Return burn-in period.

        Multiplies `tau` by `min_tau_periods` and converts to an integer.

        :param tau: kernel tau (approximately equal to center of mass)
        :return: minimum number of periods required to generate a prediction
        """
        return int(np.rint(self._min_tau_periods * tau))

    def _predict(self, x: np.array) -> np.array:
        x_srs = pd.DataFrame(x.flatten())
        # TODO(Paul): Make `min_periods` configurable.
        min_periods = int(np.rint(self._min_tau_periods * self._tau))
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("min_periods=%f", min_periods)
        x_sma = csigproc.compute_smooth_moving_average(
            x_srs,
            tau=self._tau,
            min_periods=min_periods,
            min_depth=self._min_depth,
            max_depth=self._max_depth,
        )
        return x_sma.values


class SingleColumnVolatilityModel(dtfconobas.FitPredictNode):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        steps_ahead: int,
        col: dtfcorutil.NodeColumn,
        p_moment: float = 2,
        progress_bar: bool = False,
        tau: Optional[float] = None,
        nan_mode: Optional[str] = None,
        out_col_prefix: Optional[str] = None,
    ) -> None:
        """
        Parameters have the same meaning as `SmaModel`.
        """
        super().__init__(nid)
        self._col = col
        self._steps_ahead = steps_ahead
        hdbg.dassert_lte(1, p_moment)
        self._p_moment = p_moment
        self._progress_bar = progress_bar
        self._tau = tau
        self._learn_tau_on_fit = tau is None
        self._nan_mode = nan_mode
        self._out_col_prefix = out_col_prefix

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_col": self._col,
            "_tau": self._tau,
            "_info['fit']": self._info["fit"],
            "_out_col_prefix": self._out_col_prefix,
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]):
        self._col = fit_state["_col"]
        self._tau = fit_state["_tau"]
        self._info["fit"] = fit_state["_info['fit']"]
        self._out_col_prefix = fit_state["_out_col_prefix"]

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return {"df_out": self._fit_predict_helper(df_in, fit=True)}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return {"df_out": self._fit_predict_helper(df_in, fit=False)}

    # TODO(gp): This code has several copies. Move it to the base class.
    @staticmethod
    def _append(
        dag: dtfcordag.DAG, tail_nid: Optional[str], node: dtfcornode.Node
    ) -> str:
        dag.add_node(node)
        if tail_nid is not None:
            dag.connect(tail_nid, node.nid)
        return node.nid

    def _fit_predict_helper(self, df_in: pd.DataFrame, fit: bool) -> pd.DataFrame:
        info = collections.OrderedDict()
        name = self._out_col_prefix or self._col
        name = str(name)
        hdbg.dassert_not_in(name + "_vol", df_in.columns)
        if self._learn_tau_on_fit and fit:
            tau = None
        else:
            tau = self._tau
        config = self._get_config(col=self._col, out_col_prefix=name, tau=tau)
        dag = self._get_dag(df_in[[self._col]], config)
        mode = "fit" if fit else "predict"
        df_out = dag.run_leq_node(
            "demodulate_using_vol_pred", mode, progress_bar=self._progress_bar
        )["df_out"]
        info[self._col] = dtfcorvisi.extract_info(dag, [mode])
        if self._learn_tau_on_fit and fit:
            self._tau = info[self._col]["compute_smooth_moving_average"]["fit"][
                "tau"
            ]
        df_out = df_out.reindex(df_in.index)
        self._set_info(mode, info)
        return df_out

    def _get_config(
        self,
        col: dtfcorutil.NodeColumn,
        out_col_prefix: dtfcorutil.NodeColumn,
        tau: Optional[float] = None,
    ) -> cconfig.Config:
        """
        Generate a DAG config.

        :param col: column whose volatility is to be modeled
        :param tau: tau for SMA; if `None`, then to be learned
        :return: a complete config to be used with `_get_dag()`
        """
        config = cconfig.Config.from_dict(
            {
                "calculate_vol_pth_power": {
                    "cols": [col],
                    "col_rename_func": lambda x: out_col_prefix + "_vol",
                    "col_mode": "merge_all",
                },
                "compute_smooth_moving_average": {
                    "col": [out_col_prefix + "_vol"],
                    "steps_ahead": self._steps_ahead,
                    "tau": tau,
                    "col_mode": "merge_all",
                    "nan_mode": self._nan_mode,
                },
                "calculate_vol_pth_root": {
                    "cols": [
                        out_col_prefix + "_vol",
                        out_col_prefix
                        + "_vol"
                        + ".shift_-"
                        + str(self._steps_ahead),
                        out_col_prefix
                        + "_vol"
                        + ".shift_-"
                        + str(self._steps_ahead)
                        + "_hat",
                    ],
                    "col_mode": "replace_selected",
                },
                "demodulate_using_vol_pred": {
                    "signal_cols": [col],
                    "volatility_col": out_col_prefix
                    + "_vol"
                    + ".shift_-"
                    + str(self._steps_ahead)
                    + "_hat",
                    "signal_steps_ahead": 0,
                    "volatility_steps_ahead": self._steps_ahead,
                    "col_rename_func": lambda x: out_col_prefix + "_vol_adj",
                    "col_mode": "replace_selected",
                    "nan_mode": self._nan_mode,
                },
            }
        )
        return config

    def _get_dag(
        self, df_in: pd.DataFrame, config: cconfig.Config
    ) -> dtfcordag.DAG:
        """
        Build a DAG from data and config.

        :param df_in: data over which to run DAG
        :param config: config for configuring DAG nodes
        :return: ready-to-run DAG
        """
        dag = dtfcordag.DAG(mode="strict")
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        # Load `df_in`.
        nid = "load_data"
        node = dtfconosou.DfDataSource(nid, df_in)
        tail_nid = self._append(dag, None, node)
        # Raise volatility columns to pth power.
        nid = "calculate_vol_pth_power"
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=lambda x: np.abs(x) ** self._p_moment,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Predict pth power of volatility using smooth moving average.
        nid = "compute_smooth_moving_average"
        node = SmaModel(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, tail_nid, node)
        # Calculate the pth root of volatility columns.
        nid = "calculate_vol_pth_root"
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=lambda x: np.abs(x) ** (1.0 / self._p_moment),
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Divide returns by volatilty prediction.
        nid = "demodulate_using_vol_pred"
        node = VolatilityModulator(
            nid, mode="demodulate", **config[nid].to_dict()
        )
        self._append(dag, tail_nid, node)
        return dag


class _MultiColVolatilityModelMixin:
    def _fit_predict_volatility_model(
        self, df: pd.DataFrame, fit: bool, out_col_prefix: Optional[str] = None
    ) -> Tuple[Dict[str, pd.DataFrame], collections.OrderedDict]:
        dfs = {}
        info = collections.OrderedDict()
        for col in df.columns:
            local_out_col_prefix = out_col_prefix or col
            scvm = SingleColumnVolatilityModel(
                "volatility",
                steps_ahead=self._steps_ahead,
                col=col,
                p_moment=self._p_moment,
                progress_bar=self._progress_bar,
                tau=self._tau,
                nan_mode=self._nan_mode,
                out_col_prefix=local_out_col_prefix,
            )
            if fit:
                df_out = scvm.fit(df[[col]])["df_out"]
                info_out = scvm.get_info("fit")
                self._col_fit_state[col] = scvm.get_fit_state()
            else:
                scvm.set_fit_state(self._col_fit_state[col])
                df_out = scvm.predict(df[[col]])["df_out"]
                info_out = scvm.get_info("predict")
            dfs[col] = df_out
            info[col] = info_out
        return dfs, info


class VolatilityModel(
    dtfconobas.FitPredictNode,
    dtfconobas.ColModeMixin,
    _MultiColVolatilityModelMixin,
):
    """
    Fit and predict a smooth moving average volatility model.

    Wraps `SmaModel` internally, handling calculation of volatility from
    returns and column appends.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        steps_ahead: int,
        cols: Optional[dtfcorutil.NodeColumnList] = None,
        p_moment: float = 2,
        progress_bar: bool = False,
        tau: Optional[float] = None,
        col_rename_func: Callable[[Any], Any] = lambda x: f"{x}_zscored",
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        Specify the data and smooth moving average (SMA) modeling parameters.

        :param nid: unique node id
        :param cols: name of columns to model
        :param steps_ahead: as in ContinuousSkLearnModel
        :param p_moment: exponent to apply to the absolute value of returns
        :param tau: as in `csigproc.compute_smooth_moving_average`. If `None`,
            learn this parameter
        :param col_rename_func: renaming function for z-scored column
        :param col_mode:
            - If "merge_all" (default), merge all columns from input dataframe and
              transformed columns
            - If "replace_selected", merge unselected columns from input dataframe
              and transformed selected columns
            - If "replace_all", leave only transformed selected columns
        :param nan_mode: as in ContinuousSkLearnModel
        """
        super().__init__(nid)
        self._cols = cols
        self._steps_ahead = steps_ahead
        #
        hdbg.dassert_lte(1, p_moment)
        self._p_moment = p_moment
        #
        self._progress_bar = progress_bar
        #
        hdbg.dassert(tau is None or tau > 0)
        self._tau = tau
        self._col_rename_func = col_rename_func
        self._col_mode = col_mode or "merge_all"
        self._nan_mode = nan_mode
        # State of the model to serialize/deserialize.
        self._fit_cols: List[dtfcorutil.NodeColumn] = []
        self._col_fit_state = {}

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_fit_cols": self._fit_cols,
            "_col_fit_state": self._col_fit_state,
            "_info['fit']": self._info["fit"],
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]):
        self._fit_cols = fit_state["_fit_cols"]
        self._col_fit_state = fit_state["_col_fit_state"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _fit_predict_helper(self, df_in: pd.DataFrame, fit: bool):
        dtfcorutil.validate_df_indices(df_in)
        # Get the columns.
        self._fit_cols = dtfcorutil.convert_to_list(
            self._cols or df_in.columns.tolist()
        )
        df = df_in[self._fit_cols]
        dfs, info = self._fit_predict_volatility_model(df, fit=fit)
        df_out = pd.concat(dfs.values(), axis=1)
        df_out = self._apply_col_mode(
            df_in.drop(df_out.columns.intersection(df_in.columns), axis=1),
            df_out,
            cols=self._fit_cols,
            col_mode=self._col_mode,
        )
        method = "fit" if fit else "predict"
        self._set_info(method, info)
        return {"df_out": df_out}


class MultiindexVolatilityModel(
    dtfconobas.FitPredictNode, _MultiColVolatilityModelMixin
):
    """
    Fit and predict a smooth moving average volatility model.

    Wraps SmaModel internally, handling calculation of volatility from
    returns and column appends.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_group: Tuple[dtfcorutil.NodeColumn],
        steps_ahead: int,
        p_moment: float = 2,
        progress_bar: bool = False,
        tau: Optional[float] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        Specify the data and sma modeling parameters.

        :param nid: unique node id
        :param steps_ahead: as in ContinuousSkLearnModel
        :param p_moment: exponent to apply to the absolute value of returns
        :param tau: as in `csigproc.compute_smooth_moving_average`. If `None`,
            learn this parameter
        :param nan_mode: as in ContinuousSkLearnModel
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(in_col_group, tuple)
        self._in_col_group = in_col_group
        self._out_col_group = in_col_group[:-1]
        self._out_col_prefix = str(in_col_group[-1])
        #
        self._steps_ahead = steps_ahead
        hdbg.dassert_lte(1, p_moment)
        self._p_moment = p_moment
        #
        self._progress_bar = progress_bar
        #
        self._tau = tau
        self._nan_mode = nan_mode
        #
        self._col_fit_state = {}

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._fit_predict_helper(df_in, fit=False)

    def get_fit_state(self) -> Dict[str, Any]:
        fit_state = {
            "_col_fit_state": self._col_fit_state,
            "_info['fit']": self._info["fit"],
        }
        return fit_state

    def set_fit_state(self, fit_state: Dict[str, Any]):
        self._col_fit_state = fit_state["_col_fit_state"]
        self._info["fit"] = fit_state["_info['fit']"]

    def _fit_predict_helper(self, df_in: pd.DataFrame, fit: bool):
        dtfcorutil.validate_df_indices(df_in)
        df = dtfconobas.SeriesToDfColProcessor.preprocess(
            df_in, self._in_col_group
        )
        dfs, info = self._fit_predict_volatility_model(
            df, fit=fit, out_col_prefix=self._out_col_prefix
        )
        df_out = dtfconobas.SeriesToDfColProcessor.postprocess(
            dfs, self._out_col_group
        )
        df_out = dtfcorutil.merge_dataframes(df_in, df_out)
        method = "fit" if fit else "predict"
        self._set_info(method, info)
        return {"df_out": df_out}


class VolatilityModulator(dtfconobas.FitPredictNode, dtfconobas.ColModeMixin):
    """
    Modulate or demodulate signal by volatility.

    Processing steps:
      - shift volatility to align it with signal
      - multiply/divide signal by volatility

    Usage examples:
      - Z-scoring
        - to obtain volatility prediction, pass in returns into `SmaModel` with
          a `steps_ahead` parameter
        - to z-score, pass in signal, volatility prediction, `signal_steps_ahead=0`,
          `volatility_steps_ahead=steps_ahead`, `mode='demodulate'`
      - Undoing z-scoring
        - Let's say we have
          - forward volatility prediction `n` steps ahead
          - prediction of forward z-scored returns `m` steps ahead. Z-scoring
            for the target has been done using the volatility prediction above
        - To undo z-scoring, we need to pass in the prediction of forward
          z-scored returns, forward volatility prediction, `signal_steps_ahead=n`,
          `volatility_steps_ahead=m`, `mode='modulate'`
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        signal_cols: dtfcorutil.NodeColumnList,
        volatility_col: dtfcorutil.NodeColumn,
        signal_steps_ahead: int,
        volatility_steps_ahead: int,
        mode: str,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        :param nid: node identifier
        :param signal_cols: names of columns to (de)modulate
        :param volatility_col: name of volatility column
        :param signal_steps_ahead: steps ahead of the signal columns. If signal
            is at `t_0`, this value should be `0`. If signal is a forward
            prediction of z-scored returns indexed by knowledge time, this
            value should be equal to the number of steps of the prediction
        :param volatility_steps_ahead: steps ahead of the volatility column. If
            volatility column is an output of `SmaModel`, this corresponds to
            the `steps_ahead` parameter
        :param mode: "modulate" or "demodulate"
        :param col_rename_func: as in `ColumnTransformer`
        :param col_mode: as in `ColumnTransformer`
        """
        super().__init__(nid)
        self._signal_cols = dtfcorutil.convert_to_list(signal_cols)
        self._volatility_col = volatility_col
        hdbg.dassert_lte(0, signal_steps_ahead)
        self._signal_steps_ahead = signal_steps_ahead
        hdbg.dassert_lte(0, volatility_steps_ahead)
        self._volatility_steps_ahead = volatility_steps_ahead
        hdbg.dassert_in(mode, ["modulate", "demodulate"])
        self._mode = mode
        self._col_rename_func = col_rename_func or (lambda x: x)
        self._col_mode = col_mode or "replace_all"
        self._nan_mode = nan_mode or "leave_unchanged"

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        df_out = self._process_signal(df_in)
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        df_out = self._process_signal(df_in)
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        return {"df_out": df_out}

    def _process_signal(self, df_in: pd.DataFrame) -> pd.DataFrame:
        """
        Modulate or demodulate signal by volatility prediction.

        :param df_in: dataframe with `self._signal_cols` and
            `self._volatility_col` columns
        :return: adjusted signal indexed in the same way as the input signal
        """
        hdbg.dassert_is_subset(self._signal_cols, df_in.columns.tolist())
        hdbg.dassert_in(self._volatility_col, df_in.columns)
        fwd_signal = df_in[self._signal_cols]
        fwd_volatility = df_in[self._volatility_col]
        # Shift volatility to align it with signal.
        volatility_shift = self._volatility_steps_ahead - self._signal_steps_ahead
        if self._nan_mode == "drop":
            fwd_volatility = fwd_volatility.dropna()
        elif self._nan_mode == "leave_unchanged":
            pass
        else:
            raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
        volatility_aligned = fwd_volatility.shift(volatility_shift)
        # Adjust signal by volatility.
        if self._mode == "demodulate":
            adjusted_signal = fwd_signal.divide(volatility_aligned, axis=0)
        elif self._mode == "modulate":
            adjusted_signal = fwd_signal.multiply(volatility_aligned, axis=0)
        else:
            raise ValueError(f"Invalid mode=`{self._mode}`")
        df_out = self._apply_col_mode(
            df_in,
            adjusted_signal,
            cols=self._signal_cols,
            col_rename_func=self._col_rename_func,
            col_mode=self._col_mode,
        )
        return df_out
