"""
Import as:

import dataflow_amp.system.mock1.mock1_builders as dtfasmmobu
"""
import logging
from typing import Any, Dict

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import market_data as mdata

_LOG = logging.getLogger(__name__)

# TODO(gp): -> mock1_system_builder.py? What's the convention now?

# #############################################################################
# Market data instances
# #############################################################################


def get_Mock1_MarketData_example2(
    system: dtfsys.System,
) -> mdata.ImClientMarketData:
    """
    Build a historical ImClientMarketData from a `System.config`.
    """
    im_client = dtfsys.build_ImClient_from_System(system)
    asset_ids = system.config["market_data_config", "asset_ids"]
    # TODO(gp): Specify only the columns that are needed.
    columns = None
    columns_remap = None
    market_data = mdata.get_HistoricalImClientMarketData_example1(
        im_client, asset_ids, columns, columns_remap
    )
    return market_data


# #############################################################################
# Process forecasts configs.
# #############################################################################


def get_Mock1_ProcessForecastsNode_dict_example1(
    system: dtfsys.System,
) -> Dict[str, Any]:
    """
    Get the dictionary with `ProcessForecastsNode` config params for Mock1
    pipeline.
    """
    prediction_col = "feature1"
    volatility_col = "vwap.ret_0.vol"
    spread_col = None
    order_config = {
        "order_type": "price@twap",
        "passivity_factor": None,
        "order_duration_in_mins": 5,
        "execution_frequency": "1T",
    }
    compute_target_positions_kwargs = {
        "bulk_frac_to_remove": 0.0,
        "bulk_fill_method": "zero",
        "target_gmv": 1e5,
    }
    optimizer_config = {
        "backend": "pomo",
        "asset_class": "equities",
        "apply_cc_limits": None,
        "params": {
            "style": "cross_sectional",
            "kwargs": compute_target_positions_kwargs,
        },
    }
    root_log_dir = None
    process_forecasts_dict = dtfsys.get_ProcessForecastsNode_dict_example1(
        system.portfolio,
        prediction_col,
        volatility_col,
        spread_col,
        order_config,
        optimizer_config,
        root_log_dir,
    )
    return process_forecasts_dict


# #############################################################################
# DAG instances.
# #############################################################################


def get_Mock1_HistoricalDag_example1(
    system: dtfsys.System, timestamp_column_name: str
) -> dtfcore.DAG:
    """
    Build a DAG with `HistoricalDataSource` for simulation.
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    # Create HistoricalDataSource.
    stage = "read_data"
    market_data = system.market_data
    multiindex_output = True
    col_names_to_remove = ["start_ts"]
    node = dtfsys.HistoricalDataSource(
        stage,
        market_data,
        timestamp_column_name,
        multiindex_output,
        col_names_to_remove=col_names_to_remove,
    )
    dag = dtfsys.build_dag_with_data_source_node(system, node)
    return dag


# TODO(Grisha): -> `..._example1`.
def get_Mock1_RealtimeDag_example2(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build a DAG with `RealTimeDataSource`.
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    # How much history is needed for the DAG to compute.
    history_lookback = system.config.get_and_mark_as_used(
        ("market_data_config", "days")
    )
    system = dtfsys.apply_history_lookback(system, days=history_lookback)
    dag = dtfsys.add_real_time_data_source(system)
    return dag


# TODO(Grisha): -> `..._example2`.
def get_Mock1_RealtimeDag_example3(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build a DAG with `RealTimeDataSource` and `ForecastProcessorNode`.
    """
    # How much history is needed for the DAG to compute.
    history_lookback = system.config.get_and_mark_as_used(
        ("market_data_config", "history_lookback")
    )
    system = dtfsys.apply_history_lookback(system, days=history_lookback)
    dag = dtfsys.add_real_time_data_source(system)
    # Configure a `ProcessForecastNode`.
    # TODO(gp): Factor out this idiom in a function `config_update()`.
    process_forecasts_node_dict = get_Mock1_ProcessForecastsNode_dict_example1(
        system
    )
    process_forecasts_node_config = cconfig.Config.from_dict(
        process_forecasts_node_dict
    )
    if "process_forecasts_node_dict" in system.config:
        process_forecasts_node_config.update(
            system.config["process_forecasts_node_dict"]
        )
    system.config["process_forecasts_node_dict"] = process_forecasts_node_config
    system = dtfsys.apply_ProcessForecastsNode_config_for_equities(system)
    # Append the `ProcessForecastNode`.
    dag = dtfsys.add_ProcessForecastsNode(system, dag)
    return dag
