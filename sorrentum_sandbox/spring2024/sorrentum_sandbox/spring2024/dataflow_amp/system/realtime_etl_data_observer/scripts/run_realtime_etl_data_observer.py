#!/usr/bin/env python

import logging
from typing import List

import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.system.real_time_dag_runner as dtfsrtdaru
import dataflow.system.source_nodes as dtfsysonod
import dataflow_amp.pipelines.realtime_etl_data_observer.realtime_etl_data_observer_pipeline as dtfapredoredop
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import market_data.market_data_example as mdmadaex

hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)


def run() -> List[dtfcore.ResultBundle]:
    # 1) Generate synthetic OHLCV data.
    tz = "America/New_York"
    start_datetime = pd.Timestamp("2023-01-03 09:35:00", tz=tz)
    end_datetime = pd.Timestamp("2023-01-03 11:30:00", tz=tz)
    asset_ids = [101, 201, 301]
    columns = ["open", "high", "low", "close", "volume"]
    freq = "1S"
    market_data = cofinanc.generate_random_price_data(
        start_datetime, end_datetime, columns, asset_ids, freq=freq
    )
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hpandas.df_to_str(market_data))
    # 2) Create an event loop.
    with hasynci.solipsism_context() as event_loop:
        # 3) Instantiate `ReplayedMarketData`.
        # Use minimum bar end timestamp as a starting point.
        data_start_timestamp = market_data["end_datetime"].min()
        # How much history is needed, it loads in the interval [wall_clock_time - timedelta, wall_clock_time).
        timedelta = pd.Timedelta("1S")
        # Replay data forward a bit so that there is enough history to load the first bar. E.g., if we start
        # at 09:35:01, it will try to load [09:35:00, 09:35:01) using `end_ts` -> the resulting df will be
        # empty.
        replayed_delay_in_mins_or_timestamp = data_start_timestamp + timedelta
        (
            replayed_market_data,
            get_wall_clock_time,
        ) = mdmadaex.get_ReplayedTimeMarketData_from_df(
            event_loop, replayed_delay_in_mins_or_timestamp, market_data
        )
        # 4) Build `RealTimeDataSource`.
        knowledge_datetime_col_name = "timestamp_db"
        multiindex_output = True
        replayed_market_data_node = dtfsysonod.RealTimeDataSource(
            "replayed_market_data",
            replayed_market_data,
            timedelta,
            knowledge_datetime_col_name,
            multiindex_output,
        )
        # 5) Build a `DataObserver` DAG with `RealTimeDataSource`.
        dag_builder = dtfapredoredop.Realtime_etl_DataObserver_DagBuilder()
        dag_config = dag_builder.get_config_template()
        dag = dag_builder.get_dag(dag_config)
        dag.insert_at_head(replayed_market_data_node)
        # 6) Build a `RealTimeDagRunner`.
        bar_duration_in_secs = 1
        # Run the loop for 10 seconds.
        rt_timeout_in_secs_or_time = 10 * bar_duration_in_secs
        execute_rt_loop_kwargs = {
            # Should be the same clock as in `ReplayedMarketData`.
            "get_wall_clock_time": get_wall_clock_time,
            "bar_duration_in_secs": bar_duration_in_secs,
            "rt_timeout_in_secs_or_time": rt_timeout_in_secs_or_time,
        }
        dag_runner_kwargs = {
            "dag": dag,
            "fit_state": None,
            "execute_rt_loop_kwargs": execute_rt_loop_kwargs,
            "dst_dir": None,
            "get_wall_clock_time": get_wall_clock_time,
            "bar_duration_in_secs": bar_duration_in_secs,
            # We don't want to set the current bar in this test.
            # "set_current_bar_timestamp": False,
            "set_current_bar_timestamp": True,
        }
        # 7) Run the `DAG` using a simulated clock.
        dag_runner = dtfsrtdaru.RealTimeDagRunner(**dag_runner_kwargs)
        result_bundles = hasynci.run(dag_runner.predict(), event_loop=event_loop)
        _ = dag_runner.events
    return result_bundles


if __name__ == "__main__":
    run()
