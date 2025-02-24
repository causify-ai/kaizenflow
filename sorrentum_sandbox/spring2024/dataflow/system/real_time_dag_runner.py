"""
Import as:

import dataflow.system.real_time_dag_runner as dtfsrtdaru
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import core.config as cconfig
import core.real_time as creatime
import dataflow.core as dtfcore
import dataflow.system.sink_nodes as dtfsysinod
import dataflow.system.source_nodes as dtfsysonod
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.htimer as htimer
import helpers.hwall_clock_time as hwacltim

_LOG = logging.getLogger(__name__)


# TODO(Paul): Consider renaming `EventLoopDagRunner`.
class RealTimeDagRunner(dtfcore.DagRunner):
    """
    Run a DAG in true or simulated real-time.

    A DAG can be executed in real-time if one of the source nodes has a notion of
    time and emits different data for the same invocation because time has elapsed.

    See:
    - `real_time.py` for definitions of different types of real-time executions
    - `_AbstractRealTimeDataSource` and descendants for nodes with real-time semantic
    """

    def __init__(
        self,
        dag: dtfcore.DAG,
        fit_state: cconfig.Config,
        execute_rt_loop_kwargs: Dict[str, Any],
        dst_dir: str,
        *,
        fit_at_beginning: bool = False,
        get_wall_clock_time: Optional[hdateti.GetWallClockTime] = None,
        wake_up_timestamp: Optional[pd.Timestamp] = None,
        bar_duration_in_secs: Optional[int] = None,
        set_current_bar_timestamp: bool = True,
        # TODO(Danya): -> `max_allowed_delay_from_bar_start_in_secs`.
        max_distance_in_secs: int = 30,
    ) -> None:
        """
        Build object.

        :param dag: DAG to execute
        :param fit_state: configures `fit()`
        :param execute_rt_loop_kwargs: configures
            `execute_with_real_time_loop()`
        :param dst_dir: directory where to save the results
        :param fit_at_beginning: force the system to fit before making
            predictions
        :param get_wall_clock_time: wall clock to use
        :param wake_up_timestamp: timestamp to wait to start the
            execution (e.g., 9:30am)
        :param bar_duration_in_secs: duration of a bar (e.g., 5 mins =
            300 secs)
        :param set_current_bar_timestamp: True if we need to set the
            timestamp of the bar. It requires bar_duration_in_secs to be
            a multiple of 60 secs, since for now we support only bars
            that last a multiple of one minute.
        :param max_distance_in_secs: maximal distance that is allowed
            from the start of the bar.
        """
        super().__init__(dag)
        # Save input parameters.
        # TODO(gp): Use this for stateful DAGs.
        _ = fit_state
        self._execute_rt_loop_kwargs = execute_rt_loop_kwargs
        self._dst_dir = dst_dir
        self._fit_at_beginning = fit_at_beginning
        self._get_wall_clock_time = get_wall_clock_time
        self._wake_up_timestamp = wake_up_timestamp
        self._bar_duration_in_secs = bar_duration_in_secs
        self._set_current_bar_timestamp = set_current_bar_timestamp
        self._max_distance_in_secs = max_distance_in_secs
        # Store information about the real-time execution.
        self._events: creatime.Events = []
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("After RealTimeDagRunner ctor: \n%s", repr(self))

    @property
    def events(self) -> Optional[creatime.Events]:
        return self._events

    async def predict(self) -> List[dtfcore.ResultBundle]:
        """
        Execute the DAG for all the events.

        This adapts the asynchronous generator to a synchronous semantic.

        :return: list of `ResultBundle`, one per execution
        """
        if self._fit_at_beginning:
            _LOG.info("Fitting model")
            # TODO(gp): For now we assume that the ML node is called "predict",
            #  we should check that there is a node that has state.
            hdbg.dassert(self.dag._nx_dag.has_node("predict"))
            method = "fit"
            await self._run_dag(method)
            _LOG.info("dag after fit=\n%s", str(self.dag))
            fit_state = self.dag.get_node("predict").get_fit_state()
            _LOG.info("fit_state=\n%s", str(fit_state))
        # Wait until time to wake up and start execution.
        if self._wake_up_timestamp is not None:
            # TODO(gp): Add a check to make sure that all the params are set up
            #  consistently.
            await self._wait_for_start_trading()
        # Align on the bar.
        await self._align_on_grid()
        # Reset the current bar, if needed.
        if self._set_current_bar_timestamp:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Resetting current bar time")
            hwacltim.reset_current_bar_timestamp()
        # Start loop.
        result_bundles: List[dtfcore.ResultBundle] = []
        # We need to set the first bar outside the loop so that
        # `predict_at_datetime()` can recover the current bar time.
        self._apply_current_bar_timestamp()
        async for result_bundle in self.predict_at_datetime():
            self._apply_current_bar_timestamp()
            result_bundles.append(result_bundle)
        return result_bundles

    async def predict_at_datetime(self) -> dtfcore.ResultBundle:
        """
        Predict every time there is a real-time event.

        :return: list of `ResultBundle`, one per event
        """
        method = "predict"
        # Adapt `_dag_workload()` to the expected call back signature.
        workload = lambda current_time: self._run_dag(method)
        # Call the event loop.
        async for event, result_bundle in creatime.execute_with_real_time_loop(
            **self._execute_rt_loop_kwargs, workload=workload
        ):
            self._events.append(event)
            yield result_bundle

    def compute_run_signature(
        self, result_bundles: List[dtfcore.ResultBundle]
    ) -> str:
        """
        Compute a signature of an execution in terms of `ResultBundles` and
        `events`.
        """
        ret = []
        events = self.events
        hdbg.dassert_eq(len(events), len(result_bundles))
        for event, result_bundle in zip(events, result_bundles):
            event_as_str = event.to_str(
                include_tenths_of_secs=False, include_wall_clock_time=False
            )
            ret.append(hprint.frame(event_as_str))
            ret.append("result_bundle=\n%s" % str(result_bundle))
        ret = "\n".join(ret)
        return ret

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    async def _wait_for_start_trading(self) -> None:
        """
        Wait until `wake_up_timestamp` passed in the constructor (e.g.,
        9:45am).

        This is used when we need to wait for a certain time before
        starting the execution loop.
        """
        # The system should come up sometime before the first bar (e.g., around
        # 9:37am ET) and then we align to the next trading bar.
        current_timestamp = self._get_wall_clock_time()
        _LOG.info("Current time=%s", current_timestamp)
        wake_up_timestamp = self._wake_up_timestamp
        _LOG.info("Waiting until session start at %s ...", wake_up_timestamp)
        await hasynci.async_wait_until(
            wake_up_timestamp, self._get_wall_clock_time
        )
        _LOG.info("Waiting ... done")
        current_timestamp = self._get_wall_clock_time()
        _LOG.info(
            "Current time=%s: session started at %s",
            current_timestamp,
            wake_up_timestamp,
        )

    async def _align_on_grid(self) -> None:
        """
        Align the execution on a grid with spacing given by
        `bar_duration_in_secs`.

        E.g., if we want to execute a graph every 5 minutes, we need to
        wait until the current time is a multiple of 5 minutes.
        """
        get_wall_clock_time = self._get_wall_clock_time
        # If the system comes up in the middle of the day then we need to wait to
        # align to a bar.
        # Align on the trading grid (e.g., 1, 5, 15 minutes).
        bar_duration_in_secs = self._bar_duration_in_secs
        _LOG.info("Aligning on a bar lasting %s secs ...", bar_duration_in_secs)
        # Add one second to make sure we are after the start trading time.
        add_buffer_in_secs = 1
        target_time, secs_to_wait = hasynci.get_seconds_to_align_to_grid(
            bar_duration_in_secs,
            get_wall_clock_time,
            add_buffer_in_secs=add_buffer_in_secs,
        )
        await hasynci.async_wait_until(target_time, get_wall_clock_time)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Aligning ... done")

    def _apply_current_bar_timestamp(self) -> None:
        if self._set_current_bar_timestamp:
            # TODO(gp): This is similar to `hdateti.set_current_bar_timestamp()`.
            #  Consider factoring it out.
            # Compute the current bar by snapping the current timestamp to the
            # grid.
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Setting current bar time")
            current_timestamp = self._get_wall_clock_time()
            mode = "round"
            bar_timestamp = hdateti.find_bar_timestamp(
                current_timestamp,
                self._bar_duration_in_secs,
                mode=mode,
                max_distance_in_secs=self._max_distance_in_secs,
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(hprint.to_str("current_timestamp bar_timestamp"))
            _LOG.info("\n%s", hprint.frame("bar_timestamp=%s" % bar_timestamp))
            hwacltim.set_current_bar_timestamp(bar_timestamp)

    async def _run_dag(self, method: dtfcore.Method) -> dtfcore.ResultBundle:
        # Wait until all the real-time source nodes are ready to compute.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Waiting for real-time nodes to be ready ...")
        sources = self.dag.get_sources()
        for nid in sources:
            node = self.dag.get_node(nid)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "nid=%s node=%s type=%s", nid, str(node), str(type(node))
                )
            if isinstance(node, dtfsysonod.HistoricalDataSource):
                raise ValueError(
                    f"HistoricalDataSource node {node} not allowed "
                    "in RealTimeDagRunner"
                )
            if isinstance(node, dtfsysonod.RealTimeDataSource):
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug("Waiting on node '%s' ...", str(nid))
                with htimer.TimedScope(
                    logging.INFO, "wait_for_latest_data"
                ) as ts1:
                    await node.wait_for_latest_data()
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug("Waiting on node '%s': done", str(nid))
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Waiting for real-time nodes to be ready: done")
        # Execute the DAG.
        with htimer.TimedScope(logging.INFO, "_run_dag_helper") as ts2:
            df_out, info = self._run_dag_helper(method)
        # Wait for the sinks to complete.
        # TODO(gp): Find ProcessForecast. We can also create an abstract class
        #  AwaitableNode with a `wait()` method and then wait on all the
        #  sources and sinks that are awaitable.
        nid = self.dag.get_unique_sink()
        node = self.dag.get_node(nid)
        if isinstance(node, dtfsysinod.ProcessForecastsNode):
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Waiting on node '%s' ...", str(nid))
            with htimer.TimedScope(logging.INFO, "process_forecasts") as ts3:
                await node.process_forecasts()
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Waiting on node '%s': done", str(nid))
        #
        return self._to_result_bundle(method, df_out, info)
