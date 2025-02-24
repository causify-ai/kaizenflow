"""
Import as:

import dataflow.system.real_time_dag_adapter as dtfsrtdaad
"""
import logging
from typing import Any, Dict

import pandas as pd

import dataflow.core as dtfcore
import dataflow.system.sink_nodes as dtfsysinod
import dataflow.system.source_nodes as dtfsysonod
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import market_data as mdata

_LOG = logging.getLogger(__name__)

# TODO(gp): -> adapt_dag_to_real_time.py or something more general like adapt_dag.py


def adapt_dag_to_real_time(
    dag: dtfcore.DAG,
    market_data: mdata.MarketData,
    # TODO(gp): This could become a market_data_dict
    market_data_history_lookback: pd.Timedelta,
    process_forecasts_node_dict: Dict[str, Any],
    # TODO(gp): Move after market_data_history_lookback.
    ts_col_name: str,
) -> dtfcore.DAG:
    """
    Insert a `RealTimeDataSource` node at the beginning of a DAG and a
    `ProcessForecasts` at the end of a DAG. The DAG needs to have a single
    source and sink to be compatible with this operation.

    This function is equivalent to the old approach of
    `RealTimeDagAdapter`, but working on the `DAG` directly instead of a
    `DagBuilder`.
    """
    hdbg.dassert_isinstance(process_forecasts_node_dict, dict)
    # Add the `DataSource` node.
    stage = "read_data"
    multiindex_output = True
    # ts_col_name = "timestamp_db"
    # col_names_to_remove = ["start_time"]  # , "timestamp_db"]
    node = dtfsysonod.RealTimeDataSource(
        stage,
        market_data,
        market_data_history_lookback,
        ts_col_name,
        multiindex_output,
    )
    dag.insert_at_head(node)
    # Add the `ProcessForecast` node.
    stage = "process_forecasts"
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("stage process_forecasts_node_dict"))
    node = dtfsysinod.ProcessForecastsNode(stage, **process_forecasts_node_dict)
    dag.append_to_tail(node)
    return dag
