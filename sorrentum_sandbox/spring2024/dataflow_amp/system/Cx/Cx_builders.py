"""
Import as:

import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
"""

import datetime
import logging
import os
from typing import Any, Dict, List, Optional, Union

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
import im_v2.common.db.db_utils as imvcddbut
import market_data as mdata

# TODO(Sonya): it needs to be just `import oms`, but avoiding potential
# circular imports: https://github.com/cryptokaizen/cmamp/issues/4510.
import oms.broker.ccxt.ccxt_portfolio as obccccpo

_LOG = logging.getLogger(__name__)

# TODO(gp): @all -> Cx_system_builders.py


# #############################################################################
# Market data instances.
# #############################################################################


def get_Cx_HistoricalMarketData_example1(
    system: dtfsys.System,
) -> mdata.ImClientMarketData:
    """
    Build a `MarketData` client backed with the data defined by `ImClient`.
    """
    im_client = dtfsys.build_ImClient_from_System(system)
    asset_ids = system.config["market_data_config", "asset_ids"]
    columns = None
    columns_remap = None
    # TODO(gp): Document why this is the wall clock time.
    wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
    market_data = mdata.get_HistoricalImClientMarketData_example1(
        im_client,
        asset_ids,
        columns,
        columns_remap,
        wall_clock_time=wall_clock_time,
    )
    return market_data


# TODO(Nina): pass System here and extract param values from System.config
# instead of propagating multiple params via interface.
def get_Cx_RealTimeMarketData_prod_instance1(
    asset_ids: List[int],
    db_stage: str,
    *,
    # TODO(Grisha): remove the default value once the analysis notebooks
    # are updated, see CmTask7511.
    table_name: str = "ccxt_ohlcv_futures",
    sleep_in_secs: float = 1.0,
) -> mdata.MarketData:
    """
    Build a `MarketData` backed with `RealTimeImClient`.

    :param db_stage: stage of the database to use, e.g. 'prod' or
        'local'
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("asset_ids db_stage"))
    universe_version = "infer_from_data"
    # Get DB connection.
    db_connection = imvcddbut.DbConnectionManager.get_connection(db_stage)
    # Get the real-time `ImClient`.
    # TODO(Grisha): @Dan pass as much as possible via `system.config`.
    resample_1min = False
    im_client = imvcdccccl.CcxtSqlRealTimeImClient(
        universe_version, db_connection, table_name, resample_1min=resample_1min
    )
    # TODO(Grisha): extract values from SystemConfig instead of setting them in
    # the builder.
    # Get the real-time `MarketData`.
    asset_id_col = "asset_id"
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    event_loop = None
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="ET", event_loop=event_loop
    )
    # We can afford to wait only for 60 seconds in prod because we need to have
    # enough time to compute the forecasts and after one minute we start
    # getting data for the next bar.
    time_out_in_secs = 60
    #
    market_data = mdata.RealTimeMarketData2(
        im_client,
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data


def get_Cx_RealTimeMarketData_prod_instance2(
    asset_ids: List[int],
    universe: str,
) -> mdata.MarketData:
    """
    Build a `MarketData` instance backed by `RealTimeImClient` without
    establishing a database connection.

    This is particularly useful when running the broker without relying
    on database operations such as flattening or fetching balance. In
    the current context, market data is utilized solely for wall clock
    time, making it less dependent on a database connection.
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("asset_ids"))
    universe = universe
    # Get DB connection.
    db_connection = None
    # Get the real-time `ImClient`.
    table_name = "ccxt_ohlcv_futures"
    # TODO(Grisha): @Dan pass as much as possible via `system.config`.
    resample_1min = False
    im_client = imvcdccccl.CcxtSqlRealTimeImClient(
        universe, db_connection, table_name, resample_1min=resample_1min
    )
    # Get the real-time `MarketData`.
    market_data, _ = mdata.get_RealTimeImClientMarketData_example1(
        im_client, asset_ids
    )
    return market_data


# #############################################################################
# Process forecasts configs.
# #############################################################################


def apply_ProcessForecastsNode_config(
    system: dtfsys.System,
    order_config: Dict[str, Any],
    optimizer_config: Dict[str, Any],
    log_dir: str,
) -> Dict[str, Any]:
    """
    Build the `ProcessForecastsNode` dictionary for simulation.
    """
    process_forecasts_dict = {
        # Params for `ForecastProcessor`.
        "order_config": order_config,
        "optimizer_config": optimizer_config,
        # Params for `process_forecasts()`.
        "execution_mode": "real_time",
        "log_dir": log_dir,
    }
    #
    dag_builder = system.config["dag_builder_object"]
    volatility_col = dag_builder.get_column_name("volatility")
    prediction_col = dag_builder.get_column_name("prediction")
    spread_col = None
    process_forecasts_node_dict = {
        "prediction_col": prediction_col,
        "volatility_col": volatility_col,
        "spread_col": spread_col,
        # This configures `process_forecasts()`.
        "process_forecasts_dict": process_forecasts_dict,
    }
    system.config["process_forecasts_node_dict"] = cconfig.Config.from_dict(
        process_forecasts_node_dict
    )
    return system


def get_Cx_order_config_instance1() -> cconfig.Config:
    """
    Get a default order config.
    """
    order_config = {
        "order_type": "price@twap",
        "order_duration_in_mins": 5,
        "execution_frequency": "1T",
    }
    order_config = cconfig.Config.from_dict(order_config)
    return order_config


def get_Cx_optimizer_config_instance1() -> cconfig.Config:
    """
    Get a default optimizer config.
    """
    optimizer_config = {
        "backend": "pomo",
        "asset_class": "crypto",
        "apply_cc_limits": True,
        "params": {
            "style": "cross_sectional",
            "kwargs": {
                "bulk_frac_to_remove": 0.0,
                "target_gmv": 3000.0,
            },
        },
    }
    optimizer_config = cconfig.Config.from_dict(optimizer_config)
    return optimizer_config


# #############################################################################
# DAG instances.
# #############################################################################


def _get_Cx_RealTimeDag(
    system: dtfsys.System,
    share_quantization: Optional[int],
) -> dtfcore.DAG:
    """
    Build a DAG with `RealTimeDataSource` and `ForecastProcessorNode`.
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    history_looback = system.config.get_and_mark_as_used(
        ("market_data_config", "days")
    )
    system = dtfsys.apply_history_lookback(system, days=history_looback)
    dag = dtfsys.add_real_time_data_source(system)
    # Configure a `ProcessForecastNode`.
    system.config["process_forecasts_node_dict", "portfolio"] = system.portfolio
    system = dtfsys.apply_ProcessForecastsNode_config_for_crypto(
        system, share_quantization
    )
    # Append the `ProcessForecastNode`.
    dag = dtfsys.add_ProcessForecastsNode(system, dag)
    return dag


def get_Cx_HistoricalDag_example1(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build a DAG with a historical data source for simulation.
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    # Create HistoricalDataSource.
    stage = "read_data"
    market_data = system.market_data
    # TODO(gp): This in the original code was
    # ts_col_name = "timestamp_db"
    ts_col_name = "end_ts"
    multiindex_output = True
    # col_names_to_remove = ["start_datetime", "timestamp_db"]
    col_names_to_remove = []
    node = dtfsys.HistoricalDataSource(
        stage,
        market_data,
        ts_col_name,
        multiindex_output,
        col_names_to_remove=col_names_to_remove,
    )
    # Build the DAG.
    dag_builder = system.config["dag_builder_object"]
    dag = dag_builder.get_dag(system.config["dag_config"])
    # Add the data source node.
    dag.insert_at_head(node)
    return dag


def get_Cx_RealTimeDag_example1(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build a DAG with `RealTimeDataSource` for a unit tests from a system
    config.
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    system = dtfsys.apply_history_lookback(system)
    dag = dtfsys.add_real_time_data_source(system)
    return dag


def get_Cx_RealTimeDag_example2(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build a DAG for unit tests with `RealTimeDataSource` and
    `ForecastProcessorNode` from a system config.
    """
    # Round to a meaningful number of decimal places for the unit tests, otherwise
    # the division is performed differently on different machines, see CmTask4707.
    share_quantization = 9
    #
    dag = _get_Cx_RealTimeDag(
        system,
        share_quantization,
    )
    return dag


def get_Cx_dag_prod_instance1(system: dtfsys.System) -> dtfcore.DAG:
    """
    Build the DAG for a prod run from a system config.

    Compute target posisions style is "cross_sectional".
    """
    share_quantization = None
    #
    dag = _get_Cx_RealTimeDag(
        system,
        share_quantization,
    )
    return dag


# #############################################################################
# Portfolio instances.
# #############################################################################


# TODO(gp): We should dump the state of the portfolio and load it back.
# TODO(gp): Probably all prod system needs to have run_mode and trade_date and
#  so we can generalize the class to be not E8 specific.
def get_Cx_portfolio_prod_instance1(
    system: dtfsys.System,
) -> obccccpo.CcxtPortfolio:
    """
    Build Portfolio instance for production.
    """
    run_mode = system.config.get_and_mark_as_used("run_mode")
    #
    market_data = system.market_data
    column_remap = system.config.get_and_mark_as_used(
        ("portfolio_config", "column_remap")
    )
    asset_ids = system.config.get_and_mark_as_used(
        ("market_data_config", "asset_ids")
    )
    cf_config_strategy = system.config.get_and_mark_as_used(
        ("cf_config", "strategy"), default_value="Cx"
    )
    universe_version = system.config.get_and_mark_as_used(
        ("market_data_config", "universe_version"), default_value=None
    )
    pricing_method = system.config.get_and_mark_as_used(
        ("portfolio_config", "pricing_method")
    )
    secret_identifier_config = system.config.get_and_mark_as_used(
        "secret_identifier_config", default_value=None
    )
    log_dir = system.config.get_and_mark_as_used("system_log_dir")
    log_dir = os.path.join(log_dir, "process_forecasts")
    #
    broker_config = system.config.get_and_mark_as_used(
        ("portfolio_config", "broker_config")
    ).to_dict()
    mark_to_market_col = system.config.get_and_mark_as_used(
        ("portfolio_config", "mark_to_market_col")
    )
    portfolio = obccccpo.get_CcxtPortfolio_prod_instance1(
        run_mode,
        cf_config_strategy,
        market_data,
        column_remap,
        universe_version,
        secret_identifier_config,
        pricing_method,
        asset_ids,
        broker_config,
        log_dir,
        mark_to_market_col,
    )
    return portfolio


# #############################################################################
# Apply config utils.
# #############################################################################


# TODO(Grisha): P1, consider removing.
def apply_Cx_MarketData_config(
    system: dtfsys.System,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
) -> dtfsys.System:
    """
    Extend system config with parameters for `MarketData` init.
    """
    system.config["market_data_config", "datetime_columns"] = [
        "start_datetime",
        "end_datetime",
        "timestamp_db",
    ]
    system.config["market_data_config", "timestamp_db_column"] = "end_datetime"
    system.config["market_data_config", "aws_profile"] = "ck"
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    system.config["market_data_config", "delay_in_secs"] = 10
    system.config[
        "market_data_config", "replayed_delay_in_mins_or_timestamp"
    ] = replayed_delay_in_mins_or_timestamp
    return system


# TODO(Grisha): P1, consider removing.
def apply_Cx_DagRunner_config(
    system: dtfsys.System,
    rt_timeout_in_secs_or_time: Union[int, datetime.time],
) -> dtfsys.System:
    """
    Extend system config with parameters for `DagRunner` init.
    """
    # TODO(Grisha): @Dan Factor out to `get_trading_period_from_system()`.
    dag_builder = system.config["dag_builder_object"]
    dag_config = system.config["dag_config"]
    mark_key_as_used = False
    trading_period = dag_builder.get_trading_period(dag_config, mark_key_as_used)
    system.config["dag_runner_config", "bar_duration_in_secs"] = int(
        pd.Timedelta(trading_period).total_seconds()
    )
    if hasattr(dag_builder, "fit_at_beginning"):
        system.config[
            "dag_runner_config", "fit_at_beginning"
        ] = dag_builder.fit_at_beginning
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    return system
