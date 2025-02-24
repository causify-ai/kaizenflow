"""
Import as:

import dataflow_amp.system.common.system_simulation_utils as dtfascssiut
"""
# TODO(Grisha): find a better file: it should not be under Cx and `utils` in
# the name is not concrete enough.

import logging
import os
from typing import Any, List, Optional

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx as dtfamsysc
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# TODO(Grisha): find a better, e.g., `run_replayed_time_simulation`, because
# the `simulation` term is too broad.
def run_simulation(
    system: dtfsys.System,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    market_data_file_path: str,
    system_log_dir: str,
    *,
    set_config_values: Optional[str] = None,
    incremental: bool = False,
    db_stage: str = "preprod",
    # TODO(Grisha): separate unit testing from the actual use, i.e. move
    # out the unit-test related parameters to a different function (or test case).
    config_tag: Optional[str] = None,
    self_: Optional[Any] = None,
    check_config: bool = False,
) -> List[dtfcore.ResultBundle]:
    """
    Run a simulation equivalent to the production run.

    :param system: a system object
    :param start_timestamp_as_str: string representation of timestamp at
        which to start simulation run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp at
        which to end simulation run, e.g. "20221010_080000"
    :param market_data_file_path: path to a file with market data
    :param system_log_dir: a dir where to save results to
    :param set_config_values: string representations of config values used
        to override simulation params and update research portoflio config when
        running the system reconciliation notebook. Config values are separated
        with ';' in order to be processed by invoke. E.g.,
        '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal")); \n
        ("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(0.1), "prediction_abs_threshold": float(0.35)})'
    :param incremental:
        - if `True` use the data located at `market_data_file_path`
            in case the file path exists
        - if `False` dump market data
    :param db_stage: stage of the database to use, e.g., "prod"
    :param config_tag: tag used to freeze the system config by
        `check_SystemConfig()`
    :param check_config: freeze the config before running the System
    """
    hdbg.dassert_isinstance(system, dtfsys.System)
    # Fill the `SystemConfig`.
    start_timestamp = hdateti.timestamp_as_str_to_timestamp(
        start_timestamp_as_str
    )
    end_timestamp = hdateti.timestamp_as_str_to_timestamp(end_timestamp_as_str)
    # TODO(Grisha): the API is more general than Cx, we should move out the
    # "apply config" piece out of the function to make it work for any kind of
    # a System.
    # 1) Apply Market data config.
    replayed_delay_in_mins_or_timestamp = start_timestamp
    system = dtfasccxbu.apply_Cx_MarketData_config(
        system, replayed_delay_in_mins_or_timestamp
    )
    # 2) Apply DAG config.
    # TODO(Grisha): Pass via `apply_dag_property()`.
    system.config["dag_builder_config", "fast_prod_setup"] = False
    system.config["dag_property_config", "force_free_nodes"] = True
    system.config[
        "dag_property_config", "debug_mode_config"
    ] = cconfig.Config.from_dict(
        {
            "save_node_io": "df_as_pq",
            "save_node_df_out_stats": True,
            "profile_execution": False,
        }
    )
    system.config["market_data_config", "file_path"] = market_data_file_path
    system.config["system_log_dir"] = system_log_dir
    #
    if set_config_values is not None:
        # Extract config values from a string.
        # TODO(Nina): pass already split values.
        set_config_values = set_config_values.split(";")
        # Override config.
        config = system.config
        # TODO(Grisha): this is a hack to override a value even if it was used,
        # the correct way is to make sure that we `mark_as_used` only when building
        # a component and that we do not override values after that.
        clobber_mode = "allow_write_after_use"
        config = cconfig.apply_config(
            config, set_config_values, clobber_mode=clobber_mode
        )
        system.set_config(config)
    path_exists = os.path.exists(market_data_file_path)
    universe_version = system.config["market_data_config", "universe_version"]
    # 3) Dump Market data.
    # Dump market data if either condition is false, otherwise copy from
    # `market_data_file_path`.
    if incremental and path_exists:
        _LOG.warning(
            "Skipping generating %s, since it already exists.",
            market_data_file_path,
        )
    else:
        table_name = system.config[
            "market_data_config", "im_client_config", "table_name"
        ]
        dtfamsysc.dump_market_data_from_db(
            market_data_file_path,
            start_timestamp_as_str,
            end_timestamp_as_str,
            db_stage,
            table_name,
            universe_version,
        )
    # TODO(Nina): pass via config so it will be possible to override vendor
    # and/or mode if needed.
    # The version corresponds to `CCXT` trade universe.
    vendor = "CCXT"
    mode = "trade"
    # Add asset ids to the `SystemConfig` after all values are overridden
    # so that asset ids correspond with universe version.
    asset_ids = ivcu.get_vendor_universe_as_asset_ids(
        universe_version, vendor, mode
    )
    system.config["market_data_config", "asset_ids"] = asset_ids
    # Override `bar_duration_in_secs` after overriding all values since it
    # depends on `trading_period` which also can be overridden.
    bar_duration_in_secs = int(
        pd.Timedelta(system.config["trading_period"]).total_seconds()
    )
    system.config[
        "dag_runner_config", "bar_duration_in_secs"
    ] = bar_duration_in_secs
    # TODO(Grisha): not clear, add an example.
    # TODO(Nina): `rt_timeout_in_secs_or_time` should not depend on
    # `bar_duration_in_secs`; it's done this way because we use `start_timestamp`
    # and `end_timestamp` in the API. Ideally an API just accepts `System` with
    # `rt_timeout_in_secs_or_time` being already set.
    # Compute `rt_timeout_in_secs_or_time` after config overrides because it
    # depends on `bar_duration_in_secs` and it is required to use an overridden
    # value.
    # The interval type is `[a, b]`, add one bar to include the upper boundary.
    rt_timeout_in_secs_or_time = (
        int((end_timestamp - start_timestamp).total_seconds())
        + bar_duration_in_secs
    )
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = rt_timeout_in_secs_or_time
    # Run the System.
    use_unit_test_log_dir = False
    # TODO(Grisha): The function is specific of unit tests. Use a different one for
    # running a simulation because not all the unit tests features are needed here.
    result_bundle = dtfsys.run_Time_ForecastSystem(
        self_,
        system,
        config_tag,
        use_unit_test_log_dir,
        check_config=check_config,
    )
    return result_bundle
