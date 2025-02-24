"""
Import as:

import dataflow.core.dag_statistics as dtfcodasta
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd

import core.plotting as coplotti
import dataflow.core.dag as dtfcordag
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


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
    if _LOG.isEnabledFor(logging.DEBUG):
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
        if _LOG.isEnabledFor(logging.DEBUG):
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
def get_dag_node_csv_file_names(dag_dir: str) -> List[str]:
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

    E.g.,
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

    :param dag_dir: dir with the DAG output
    :return: a sorted list of all DAG node names
    """
    file_names = _get_dag_node_parquet_file_names(dag_dir)
    # E.g., if file name is
    # `predict.8.process_forecasts.df_out.20221028_080000.parquet` then the
    # node name is `predict.8.process_forecasts`.
    node_names = sorted(
        list(set(node.split(".df_out")[0] for node in file_names)),
        key=lambda x: list(map(int, re.findall(r"\d+", x))),
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
    :param log_level: level of debugging to use
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
    # TODO(Nina): consider using `listdir()`.
    cmd = f"find '{dag_dir}' -name {dag_node_name}*.parquet"
    cmd += f" | grep 'df_out.{timestamp}'"
    _, files = hsystem.system_to_string(cmd)
    files = files.split("\n")
    number_of_files = len(files)
    msg = f"There were found {number_of_files} files at {dag_dir} for node={dag_node_name} for bar_timestamp={timestamp} while should be only one file for each node, bar timestamp."
    hdbg.dassert_eq(1, number_of_files, msg=msg)
    df = hparque.from_parquet(files[0])
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
    (i.e. the last row) for every bar timestamp and concatenate the rows
    into a single dataframe.

    :param dag_data_path: a path to DAG output data
    :param node_name: a node name to load an output for
    :return: a df that consists of last rows from every bar timestamp
        DAG results df
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
) -> Dict[str, Dict[pd.Timestamp, pd.DataFrame]]:
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
    # Check provided DAG paths exist.
    dirs_exist = all([os.path.exists(path) for path in dag_path_dict.values()])
    # TODO(Grisha): consider adding an `only_warning` switch to the interface so that it exits only
    # if `only_warning = True`.
    if not dirs_exist:
        # We might not save DAG output files in some experiments. Safely exit
        # the function with a warning to prevent potential disruptions to the
        # reconciliation notebooks.
        _LOG.warning(
            "Provided DAG directory paths don't exist: %s", dag_path_dict
        )
        return None
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
    # Create a dictionary to store results from the comparison of data
    # frames for each individual node and timestamp.
    diff_dfs = {}
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
        diff_dfs.update({node: {}})
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
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Comparing DAG output for node=%s and timestamp=%s",
                    node,
                    timestamp,
                )
            diff_df = hpandas.compare_dfs(df_1, df_2, **compare_dfs_kwargs)
            max_diff = diff_df.abs().max().max()
            diff_dfs[node].update({timestamp: diff_df})
            hdbg.dassert_lte(
                max_diff,
                diff_threshold,
                msg=f"Comparison failed for node={node} for bar timestamps={timestamp}",
            )
    return diff_dfs


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
    if _LOG.isEnabledFor(logging.DEBUG):
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
    "20230828_152500.20230828_152600.csv" where "20230828_152500" is a
    bar timestamp and "20230828_152600" is a wall clock time as strings.

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

    # TODO(Grisha): use a better name for the function since it's not #
    really about the execution but rather about the distance from # a
    bar timestamp. The time computed is the difference between the time
    when an order is executed and a bar timestamp.

    E.g.,
    ```
                            wall_clock_time  execution_time
    bar_timestamp
    2023-02-21 02:55:00  2023-02-21 02:55:44             44
    2023-02-21 03:00:00  2023-02-21 03:00:45             45
    2023-02-21 03:05:00  2023-02-21 03:05:46             46
    ```

    :param orders_dir: dir with order files
    :return: execution time stats for all orders
    """
    hdbg.dassert_dir_exists(orders_dir)
    # TODO(Grisha): use `hio.listdir()` since we are not looking for DAG files
    # here.
    orders = get_dag_node_csv_file_names(orders_dir)
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
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("df_size_as_str"))
    # Extract the number of rows and columns.
    df_size = re.findall("\d+", df_size_as_str)
    hdbg.dassert_eq(
        2,
        len(df_size),
        msg="Must be exactly 2 matches that correspond to the number of rows and the number of columns, received multiple of those: {df_size}",
    )
    if _LOG.isEnabledFor(logging.DEBUG):
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
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("dag_data_dir"))
    hdbg.dassert_dir_exists(dag_data_dir)
    # TODO(Grisha): Pass a DAG dir instead, i.e. `.../dag/node_io` instead of
    # `.../dag/node_io/node_io.data`.
    dag_dir = dag_data_dir.strip("node_io.data")
    # Get all node names.
    dag_node_names = get_dag_node_names(dag_data_dir)
    df_size_dict = {}
    for node_name in dag_node_names:
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("node_name"))
        node_dict = {}
        # Get all bar timestamps.
        dag_node_timestamps = get_dag_node_timestamps(
            dag_data_dir, node_name, as_timestamp=True
        )
        for node_timestamp in dag_node_timestamps:
            bar_timestamp = node_timestamp[0]
            if _LOG.isEnabledFor(logging.DEBUG):
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

    :param dag_df_out_size_stats: info about DAG results dfs' size see
        `get_dag_df_out_size_for_all_nodes()`
    :param report_stats: print the basic stats about the dfs' size on a
        DAG node level if True, otherwise pass
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
