"""
Import as:

import oms.reconciliation as omreconc
"""

import datetime
import itertools
import logging
import os
import pprint
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import dataflow.core.dag as dtfcordag
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hintrospection as hintros
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hpickle as hpickle
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import oms.ccxt.ccxt_utils as occccuti
import oms.portfolio as omportfo
import oms.target_position_and_order_generator as otpaorge

_LOG = logging.getLogger(__name__)

# Each function should accept a `log_level` parameter that controls at which
# level output summarizing the results. By default it is set by function to
# logging.DEBUG (since we don't want to print anything).
# The internal debugging info is printed as usual at level `logging.DEBUG`.


def get_asset_slice(df: pd.DataFrame, asset_id: int) -> pd.DataFrame:
    """
    Extract all columns related to `asset_id`.
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    hdbg.dassert_in(asset_id, df.columns.levels[1])
    slice_ = df.T.xs(asset_id, level=1).T
    return slice_


# #############################################################################
# Config
# #############################################################################


# TODO(Grisha): separate crypto and equities (e.g., create 2 functions).
# TODO(Grisha): add a separate config for the slow version of the
# Master system reconciliation notebook.
def build_reconciliation_configs(
    dst_root_dir: str,
    dag_builder_name: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    run_mode: str,
    mode: str,
) -> cconfig.ConfigList:
    """
    Build reconciliation configs that are specific of an asset class.

    Note: the function returns list of configs because the function is used
    as a config builder function for the run notebook script.

    :param dst_root_dir: dir to store the reconciliation results in, e.g.,
        "/shared_data/prod_reconciliation/"
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run, e.g. "20221010_080000"
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :param mode: reconciliation run mode, i.e., "scheduled" and "manual"
    :return: list of reconciliation configs
    """
    run_date = get_run_date(start_timestamp_as_str)
    _LOG.info("Using run_date=%s", run_date)
    #
    asset_key = "AM_ASSET_CLASS"
    if asset_key in os.environ:
        asset_class = os.environ[asset_key]
    else:
        asset_class = "crypto"
    # Set values for variables that are specific of an asset class.
    if asset_class == "crypto":
        # For crypto the TCA part is not implemented yet.
        run_tca = False
        #
        bar_duration = "5T"
        #
        target_dir = get_target_dir(
            dst_root_dir, dag_builder_name, start_timestamp_as_str, run_mode
        )
        system_log_path_dict = get_system_log_dir_paths(
            target_dir, mode, start_timestamp_as_str, end_timestamp_as_str
        )
        # Get column names from `DagBuilder`.
        system_config_func_as_str = f"dataflow_orange.system.Cx.get_Cx_system_config_template_instance('{dag_builder_name}')"
        system_config = hintros.get_function_from_string(
            system_config_func_as_str
        )
        dag_builder = system_config["dag_builder_object"]
        fep_init_dict = {
            "price_col": dag_builder.get_column_name("price"),
            "prediction_col": dag_builder.get_column_name("prediction"),
            "volatility_col": dag_builder.get_column_name("volatility"),
        }
        quantization = "asset_specific"
        market_info = occccuti.load_market_data_info()
        asset_id_to_share_decimals = occccuti.subset_market_info(
            market_info, "amount_precision"
        )
        gmv = 3000.0
        liquidate_at_end_of_day = False
        initialize_beginning_of_day_trades_to_zero = False
    elif asset_class == "equities":
        run_tca = True
        #
        bar_duration = "15T"
        #
        root_dir = ""
        search_str = ""
        prod_dir_cmd = f"find {root_dir}/{run_date}/prod -name '{search_str}'"
        _, prod_dir = hsystem.system_to_string(prod_dir_cmd)
        cand_cmd = (
            f"find {root_dir}/{run_date}/job.candidate.* -name '{search_str}'"
        )
        _, cand_dir = hsystem.system_to_string(cand_cmd)
        system_log_path_dict = {
            "prod": prod_dir,
            "cand": cand_dir,
            "sim": os.path.join(root_dir, run_date, "system_log_dir"),
        }
        #
        fep_init_dict = {
            "price_col": "twap",
            "prediction_col": "prediction",
            "volatility_col": "garman_klass_vol",
        }
        quantization = "nearest_share"
        asset_id_to_share_decimals = None
        gmv = 20000.0
        liquidate_at_end_of_day = True
        initialize_beginning_of_day_trades_to_zero = True
    else:
        raise ValueError(f"Unsupported asset class={asset_class}")
    # Sanity check dirs.
    for dir_name in system_log_path_dict.values():
        hdbg.dassert_dir_exists(dir_name)
    # Build the config.
    config_dict = {
        "meta": {
            "date_str": run_date,
            "asset_class": asset_class,
            "run_tca": run_tca,
            "bar_duration": bar_duration,
        },
        "system_log_path": system_log_path_dict,
        "system_config_func_as_str": system_config_func_as_str,
        "research_forecast_evaluator_from_prices": {
            "init": fep_init_dict,
            "annotate_forecasts_kwargs": {
                "style": "cross_sectional",
                "quantization": quantization,
                "liquidate_at_end_of_day": liquidate_at_end_of_day,
                "initialize_beginning_of_day_trades_to_zero": initialize_beginning_of_day_trades_to_zero,
                "burn_in_bars": 3,
                "asset_id_to_share_decimals": asset_id_to_share_decimals,
                "bulk_frac_to_remove": 0.0,
                "target_gmv": gmv,
            },
        },
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# TODO(Grisha): Factor out common code with `build_reconciliation_configs()`.
def build_prod_pnl_real_time_observer_configs(
    prod_data_root_dir: str,
    dag_builder_name: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    mode: str,
    save_plots_for_investors: bool,
    *,
    s3_dst_dir: Optional[str] = None,
) -> cconfig.ConfigList:
    """
    Build prod PnL real-time observer configs.

    Note: the function returns list of configs because the function is used
    as a config builder function for the run notebook script.

    :param prod_data_root_dir: dir to store the production results in, e.g.,
        "/shared_data/ecs/preprod/system_reconciliation/"
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param start_timestamp_as_str: string representation of timestamp
        at which a production run started, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which a production run ended, e.g. "20221010_080000"
    :param mode: prod run mode, i.e., "scheduled" and "manual"
    :param save_plots_for_investors: whether to save PnL plots for investors or not
    :param s3_dst_dir: dst dir where to save plots for investors on S3
    :return: list of configs
    """
    run_date = get_run_date(start_timestamp_as_str)
    prod_data_dir = os.path.join(prod_data_root_dir, dag_builder_name, run_date)
    _LOG.info("Using run_date=%s", run_date)
    #
    system_log_subdir = get_prod_system_log_dir(
        mode, start_timestamp_as_str, end_timestamp_as_str
    )
    system_log_dir = os.path.join(prod_data_dir, system_log_subdir)
    hdbg.dassert_dir_exists(system_log_dir)
    # Get necessary data from `DagBuilder`.
    system_config_func_as_str = f"dataflow_orange.system.Cx.get_Cx_system_config_template_instance('{dag_builder_name}')"
    system_config = hintros.get_function_from_string(system_config_func_as_str)
    bar_duration = system_config["dag_config"]["resample"]["transformer_kwargs"][
        "rule"
    ]
    dag_builder = system_config["dag_builder_object"]
    fep_init_dict = {
        "price_col": dag_builder.get_column_name("price"),
        "prediction_col": dag_builder.get_column_name("prediction"),
        "volatility_col": dag_builder.get_column_name("volatility"),
    }
    quantization = "asset_specific"
    market_info = occccuti.load_market_data_info()
    asset_id_to_share_decimals = occccuti.subset_market_info(
        market_info, "amount_precision"
    )
    gmv = 3000.0
    liquidate_at_end_of_day = False
    initialize_beginning_of_day_trades_to_zero = False
    # Build the config.
    config_dict = {
        "meta": {
            "dag_builder_name": dag_builder_name,
            "date_str": run_date,
            "bar_duration": bar_duration,
            "save_plots_for_investors": save_plots_for_investors,
        },
        "s3_dst_dir": s3_dst_dir,
        "system_log_dir": system_log_dir,
        "system_config_func_as_str": system_config_func_as_str,
        "research_forecast_evaluator_from_prices": {
            "init": fep_init_dict,
            "annotate_forecasts_kwargs": {
                "style": "cross_sectional",
                "quantization": quantization,
                "liquidate_at_end_of_day": liquidate_at_end_of_day,
                "initialize_beginning_of_day_trades_to_zero": initialize_beginning_of_day_trades_to_zero,
                "burn_in_bars": 3,
                "asset_id_to_share_decimals": asset_id_to_share_decimals,
                "bulk_frac_to_remove": 0.0,
                "target_gmv": gmv,
            },
        },
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# /////////////////////////////////////////////////////////////////////////////


def load_config_from_pickle(
    system_log_path_dict: Dict[str, str]
) -> Dict[str, cconfig.Config]:
    """
    Load configs from pickle files given a dict of paths.
    """
    config_dict = {}
    file_name = "system_config.input.values_as_strings.pkl"
    for stage, path in system_log_path_dict.items():
        path = os.path.join(path, file_name)
        hdbg.dassert_path_exists(path)
        _LOG.debug("Reading config from %s", path)
        config_pkl = hpickle.from_pickle(path)
        config = cconfig.Config.from_dict(config_pkl)
        config_dict[stage] = config
    return config_dict


# /////////////////////////////////////////////////////////////////////////////


# TODO(Grisha): seems more general than this file.
def _dassert_is_date(date: str) -> None:
    """
    Check if an input string is a date.

    :param date: date as string, e.g., "20221101"
    """
    hdbg.dassert_isinstance(date, str)
    try:
        _ = datetime.datetime.strptime(date, "%Y%m%d")
    except ValueError as e:
        raise ValueError(f"date='{date}' doesn't have the right format: {e}")


def _dassert_is_date_time(date_time: str) -> None:
    """
    Check if an input string is a start timestamp.

    :param date_time: date time as string, e.g., "20231013_064500"
    """
    hdbg.dassert_isinstance(date_time, str)
    m = re.match(r"^\d{8}_\d{6}$", date_time)
    hdbg.dassert(m, "date_time_as_str='%s'", date_time)


# TODO(Grisha): -> `_get_run_date_from_start_timestamp`.
def get_run_date(start_timestamp_as_str: Optional[str]) -> str:
    """
    Return the run date as string from start timestamp, e.g. "20221017".

    If start timestamp is not specified by a user then return current
    date.

    E.g., "20221101_064500" -> "20221101".
    """
    if start_timestamp_as_str is None:
        # TODO(Grisha): do not use default values.
        run_date = datetime.date.today().strftime("%Y%m%d")
    else:
        _dassert_is_date_time(start_timestamp_as_str)
        run_date = start_timestamp_as_str.split("_")[0]
    _LOG.info(hprint.to_str("run_date"))
    _dassert_is_date(run_date)
    return run_date


# TODO(Grisha): consider moving to `helpers/hdatetime.py`.
# TODO(Grisha): pass timezone as a param.
def timestamp_as_str_to_timestamp(timestamp_as_str: str) -> pd.Timestamp:
    """
    Convert the given string UTC timestamp to the ET timezone timestamp.
    """
    # TODO(Dan): Add assert for `start_timestamp_as_str` and `end_timestamp_as_str` regex.
    hdbg.dassert_isinstance(timestamp_as_str, str)
    timestamp_as_str = timestamp_as_str.replace("_", " ")
    # Add timezone offset in order to standartize the time.
    timestamp_as_str = "".join([timestamp_as_str, "+00:00"])
    timestamp = pd.Timestamp(timestamp_as_str, tz="America/New_York")
    return timestamp


# /////////////////////////////////////////////////////////////////////////////


def get_system_reconciliation_notebook_path(notebook_run_mode: str) -> str:
    """
    Get a system reconciliation notebook path.

    :param notebook_run_mode: version of the notebook to run
        - "fast": run fast checks only, i.e. compare DAG output for the last
            node / last bar timestamp
        - "slow": run slow checks only,  i.e. compare DAG output for all nodes / all
            bar timestamps
    :return: path to a system reconciliation notebook, e.g.,
        ".../.../Master_system_reconciliation.slow.ipynb"
    """
    hdbg.dassert_in(notebook_run_mode, ["fast", "slow"])
    amp_dir = hgit.get_amp_abs_path()
    base_name = "Master_system_reconciliation"
    notebook_path = os.path.join(
        amp_dir, "oms", "notebooks", f"{base_name}_{notebook_run_mode}.ipynb"
    )
    hdbg.dassert_file_exists(notebook_path)
    return notebook_path


def get_prod_dir(dst_root_dir: str) -> str:
    """
    Return prod results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/20230213/prod".
    """
    prod_dir = os.path.join(
        dst_root_dir,
        "prod",
    )
    return prod_dir


def get_simulation_dir(dst_root_dir: str) -> str:
    """
    Return simulation results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/20230213/simulation".
    """
    sim_dir = os.path.join(
        dst_root_dir,
        "simulation",
    )
    return sim_dir


def get_target_dir(
    dst_root_dir: str,
    dag_builder_name: str,
    start_timestamp_as_str: str,
    run_mode: str,
) -> str:
    """
    Return the target dir name to store reconcilation results.

    If a dir name is not specified by a user then use prod reconcilation
    dir on the shared disk with the corresponding `dag_builder_name`, run date,
    and `run_mode` subdirs.

    E.g., "/shared_data/prod_reconciliation/C1b/20221101/paper_trading".

    :param dst_root_dir: root dir of reconciliation result dirs, e.g.,
        "/shared_data/prod_reconciliation"
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :return: a target dir to store reconcilation results
    """
    _LOG.info(
        hprint.to_str(
            "dst_root_dir dag_builder_name start_timestamp_as_str run_mode"
        )
    )
    hdbg.dassert_path_exists(dst_root_dir)
    hdbg.dassert_isinstance(dag_builder_name, str)
    hdbg.dassert_isinstance(start_timestamp_as_str, str)
    hdbg.dassert_in(run_mode, ["prod", "paper_trading"])
    #
    run_date = get_run_date(start_timestamp_as_str)
    target_dir = os.path.join(dst_root_dir, dag_builder_name, run_date, run_mode)
    _LOG.info(hprint.to_str("target_dir"))
    return target_dir


def get_reconciliation_notebook_dir(dst_root_dir: str) -> str:
    """
    Return reconciliation notebook dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/20230213/reconciliation_notebook".
    """
    notebook_dir = os.path.join(
        dst_root_dir,
        "reconciliation_notebook",
    )
    return notebook_dir


def get_tca_dir(dst_root_dir: str) -> str:
    """
    Return TCA results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/20230213/tca".
    """
    tca_dir = os.path.join(
        dst_root_dir,
        "tca",
    )
    return tca_dir


# TODO(Grisha): I would pass also a `root_dir` and check if
# the resulting dir exists.
def get_prod_system_log_dir(
    mode: str, start_timestamp_as_str: str, end_timestamp_as_str: str
) -> str:
    """
    Get a prod system log dir.

    E.g.:
    "system_log_dir.manual.20221109_0605.20221109_080000".

    See `lib_tasks_reconcile.reconcile_run_all()` for params description.
    """
    system_log_dir = (
        f"system_log_dir.{mode}.{start_timestamp_as_str}.{end_timestamp_as_str}"
    )
    _LOG.info(hprint.to_str("system_log_dir"))
    return system_log_dir


# TODO(Grisha): support multiple experiments, not only "sim" and "prod".
def get_system_log_dir_paths(
    target_dir: str,
    mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
) -> Dict[str, str]:
    """
    Get paths to system log dirs.

    :param target_dir: dir to store the reconciliation results in, e.g.,
        "/shared_data/prod_reconciliation/C3a/20221120/paper_trading"
    :param mode: reconciliation run mode, i.e., "scheduled" and "manual"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run, e.g. "20221010_061500"
    :return: system log dir paths for prod and simulation, e.g.,
        ```
        {
            "prod": ".../prod/system_log_dir.manual.20221109_0605.20221109_080000",
            "sim": ...
        }
        ```
    """
    prod_dir = get_prod_dir(target_dir)
    prod_system_log_dir = get_prod_system_log_dir(
        mode, start_timestamp_as_str, end_timestamp_as_str
    )
    prod_system_log_dir = os.path.join(prod_dir, prod_system_log_dir)
    #
    sim_dir = get_simulation_dir(target_dir)
    sim_system_log_dir = os.path.join(sim_dir, "system_log_dir")
    system_log_dir_paths = {
        "prod": prod_system_log_dir,
        "sim": sim_system_log_dir,
    }
    return system_log_dir_paths


def get_data_type_system_log_path(system_log_path: str, data_type: str) -> str:
    """
    Get path to data inside a system log dir.

    :param system_log_path: system log dir path
    :param data_type: type of data to create paths to
        - "dag_data": DAG output
        - "dag_stats": DAG execution profiling stats
        - "portfolio": Portfolio output
        - "orders": orders info
    :return: path to the specified data type system log dir, e.g.,
        `system_log_dir/dag/node_io/node_io.data`
    """
    if data_type == "dag_data":
        dir_name = os.path.join(system_log_path, "dag/node_io/node_io.data")
    elif data_type == "dag_stats":
        dir_name = os.path.join(system_log_path, "dag/node_io/node_io.prof")
    elif data_type == "portfolio":
        dir_name = os.path.join(system_log_path, "process_forecasts/portfolio")
    elif data_type == "orders":
        dir_name = os.path.join(system_log_path, "process_forecasts/orders")
    else:
        raise ValueError(f"Unsupported data type={data_type}")
    return dir_name


# TODO(gp): -> _get_system_log_paths?
def get_system_log_paths(
    system_log_path_dict: Dict[str, str],
    data_type: str,
    *,
    log_level: int = logging.DEBUG,
) -> Dict[str, str]:
    """
    Get paths to data inside a system log dir.

    :param system_log_path_dict: system log dirs paths for different experiments, e.g.,
        ```
        {
            "prod": "/shared_data/system_log_dir",
            "sim": ...
        }
        ```
    :param data_type: type of data to create paths for, e.g., "dag" for
        DAG output, "portfolio" to load Portfolio
    :return: dir paths inside system log dir for different experiments, e.g.,
        ```
        {
            "prod": "/shared_data/system_log_dir/process_forecasts/portfolio",
            "sim": ...
        }
        ```
    """
    data_path_dict = {}
    for k, v in system_log_path_dict.items():
        cur_dir = get_data_type_system_log_path(v, data_type)
        hdbg.dassert_dir_exists(cur_dir)
        data_path_dict[k] = cur_dir
    _LOG.log(log_level, "# %s=\n%s", data_type, pprint.pformat(data_path_dict))
    return data_path_dict


def get_path_dicts(
    config: cconfig.Config, *, log_level: int = logging.DEBUG
) -> Tuple:
    # Point to `system_log_dir` for different experiments.
    system_log_path_dict = dict(config["system_log_path"].to_dict())
    _LOG.log(
        log_level,
        "# system_log_path_dict=\n%s",
        pprint.pformat(system_log_path_dict),
    )
    # Point to `system_log_dir/process_forecasts/portfolio` for different experiments.
    data_type = "portfolio"
    portfolio_path_dict = get_system_log_paths(
        system_log_path_dict, data_type, log_level=log_level
    )
    # Point to `system_log_dir/dag/node_io/node_io.data` for different experiments.
    data_type = "dag"
    dag_path_dict = get_system_log_paths(
        system_log_path_dict, data_type, log_level=log_level
    )
    return (system_log_path_dict, portfolio_path_dict, dag_path_dict)


# #############################################################################
# DAG loader
# #############################################################################


def get_latest_output_from_last_dag_node(dag_dir: str) -> pd.DataFrame:
    """
    Retrieve the most recent output from the last DAG node.

    This function relies on our file naming conventions.
    """
    hdbg.dassert_dir_exists(dag_dir)
    parquet_files = list(
        filter(lambda x: "parquet" in x, sorted(os.listdir(dag_dir)))
    )
    _LOG.info("Tail of files found=%s", parquet_files[-3:])
    file_name = parquet_files[-1]
    dag_parquet_path = os.path.join(dag_dir, file_name)
    _LOG.info("DAG parquet path=%s", dag_parquet_path)
    dag_df = hparque.from_parquet(dag_parquet_path)
    return dag_df


# #############################################################################
# Compare DAGs
# #############################################################################


def _prepare_dfs_for_comparison(
    previous_df: pd.DataFrame,
    current_df: pd.DataFrame,
    dag_start_timestamp: pd.Timestamp,
    dag_end_timestamp: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare 2 consecutive node dataframes for comparison.

    Preparation includes:
        - Aligning the indices
        - Excluding the history computed before a DAG run
        - Sanity checks

    :param previous_df: DAG node output that corresponds to the (i-1)-th
       timestamp
    :param current_df: DAG node output that corresponds to the i-th timestamp
    :param dag_start_timestamp: timestamp at which a DAG run started
    :param dag_end_timestamp: timestamp at which a DAG run ended
    :return: processed DAG node outputs
    """
    _LOG.debug(hprint.to_str("dag_start_timestamp dag_end_timestamp"))
    # Assert that both dfs are sorted by timestamp.
    hpandas.dassert_strictly_increasing_index(previous_df)
    hpandas.dassert_strictly_increasing_index(current_df)
    # A df at timestamp T-1 has one additional row in the beginning compared to
    # that at timestamp T.
    previous_df = previous_df[1:]
    # Remove the row that corresponds to the current timestamp because it is
    # not presented in a df at timestamp T-1.
    current_df = current_df[:-1]
    # Compare DAG output only within a DAG run period.
    mask1 = (previous_df.index >= dag_start_timestamp) & (
        previous_df.index <= dag_end_timestamp
    )
    mask2 = (current_df.index >= dag_start_timestamp) & (
        current_df.index <= dag_end_timestamp
    )
    previous_df = previous_df[mask1]
    current_df = current_df[mask2]
    # Assert both dfs share a common index.
    hpandas.dassert_indices_equal(previous_df, current_df)
    return previous_df, current_df


# TODO(Grisha): add "all" options for node_names.
def check_dag_output_self_consistency(
    dag_output_path: str,
    node_name: str,
    bar_timestamp: Union[str, pd.Timestamp],
    *,
    trading_freq: Optional[str] = None,
    diff_threshold: float = 1e-3,
    **compare_dfs_kwargs: Any,
) -> None:
    """
    Check that all the DAG output dataframes for all the timestamps are equal
    at intersecting time intervals.

    A dataframe at `t` should be equal to a dataframe at `t-1` except for
    the row that corresponds to the timestamp `t`.

    Exclude history lookback period from comparison since each model has its
    own peculiarities and it is hard to make the check general, e.g., a model
    needs 2**7 rows to compute volatility. I.e. compare DAG output within
    [dag_start_timestamp, dag_end_timestamp] instead of
    [dag_start_timestamp - history_lookback_period, dag_end_timestamp].

    :param dag_output_path: dir with the DAG output
    :param node_name: name of the node to check DAG outputs for
    :param bar_timestamp: bar timestamp for a given node, e.g.,
        `2023-03-23 09:05:00-04:00`
        - "all" - run for timestamps
    :param trading_freq: trading period frequency as pd.offset, e.g., "5T"
    :param diff_threshold: maximum allowed total difference
    :param compare_dfs_kwargs: params for `compare_dfs()`
    """
    dag_timestamps = get_dag_node_timestamps(dag_output_path, node_name)
    hdbg.dassert_lte(2, len(dag_timestamps))
    dag_start_timestamp = dag_timestamps[0][0]
    dag_end_timestamp = dag_timestamps[-1][0]
    if bar_timestamp == "all":
        # Keep bar timestamps only.
        bar_timestamps = [bar_timestamp for bar_timestamp, _ in dag_timestamps]
    else:
        # Compare only the data for the specified bar timestamp vs that
        # for the previous bar timestamp.
        hdbg.dassert_isinstance(trading_freq, str)
        prev_timestamp = bar_timestamp - pd.Timedelta(trading_freq)
        bar_timestamps = [prev_timestamp, bar_timestamp]
    #
    start = 1
    end = len(bar_timestamps)
    for t in range(start, end):
        # Load DAG output at `t` timestamp.
        current_timestamp = bar_timestamps[t]
        current_df = get_dag_node_output(
            dag_output_path, node_name, current_timestamp
        )
        current_df = current_df.sort_index()
        # Load DAG output at `t-1` timestamp.
        previous_timestamp = bar_timestamps[t - 1]
        previous_df = get_dag_node_output(
            dag_output_path, node_name, previous_timestamp
        )
        previous_df = previous_df.sort_index()
        # Check that DAG outputs are equal at intersecting time periods.
        _LOG.debug(
            "Comparing DAG output for node=%s current_timestamp=%s and previous_timestamp=%s",
            node_name,
            current_timestamp,
            previous_timestamp,
        )
        previous_df, current_df = _prepare_dfs_for_comparison(
            previous_df, current_df, dag_start_timestamp, dag_end_timestamp
        )
        diff_df = hpandas.compare_dfs(
            previous_df, current_df, **compare_dfs_kwargs
        )
        max_diff = diff_df.abs().max().max()
        hdbg.dassert_lte(
            max_diff,
            diff_threshold,
            msg=f"Comparison failed for node={node_name} for current_timestamp={current_timestamp} and previous_timestamp={previous_timestamp}",
        )


# TODO(Grisha): @Dan use `hio.listdir()` instead.
def _get_dag_node_parquet_file_names(dag_dir: str) -> List[str]:
    """
    Get Parquet file names for all the nodes in the target folder.

    :param dag_dir: dir with the DAG output
    :return: list of all files for all nodes and timestamps in the dir
    """
    hdbg.dassert_dir_exists(dag_dir)
    cmd = f"ls {dag_dir} | grep '.parquet'"
    _, nodes = hsystem.system_to_string(cmd)
    nodes = nodes.split("\n")
    return nodes


# TODO(Grisha): @Dan use `hio.listdir()` instead.
def _get_dag_node_csv_file_names(dag_dir: str) -> List[str]:
    """
    Get CSV file names for all the nodes in the target folder.

    :param dag_dir: dir with the DAG output
    :return: list of all files for all nodes and timestamps in the dir
    """
    hdbg.dassert_dir_exists(dag_dir)
    cmd = f"ls {dag_dir} | grep '.csv'"
    _, nodes = hsystem.system_to_string(cmd)
    nodes = nodes.split("\n")
    return nodes


# TODO(Grisha): we should return (method, topological_id, nid) instead of
# a single string to comply with the `dataflow/core/dag.py` notation.
def get_dag_node_names(
    dag_dir: str, *, log_level: int = logging.DEBUG
) -> List[str]:
    """
    Get names of DAG node from a target dir.

    :param dag_dir: dir with the DAG output
    :return: a sorted list of all DAG node names
        ```
        ['predict.0.read_data',
        'predict.1.resample',
        'predict.2.compute_ret_0',
        'predict.3.compute_vol',
        'predict.4.adjust_rets',
        'predict.5.compress_rets',
        'predict.6.add_lags',
        'predict.7.predict',
        'predict.8.process_forecasts']
        ```
    """
    file_names = _get_dag_node_parquet_file_names(dag_dir)
    # E.g., if file name is
    # `predict.8.process_forecasts.df_out.20221028_080000.parquet` then the
    # node name is `predict.8.process_forecasts`.
    node_names = sorted(
        list(set(node.split(".df_out")[0] for node in file_names))
    )
    _LOG.log(
        log_level,
        "dag_node_names=\n%s",
        hprint.indent("\n".join(map(str, node_names))),
    )
    return node_names


def get_dag_node_timestamps(
    dag_dir: str,
    dag_node_name: str,
    *,
    as_timestamp: bool = True,
    log_level: int = logging.DEBUG,
) -> List[Tuple[Union[str, pd.Timestamp], Union[str, pd.Timestamp]]]:
    """
    Get all bar timestamps and the corresponding wall clock timestamps.

    E.g., DAG node for bar timestamp `20221028_080000` was computed at
    `20221028_080143`.

    :param dag_dir: dir with the DAG output
    :param dag_node_name: a node name, e.g., `predict.0.read_data`
    :param as_timestamp: if True return as `pd.Timestamp`, otherwise
        return as string
    :return: a list of tuples with bar timestamps and wall clock timestamps
        for the specified node
    """
    _LOG.log(log_level, hprint.to_str("dag_dir dag_node_name as_timestamp"))
    file_names = _get_dag_node_parquet_file_names(dag_dir)
    node_file_names = list(filter(lambda node: dag_node_name in node, file_names))
    node_timestamps = []
    for file_name in node_file_names:
        # E.g., file name is "predict.8.process_forecasts.df_out.20221028_080000.20221028_080143.parquet".
        # The bar timestamp is "20221028_080000", and the wall clock timestamp
        # is "20221028_080143".
        splitted_file_name = file_name.split(".")
        bar_timestamp = splitted_file_name[-3]
        wall_clock_timestamp = splitted_file_name[-2]
        if as_timestamp:
            bar_timestamp = bar_timestamp.replace("_", " ")
            wall_clock_timestamp = wall_clock_timestamp.replace("_", " ")
            # TODO(Grisha): Pass tz as a param?
            tz = "America/New_York"
            bar_timestamp = pd.Timestamp(bar_timestamp, tz=tz)
            wall_clock_timestamp = pd.Timestamp(wall_clock_timestamp, tz=tz)
        node_timestamps.append((bar_timestamp, wall_clock_timestamp))
    #
    _LOG.log(
        log_level,
        "dag_node_timestamps=\n%s",
        hprint.indent("\n".join(map(str, node_timestamps))),
    )
    return node_timestamps


def get_dag_node_output(
    dag_dir: str,
    dag_node_name: str,
    timestamp: pd.Timestamp,
) -> pd.DataFrame:
    """
    Load DAG output for the specified node and the bar timestamp.

    This function relies on our file naming conventions, e.g.,
    `dag/node_io/node_io.data/predict.0.read_data.df_out.20221021_060500.parquet`.

    :param dag_dir: dir with the DAG output
    :param dag_node_name: a node name, e.g., `predict.0.read_data`
    :param timestamp: bar timestamp
    :return: a DAG node output
    """
    hdbg.dassert_dir_exists(dag_dir)
    hdbg.dassert_isinstance(timestamp, pd.Timestamp)
    timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    # TODO(Grisha): merge the logic with the one in `get_dag_node_names()`.
    cmd = f"find '{dag_dir}' -name {dag_node_name}*.parquet"
    cmd += f" | grep 'df_out.{timestamp}'"
    _, file = hsystem.system_to_string(cmd)
    df = hparque.from_parquet(file)
    hpandas.dassert_index_is_datetime(df.index)
    return df


# TODO(Grisha): find a name that better reflects the behavior.
def load_dag_outputs(
    dag_data_path: str,
    node_name: str,
) -> pd.DataFrame:
    """
    Load DAG data for a specified node for all bar timestamps.

    Keep only the row that corresponds to the current bar timestamp
    (i.e. the last row) for every bar timestamp and concatenate the rows into
    a single dataframe.

    :param dag_data_path: a path to DAG output data
    :param node_name: a node name to load an output for
    :return: a df that consists of last rows from every bar timestamp DAG
        results df
    """
    # Get DAG timestamps to iterate over them.
    dag_timestamps = get_dag_node_timestamps(dag_data_path, node_name)
    # Keep bar timestamps only.
    bar_timestamps = [bar_timestamp for bar_timestamp, _ in dag_timestamps]
    last_rows = []
    for timestamp in bar_timestamps:
        # Get the row that corresponds to the current bar timestamp, i.e.
        # the last row.
        df = get_dag_node_output(dag_data_path, node_name, timestamp)
        df = df.sort_index().tail(1)
        last_rows.append(df)
    df = pd.concat(last_rows)
    return df


# TODO(Grisha): obsolete, consider removing it. It's memory consuming
# to load everything at once.
def compute_dag_outputs_diff(
    dag_df_dict: Dict[str, Dict[str, Dict[pd.Timestamp, pd.DataFrame]]],
    **compare_dfs_kwargs: Any,
) -> pd.DataFrame:
    """
    Compute DAG output differences for different experiments.

    Output example:
    ```
                               predict.0.read_data
                               2022-11-04 06:05:00-04:00
                               close.pct_change
                               1891737434.pct_change  1966583502.pct_change
    end_timestamp
    2022-01-01 21:01:00+00:00                  -0.0                   +0.23
    2022-01-01 21:02:00+00:00                 -1.11                    -3.4
    2022-01-01 21:03:00+00:00                  12.2                   -32.0
    ```

    :param dag_df_dict: DAG output per experiment, node and bar timestamp
    :param compare_dfs_kwargs: params for `compare_dfs()`
    :return: DAG output differences for each experiment, node and bar timestamp
    """
    # Get experiment DAG output dicts to iterate over them.
    experiment_names = list(dag_df_dict.keys())
    hdbg.dassert_eq(2, len(experiment_names))
    dag_dict_1 = dag_df_dict[experiment_names[0]]
    dag_dict_2 = dag_df_dict[experiment_names[1]]
    # Assert that output dicts have equal node names.
    hdbg.dassert_set_eq(dag_dict_1.keys(), dag_dict_2.keys())
    # Get node names and set a list to store nodes data.
    node_names = list(dag_dict_1.keys())
    node_dfs = []
    for node_name in node_names:
        # Get node DAG output dicts to iterate over them.
        dag_dict_1_node = dag_dict_1[node_name]
        dag_dict_2_node = dag_dict_2[node_name]
        # Assert that node dicts have equal bar timestamps.
        hdbg.dassert_set_eq(dag_dict_1_node.keys(), dag_dict_2_node.keys())
        # Get bar timestamps and set a list to store bar timestamp data.
        bar_timestamps = list(dag_dict_1_node.keys())
        bar_timestamp_dfs = []
        for bar_timestamp in bar_timestamps:
            # Get DAG outputs per timestamp and compare them.
            df_1 = dag_dict_1_node[bar_timestamp]
            df_2 = dag_dict_2_node[bar_timestamp]
            # Pick only float columns for difference computations.
            # Only float columns are picked because int columns represent
            # not metrics but ids, etc.
            df_1 = df_1.select_dtypes("float")
            df_2 = df_2.select_dtypes("float")
            # Compute the difference.
            df_diff = hpandas.compare_dfs(df_1, df_2, **compare_dfs_kwargs)
            # Add bar timestamp diff data to the corresponding list.
            bar_timestamp_dfs.append(df_diff)
        # Merge bar timestamp diff data into node diff data.
        node_df = pd.concat(bar_timestamp_dfs, axis=1, keys=bar_timestamps)
        node_dfs.append(node_df)
    # Merge node diff data into result diff data.
    dag_diff_df = pd.concat(node_dfs, axis=1, keys=node_names)
    return dag_diff_df


# TODO(Grisha): consider extending for more than 2 experiments.
def compare_dag_outputs(
    dag_path_dict: Dict[str, str],
    node_name: str,
    bar_timestamp: Union[str, pd.Timestamp],
    *,
    diff_threshold: float = 1e-3,
    **compare_dfs_kwargs: Any,
) -> None:
    """
    Compare DAG output differences for different experiments.

    Iterate over DAG outputs for different experiments and check that
    the maximum difference between the corresponding dataframes is below
    the threshold.

    :param dag_path_dict: dst dir for every experiment
    :param node_name: name of the DAG node to compare output for
        - "all" means run for all nodes available
    :param bar_timestamp: bar timestamp for a given node, e.g.,
        `2023-03-23 09:05:00-04:00`
        - "all" means run for all timestamps
    :param diff_threshold: maximum allowed total difference
    :param compare_dfs_kwargs: params for `compare_dfs()`
    """
    # Get experiment names.
    experiment_names = list(dag_path_dict.keys())
    hdbg.dassert_eq(2, len(experiment_names))
    # Get DAG paths.
    dag_paths = list(dag_path_dict.values())
    hdbg.dassert_eq(2, len(dag_paths))
    dag_paths_1 = dag_paths[0]
    dag_paths_2 = dag_paths[1]
    # Get DAG node names to iterate over them.
    if node_name == "all":
        # Run the check for all the nodes.
        nodes_1 = get_dag_node_names(dag_paths_1)
        nodes_2 = get_dag_node_names(dag_paths_2)
        hdbg.dassert_set_eq(nodes_1, nodes_2)
    else:
        # Run the check only for the specified node.
        nodes_1 = [node_name]
    #
    for node in nodes_1:
        if bar_timestamp == "all":
            # TODO(Grisha): check that timestamps are equal for experiments.
            # Run the check for all bar timestamps available.
            dag_timestamps = get_dag_node_timestamps(dag_paths_1, node)
            # Keep bar timestamps only.
            bar_timestamps = [
                bar_timestamp for bar_timestamp, _ in dag_timestamps
            ]
        else:
            # Run the check for a specified bar timestamp.
            bar_timestamps = [bar_timestamp]
        for timestamp in bar_timestamps:
            # Get DAG output for the specified node and timestamp.
            df_1 = get_dag_node_output(dag_paths_1, node, timestamp)
            df_2 = get_dag_node_output(dag_paths_2, node, timestamp)
            # Pick only float columns for difference computations.
            # Only float columns are picked because int columns represent
            # not metrics but ids, etc.
            df_1 = df_1.select_dtypes("float")
            df_2 = df_2.select_dtypes("float")
            # Compare DAG output differences.
            _LOG.debug(
                "Comparing DAG output for node=%s and timestamp=%s",
                node,
                timestamp,
            )
            diff_df = hpandas.compare_dfs(df_1, df_2, **compare_dfs_kwargs)
            max_diff = diff_df.abs().max().max()
            hdbg.dassert_lte(
                max_diff,
                diff_threshold,
                msg=f"Comparison failed for node={node} for bar timestamps={timestamp}",
            )


def compute_dag_output_diff_stats(
    dag_diff_df: pd.DataFrame,
    aggregation_level: str,
    *,
    node: Optional[str] = None,
    bar_timestamp: Optional[pd.Timestamp] = None,
    display_plot: bool = True,
) -> pd.Series:
    """
    Compute DAG outputs max absolute differences using the specified
    aggregation level.

    :param dag_diff_df: DAG output differences data
    :param aggregation_level: used to determine the groups for `groupby`
        - "node": for each node
        - "bar_timestamp": for each bar timestamp
            - for a given node
        - "time": by the timestamp in a diff df
            - for a given node and a given bar timestamp
        - "column": by each column
            - for a given node and a given bar timestamp
        - "asset_id": by each asset id
            - for a given node and a given bar timestamp
    :param node: node name to aggregate for
    :param bar_timestamp: bar timestamp to aggregate by
    :param display_plot: if `True` plot the stats, do not plot otherwise
    :return: DAG outputs max absolute differences for the specified aggregation level
    """
    if aggregation_level in ["bar_timestamp", "time", "column", "asset_id"]:
        hdbg.dassert_isinstance(node, str)
        if aggregation_level != "bar_timestamp":
            hdbg.dassert_type_is(bar_timestamp, pd.Timestamp)
    # Remove the sign.
    dag_diff_df = dag_diff_df.abs()
    #
    if aggregation_level == "node":
        stats = dag_diff_df.max().groupby(level=[0]).max()
    elif aggregation_level == "bar_timestamp":
        stats = dag_diff_df[node].max().groupby(level=[0]).max()
    elif aggregation_level == "time":
        stats = dag_diff_df[node][bar_timestamp].T.max()
    elif aggregation_level == "column":
        stats = dag_diff_df[node][bar_timestamp].max().groupby(level=[0]).max()
    elif aggregation_level == "asset_id":
        stats = dag_diff_df[node][bar_timestamp].max().groupby(level=[1]).max()
    else:
        raise ValueError(f"Invalid aggregation_level='{aggregation_level}'")
    #
    if display_plot:
        if aggregation_level == "time":
            _ = stats.dropna().plot.line()
        else:
            _ = stats.plot.bar()
        plt.show()
    return stats


def compute_dag_output_diff_detailed_stats(
    dag_diff_df: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Compute and plot detailed DAG output diff stats.

    Tweak the params to change the output.

    :param dag_diff_df: DAG output differences
    :return: dict of detailed DAG output diff stats
    """
    res_dict = {}
    if False:
        # Plot differences across nodes.
        aggregation_level = "node"
        display_plot = True
        node_diff_stats = compute_dag_output_diff_stats(
            dag_diff_df, aggregation_level, display_plot=display_plot
        )
        res_dict["node_diff_stats"] = node_diff_stats
    if False:
        # Plot differences across bar timestamps.
        aggregation_level = "bar_timestamp"
        node = "predict.2.compute_ret_0"
        display_plot = True
        bar_timestamp_diff_stats = compute_dag_output_diff_stats(
            dag_diff_df,
            aggregation_level,
            node=node,
            display_plot=display_plot,
        )
        res_dict["bar_timestamp_diff_stats"] = bar_timestamp_diff_stats
    if False:
        # Plot differences across timestamps in a diff df.
        aggregation_level = "time"
        node = "predict.2.compute_ret_0"
        bar_timestamp = pd.Timestamp("2022-11-09 06:05:00-04:00")
        display_plot = True
        time_diff_stats = compute_dag_output_diff_stats(
            dag_diff_df,
            aggregation_level,
            node=node,
            bar_timestamp=bar_timestamp,
            display_plot=display_plot,
        )
        res_dict["time_diff_stats"] = time_diff_stats
    if False:
        # Plot differences across columns names.
        aggregation_level = "column"
        node = "predict.2.compute_ret_0"
        bar_timestamp = pd.Timestamp("2022-11-09 06:05:00-04:00")
        display_plot = True
        column_diff_stats = compute_dag_output_diff_stats(
            dag_diff_df,
            aggregation_level,
            node=node,
            bar_timestamp=bar_timestamp,
            display_plot=display_plot,
        )
        res_dict["column_diff_stats"] = column_diff_stats
    if False:
        # Plot differences across asset ids.
        aggregation_level = "asset_id"
        node = "predict.2.compute_ret_0"
        bar_timestamp = pd.Timestamp("2022-11-09 06:05:00-04:00")
        display_plot = True
        asset_id_diff_stats = compute_dag_output_diff_stats(
            dag_diff_df,
            aggregation_level,
            node=node,
            bar_timestamp=bar_timestamp,
            display_plot=display_plot,
        )
        res_dict["asset_id_diff_stats"] = asset_id_diff_stats
    if False:
        # Spot check using heatmap.
        check_node_name = "predict.2.compute_ret_0"
        check_bar_timestamp = pd.Timestamp("2022-11-09 06:05:00-04:00")
        check_column_name = "close.ret_0.pct_change"
        check_heatmap_df = hpandas.heatmap_df(
            dag_diff_df[check_node_name][check_bar_timestamp][check_column_name],
            axis=1,
        )
        display(check_heatmap_df)
        res_dict["check_heatmap_df"] = check_heatmap_df
    return res_dict


# TODO(Grisha): move the section to the `dataflow/core/dag.py`.
# #############################################################################
# DAG time execution statistics
# #############################################################################


def get_dag_node_execution_time(
    dag_dir: str,
    node_name: str,
    bar_timestamp: pd.Timestamp,
) -> float:
    """
    Get DAG node execution time for a given bar from a profiling stats file.

    :param dag_dir: dir with DAG data and info
    :param node_name: name of the DAG node to get excution time for
    :param bar_timestamp: bar timestamp to get excution time for
    :return: exection time for a DAG node's bar timestamp
    """
    _LOG.debug(hprint.to_str("dag_dir node_name bar_timestamp"))
    hdbg.dassert_dir_exists(dag_dir)
    method, topological_id, nid = node_name.split(".")
    output_name = "after_execution"
    bar_timestamp_as_str = bar_timestamp.strftime("%Y%m%d_%H%M%S")
    # Load profile execution stats.
    txt = dtfcordag.load_prof_stats_from_dst_dir(
        dag_dir,
        topological_id,
        nid,
        method,
        output_name,
        bar_timestamp_as_str,
    )
    # TODO(Grisha): Factor out and unit test the execution time extraction from a file.
    # Extract execution time value from the file string line.
    txt_lines = txt.split("\n")
    node_exec_line = txt_lines[3]
    node_exec_time = float(
        node_exec_line[node_exec_line.find("(") + 1 : node_exec_line.find(" s)")]
    )
    return node_exec_time


# TODO(Grisha): pass dag_dir instead, i.e. `.../dag/node_io` instead of
# `.../dag/node_io/node_io.data`.
def get_execution_time_for_all_dag_nodes(dag_data_dir: str) -> pd.DataFrame:
    """
    Get execution time for all DAG nodes and bars.

    E.g.,
                              all_nodes  read_data   resample  ...  predict  process_forecasts
    bar_timestamp
    2023-02-21 02:55:00-05:00    31.279     11.483      2.030         2.862              2.766
    2023-02-21 03:00:00-05:00    31.296     11.573      2.046         2.880              2.770
    2023-02-21 03:05:00-05:00    32.315     12.397      2.023         2.903              2.808

    :param dag_data_dir: a path where nodes data is stored
    :return: exection delays for all DAG nodes and bar timestamps
    """
    # Get a dir that contains DAG data and info.
    dag_dir = dag_data_dir.strip("node_io.data")
    # Get all the DAG node names.
    dag_node_names = get_dag_node_names(dag_data_dir)
    delays_dict = {}
    for node_name in dag_node_names:
        node_dict = {}
        # Get all bar timestamps.
        dag_node_timestamps = get_dag_node_timestamps(
            dag_data_dir, node_name, as_timestamp=True
        )
        for node_timestamp in dag_node_timestamps:
            bar_timestamp = node_timestamp[0]
            # Extract execution time from a profiling stats file.
            node_exec_time = get_dag_node_execution_time(
                dag_dir, node_name, bar_timestamp
            )
            node_dict[bar_timestamp] = node_exec_time
        _, _, nid = node_name.split(".")
        delays_dict[nid] = node_dict
    # Package in a DataFrame.
    df_res = pd.DataFrame.from_dict(delays_dict)
    df_res.index.name = "bar_timestamp"
    # Add column with summary nodes delay.
    df_res.insert(0, "all_nodes", df_res.sum(axis=1))
    return df_res


def plot_dag_execution_stats(
    df_dag_execution_time: pd.DataFrame, *, report_stats: bool = False
) -> None:
    """
    Plot DAG nodes execution time distribution and display stats if requested.

    :param df_dag_execution_time: DAG execution time data
    :param report_stats: whether to display averaged stats or not
    """
    _ = df_dag_execution_time.plot(
        kind="box",
        rot=30,
        title="DAG node execution time",
    )
    if report_stats:
        stats = df_dag_execution_time.agg(["mean", "min", "max", "std"]).T
        hpandas.df_to_str(stats, num_rows=None, log_level=logging.INFO)


# /////////////////////////////////////////////////////////////////////////////


def _get_timestamps_from_order_file_name(
    file_name: str,
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Get bar timestamp and wall clock time from an order file name.

    File name contains a bar timestamp and a wall clock time, e.g.,
    "20230828_152500.20230828_152600.csv" where "20230828_152500" is a bar
    timestamp and "20230828_152600" is a wall clock time as strings.

    :param file_name: order file name
    :return: order bar timestamp and wall clock time
    """
    bar_timestamp_as_str, wall_clock_time_as_str = file_name.split(".")[:2]
    bar_timestamp_as_str = bar_timestamp_as_str.replace("_", " ")
    wall_clock_time_as_str = wall_clock_time_as_str.replace("_", " ")
    # TODO(Grisha): do we need a timezone info?
    bar_timestamp = pd.Timestamp(bar_timestamp_as_str)
    wall_clock_time = pd.Timestamp(wall_clock_time_as_str)
    return bar_timestamp, wall_clock_time


def get_orders_execution_time(orders_dir: str) -> pd.DataFrame:
    """
    Get orders execution time.

    # TODO(Grisha): use a better name for the function since it's not
    # really about the execution but rather about the distance from
    # a bar timestamp.
    The time computed is the difference between the time when an
    order is executed and a bar timestamp.

    E.g.,
                             wall_clock_time  execution_time
    bar_timestamp
    2023-02-21 02:55:00  2023-02-21 02:55:44              44
    2023-02-21 03:00:00  2023-02-21 03:00:45              45
    2023-02-21 03:05:00  2023-02-21 03:05:46              46

    :param orders_dir: dir with order files
    :return: execution time stats for all orders
    """
    hdbg.dassert_dir_exists(orders_dir)
    # TODO(Grisha): use `hio.listdir()` since we are not looking for DAG files
    # here.
    orders = _get_dag_node_csv_file_names(orders_dir)
    data = {
        "wall_clock_time": [],
        "execution_time": [],
    }
    index = []
    for file_name in orders:
        bar_timestamp, wall_clock_time = _get_timestamps_from_order_file_name(
            file_name
        )
        # Compute execution time for the bar.
        execution_time = (wall_clock_time - bar_timestamp).seconds
        #
        data["wall_clock_time"].append(wall_clock_time)
        data["execution_time"].append(execution_time)
        index.append(bar_timestamp)
    df_res = pd.DataFrame(data, index=index)
    df_res.index.name = "bar_timestamp"
    return df_res


# TODO(Grisha): move the section to the `dataflow/core/dag.py`.
# #############################################################################
# DAG memory statistics
# #############################################################################


def extract_df_out_size_from_dag_output(dag_df_out_stats: str) -> Tuple[int, int]:
    """
    Extract results df size info from a DAG output file.

    :param dag_df_out_stats: text with statistics about DAG results df
    :return: results df size:
        - the number of rows
        - the number of columns
    """
    # Extract info about df's size, e.g., 'shape=(1152, 200)'.
    pattern = r"shape=\(\d+, \d+\)"
    df_size_as_str = re.findall(pattern, dag_df_out_stats)
    hdbg.dassert_eq(
        1,
        len(df_size_as_str),
        msg="Must be a single occurence of size stats, received multiple of those: {df_size_as_str}",
    )
    df_size_as_str = df_size_as_str[0]
    _LOG.debug(hprint.to_str("df_size_as_str"))
    # Extract the number of rows and columns.
    df_size = re.findall("\d+", df_size_as_str)
    hdbg.dassert_eq(
        2,
        len(df_size),
        msg="Must be exactly 2 matches that correspond to the number of rows and the number of columns, received multiple of those: {df_size}",
    )
    _LOG.debug(hprint.to_str("df_size"))
    n_rows = int(df_size[0])
    n_cols = int(df_size[1])
    return n_rows, n_cols


def get_dag_df_out_size_for_all_nodes(dag_data_dir) -> pd.DataFrame:
    """
    Get results df size stats for all nodes and timestamps in a DAG dir.

    :param dag_data_dir: a dir that contains DAG output
    :return: a table that contains df results size per node, per bar timestamp, e.g.,
        # TODO(Grisha): swap `n_cols` and `n_rows`.
        ```
                                    read_data        resample
                                    n_cols    n_rows    n_cols    n_rows
        bar_timestamp
        2023-04-13 10:35:00-04:00    250        5760    275        5760
        2023-04-13 10:40:00-04:00    250        5760    275        5760
        ```
    """
    _LOG.debug(hprint.to_str("dag_data_dir"))
    hdbg.dassert_dir_exists(dag_data_dir)
    # TODO(Grisha): Pass a DAG dir instead, i.e. `.../dag/node_io` instead of
    # `.../dag/node_io/node_io.data`.
    dag_dir = dag_data_dir.strip("node_io.data")
    # Get all node names.
    dag_node_names = get_dag_node_names(dag_data_dir)
    df_size_dict = {}
    for node_name in dag_node_names:
        _LOG.debug(hprint.to_str("node_name"))
        node_dict = {}
        # Get all bar timestamps.
        dag_node_timestamps = get_dag_node_timestamps(
            dag_data_dir, node_name, as_timestamp=True
        )
        for node_timestamp in dag_node_timestamps:
            bar_timestamp = node_timestamp[0]
            _LOG.debug(hprint.to_str("bar_timestamp"))
            # E.g., `predict.0.read_data` -> `predict`, `0`, `read_data`.
            method, topological_id, nid = node_name.split(".")
            bar_timestamp_as_str = bar_timestamp.strftime("%Y%m%d_%H%M%S")
            # Load the df stats data.
            df_stats_data = dtfcordag.load_node_df_out_stats_from_dst_dir(
                dag_dir, topological_id, nid, method, bar_timestamp_as_str
            )
            # Get the df size.
            n_rows, n_cols = extract_df_out_size_from_dag_output(df_stats_data)
            node_dict[(bar_timestamp, "n_rows")] = n_rows
            node_dict[(bar_timestamp, "n_cols")] = n_cols
        df_size_dict[nid] = node_dict
    # Combine the results into a single df.
    # TODO(Grisha): check that the size is stable across bar timestamps within a node.
    df_res = pd.DataFrame.from_dict(df_size_dict)
    df_res = df_res.unstack()
    df_res.index.name = "bar_timestamp"
    return df_res


def plot_dag_df_out_size_stats(
    dag_df_out_size_stats: pd.DataFrame, report_stats: bool = False
) -> None:
    """
    Plot the distribution of the number of rows/columns over DAG nodes.

    :param dag_df_out_size_stats: info about DAG results dfs' size
        see `get_dag_df_out_size_for_all_nodes()`
    :param report_stats: print the basic stats about the dfs' size on a DAG node
        level if True, otherwise pass
    """
    # Check that an input df is multiindexed and has the required
    # columns.
    hdbg.dassert_isinstance(dag_df_out_size_stats, pd.DataFrame)
    hdbg.dassert_eq(2, dag_df_out_size_stats.columns.nlevels)
    hdbg.dassert_in("n_rows", dag_df_out_size_stats.columns.get_level_values(1))
    hdbg.dassert_in("n_cols", dag_df_out_size_stats.columns.get_level_values(1))
    # Plot the results.
    n_plots = 2
    n_columns = 1
    y_scale = 5
    _, axes = coplotti.get_multiple_plots(n_plots, n_columns, y_scale)
    title = "The number of rows in a results df per DAG node"
    dag_df_out_size_stats.swaplevel(axis=1)["n_rows"].max().plot(
        ax=axes[0], kind="bar", title=title
    )
    title = "The number of columns in a results df per DAG node"
    dag_df_out_size_stats.swaplevel(axis=1)["n_cols"].max().plot(
        ax=axes[1], kind="bar", title=title
    )
    if report_stats:
        # Compute basic stats about dfs' size.
        stats = dag_df_out_size_stats.agg(["mean", "min", "max", "std"])
        # Sort for readability.
        stats_sorted = stats.sort_index(
            axis=1, level=1, ascending=True, sort_remaining=False
        ).T
        hpandas.df_to_str(stats_sorted, num_rows=None, log_level=logging.INFO)


# #############################################################################
# Portfolio loader
# #############################################################################


# TODO(gp): This needs to go close to Portfolio?
def load_portfolio_artifacts(
    portfolio_dir: str,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load a portfolio dataframe and its associated stats dataframe.

    :return: portfolio_df, portfolio_stats_df
    """
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(portfolio_dir)
    # Load the portfolio and stats dataframes.
    portfolio_df, portfolio_stats_df = omportfo.Portfolio.read_state(
        portfolio_dir,
    )
    # Sanity-check the dataframes.
    hpandas.dassert_time_indexed_df(
        portfolio_df, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        portfolio_stats_df, allow_empty=False, strictly_increasing=True
    )
    # Sanity-check the date ranges of the dataframes against the start and
    # end timestamps.
    first_timestamp = portfolio_df.index[0]
    _LOG.debug("First portfolio_df timestamp=%s", first_timestamp)
    last_timestamp = portfolio_df.index[-1]
    _LOG.debug("Last portfolio_df timestamp=%s", last_timestamp)
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times_freq is not None:
        hdbg.dassert_isinstance(normalize_bar_times_freq, str)
        _LOG.debug("Normalizing bar times to %s grid", normalize_bar_times_freq)
        portfolio_df.index = portfolio_df.index.round(normalize_bar_times_freq)
        portfolio_stats_df.index = portfolio_stats_df.index.round(
            normalize_bar_times_freq
        )
    return portfolio_df, portfolio_stats_df


def load_portfolio_dfs(
    portfolio_path_dict: Dict[str, str],
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    Load multiple portfolios and portfolio stats from disk.

    :param portfolio_path_dict: paths to portfolios for different experiments
    :param normalize_bar_times_freq: frequency to normalize the bar timestamps
    :return: portfolios and portfolio stats for different experiments
    """
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    for name, path in portfolio_path_dict.items():
        hdbg.dassert_path_exists(path)
        _LOG.info("Processing portfolio=%s path=%s", name, path)
        portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
            path, normalize_bar_times_freq
        )
        portfolio_dfs[name] = portfolio_df
        portfolio_stats_dfs[name] = portfolio_stats_df
    #
    return portfolio_dfs, portfolio_stats_dfs


# TODO(gp): Merge with load_portfolio_dfs
def load_portfolio_versions(
    run_dir_dict: Dict[str, dict],
    normalize_bar_times_freq: Optional[str] = None,
    start_timestamp: Optional[pd.Timestamp] = None,
    end_timestamp: Optional[pd.Timestamp] = None,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    for run, dirs in run_dir_dict.items():
        _LOG.info("Processing portfolio=%s", run)
        portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
            dirs["portfolio"],
            normalize_bar_times_freq,
        )
        if start_timestamp is not None:
            portfolio_df = portfolio_df.loc[start_timestamp:]
            portfolio_stats_df = portfolio_stats_df.loc[start_timestamp:]
        if end_timestamp is not None:
            portfolio_df = portfolio_df.loc[:end_timestamp]
            portfolio_stats_df = portfolio_stats_df.loc[:end_timestamp]
        portfolio_dfs[run] = portfolio_df
        portfolio_stats_dfs[run] = portfolio_stats_df
    return portfolio_dfs, portfolio_stats_dfs


def compare_portfolios(
    portfolio_dict: Dict[str, pd.DataFrame],
    *,
    report_stats: bool = True,
    display_plot: bool = False,
    **compare_dfs_kwargs: Any,
) -> pd.DataFrame:
    """
    Compute pairwise max absolute portfolio stats differences.

    :param portfolio_dict: portfolio stats
    :param report_stats: print max abs diff for each pair if True,
        do not print otherwise
    :param display_plot: display plot for each pair if True,
        do not plot otherwise
    :param compare_dfs_kwargs: kwargs for `compare_dfs()`
    :return: pairwise max absolute portfolio stats differences
    """
    # Get a list of portfolio names.
    portfolio_names = sorted(list(portfolio_dict.keys()))
    hdbg.dassert_eq(portfolio_names, ["prod", "research", "sim"])
    # Set a list for pairwise stats data.
    portfolios_diff_dfs = []
    # Iterate over all the possible portfolio pairs.
    for name_pair in itertools.combinations(portfolio_names, 2):
        # Compute all the pairwise portfolio differences.
        name1 = name_pair[0]
        name2 = name_pair[1]
        diff_df = hpandas.compare_multiindex_dfs(
            portfolio_dict[name1],
            portfolio_dict[name2],
            compare_dfs_kwargs=compare_dfs_kwargs,
        )
        # Remove the sign.
        diff_df = diff_df.abs()
        if report_stats:
            max_diff = diff_df.max().max()
            _LOG.info(
                "Max difference between %s and %s is=%s",
                name1,
                name2,
                max_diff,
            )
        # Compute pairwise portfolio differences stats.
        portfolios_diff = diff_df.max().unstack().max(axis=1)
        portfolios_diff.name = "_".join([name1, name2, "diff"])
        if display_plot:
            _ = portfolios_diff.plot.bar()
            plt.xticks(rotation=0)
            plt.show()
        # Add stats data to the result list.
        portfolios_diff_dfs.append(portfolios_diff)
    # Combine the stats.
    res_diff_df = pd.concat(portfolios_diff_dfs, axis=1)
    return res_diff_df


def normalize_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = df.copy()
    normalized_df.drop(-1, axis=1, level=1, inplace=True)
    return normalized_df


def compute_delay(df: pd.DataFrame, freq: str) -> pd.Series:
    bar_index = df.index.round(freq)
    delay_vals = df.index - bar_index
    delay = pd.Series(delay_vals, bar_index, name="delay")
    return delay


# #############################################################################
# Target position loader
# #############################################################################


def load_target_positions(
    target_position_dir: str,
    normalize_bar_times_freq: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load a target position dataframe.
    """
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(target_position_dir)
    # Load the target position dataframe.
    target_position_df = (
        otpaorge.TargetPositionAndOrderGenerator.load_target_positions(
            target_position_dir
        )
    )
    # Sanity-check the dataframe.
    hpandas.dassert_time_indexed_df(
        target_position_df, allow_empty=False, strictly_increasing=True
    )
    # Sanity-check the date ranges of the dataframes against the start and
    # end timestamps.
    first_timestamp = target_position_df.index[0]
    _LOG.debug("First target_position_df timestamp=%s", first_timestamp)
    last_timestamp = target_position_df.index[-1]
    _LOG.debug("Last target_position_df timestamp=%s", last_timestamp)
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times_freq is not None:
        hdbg.dassert_isinstance(normalize_bar_times_freq, str)
        _LOG.debug("Normalizing bar times to %s grid", normalize_bar_times_freq)
        target_position_df.index = target_position_df.index.round(
            normalize_bar_times_freq
        )
    return target_position_df


def load_target_position_versions(
    run_dir_dict: Dict[str, dict],
    normalize_bar_times_freq: Optional[str] = None,
    start_timestamp: Optional[pd.Timestamp] = None,
    end_timestamp: Optional[pd.Timestamp] = None,
) -> Dict[str, pd.DataFrame]:
    dfs = {}
    for run, dirs in run_dir_dict.items():
        _LOG.info("Processing run=%s", run)
        df = load_target_positions(
            dirs["target_positions"],
            normalize_bar_times_freq,
        )
        if start_timestamp is not None:
            df = df.loc[start_timestamp:]
        if end_timestamp is not None:
            df = df.loc[:end_timestamp]
        dfs[run] = df
    return dfs


# #############################################################################
# Portfolio/order reconciliation
# #############################################################################


def compute_shares_traded(
    portfolio_df: pd.DataFrame,
    order_df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    """
    Compute the number of shares traded between portfolio snapshots.

    :param portfolio_df: dataframe reconstructed from logged `Portfolio`
        object
    :param order_df: dataframe constructed from logged `Order` objects
    :freq: bar frequency for dataframe index rounding (for bar alignment and
        easy merging)
    :return: multilevel column dataframe with shares traded, targets,
        estimated benchmark cost per share, and underfill counts
    """
    # Process `portfolio_df`.
    hdbg.dassert_isinstance(portfolio_df, pd.DataFrame)
    hdbg.dassert_in("executed_trades_shares", portfolio_df.columns)
    hdbg.dassert_in("executed_trades_notional", portfolio_df.columns)
    portfolio_df.index = portfolio_df.index.round(freq)
    executed_trades_shares = portfolio_df["executed_trades_shares"]
    executed_trades_notional = portfolio_df["executed_trades_notional"]
    # Divide the notional flow (signed) by the shares traded (signed)
    # to get the estimated (positive) price at which the trades took place.
    executed_trades_price_per_share = executed_trades_notional.abs().divide(
        executed_trades_shares
    )
    # Process `order_df`.
    hdbg.dassert_isinstance(order_df, pd.DataFrame)
    hdbg.dassert_is_subset(
        ["end_timestamp", "asset_id", "diff_num_shares"], order_df.columns
    )
    # Pivot the order dataframe.
    order_share_targets = order_df.pivot(
        index="end_timestamp",
        columns="asset_id",
        values="diff_num_shares",
    )
    order_share_targets.index = order_share_targets.index.round(freq)
    # Compute underfills.
    share_target_sign = np.sign(order_share_targets)
    underfill = share_target_sign * (order_share_targets - executed_trades_shares)
    # Combine into a multi-column dataframe.
    df = pd.concat(
        {
            "shares_traded": executed_trades_shares,
            "order_share_target": order_share_targets,
            "executed_trades_price_per_shares": executed_trades_price_per_share,
            "underfill": underfill,
        },
        axis=1,
    )
    # The indices may not perfectly agree in the concat, and so we perform
    # another fillna and int casting.
    df["underfill"] = df["underfill"].fillna(0).astype(int)
    return df


# #############################################################################
# Costs derived from Portfolio and Target Positions
# #############################################################################


def compute_notional_costs(
    portfolio_df: pd.DataFrame,
    target_position_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute notional slippage and underfill costs.

    This is more accurate than slippage computed from `Portfolio` alone,
    because `target_position_df` provides baseline prices even when
    `holdings_shares` is zero (in which case we cannot compute the
    baseline price from `Portfolio`).
    """
    executed_trades_shares = portfolio_df["executed_trades_shares"]
    target_trades_shares = target_position_df["target_trades_shares"]
    underfill_share_count = (
        target_trades_shares.shift(1).abs() - executed_trades_shares.abs()
    )
    # Get baseline price.
    price = target_position_df["price"]
    # Compute underfill opportunity cost with respect to baseline price.
    side = np.sign(target_position_df["target_trades_shares"].shift(2))
    underfill_notional_cost = (
        side * underfill_share_count.shift(1) * price.subtract(price.shift(1))
    )
    # Compute notional slippage.
    executed_trades_notional = portfolio_df["executed_trades_notional"]
    slippage_notional = executed_trades_notional - (
        price * executed_trades_shares
    )
    # Aggregate results.
    cost_df = pd.concat(
        {
            "underfill_notional_cost": underfill_notional_cost,
            "slippage_notional": slippage_notional,
        },
        axis=1,
    )
    return cost_df


def apply_costs_to_baseline(
    baseline_portfolio_stats_df: pd.DataFrame,
    portfolio_stats_df: pd.DataFrame,
    portfolio_df: pd.DataFrame,
    target_position_df: pd.DataFrame,
) -> pd.DataFrame:
    srs = []
    # Add notional pnls.
    baseline_pnl = baseline_portfolio_stats_df["pnl"].rename("baseline_pnl")
    srs.append(baseline_pnl)
    pnl = portfolio_stats_df["pnl"].rename("pnl")
    srs.append(pnl)
    # Compute notional costs.
    costs = compute_notional_costs(portfolio_df, target_position_df)
    slippage = costs["slippage_notional"].sum(axis=1).rename("slippage_notional")
    srs.append(slippage)
    underfill_cost = (
        costs["underfill_notional_cost"]
        .sum(axis=1)
        .rename("underfill_notional_cost")
    )
    srs.append(underfill_cost)
    # Adjust baseline pnl by costs.
    baseline_pnl_minus_costs = (baseline_pnl - slippage - underfill_cost).rename(
        "baseline_pnl_minus_costs"
    )
    srs.append(baseline_pnl_minus_costs)
    # Compare adjusted baseline pnl to pnl.
    baseline_pnl_minus_costs_minus_pnl = (baseline_pnl_minus_costs - pnl).rename(
        "baseline_pnl_minus_costs_minus_pnl"
    )
    srs.append(baseline_pnl_minus_costs_minus_pnl)
    # Compare baseline pnl to pnl.
    baseline_pnl_minus_pnl = (baseline_pnl - pnl).rename("baseline_pnl_minus_pnl")
    srs.append(baseline_pnl_minus_pnl)
    df = pd.concat(srs, axis=1)
    return df


# #############################################################################
# Slippage derived from Portfolio
# #############################################################################


def compute_share_prices_and_slippage(
    df: pd.DataFrame,
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Compare trade prices against benchmark.
    NOTE: baseline prices are not available when holdings_shares is zero, and
        this may lead to artificial NaNs in the calculations.
    :param df: a portfolio-like dataframe, with the following columns for
        each asset:
        - holdings_notional
        - holdings_shares
        - executed_trades_notional
        - executed_trades_shares
    :return: dataframe with per-asset
        - holdings_price_per_share
        - trade_price_per_share
        - slippage_in_bps
        - is_benchmark_profitable
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    cols = [
        "holdings_notional",
        "holdings_shares",
        "executed_trades_notional",
        "executed_trades_shares",
    ]
    hdbg.dassert_is_subset(cols, df.columns.levels[0])
    # Compute price per share of holdings (using holdings reference price).
    # We assume that holdings are computed with a benchmark price (e.g., TWAP).
    holdings_price_per_share = df["holdings_notional"] / df["holdings_shares"]
    # We do not expect negative prices.
    hdbg.dassert_lte(0, holdings_price_per_share.min().min())
    # Compute price per share of trades (using execution reference prices).
    trade_price_per_share = (
        df["executed_trades_notional"] / df["executed_trades_shares"]
    )
    hdbg.dassert_lte(0, trade_price_per_share.min().min())
    # Buy = +1, sell = -1.
    buy = (df["executed_trades_notional"] > 0).astype(int)
    sell = (df["executed_trades_notional"] < 0).astype(int)
    side = buy - sell
    # Compute notional slippage against benchmark.
    slippage_notional_per_share = side * (
        trade_price_per_share - holdings_price_per_share
    )
    slippage_notional = (
        slippage_notional_per_share * df["executed_trades_shares"].abs()
    )
    # Compute slippage in bps.
    slippage_in_bps = 1e4 * slippage_notional_per_share / holdings_price_per_share
    # Determine whether the trade, if closed at t+1, would be profitable if
    # executed at the benchmark price on both legs.
    is_benchmark_profitable = side * np.sign(
        holdings_price_per_share.diff().shift(-1)
    )
    benchmark_return_notional = side * holdings_price_per_share.diff().shift(-1)
    benchmark_return_in_bps = (
        1e4 * side * holdings_price_per_share.pct_change().shift(-1)
    )
    price_df = pd.concat(
        {
            "holdings_price_per_share": holdings_price_per_share,
            "trade_price_per_share": trade_price_per_share,
            "slippage_notional": slippage_notional,
            "slippage_notional_per_share": slippage_notional_per_share,
            "slippage_in_bps": slippage_in_bps,
            "benchmark_return_notional": benchmark_return_notional,
            "benchmark_return_in_bps": benchmark_return_in_bps,
            "is_benchmark_profitable": is_benchmark_profitable,
        },
        axis=1,
    )
    if join_output_with_input:
        price_df = pd.concat([df, price_df], axis=1)
    return price_df


# #############################################################################
# Fill stats derived from target position dataframe
# #############################################################################


def compute_fill_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare targets to realized.

    :param df: a target position dataframe.
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    cols = [
        "holdings_shares",
        "price",
        "target_holdings_shares",
        "target_trades_shares",
    ]
    hdbg.dassert_is_subset(cols, df.columns.levels[0])
    # The trades and shares are signed to indicate the side.
    realized_trades_shares = df["holdings_shares"].subtract(
        df["holdings_shares"].shift(1), fill_value=0
    )
    # These are end-of-bar time-indexed.
    fill_rate = (
        realized_trades_shares / df["target_trades_shares"].shift(1)
    ).abs()
    tracking_error_shares = df["holdings_shares"] - df[
        "target_holdings_shares"
    ].shift(1)
    underfill_share_count = (
        df["target_trades_shares"].shift(1).abs() - realized_trades_shares.abs()
    )
    tracking_error_notional = df["holdings_notional"] - df[
        "target_holdings_notional"
    ].shift(1)
    tracking_error_bps = (
        1e4 * tracking_error_notional / df["target_holdings_notional"].shift(1)
    )
    #
    fills_df = pd.concat(
        {
            "realized_trades_shares": realized_trades_shares,
            "fill_rate": fill_rate,
            "underfill_share_count": underfill_share_count,
            "tracking_error_shares": tracking_error_shares,
            "tracking_error_notional": tracking_error_notional,
            "tracking_error_bps": tracking_error_bps,
        },
        axis=1,
    )
    return fills_df


# #############################################################################
# Log file helpers
# #############################################################################


def get_dir(root_dir: str, date_str: str, search_str: str, mode: str) -> str:
    """
    Get base log directory for a specific date.
    """
    hdbg.dassert(root_dir)
    hdbg.dassert_dir_exists(root_dir)
    if mode == "sim":
        dir_ = os.path.join(f"{root_dir}/{date_str}/system_log_dir")
    else:
        if mode == "prod":
            cmd = f"find {root_dir}/{date_str}/job.live* -name '{search_str}'"
        elif mode == "cand":
            cmd = (
                f"find {root_dir}/{date_str}/job.candidate.* -name '{search_str}'"
            )
        else:
            raise ValueError("Invalid mode %s", mode)
        rc, dir_ = hsystem.system_to_string(cmd)
    hdbg.dassert(dir_)
    hdbg.dassert_dir_exists(dir_)
    return dir_


def get_run_dirs(
    root_dir: str, date_str: str, search_str: str, modes: List[str]
) -> Dict[str, dict]:
    """
    Get a dictionary of base and derived run directories for a specific date.
    """
    run_dir_dict = {}
    for run in modes:
        dir_ = get_dir(root_dir, date_str, search_str, run)
        dict_ = {
            "base": dir_,
            "dag": os.path.join(dir_, "dag/node_io/node_io.data"),
            "portfolio": os.path.join(dir_, "process_forecasts/portfolio"),
            "target_positions": os.path.join(dir_, "process_forecasts"),
        }
        run_dir_dict[run] = dict_
    return run_dir_dict


# #############################################################################
# Multiday loader
# #############################################################################


def load_and_process_artifacts(
    root_dir: str,
    date_strs: List[str],
    search_str: str,
    mode: str,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[
    Dict[str, dict],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
]:
    hdbg.dassert(date_strs)
    runs = {}
    dag_dfs = {}
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    target_position_dfs = {}
    for date_str in date_strs:
        try:
            run_dir_dict = get_run_dirs(root_dir, date_str, search_str, [mode])
            runs[date_str] = run_dir_dict
        except:
            _LOG.warning("Unable to get directories for %s", date_str)
        try:

            def warn_if_duplicates_exist(df, name):
                if df.index.has_duplicates:
                    _LOG.warning(
                        "df %s has duplicates on date_str=%s", name, date_str
                    )

            # Load DAG.
            dag_df = get_latest_output_from_last_dag_node(
                run_dir_dict[mode]["dag"]
            )
            warn_if_duplicates_exist(dag_df, "dag")
            # Localize DAG to `date_str`.
            dag_df = dag_df.loc[date_str]
            dag_dfs[date_str] = dag_df
            # Load Portfolio.
            portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
                run_dir_dict[mode]["portfolio"],
                normalize_bar_times_freq,
            )
            warn_if_duplicates_exist(portfolio_df, "portfolio")
            warn_if_duplicates_exist(portfolio_stats_df, "portfolio_stats")
            portfolio_dfs[date_str] = portfolio_df
            portfolio_stats_dfs[date_str] = portfolio_stats_df
            # Load target positions.
            target_position_df = load_target_positions(
                run_dir_dict[mode]["target_positions"], normalize_bar_times_freq
            )
            warn_if_duplicates_exist(target_position_df, "target_positions")
            target_position_dfs[date_str] = target_position_df
        except:
            _LOG.warning("Unable to load data for %s", date_str)
    _ = runs
    return (
        runs,
        dag_dfs,
        portfolio_dfs,
        portfolio_stats_dfs,
        target_position_dfs,
    )
