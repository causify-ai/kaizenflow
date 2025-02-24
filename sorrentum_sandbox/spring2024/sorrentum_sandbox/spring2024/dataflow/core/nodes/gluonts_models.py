"""
Import as:

import dataflow.core.nodes.gluonts_models as dtfcnoglmo
"""

import collections
import logging
from typing import Any, Dict, Optional

import gluonts.model.deepar as gmdeep
import gluonts.trainer as gtrain
import pandas as pd

import core.backtest as cobackte
import core.data_adapters as cdatadap
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# ContinuousDeepArModel
# #############################################################################


class ContinuousDeepArModel(dtfconobas.FitPredictNode):
    """
    A dataflow node for a DeepAR model.

    This node trains a DeepAR model using only one time series
    - By using only one time series, we are not taking advantage of the
      "global" modeling capabilities of gluonts or DeepAR
    - This may be somewhat mitigated by the fact that the single time series
      that we provide will typically contain on the order of 10E5 or more time
      points
    - In training, DeepAR randomly cuts the time series provided, and so
      unless there are obvious cut-points we want to take advantage of, it may
      be best to let DeepAR cut
    - If certain cut-points are naturally more appropriate in our problem
      domain, an event study modeling approach may be more suitable

    See https://arxiv.org/abs/1704.04110 for a description of the DeepAR model.

    For additional context and best-practices, see
    https://github.com/.../.../issues/966
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        y_vars: dtfcorutil.NodeColumnList,
        trainer_kwargs: Optional[Any] = None,
        estimator_kwargs: Optional[Any] = None,
        x_vars: Optional[dtfcorutil.NodeColumnList] = None,
        num_traces: int = 100,
    ) -> None:
        """
        Initialize dataflow node for gluon-ts DeepAR model.

        :param nid: unique node id
        :param y_vars: Used in autoregression
        :param trainer_kwargs: See
          - https://gluon-ts.mxnet.io/api/gluonts/gluonts.trainer.html#gluonts.trainer.Trainer
          - https://github.com/awslabs/gluon-ts/blob/master/src/gluonts/trainer/_base.py
        :param estimator_kwargs: See
          - https://gluon-ts.mxnet.io/api/gluonts/gluonts.model.deepar.html
          - https://github.com/awslabs/gluon-ts/blob/master/src/gluonts/model/deepar/_estimator.py
        :param x_vars: Covariates. Could be, e.g., features associated with a
            point-in-time event. Must be known throughout the prediction
            window at the time the prediction is made. May be omitted.
        :num_traces: Number of sample paths / traces to generate per
            prediction. The mean of the traces is used as the prediction.
        """
        super().__init__(nid)
        self._estimator_kwargs = estimator_kwargs
        # To avoid passing a class through config, handle `Trainer()`
        # parameters separately from `estimator_kwargs`.
        self._trainer_kwargs = trainer_kwargs
        self._trainer = gtrain.Trainer(**self._trainer_kwargs)
        hdbg.dassert_not_in("trainer", self._estimator_kwargs)
        #
        self._estimator_func = gmdeep.DeepAREstimator
        # NOTE: Covariates (x_vars) are not required by DeepAR.
        #   - This could be useful for, e.g., predicting future values of
        #     what would normally be predictors
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._num_traces = num_traces
        self._estimator = None
        self._predictor = None
        #
        hdbg.dassert_in("prediction_length", self._estimator_kwargs)
        self._prediction_length = self._estimator_kwargs["prediction_length"]
        hdbg.dassert_lt(0, self._prediction_length)
        hdbg.dassert_not_in(
            "freq",
            self._estimator_kwargs,
            "`freq` to be autoinferred from `df_in`; do not specify",
        )

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        df = df_in.copy()
        # Obtain index slice for which forward targets exist.
        hdbg.dassert_lt(self._prediction_length, df.index.size)
        df_fit = df.iloc[: -self._prediction_length]
        #
        if self._x_vars is not None:
            x_vars = dtfcorutil.convert_to_list(self._x_vars)
        else:
            x_vars = None
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        # Transform dataflow local timeseries dataframe into gluon-ts format.
        gluon_train = cdatadap.transform_to_gluon(
            df_fit, x_vars, y_vars, df_fit.index.freq.freqstr
        )
        # Instantiate the (DeepAR) estimator and train the model.
        self._estimator = self._estimator_func(
            trainer=self._trainer,
            freq=df_fit.index.freq.freqstr,
            **self._estimator_kwargs,
        )
        self._predictor = self._estimator.train(gluon_train)
        # Predict. Generate predictions over all of `df_in` (not just on the
        #     restricted slice `df_fit`).
        fwd_y_hat, fwd_y = cobackte.generate_predictions(
            predictor=self._predictor,
            df=df,
            y_vars=y_vars,
            prediction_length=self._prediction_length,
            num_samples=self._num_traces,
            x_vars=x_vars,
        )
        # Store info.
        info = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        #
        df_out = fwd_y.merge(fwd_y_hat, left_index=True, right_index=True)
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        hdbg.dassert_no_duplicates(df_out.columns)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dtfcorutil.validate_df_indices(df_in)
        df = df_in.copy()
        if self._x_vars is not None:
            x_vars = dtfcorutil.convert_to_list(self._x_vars)
        else:
            x_vars = None
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        gluon_train = cdatadap.transform_to_gluon(
            df, x_vars, y_vars, df.index.freq.freqstr
        )
        # Instantiate the (DeepAR) estimator and train the model.
        self._estimator = self._estimator_func(
            trainer=self._trainer,
            freq=df.index.freq.freqstr,
            **self._estimator_kwargs,
        )
        self._predictor = self._estimator.train(gluon_train)
        #
        fwd_y_hat, fwd_y = cobackte.generate_predictions(
            predictor=self._predictor,
            df=df,
            y_vars=y_vars,
            prediction_length=self._prediction_length,
            num_samples=self._num_traces,
            x_vars=x_vars,
        )
        # Store info.
        info = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        #
        df_out = fwd_y.merge(fwd_y_hat, left_index=True, right_index=True)
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        hdbg.dassert_no_duplicates(df_out.columns)
        return {"df_out": df_out}


# #############################################################################
# DeepARGlobalModel
# #############################################################################


class DeepARGlobalModel(dtfconobas.FitPredictNode):
    """
    A dataflow node for a DeepAR model.

    See https://arxiv.org/abs/1704.04110 for a description of the DeepAR model.

    For additional context and best-practices, see
    https://github.com/.../.../issues/966
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        x_vars: dtfcorutil.NodeColumnList,
        y_vars: dtfcorutil.NodeColumnList,
        trainer_kwargs: Optional[Any] = None,
        estimator_kwargs: Optional[Any] = None,
    ) -> None:
        """
        Initialize dataflow node for gluon-ts DeepAR model.

        :param nid: unique node id
        :param trainer_kwargs: See
          - https://gluon-ts.mxnet.io/api/gluonts/gluonts.trainer.html#gluonts.trainer.Trainer
          - https://github.com/awslabs/gluon-ts/blob/master/src/gluonts/trainer/_base.py
        :param estimator_kwargs: See
          - https://gluon-ts.mxnet.io/api/gluonts/gluonts.model.deepar.html
          - https://github.com/awslabs/gluon-ts/blob/master/src/gluonts/model/deepar/_estimator.py
        :param x_vars: Covariates. Could be, e.g., features associated with a
            point-in-time event. Must be known throughout the prediction
            window at the time the prediction is made.
        :param y_vars: Used in autoregression
        """
        super().__init__(nid)
        self._estimator_kwargs = estimator_kwargs
        # To avoid passing a class through config, handle `Trainer()`
        # parameters separately from `estimator_kwargs`.
        self._trainer_kwargs = trainer_kwargs
        self._trainer = gtrain.Trainer(**self._trainer_kwargs)
        hdbg.dassert_not_in("trainer", self._estimator_kwargs)
        #
        self._estimator_func = gmdeep.DeepAREstimator
        # NOTE: Covariates (x_vars) are not required by DeepAR.
        # TODO(Paul): Allow this model to accept y_vars only.
        #   - This could be useful for, e.g., predicting future values of
        #     what would normally be predictors
        self._x_vars = x_vars
        self._y_vars = y_vars
        self._estimator = None
        self._predictor = None
        # We determine `prediction_length` automatically and therefore do not
        # allow it to be set by the user.
        hdbg.dassert_not_in("prediction_length", self._estimator_kwargs)
        #
        hdbg.dassert_in("freq", self._estimator_kwargs)
        self._freq = self._estimator_kwargs["freq"]

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Fit model to multiple series reflected in multiindexed `df_in`.

        `prediction_length` is autoinferred from the max index of `t_j`, e.g.,
        each `df_in` is assumed to include the index `0` for, e.g.,
        "event time", and indices are assumed to be consecutive integers. So
        if there are time points

            t_{-2} < t_{-1} < t_0 < t_1 < t_2

        then `prediction_length = 2`.
        """
        hdbg.dassert_isinstance(df_in, pd.DataFrame)
        hdbg.dassert_no_duplicates(df_in.columns)
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        df = df_in.copy()
        # Transform dataflow local timeseries dataframe into gluon-ts format.
        gluon_train = cdatadap.transform_to_gluon(df, x_vars, y_vars, self._freq)
        # Set the prediction length to the length of the local timeseries - 1.
        #   - To predict for time t_j at time t_i, t_j > t_i, we need to know
        #     x_vars up to and including time t_j
        #   - For this model, multi-step predictions are equivalent to
        #     iterated single-step predictions
        self._prediction_length = df.index.get_level_values(0).max()
        # Instantiate the (DeepAR) estimator and train the model.
        self._estimator = self._estimator_func(
            prediction_length=self._prediction_length,
            trainer=self._trainer,
            **self._estimator_kwargs,
        )
        self._predictor = self._estimator.train(gluon_train)
        # Apply model predictions to the training set (so that we can evaluate
        # in-sample performance).
        #   - Include all data points up to and including zero (the event time)
        gluon_test = cdatadap.transform_to_gluon(
            df, x_vars, y_vars, self._freq, self._prediction_length
        )
        fit_predictions = list(self._predictor.predict(gluon_test))
        # Transform gluon-ts predictions into a dataflow local timeseries
        # dataframe.
        # TODO(Paul): Gluon has built-in functionality to take the mean of
        #     traces, and we might consider using it instead.
        y_hat_traces = cdatadap.transform_from_gluon_forecasts(fit_predictions)
        # TODO(Paul): Store the traces / dispersion estimates.
        # Average over all available samples.
        y_hat = y_hat_traces.mean(level=[0, 1])
        # Map multiindices to align our prediction indices with those used
        # by the passed-in local timeseries dataframe.
        # TODO(Paul): Do this mapping earlier before removing the traces.
        aligned_idx = y_hat.index.map(
            lambda x: (
                x[0] + 1,
                x[1] - pd.Timedelta(f"1{self._freq}"),
            )
        )
        y_hat.index = aligned_idx
        y_hat.name = str(y_vars[0]) + "_hat"
        y_hat.index.rename(df.index.names, inplace=True)
        # Store info.
        info = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        # TODO(Paul): Consider storing only the head of each list in `info`
        #     for debugging purposes.
        # info["gluon_train"] = list(gluon_train)
        # info["gluon_test"] = list(gluon_test)
        # info["fit_predictions"] = fit_predictions
        df_out = y_hat.to_frame()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        hdbg.dassert_isinstance(df_in, pd.DataFrame)
        hdbg.dassert_no_duplicates(df_in.columns)
        x_vars = dtfcorutil.convert_to_list(self._x_vars)
        y_vars = dtfcorutil.convert_to_list(self._y_vars)
        df = df_in.copy()
        # Transform dataflow local timeseries dataframe into gluon-ts format.
        gluon_test = cdatadap.transform_to_gluon(
            df,
            x_vars,
            y_vars,
            self._freq,
            self._prediction_length,
        )
        predictions = list(self._predictor.predict(gluon_test))
        # Transform gluon-ts predictions into a dataflow local timeseries
        # dataframe.
        # TODO(Paul): Gluon has built-in functionality to take the mean of
        #     traces, and we might consider using it instead.
        y_hat_traces = cdatadap.transform_from_gluon_forecasts(predictions)
        # TODO(Paul): Store the traces / dispersion estimates.
        # Average over all available samples.
        y_hat = y_hat_traces.mean(level=[0, 1])
        # Map multiindices to align our prediction indices with those used
        # by the passed-in local timeseries dataframe.
        # TODO(Paul): Do this mapping earlier before removing the traces.
        aligned_idx = y_hat.index.map(
            lambda x: (
                x[0] + 1,
                x[1] - pd.Timedelta(f"1{self._freq}"),
            )
        )
        y_hat.index = aligned_idx
        y_hat.name = str(y_vars[0]) + "_hat"
        y_hat.index.rename(df.index.names, inplace=True)
        # Store info.
        info = collections.OrderedDict()
        info["model_x_vars"] = x_vars
        # TODO(Paul): Consider storing only the head of each list in `info`
        #     for debugging purposes.
        # info["gluon_train"] = list(gluon_train)
        # info["gluon_test"] = list(gluon_test)
        # info["fit_predictions"] = fit_predictions
        df_out = y_hat.to_frame()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df_out)
        self._set_info("predict", info)
        return {"df_out": df_out}
