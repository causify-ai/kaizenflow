"""
Types and utilities used in entire core/dataflow.

Note this file should not depend on anything in `core`.

Import as:

import dataflow.core.utils as dtfcorutil
"""

import datetime
import io
import logging
import re
from typing import Callable, List, Tuple, Union

import numpy as np
import pandas as pd

import dataflow.core.dag_builder as dtfcodabui
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################
# Node columns.
# #############################################################################

NodeColumn = Union[int, str]
# A list of columns or a function that returns a list of column types.
NodeColumnList = Union[List[NodeColumn], Callable[[], List[NodeColumn]]]


# #############################################################################
# Intervals.
# #############################################################################

# TODO(gp): Consolidate all the code about Interval in helpers/hinterval.py
#  (including code in hdatetime.py).

# TODO(gp): Always use pd.Timestamp with tz. This will require to update many
#  unit tests.
IntervalEndpoint = Union[datetime.datetime, pd.Timestamp, None]
# Intervals are considered as closed, i.e., [a, b]. An endpoint equal to `None`
# means unbounded interval on that direction.
Interval = Tuple[IntervalEndpoint, IntervalEndpoint]
Intervals = List[Interval]


# TODO(gp): Unify with -> dassert_is_valid_interval
def dassert_valid_interval(interval: Interval) -> None:
    hdbg.dassert_isinstance(interval, tuple)
    # Intervals are [a, b] with a <= b.
    hdbg.dassert_eq(len(interval), 2)
    for interval_endpoint in interval:
        if interval_endpoint is not None:
            hdbg.dassert_isinstance(
                interval_endpoint, (datetime.datetime, pd.Timestamp)
            )
            # TODO(gp): Check that it has a tzinfo.
    if interval[0] is not None and interval[1] is not None:
        hdbg.dassert_lte(interval[0], interval[1])


def dassert_valid_intervals(intervals: Intervals) -> None:
    hdbg.dassert_isinstance(intervals, list)
    hdbg.dassert_lte(1, len(intervals))
    for interval in intervals:
        dassert_valid_interval(interval)


# TODO(gp): Unit test.
def find_min_max_timestamps_from_intervals(
    intervals: Intervals,
) -> Interval:
    """
    Return the extremes of the interval including all the given `intervals`.

    The interval can be unbounded (i.e., having `None` endpoints) or
    not.
    """
    if intervals is not None:
        dassert_valid_intervals(intervals)
        interval = intervals[0]
        min_timestamp, max_timestamp = interval
        for interval in intervals[1:]:
            min_timestamp_tmp, max_timestamp_tmp = interval
            #
            if min_timestamp is None or min_timestamp_tmp is None:
                min_timestamp = None
            else:
                min_timestamp = min(min_timestamp, min_timestamp_tmp)
            #
            if max_timestamp is None or max_timestamp_tmp is None:
                max_timestamp = None
            else:
                max_timestamp = max(max_timestamp, max_timestamp_tmp)
    else:
        min_timestamp = None
        max_timestamp = None
    return (min_timestamp, max_timestamp)


# #############################################################################


# TODO(gp): Move to helpers/hprint.py since it's general, although not very
#  useful.
def get_df_info_as_string(
    df: pd.DataFrame, exclude_memory_usage: bool = True
) -> str:
    """
    Get dataframe info as string.

    :param df: dataframe
    :param exclude_memory_usage: whether to exclude memory usage information
    :return: dataframe info as `str`
    """
    buffer = io.StringIO()
    df.info(buf=buffer)
    info = buffer.getvalue()
    if exclude_memory_usage:
        # Remove memory usage (and a newline).
        info = info.rsplit("\n", maxsplit=2)[0]
    return info


# TODO(gp): Maybe move to helpers.hpandas since it's general.
def merge_dataframes(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Safely merges identically indexed `df1` and `df2`.

    This merge function checks that `df1` and `df2`
      - have equal indices
      - have no column duplicates
      - do not share column names
      - have the same column levels

    :return: merge of `df1` and `df2` on their (identical) index
    """
    # Ensure that indices are equal.
    hdbg.dassert(
        df2.index.equals(df1.index),
        "Dataframe indices differ but are expected to be the same!",
    )
    # Ensure that there are no column duplicates within a dataframe.
    hdbg.dassert_no_duplicates(df1.columns)
    hdbg.dassert_no_duplicates(df2.columns)
    # Do not allow column collisions.
    hdbg.dassert_not_in(
        df1.columns.to_list(),
        df2.columns.to_list(),
        "Column names overlap.",
    )
    # Ensure that column depth is equal.
    hdbg.dassert_eq(
        df1.columns.nlevels,
        df2.columns.nlevels,
        msg="Column hierarchy depth must be equal.",
    )
    df = df2.merge(
        df1,
        how="outer",
        left_index=True,
        right_index=True,
    )
    return df


def validate_df_indices(df: pd.DataFrame) -> None:
    """
    Assert if `df` fails index sanity checks.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_no_duplicates(df.columns.tolist())
    # TODO(Paul): assert if the datetime index has dups.


def convert_to_multiindex(df: pd.DataFrame, asset_id_col: str) -> pd.DataFrame:
    """
    Transform a df like: 
    
    ```

    :                            id close  volume
    end_time
    2022-01-04 09:01:00-05:00  13684    NaN       0
    2022-01-04 09:01:00-05:00  17085    NaN       0
    2022-01-04 09:02:00-05:00  13684    NaN       0
    2022-01-04 09:02:00-05:00  17085    NaN       0
    2022-01-04 09:03:00-05:00  13684    NaN       0
    ```

    Return a df like:
    ```
                                    close       volume
                              13684 17085  13684 17085
    end_time
    2022-01-04 09:01:00-05:00   NaN   NaN      0     0
    2022-01-04 09:02:00-05:00   NaN   NaN      0     0
    2022-01-04 09:03:00-05:00   NaN   NaN      0     0
    2022-01-04 09:04:00-05:00   NaN   NaN      0     0
    ```

    Note that the `asset_id` column is removed.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_lte(1, df.shape[0])
    # Copied from `_load_multiple_instrument_data()`.
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Before multiindex conversion:\n%s",
            hpandas.df_to_str(df.head()),
        )
    # Remove duplicates if any.
    df = hpandas.drop_duplicated(df, subset=[asset_id_col])
    #
    dfs = {}
    # TODO(Paul): Pass the column name through the constructor, so we can make it
    #  programmable.
    hdbg.dassert_in(asset_id_col, df.columns)
    hpandas.dassert_series_type_is(df[asset_id_col], np.int64)
    for asset_id, df in df.groupby(asset_id_col):
        hpandas.dassert_strictly_increasing_index(df)
        #
        hdbg.dassert_not_in(asset_id, dfs.keys())
        dfs[asset_id] = df
    # Reorganize the data into the desired format.
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("keys=%s", str(dfs.keys()))
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    # Remove the asset_id column, since it's redundant.
    del df[asset_id_col]
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "After multiindex conversion:\n%s",
            hpandas.df_to_str(df.head()),
        )
    return df


def convert_to_list(to_list: NodeColumnList) -> List[NodeColumn]:
    """
    Return a list given its input.

    - If the input is a list, the output is the same list.
    - If the input is a function that returns a list, then the output of
      the function is returned.

    How this might arise in practice:
    - A `ColumnTransformer` returns a number of x variables, with the
      number dependent upon a hyperparameter expressed in config
    - The column names of the x variables may be derived from the input
      dataframe column names, not necessarily known until graph execution
      (and not at construction)
    - The `ColumnTransformer` output columns are merged with its input
      columns (e.g., x vars and y vars are in the same dataframe)
    Post-merge, we need a way to distinguish the x vars and y vars.
    Allowing a callable here allows us to pass in the `ColumnTransformer`'s
    method `transformed_col_names()` and defer the call until graph
    execution.
    """
    if callable(to_list):
        to_list = to_list()
    if isinstance(to_list, list):
        # Check that the list is not empty and has no duplicates.
        hdbg.dassert_lte(1, len(to_list))
        hdbg.dassert_no_duplicates(to_list)
        return to_list
    raise TypeError("Data type=`%s`" % type(to_list))


def get_forward_cols(
    df: pd.DataFrame,
    cols: Union[List[NodeColumn], Tuple[NodeColumn]],
    steps_ahead: int,
) -> pd.DataFrame:
    """
    Obtain forward data values by shifting.

    WARNING: This function is non-causal for positive values of `steps_ahead`.
        It is intended to be used for the training stage of models that predict
        future values.

    :param df: input dataframe
    :param cols: column to generate forward values for
        - The `Tuple` type is useful for multiindexed columns
        - The `List` type should be used with single-level columns
    :param steps_ahead: number of shifts
    :return: dataframe of `steps_ahead` forward values of `df[col]`
    """
    if df.columns.nlevels == 1:
        hdbg.dassert_isinstance(cols, list)
    else:
        hdbg.dassert_isinstance(cols, tuple)
    # Append to the column names the number of steps ahead generated.
    mapper = lambda x: str(x) + ".shift_-%i" % steps_ahead
    forward_df = df[cols].shift(-steps_ahead).rename(columns=mapper)
    hdbg.dassert_not_intersection(forward_df.columns, df.columns)
    return forward_df


def get_x_and_forward_y_fit_df(
    df: pd.DataFrame,
    x_cols: List[NodeColumn],
    y_cols: List[NodeColumn],
    steps_ahead: int,
) -> pd.DataFrame:
    """
    Return a dataframe consisting of `x_cols` and forward `y_cols`.

    This function eliminates rows that contains NaNs (either in `x_cols`
    or in the forward values of `y_cols`), which makes the resulting
    dataframe ready for use in sklearn.
    """
    # TODO(Paul): Consider not dropping NaNs in this function but rather
    #  leaving that to the caller.
    validate_df_indices(df)
    # Obtain index slice for which forward targets exist.
    hdbg.dassert_lt(steps_ahead, df.index.size)
    idx = df.index[:-steps_ahead]
    # Determine index where no x_vars are NaN.
    non_nan_idx_x = df.loc[idx][x_cols].dropna().index
    # Determine index where target is not NaN.
    forward_y_df = get_forward_cols(df, y_cols, steps_ahead)
    forward_y_df = forward_y_df.loc[idx].dropna()
    non_nan_idx_forward_y = forward_y_df.dropna().index
    # Intersect non-NaN indices.
    non_nan_idx = non_nan_idx_x.intersection(non_nan_idx_forward_y)
    # Ensure that the intersection is not empty.
    hdbg.dassert(not non_nan_idx.empty)
    # Define the dataframes of x and forward y values.
    x_df = df.loc[non_nan_idx][x_cols]
    forward_y_df = forward_y_df.loc[non_nan_idx]
    # Merge x and forward y dataframes into one.
    df_out = merge_dataframes(x_df, forward_y_df)
    return df_out


def get_x_and_forward_y_predict_df(
    df: pd.DataFrame,
    x_cols: List[NodeColumn],
    y_cols: List[NodeColumn],
    steps_ahead: int,
) -> pd.DataFrame:
    """
    Return a dataframe consisting of `x_cols` and forward `y_cols`.

    Differs from `fit` version in that there is no requirement here that
    the forward y values be non-NaN.
    """
    # TODO(Paul): Consider combining with `get_x_and_forward_y_fit_df()` and
    #  parametrizing instead.
    validate_df_indices(df)
    # Determine index where no x_vars are NaN.
    x_df = df[x_cols].dropna()
    non_nan_idx_x = x_df.index
    hdbg.dassert(not non_nan_idx_x.empty)
    # Determine index where target is not NaN.
    forward_y_df = get_forward_cols(df, y_cols, steps_ahead)
    forward_y_df = forward_y_df.loc[non_nan_idx_x]
    # Merge x and forward y dataframes into one.
    df_out = merge_dataframes(x_df, forward_y_df)
    return df_out


# #############################################################################


# TODO(Grisha): maybe move closer to the DagBuilder class?
def get_DagBuilder_name_from_string(dag_builder_ctor_as_str: str) -> str:
    """
    Get `DagBuilder` name from DagBuilder ctor passed as a string.

    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :return: short DagBuilder name, e.g., C1b
    """
    # E.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder` ->
    # `[dataflow_orange, pipelines, C1, C1b_pipeline, C1b_DagBuilder]`.
    dag_builder_split = dag_builder_ctor_as_str.split(".")
    hdbg.dassert_lt(0, len(dag_builder_split))
    dag_builder_name = dag_builder_split[-1]
    # Find a string that is followed by `_DagBuilder`.
    # E.g., `C1b` in `C1b_DagBuilder`.
    re_pattern = r"\w+(?=(_DagBuilder))"
    dag_builder_name_match = re.match(re_pattern, dag_builder_name)
    hdbg.dassert(
        dag_builder_name_match,
        msg=f"Make sure that `DagBuilder` is in the name={dag_builder_name}",
    )
    dag_builder_name = dag_builder_name_match[0]
    return dag_builder_name


def get_DagBuilder_from_string(
    dag_builder_ctor_as_str: str, *dag_builder_args, **dag_builder_kwargs
) -> dtfcodabui.DagBuilder:
    """
    Get a `DagBuilder` object from a string pointer to a ctor.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
    :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str(
                "dag_builder_ctor_as_str dag_builder_args dag_builder_kwargs"
            )
        )
    dag_builder_func = hintros.get_function_from_string(dag_builder_ctor_as_str)
    hdbg.dassert_callable(dag_builder_func)
    dag_builder = dag_builder_func(*dag_builder_args, **dag_builder_kwargs)
    hdbg.dassert_isinstance(dag_builder, dtfcodabui.DagBuilder)
    return dag_builder
