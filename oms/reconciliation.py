"""
Import as:

import oms.reconciliation as omreconc
"""

import collections
import datetime
import itertools
import logging
import os
import pprint
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hpickle as hpickle
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import oms.ccxt_broker as occxbrok
import oms.portfolio as omportfo
import oms.target_position_and_order_generator as otpaorge

_LOG = logging.getLogger(__name__)

# Each function should accept a `log_level` parameters that controls at which
# level output summarizing the results. By default it is set by functin to
# logging.DEBUG (since we don't want to print anything).
# The internal debugging info is printed as usual at level `logging.DEBUG`.


# #############################################################################
# Config
# #############################################################################


def build_reconciliation_configs(
    dag_builder_name: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    mode: Optional[str],
) -> cconfig.ConfigList:
    """
    Build reconciliation configs that are specific of an asset class.

    Note: the function returns list of configs because the function is used
    as a config builder function for the run notebook script.

    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run, e.g. "20221010_080000"
    :param mode: reconciliation run mode
    :return: list of reconciliation configs
    """
    start_timestamp_as_str, end_timestamp_as_str = resolve_timestamps(
        start_timestamp_as_str, end_timestamp_as_str
    )
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
        mode = resolve_run_mode(mode)
        prod_subdir = get_prod_system_log_dir(
            mode, start_timestamp_as_str, end_timestamp_as_str
        )
        # For crypto the TCA part is not implemented yet.
        run_tca = False
        #
        bar_duration = "5T"
        #
        root_dir = "/shared_data/prod_reconciliation"
        # TODO(Grisha): this is not DRY, unify with `lib_tasks_reconcile.py`.
        prod_dir = os.path.join(
            root_dir,
            dag_builder_name,
            run_date,
            "prod",
            prod_subdir,
        )
        sim_dir = os.path.join(
            root_dir,
            dag_builder_name,
            run_date,
            "simulation",
            "system_log_dir",
        )
        system_log_path_dict = {
            "prod": prod_dir,
            # For crypto we do not have a `candidate`.
            # "cand": prod_dir,
            "sim": sim_dir,
        }
        #
        fep_init_dict = {
            "price_col": "twap",
            "prediction_col": "vwap.ret_0.vol_adj.lag_-2.hat",
            "volatility_col": "vwap.ret_0.vol",
        }
        quantization = "asset_specific"
        market_info = occxbrok.load_market_data_info()
        asset_id_to_share_decimals = occxbrok.subset_market_info(
            market_info, "amount_precision"
        )
        gmv = 700.0
        liquidate_at_end_of_day = False
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
        "research_forecast_evaluator_from_prices": {
            "init": fep_init_dict,
            "annotate_forecasts_kwargs": {
                "quantization": quantization,
                "asset_id_to_share_decimals": asset_id_to_share_decimals,
                "burn_in_bars": 3,
                "style": "cross_sectional",
                "bulk_frac_to_remove": 0.0,
                "target_gmv": gmv,
                "liquidate_at_end_of_day": liquidate_at_end_of_day,
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


def resolve_run_mode(mode: Optional[str]) -> str:
    """
    Return run mode.

    If a mode is not specified by a user, set a default value.
    """
    if mode is None:
        mode = "scheduled"
    hdbg.dassert_in(mode, ["scheduled", "manual"])
    return mode


# /////////////////////////////////////////////////////////////////////////////


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


def get_run_date(start_timestamp_as_str: Optional[str]) -> str:
    """
    Return the run date as string from start timestamp, e.g. "20221017".

    If start timestamp is not specified by a user then return current
    date.

    E.g., "20221101_064500" -> "20221101".
    """
    if start_timestamp_as_str is None:
        run_date = datetime.date.today().strftime("%Y%m%d")
    else:
        # TODO(Dan): Add assert for `start_timestamp_as_str` regex.
        run_date = start_timestamp_as_str.split("_")[0]
    _LOG.info(hprint.to_str("run_date"))
    _dassert_is_date(run_date)
    return run_date


def resolve_timestamps(
    start_timestamp_as_str: Optional[str], end_timestamp_as_str: Optional[str]
) -> Tuple[str, str]:
    """
    Return start and end timestamps.

    If timestamps are not specified by a user then set a default value
    for it and return it.
    """
    today_as_str = datetime.date.today().strftime("%Y%m%d")
    if start_timestamp_as_str is None:
        start_timestamp_as_str = "_".join([today_as_str, "100500"])
    if end_timestamp_as_str is None:
        end_timestamp_as_str = "_".join([today_as_str, "120000"])
    return start_timestamp_as_str, end_timestamp_as_str


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
    if data_type == "portfolio":
        dir_name = "process_forecasts/portfolio"
    elif data_type == "dag":
        dir_name = "dag/node_io/node_io.data"
    else:
        raise ValueError(f"Unsupported data type={data_type}")
    for k, v in system_log_path_dict.items():
        cur_dir = os.path.join(v, dir_name)
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
# Compare DAG
# #############################################################################


def _prepare_dfs_for_comparison(
    previous_df: pd.DataFrame, current_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare 2 consecutive node dataframes for comparison.

    Preparation includes:
        - Aligning the indices
        - Removing the burn-in interval
        - Sanity checks

    Dataframes contain a 30-minutes burn-in interval required for
    volatility computations. This interval should be dropped.

    :param previous_df: DAG node output that corresponds to the (i-1)-th timestamp
    :param current_df: DAG node output that corresponds to the i-th timestamp
    :return: processed DAG node outputs
    """
    # Assert that both dfs are sorted by timestamp.
    hpandas.dassert_strictly_increasing_index(previous_df)
    hpandas.dassert_strictly_increasing_index(current_df)
    # Align the indices.
    previous_df = previous_df[1:]
    current_df = current_df[:-1]
    # Remove the first rows. Since we remove the first row from `previous_df`
    # above and do not for `current_df`, the first rows now have different
    # values because of burn-in interval.
    previous_df = previous_df[1:]
    current_df = current_df[1:]
    # Remove burn-in interval.
    # TODO(Grisha): @Dan Parametrise the approach to selecting data interval
    # to drop, i.e. use 30 minutes burn-in interval and avoid using direct
    # indices.
    previous_df = previous_df.drop(previous_df.index[253:260])
    current_df = current_df.drop(current_df.index[253:260])
    # Assert both dfs have equal size.
    hdbg.dassert_eq(previous_df.shape[0], current_df.shape[0])
    return previous_df, current_df


def check_dag_output_self_consistency(
    node_dfs: Dict[pd.Timestamp, pd.DataFrame]
) -> None:
    """
    Check that all the DAG output dataframes are equal at intersecting time
    intervals.

    :param node_dfs: timestamp to DAG output mapping
    """
    # Make sure that the dict is sorted by timestamp.
    node_dfs = dict(sorted(node_dfs.items()))
    node_dfs = list(node_dfs.items())
    start = 1
    end = len(node_dfs)
    for i in range(start, end):
        current_timestamp = node_dfs[i][0]
        current_df = node_dfs[i][1]
        current_df = current_df.sort_index()
        #
        previous_timestamp = node_dfs[i - 1][0]
        previous_df = node_dfs[i - 1][1]
        previous_df = previous_df.sort_index()
        _LOG.debug(
            "Comparing dfs for timestamps %s and %s",
            current_timestamp,
            previous_timestamp,
        )
        previous_df, current_df = _prepare_dfs_for_comparison(
            previous_df, current_df
        )
        # Assert if the difference is above the specified threshold.
        assert_diff_threshold = 1e-3
        _ = hpandas.compare_dfs(
            previous_df,
            current_df,
            diff_mode="pct_change",
            assert_diff_threshold=assert_diff_threshold,
        )


def _get_dag_node_parquet_file_names(dag_dir: str) -> List[str]:
    """
    Get Parquet file names for all the nodes in the target folder.

    :param dag_dir: dir with the DAG output
    :return: list of all files for all nodes and timestamps in the dir
    """
    hdbg.dassert_dir_exists(dag_dir)
    cmd = f"ls {dag_dir} | grep 'parquet'"
    _, nodes = hsystem.system_to_string(cmd)
    nodes = nodes.split("\n")
    return nodes


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
            # TODO(Grisha): Pass tz a param?
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
    Retrieve output from the last DAG node.

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
    cmd += f" | grep '{timestamp}'"
    _, file = hsystem.system_to_string(cmd)
    df = hparque.from_parquet(file)
    return df


def load_dag_outputs(
    dag_path_dict: Dict[str, str],
    *,
    only_last_node: bool = True,
    only_last_timestamp: bool = True,
    only_last_row: bool = False,
) -> Dict[str, Dict[str, Dict[pd.Timestamp, pd.DataFrame]]]:
    """
    Load DAG output for different experiments.

    Output example:
    ```
    {
        "prod": {
            "predict.0.read_data": {
                "2022-11-03 06:05:00-04:00": pd.DataFrame,
                ...
            },
        },
    }
    ```

    :param dag_path_dict: dst dir for every experiment
    :param only_last_node: if `True`, get DAG output only for the last node,
        otherwise load data for all the nodes
    :param only_last_timestamp: if `True`, get DAG output only for the last timestamp,
        otherwise load data for all the timestamps
    :param only_last_row: if `True`, get DAG output only for the last data row,
        otherwise load whole dataframes
    :param log_level: log level
    :return: DAG output per experiment, node and timestamp
    """
    dag_df_dict = {}
    for experiment, path in dag_path_dict.items():
        # Set experiment default dict to fill it in the loop.
        experiment_dict = collections.defaultdict(dict)
        # Get DAG node names to iterate over them.
        nodes = get_dag_node_names(path)
        if only_last_node:
            nodes = [nodes[-1]]
        for node in nodes:
            # Get DAG timestamps to iterate over them.
            dag_timestamps = get_dag_node_timestamps(path, node)
            # Keep bar timestamps only.
            bar_timestamps = [
                bar_timestamp for bar_timestamp, _ in dag_timestamps
            ]
            if only_last_timestamp:
                bar_timestamps = [bar_timestamps[-1]]
            for timestamp in bar_timestamps:
                # Get DAG output for the specified node and timestamp.
                df = get_dag_node_output(path, node, timestamp)
                if only_last_row:
                    df = df.tail(1)
                experiment_dict[node][timestamp] = df
        # Populate result dict with experiment output dict.
        dag_df_dict[experiment] = experiment_dict
    return dag_df_dict


def compute_dag_outputs_diff(
    dag_df_dict: Dict[str, Dict[str, Dict[pd.Timestamp, pd.DataFrame]]],
    compare_dfs_kwargs: Optional[Dict[str, Any]] = None,
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
    if compare_dfs_kwargs is None:
        compare_dfs_kwargs = {}
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


def compute_dag_delay_in_seconds(
    dag_node_timestamps: List[Tuple[pd.Timestamp, pd.Timestamp]],
    *,
    print_stats: bool = True,
    display_plot: bool = False,
) -> pd.DataFrame:
    """
    Compute difference in seconds between `wall_clock_timestamp` and
    `bar_timestamp` for each timestamp.

    :param print_stats: if True print stats (i.e. min, mean, max), otherwise
        do not print
    :param display_plot: if True display delay chart over bar timestamp,
        otherwise do not display
    :return: a table with bar timestamps and corresponding delays in seconds
    """
    delay_in_seconds = []
    bar_timestamps = []
    for bar_timestamp, wall_clock_timestamp in dag_node_timestamps:
        diff = (wall_clock_timestamp - bar_timestamp).seconds
        delay_in_seconds.append(diff)
        bar_timestamps.append(bar_timestamp)
    delay_column_name = "delay_in_seconds"
    diff = pd.DataFrame(
        delay_in_seconds, columns=[delay_column_name], index=bar_timestamps
    )
    diff = diff.sort_values(
        delay_column_name,
        ascending=False,
    )
    diff.index.name = "bar_timestamp"
    if print_stats:
        _LOG.info(
            "Minimum delay=%s, mean delay=%s, maximum delay=%s",
            round(diff["delay_in_seconds"].min(), 2),
            round(diff["delay_in_seconds"].mean(), 2),
            round(diff["delay_in_seconds"].max(), 2),
        )
    if display_plot:
        diff.plot(
            kind="bar",
            title="Difference in seconds between DAG wall clock timestamp and bar timestamp",
        )
    return diff


# #############################################################################
# Portfolio
# #############################################################################


# TODO(gp): This needs to go close to Portfolio?
def load_portfolio_artifacts(
    portfolio_dir: str,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    freq: str,
    normalize_bar_times: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load a portfolio dataframe and its associated stats dataframe.

    :return: portfolio_df, portfolio_stats_df
    """
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(portfolio_dir)
    # Sanity-check timestamps.
    hdbg.dassert_isinstance(start_timestamp, pd.Timestamp)
    hdbg.dassert_isinstance(end_timestamp, pd.Timestamp)
    hdbg.dassert_lt(start_timestamp, end_timestamp)
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
    hdbg.dassert_lte(first_timestamp.round(freq), start_timestamp)
    last_timestamp = portfolio_df.index[-1]
    _LOG.debug("Last portfolio_df timestamp=%s", last_timestamp)
    hdbg.dassert_lte(end_timestamp, last_timestamp.round(freq))
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times:
        _LOG.debug("Normalizing bar times to %s grid", freq)
        portfolio_df.index = portfolio_df.index.round(freq)
        portfolio_stats_df.index = portfolio_stats_df.index.round(freq)
    # Time-localize the portfolio dataframe and portfolio stats dataframe.
    _LOG.debug(
        "Trimming times to start_timestamp=%s, end_timestamp=%s",
        start_timestamp,
        end_timestamp,
    )
    portfolio_df = portfolio_df.loc[start_timestamp:end_timestamp]
    portfolio_stats_df = portfolio_stats_df.loc[start_timestamp:end_timestamp]
    #
    return portfolio_df, portfolio_stats_df


def load_portfolio_dfs(
    portfolio_path_dict: Dict[str, str],
    portfolio_config: Dict[str, Any],
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    Load multiple portfolios and portfolio stats from disk.

    :param portfolio_path_dict: paths to portfolios for different experiments
    :param portfolio_config: params for `load_portfolio_artifacts()`
    :return: portfolios and portfolio stats for different experiments
    """
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    for name, path in portfolio_path_dict.items():
        hdbg.dassert_path_exists(path)
        _LOG.info("Processing portfolio=%s path=%s", name, path)
        portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
            path,
            **portfolio_config,
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
    compare_dfs_kwargs: Any = None,
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


def load_target_positions(
    target_position_dir: str,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    freq: str,
    normalize_bar_times: bool,
) -> pd.DataFrame:
    """
    Load a target position dataframe.
    """
    # TODO(Paul): Share code with `load_portfolio_artifacts()`.
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(target_position_dir)
    # Sanity-check timestamps.
    hdbg.dassert_isinstance(start_timestamp, pd.Timestamp)
    hdbg.dassert_isinstance(end_timestamp, pd.Timestamp)
    hdbg.dassert_lt(start_timestamp, end_timestamp)
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
    hdbg.dassert_lte(first_timestamp.round(freq), start_timestamp)
    last_timestamp = target_position_df.index[-1]
    _LOG.debug("Last target_position_df timestamp=%s", last_timestamp)
    hdbg.dassert_lte(end_timestamp, last_timestamp.round(freq))
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times:
        _LOG.debug("Normalizing bar times to %s grid", freq)
        target_position_df.index = target_position_df.index.round(freq)
    # Time-localize the target position dataframe.
    _LOG.debug(
        "Trimming times to start_timestamp=%s, end_timestamp=%s",
        start_timestamp,
        end_timestamp,
    )
    target_position_df = target_position_df.loc[start_timestamp:end_timestamp]
    #
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


def compute_share_prices_and_slippage(
    df: pd.DataFrame,
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Compare trade prices against benchmark.

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
    # Compute slippage against benchmark.
    slippage = (
        side
        * (trade_price_per_share - holdings_price_per_share)
        / holdings_price_per_share
    )
    slippage_in_bps = 1e4 * slippage
    # Determine whether the trade, if closed at t+1, would be profitable if
    # executed at the benchmark price on both legs.
    is_benchmark_profitable = side * np.sign(
        holdings_price_per_share.diff().shift(-1)
    )
    benchmark_return_in_bps = (
        1e4 * side * holdings_price_per_share.pct_change().shift(-1)
    )
    price_df = pd.concat(
        {
            "holdings_price_per_share": holdings_price_per_share,
            "trade_price_per_share": trade_price_per_share,
            "slippage_in_bps": slippage_in_bps,
            "benchmark_return_in_bps": benchmark_return_in_bps,
            "is_benchmark_profitable": is_benchmark_profitable,
        },
        axis=1,
    )
    if join_output_with_input:
        price_df = pd.concat([df, price_df], axis=1)
    return price_df


def get_asset_slice(df: pd.DataFrame, asset_id: int) -> pd.DataFrame:
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    hdbg.dassert_in(asset_id, df.columns.levels[1])
    slice_ = df.T.xs(asset_id, level=1).T
    return slice_


def compute_fill_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare targets to realized.
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    cols = [
        "holdings_shares",
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
# Multiday loader
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


def load_and_process_artifacts(
    root_dir: str,
    date_strs: List[str],
    search_str: str,
    mode: str,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hdbg.dassert(date_strs)
    runs = {}
    dag_dfs = []
    portfolio_dfs = []
    portfolio_stats_dfs = []
    target_position_dfs = []
    slippage_dfs = []
    fills_dfs = []
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
            dag_dfs.append(dag_df)
            # Load Portfolio.
            portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
                run_dir_dict[mode]["portfolio"],
                normalize_bar_times_freq,
            )
            warn_if_duplicates_exist(portfolio_df, "portfolio")
            warn_if_duplicates_exist(portfolio_stats_df, "portfolio_stats")
            portfolio_dfs.append(portfolio_df)
            portfolio_stats_dfs.append(portfolio_stats_df)
            # Load target positions.
            target_position_df = load_target_positions(
                run_dir_dict[mode]["target_positions"], normalize_bar_times_freq
            )
            warn_if_duplicates_exist(target_position_df, "target_positions")
            target_position_dfs.append(target_position_df)
            # Compute slippage.
            slippage_df = compute_share_prices_and_slippage(portfolio_df)
            slippage_dfs.append(slippage_df)
            # Compute fills.
            fills_df = compute_fill_stats(target_position_df)
            fills_dfs.append(fills_df)
        except:
            _LOG.warning("Unable to load data for %s", date_str)
    _ = runs
    dag_df = pd.concat(dag_dfs)
    portfolio_df = pd.concat(portfolio_dfs)
    portfolio_stats_df = pd.concat(portfolio_stats_dfs)
    target_position_df = pd.concat(target_position_dfs)
    slippage_df = pd.concat(slippage_dfs)
    fills_df = pd.concat(fills_dfs)
    return (
        dag_df,
        portfolio_df,
        portfolio_stats_df,
        target_position_df,
        slippage_df,
        fills_df,
    )
