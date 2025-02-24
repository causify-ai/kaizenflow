"""
Import as:

import dataflow.core.dag_runner as dtfcodarun
"""

import abc
import logging
from typing import Generator, List, Optional, Tuple

import pandas as pd

import core.config as cconfig
import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import dataflow.core.result_bundle as dtfcorebun
import dataflow.core.utils as dtfcorutil
import dataflow.core.visitors as dtfcorvisi
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################
# DagRunner
# #############################################################################


# TODO(gp): At hindsight a `DagRunner` just calls methods on a DAG so we could
#  merge the code into the DAG to simplify the class system. If we wanted to
#  keep the behaviors separated, we could use mixins like `FitPredictDag`.
# TODO(gp): This has specific code for `fit` and `predict` so we should rename
#  appropriately (_FitPredictDagRunnerMixin?). Maybe we just need a `DagRunner(
#  abc.ABC)` as placeholder.
class DagRunner(abc.ABC, hobject.PrintableMixin):
    """
    Abstract class with the common code to all `DagRunner`s.

    A `DagRunner` receives a `DAG` and allows to run methods on it (e.g., `fit()`
    and `predict()`).

    There is not a method common to all `DagRunner`s that is abstract,
    so we use `abc.ABC` to guarantee that this class is not instantiated
    directly.
    """

    def __init__(self, dag: dtfcordag.DAG) -> None:
        """
        Constructor.

        :param dag: `DAG` instance
        """
        # Save dag
        hdbg.dassert_isinstance(dag, dtfcordag.DAG)
        self.dag = dag
        # TODO(gp): Not sure what to do here.
        self.config = cconfig.Config()
        # We should pass None to `ResultBundle` in order not to rely on the
        # default value in `ResultBundle`.
        self._column_to_tags_mapping = None
        # Extract the sink node.
        self._result_nid = self.dag.get_unique_sink()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("_result_nid=%s", self._result_nid)

    # ///////////////////////////////////////////////////////////////////////////
    # Print.
    # ///////////////////////////////////////////////////////////////////////////

    def __str__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(
            [
                "dag",
            ]
        )
        return super().__str__(attr_names_to_skip=attr_names_to_skip)

    def __repr__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(
            [
                "dag",
            ]
        )
        return super().__repr__(attr_names_to_skip=attr_names_to_skip)

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    def _set_fit_predict_intervals(
        self, method: dtfcornode.Method, intervals: Optional[dtfcorutil.Intervals]
    ) -> None:
        """
        Set fit or predict intervals for all the source nodes.

        :param method: method to run
        :param intervals: as in `DataSource` node, but allowing `None` to mean no
            interval
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("method intervals"))
        if intervals is None:
            return
        # Propagate the intervals to all source nodes.
        for input_nid in self.dag.get_sources():
            node = self.dag.get_node(input_nid)
            if method == "fit":
                node.set_fit_intervals(intervals)
            elif method == "predict":
                node.set_predict_intervals(intervals)
            else:
                raise ValueError("Invalid method='%s'" % method)

    def _run_dag_helper(
        self, method: dtfcornode.Method
    ) -> Tuple[pd.DataFrame, dtfcorvisi.NodeInfo]:
        """
        Run the DAG for the given method.

        :param method: method to run
        :return: the dataframe for the only output and the associated
            Info
        """
        nid = self._result_nid
        # TODO(gp): Add a check for `df_out`.
        df_out = self.dag.run_leq_node(nid, method)["df_out"]
        info = dtfcorvisi.extract_info(self.dag, [method])
        return df_out, info

    # TODO(gp): This could be folded into `_run_dag_helper()` if we collapse
    #  `ResultBundle` and `PredictionResultBundle`.
    def _to_result_bundle(
        self,
        method: dtfcornode.Method,
        df_out: pd.DataFrame,
        info: dtfcorvisi.NodeInfo,
    ) -> dtfcorebun.ResultBundle:
        """
        Package the result of a DAG execution into a ResultBundle.
        """
        return dtfcorebun.ResultBundle(
            config=self.config,
            result_nid=self._result_nid,
            method=method,
            result_df=df_out,
            column_to_tags=self._column_to_tags_mapping,
            info=info,
        )


# #############################################################################
# FitPredictDagRunner
# #############################################################################


class FitPredictDagRunner(DagRunner):
    """
    Run DAGs that have fit / predict methods.
    """

    def set_fit_intervals(
        self, intervals: Optional[dtfcorutil.Intervals]
    ) -> None:
        """
        Set fit intervals for all the source nodes.

        :param intervals: as in `DataSource` node, but allowing `None`
        """
        method = "fit"
        self._set_fit_predict_intervals(method, intervals)

    def set_predict_intervals(
        self, intervals: Optional[dtfcorutil.Intervals]
    ) -> None:
        """
        Set predict intervals for all the source nodes.

        :param intervals: as in `DataSource` node, but allowing `None`
        """
        method = "predict"
        self._set_fit_predict_intervals(method, intervals)

    def fit(self) -> dtfcorebun.ResultBundle:
        """
        Fitting means running `fit()` method on the DAG up to the sink node.
        """
        method = "fit"
        return self._run_dag(method)

    def predict(self) -> dtfcorebun.ResultBundle:
        """
        Predicting means running `predict()` method on the DAG up to the sink
        node.
        """
        method = "predict"
        return self._run_dag(method)

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    def _run_dag(self, method: dtfcornode.Method) -> dtfcorebun.ResultBundle:
        df_out, info = self._run_dag_helper(method)
        return self._to_result_bundle(method, df_out, info)


# #############################################################################
# PredictionDagRunner
# #############################################################################


# TODO(gp): This is obsolete.
class PredictionDagRunner(FitPredictDagRunner):
    """
    Run prediction DAGs.

    Identical to `FitPredictDagRunner`, but returning a
    `PredictionResultBundle`.
    """

    def _run_dag(
        self, method: dtfcornode.Method
    ) -> dtfcorebun.PredictionResultBundle:
        """
        Same as super class but return a `PredictionResultBundle`.
        """
        df_out, info = self._run_dag_helper(method)
        return dtfcorebun.PredictionResultBundle(
            config=self.config,
            result_nid=self._result_nid,
            method=method,
            result_df=df_out,
            column_to_tags=self._column_to_tags_mapping,
            info=info,
        )


# #############################################################################
# RollingFitPredictDagRunner
# #############################################################################


# oos_start_dt (e.g., 2020-01-01)
# oos_end_dt (e.g., 2020-01-31)
# oos_end_dt - history_length (e.g., 2019-12-01)
#

# def __init__(
#         dag,
#         predict_start_timestamp,
#         predict_end_timestamp,
#         history_length_as_pd_timedelta,
#         retraining_freq_with_offset,
# ):

# retraining_freq_with_offset doesn't have to be equally spaced but it needs to be
# "independent" on the grid (e.g., every week on Monday, every first day of the month)

# - predict_start_dt, predict_end_dt (e.g., [2020-01-01, 2020-01-31])
# Each training requires 2 months of data
# Re-training happens on Monday every week
# The intervals for fitting are
# [2019-12-30 - 2 months, Dec 30, 2019] -> predict [Dec 31, 2019, Jan 1, 2020]
# [2020-01-06 - 2 months, 2019, Jan 6, 2020] -> predict [Jan 1, 2020, Jan 8, 2020]
# ...

# fit_start_dt, fit_end_dt (e.g., [2019-12-01, 2020-01-01])
#   the only constraint on how data beside the tile is provided is just to
#   accommodate on the first tile
# retraining_freq (e.g., 1W)
# retraining_lookback

# Given the predict period of time, find retraining days such that overlap


class RollingFitPredictDagRunner(DagRunner):
    """
    Run a `DAG` by periodic fitting on previous history and evaluating on new
    data.
    """

    def __init__(
        self,
        dag: dtfcordag.DAG,
        predict_start_timestamp: pd.Timestamp,
        predict_end_timestamp: pd.Timestamp,
        retraining_freq: str,
        retraining_lookback: int,
    ) -> None:
        """
        Constructor.

        :param predict_start_timestamp: start of predict window
        :param predict_end_timestamp: end of predict window
        :param retraining_freq: how often to retrain using Pandas frequency
            convention (e.g., `2B`). The frequency should be such that it's
            independent of `predict_start_timestamp` and `predict_end_timestamp`
            (since we want the retraining grid to be independent on the tiling).
            E.g., "7D" is not the same as "1W" because with "7D" Pandas starts
            sampling from predict_start_timestamp, while "1W" aligns on Sundays
        :param retraining_lookback: number of periods of past data to include
            in retraining, expressed in integral units of `retraining_freq`
        """
        super().__init__(dag)
        # Save input parameters.
        hdbg.dassert_isinstance(predict_start_timestamp, pd.Timestamp)
        self._predict_start_timestamp = predict_start_timestamp
        hdbg.dassert_isinstance(predict_end_timestamp, pd.Timestamp)
        hdbg.dassert_lt(predict_start_timestamp, predict_end_timestamp)
        self._predict_end_timestamp = predict_end_timestamp
        hdbg.dassert_isinstance(retraining_freq, str)
        self._retraining_freq = retraining_freq
        hdbg.dassert_isinstance(retraining_lookback, int)
        self._retraining_lookback = retraining_lookback
        # Generate retraining dates.
        self._retraining_datetimes = self.generate_retraining_datetimes(
            predict_start_timestamp=self._predict_start_timestamp,
            predict_end_timestamp=self._predict_end_timestamp,
            retraining_freq=self._retraining_freq,
            retraining_lookback=self._retraining_lookback,
        )
        _LOG.info("_retraining_datetimes=%s", self._retraining_datetimes)

    # TODO(Paul): Encode the fit / predict.
    @staticmethod
    def generate_retraining_datetimes(
        predict_start_timestamp: pd.Timestamp,
        predict_end_timestamp: pd.Timestamp,
        retraining_freq: str,
        retraining_lookback: int,
    ) -> pd.DataFrame:
        """
        Generate an index of retraining dates based on specs.

        The input parameters have the same meaning as in the
        constructor.

        :return: (re)training dates
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "predict_start_timestamp predict_end_timestamp "
                    "retraining_freq retraining_lookback"
                )
            )
        # Only certain retraining frequencies are supported.
        retraining_freq_tail = retraining_freq[-1]
        hdbg.dassert_in(
            retraining_freq_tail,
            ["H", "D", "W", "M", "Q"],
            "retraining_freq=%s is not supported",
            retraining_freq,
        )
        retraining_freq_timedelta = pd.Timedelta(retraining_freq)
        retraining_lookback_timedelta = (
            retraining_lookback * retraining_freq_timedelta
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "Amount of training data required=%s",
                retraining_lookback_timedelta,
            )
        # Generate a date series based upon predict start/end timestamps and the
        #  required amount of training data.
        normalized_predict_start_timestamp = (
            RollingFitPredictDagRunner._left_align_timestamp_on_grid(
                predict_start_timestamp, retraining_freq
            )
        )
        normalized_predict_end_timestamp = (
            RollingFitPredictDagRunner._left_align_timestamp_on_grid(
                predict_end_timestamp, retraining_freq
            )
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("date_range start=%s", normalized_predict_start_timestamp)
            _LOG.debug("date_range end=%s", normalized_predict_end_timestamp)
        # Compute the start datetimes for prediction.
        predict_start_datetimes = pd.date_range(
            normalized_predict_start_timestamp,
            normalized_predict_end_timestamp,
            freq=retraining_freq,
        )
        predict_start_datetimes = pd.Series(data=predict_start_datetimes)
        predict_start_datetimes.name = "predict_start"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "predict_start_datetimes=%s",
                hpandas.df_to_str(predict_start_datetimes),
            )
        # Compute the end datetimes for prediction.
        predict_end_datetimes = pd.date_range(
            normalized_predict_start_timestamp + retraining_freq_timedelta,
            normalized_predict_end_timestamp + retraining_freq_timedelta,
            freq=retraining_freq,
        ) - pd.Timedelta("1D")
        predict_end_datetimes = pd.Series(data=predict_end_datetimes)
        predict_end_datetimes.name = "predict_end"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "predict_start_datetimes=%s",
                hpandas.df_to_str(predict_end_datetimes),
            )
        # Compute the start datetimes for fitting.
        fit_start_datetimes = (
            predict_start_datetimes - retraining_lookback_timedelta
        )
        fit_start_datetimes = pd.Series(data=fit_start_datetimes)
        fit_start_datetimes.name = "fit_start"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "fit_start_datetimes=%s", hpandas.df_to_str(fit_start_datetimes)
            )
        # Compute the end datetimes for fitting.
        fit_end_datetimes = predict_start_datetimes - pd.Timedelta("1D")
        fit_end_datetimes = pd.Series(data=fit_end_datetimes)
        fit_end_datetimes.name = "fit_end"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "fit_end_datetimes=%s", hpandas.df_to_str(fit_end_datetimes)
            )
        #
        df = pd.concat(
            [
                fit_start_datetimes,
                fit_end_datetimes,
                predict_start_datetimes,
                predict_end_datetimes,
            ],
            axis=1,
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=%s", hpandas.df_to_str(df))
        return df

    def fit_predict(self) -> Generator:
        """
        Fit at each retraining date and predict until next retraining date.

        :return: the training time, fit `ResultBundle`, predict `ResultBundle`
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "retraining_datetimes=%s",
                hpandas.df_to_str(self._retraining_datetimes),
            )
        for row in self._retraining_datetimes.iterrows():
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("row=%s", row)
                _LOG.debug("fit/predict cycle=%d", row[0])
            #
            fit_start = row[1].fit_start
            fit_end = row[1].fit_end
            fit_interval = (fit_start, fit_end)
            fit_result_bundle = self._fit(fit_interval)
            #
            predict_start = row[1].predict_start
            predict_end = row[1].predict_end
            predict_interval = (fit_start, predict_end)
            predict_result_bundle = self._predict(predict_interval, predict_start)
            # TODO(gp): Better to return a pd.Timestamp rather than its representation.
            training_datetime_str = fit_start.strftime("%Y%m%d_%H%M%S")
            yield training_datetime_str, fit_result_bundle, predict_result_bundle

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _left_align_timestamp_on_grid(
        timestamp: pd.Timestamp,
        freq: str,
    ) -> pd.Timestamp:
        hdbg.dassert_isinstance(timestamp, pd.Timestamp)
        hdbg.dassert_isinstance(freq, str)
        left_aligned_timestamp = (
            pd.Series(index=pd.date_range(timestamp, periods=1))
            .resample(
                freq,
                closed="left",
                label="left",
            )
            .last()
            .index[0]
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "timestamp `%s` left aligned to `%s`",
                timestamp,
                left_aligned_timestamp,
            )
        return left_aligned_timestamp

    def _fit(
        self,
        interval: dtfcorutil.Intervals,
    ) -> dtfcorebun.ResultBundle:
        # Set fit interval on all source nodes of the DAG.
        for input_nid in self.dag.get_sources():
            node = self.dag.get_node(input_nid)
            node.set_fit_intervals([interval])
        # Fit.
        method = "fit"
        df_out, info = self._run_dag_helper(method)
        return self._to_result_bundle(method, df_out, info)

    def _predict(
        self,
        # TODO(gp): Use Interval
        interval: dtfcorutil.Intervals,
        oos_start: hdateti.Datetime,
    ) -> dtfcorebun.ResultBundle:
        # Set predict interval on all source nodes of the DAG.
        for input_nid in self.dag.get_sources():
            self.dag.get_node(input_nid).set_predict_intervals([interval])
        # Predict.
        method = "predict"
        df_out, info = self._run_dag_helper(method)
        # Restrict `df_out` to out-of-sample portion.
        df_out = df_out.loc[oos_start:]
        return self._to_result_bundle(method, df_out, info)

    def _run_dag(self, method: dtfcornode.Method) -> dtfcorebun.ResultBundle:
        """
        Run DAG and return a ResultBundle.
        """
        df_out, info = self._run_dag_helper(method)
        return self._to_result_bundle(method, df_out, info)


# #############################################################################
# IncrementalDagRunner
# #############################################################################


# TODO(gp): This might be obsolete.
class IncrementalDagRunner(DagRunner):
    """
    Run DAGs in incremental fashion, i.e., running one step at a time.

    # TODO(gp): Improve description.
    """

    def __init__(
        self,
        dag: dtfcordag.DAG,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        freq: str,
        fit_state: cconfig.Config,
    ) -> None:
        """
        Constructor.

        :param dag: `DAG` instance
        :param start_timestamp: first prediction datetime_ (e.g., first time at which we
            generate a prediction in `predict` mode, using all available data
            up to and including `start`)
        :param end_timestamp: last prediction datetime_
        :param freq: prediction frequency (typically the same as the frequency
            of the underlying DAG)
        :param fit_state: Config containing any learned state required for
            initializing the DAG
        """
        super().__init__(dag)
        self._start_timestamp = start_timestamp
        self._end_timestamp = end_timestamp
        self._freq = freq
        self._fit_state = fit_state
        dtfcorvisi.set_fit_state(self.dag, self._fit_state)
        # Create predict range.
        self._date_range = pd.date_range(
            start=self._start_timestamp, end=self._end_timestamp, freq=self._freq
        )

    def predict(self) -> Generator:
        """
        Generate a filtration and predict at each index of the filtration.

        Here we use "filtration" as it is used in the context of stochastic
        processes. To ensure that predictions are non-anticipating, we restrict
        the model inputs to times up to and including the prediction time.

        :return: a generator of `ResultBundle`s (one `ResultBundle` for each
            prediction)
        """
        for end_dt in self._date_range:
            result_bundle = self.predict_at_datetime(end_dt)
            yield result_bundle

    # TODO(gp): dt -> timestamp as used elsewhere.
    def predict_at_datetime(
        self, dt: hdateti.Datetime
    ) -> dtfcorebun.ResultBundle:
        """
        Generate a prediction as of `dt` (for a future point in time).

        :param dt: point in time at which to generate a prediction
        :return: populated `ResultBundle`
        """
        # Cut off data at `end_dt`. Do not restrict the start datetime_ so
        # so as not to adversely affect any required warm-up period.
        interval = [(None, dt)]
        # Set prediction intervals and predict.
        for input_nid in self.dag.get_sources():
            self.dag.get_node(input_nid).set_predict_intervals(interval)
        result_bundle = self._run_dag("predict")
        return result_bundle

    def _run_dag(self, method: dtfcornode.Method) -> dtfcorebun.ResultBundle:
        """
        Run DAG and return a ResultBundle.
        """
        df_out, info = self._run_dag_helper(method)
        return self._to_result_bundle(method, df_out, info)
