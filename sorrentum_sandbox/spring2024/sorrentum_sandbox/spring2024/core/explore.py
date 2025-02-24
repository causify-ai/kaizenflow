"""
Utility functions for Jupyter notebook to:

- format data
- transform pandas data structures
- compute common stats

These functions are used for both interactive data exploration and to implement
more complex pipelines. The output is reported through logging.

Import as:

import core.explore as coexplor
"""

import datetime
import logging
import math
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sklearn
import statsmodels
import statsmodels.api
import tqdm.autonotebook as tauton

import core.plotting as coplotti
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hlist as hlist
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)

# #############################################################################
# Helpers.
# #############################################################################


# TODO(gp): Move this to helpers/pandas_helpers.py


def cast_to_df(obj: Union[pd.Series, pd.DataFrame]) -> pd.DataFrame:
    """
    Convert a pandas object into a pd.DataFrame.
    """
    if isinstance(obj, pd.Series):
        df = pd.DataFrame(obj)
    else:
        df = obj
    hdbg.dassert_isinstance(df, pd.DataFrame)
    return df


def cast_to_series(obj: Union[pd.Series, pd.DataFrame]) -> pd.Series:
    """
    Convert a pandas object into a pd.Series.
    """
    if isinstance(obj, pd.DataFrame):
        hdbg.dassert_eq(obj.shape[1], 1)
        srs = obj.iloc[:, 1]
    else:
        srs = obj
    hdbg.dassert_isinstance(srs, pd.Series)
    return srs


# TODO(gp): Need to be tested.
def adapt_to_series(f: Callable) -> Callable:
    """
    Extend a function working on dataframes so that it can work on series.
    """

    def wrapper(
        obj: Union[pd.Series, pd.DataFrame], *args: Any, **kwargs: Any
    ) -> Any:
        # Convert a pd.Series to a pd.DataFrame.
        was_series = False
        if isinstance(obj, pd.Series):
            obj = pd.DataFrame(obj)
            was_series = True
        hdbg.dassert_isinstance(obj, pd.DataFrame)
        # Apply the function.
        res = f(obj, *args, **kwargs)
        # Transform the output, if needed.
        if was_series:
            if isinstance(res, tuple):
                res_obj, res_tmp = res[0], res[1:]
                res_obj_srs = cast_to_series(res_obj)
                res_obj_srs = [res_obj_srs]
                res_obj_srs.extend(res_tmp)
                res = tuple(res_obj_srs)
            else:
                res = cast_to_series(res)
        return res

    return wrapper


# #############################################################################
# Pandas helpers.
# #############################################################################


def report_zero_nan_inf_stats(
    df: pd.DataFrame,
    zero_threshold: float = 1e-9,
    verbose: bool = False,
    as_txt: bool = False,
) -> pd.DataFrame:
    """
    Report count and percentage about zeros, nans, infs for a df.
    """
    df = cast_to_df(df)
    _LOG.info("index in [%s, %s]", df.index.min(), df.index.max())
    #
    num_rows = df.shape[0]
    _LOG.info("num_rows=%s", hprint.thousand_separator(num_rows))
    _LOG.info("data=")
    display_df(df, max_lines=5, as_txt=as_txt)
    #
    num_days = len(set(df.index.date))
    _LOG.info("num_days=%s", num_days)
    #
    num_weekdays = len(set(d for d in df.index.date if d.weekday() < 5))
    _LOG.info("num_weekdays=%s", num_weekdays)
    #
    stats_df = pd.DataFrame(None, index=df.columns)
    if False:
        # Find the index of the first non-nan value.
        df = df.applymap(lambda x: not np.isnan(x))
        min_idx = df.idxmax(axis=0)
        min_idx.name = "min_idx"
        # Find the index of the last non-nan value.
        max_idx = df.reindex(index=df.index[::-1]).idxmax(axis=0)
        max_idx.name = "max_idx"
    stats_df["num_rows"] = num_rows
    #
    num_zeros = (np.abs(df) < zero_threshold).sum(axis=0)
    if verbose:
        stats_df["num_zeros"] = num_zeros
    stats_df["zeros [%]"] = (100.0 * num_zeros / num_rows).apply(
        hprint.round_digits
    )
    #
    num_nans = np.isnan(df).sum(axis=0)
    if verbose:
        stats_df["num_nans"] = num_nans
    stats_df["nans [%]"] = (100.0 * num_nans / num_rows).apply(
        hprint.round_digits
    )
    #
    num_infs = np.isinf(df).sum(axis=0)
    if verbose:
        stats_df["num_infs"] = num_infs
    stats_df["infs [%]"] = (100.0 * num_infs / num_rows).apply(
        hprint.round_digits
    )
    #
    num_valid = df.shape[0] - num_zeros - num_nans - num_infs
    if verbose:
        stats_df["num_valid"] = num_valid
    stats_df["valid [%]"] = (100.0 * num_valid / num_rows).apply(
        hprint.round_digits
    )
    #
    display_df(stats_df, as_txt=as_txt)
    return stats_df


# #############################################################################
# Column variability.
# #############################################################################


def _get_unique_elements_in_column(df: pd.DataFrame, col_name: str) -> List[Any]:
    try:
        vals = df[col_name].unique()
    except TypeError:
        # TypeError: unhashable type: 'list'
        _LOG.error("Column '%s' has unhashable types", col_name)
        vals = list(set(map(str, df[col_name])))
    cast(List[Any], vals)
    return vals


def _get_variable_cols(
    df: pd.DataFrame, threshold: int = 1
) -> Tuple[List[str], List[str]]:
    """
    Return columns of a df that contain less than <threshold> unique values.

    :return: (variable columns, constant columns)
    """
    var_cols = []
    const_cols = []
    for col_name in df.columns:
        unique_elems = _get_unique_elements_in_column(df, col_name)
        num_unique_elems = len(unique_elems)
        if num_unique_elems <= threshold:
            const_cols.append(col_name)
        else:
            var_cols.append(col_name)
    return var_cols, const_cols


def remove_columns_with_low_variability(
    df: pd.DataFrame, threshold: int = 1, log_level: int = logging.DEBUG
) -> pd.DataFrame:
    """
    Remove columns of a df that contain less than <threshold> unique values.

    :return: df with only columns with sufficient variability
    """
    var_cols, const_cols = _get_variable_cols(df, threshold=threshold)
    _LOG.log(log_level, "# Constant cols")
    for col_name in const_cols:
        unique_elems = _get_unique_elements_in_column(df, col_name)
        _LOG.log(
            log_level,
            "  %s: %s",
            col_name,
            hprint.list_to_str(list(map(str, unique_elems))),
        )
    _LOG.log(log_level, "# Var cols")
    _LOG.log(log_level, hprint.list_to_str(var_cols))
    return df[var_cols]


def print_column_variability(
    df: pd.DataFrame,
    max_num_vals: int = 3,
    num_digits: int = 2,
    use_thousands_separator: bool = True,
) -> pd.DataFrame:
    """
    Print statistics about the values in each column of a data frame.

    This is useful to get a sense of which columns are interesting.
    """
    print(("# df.columns=%s" % hprint.list_to_str(df.columns)))
    res = []
    for c in tauton.tqdm(df.columns, desc="Computing column variability"):
        vals = _get_unique_elements_in_column(df, c)
        try:
            min_val = min(vals)
        except TypeError as e:
            _LOG.debug("Column='%s' reported %s", c, e)
            min_val = "nan"
        try:
            max_val = max(vals)
        except TypeError as e:
            _LOG.debug("Column='%s' reported %s", c, e)
            max_val = "nan"
        if len(vals) <= max_num_vals:
            txt = ", ".join(map(str, vals))
        else:
            txt = ", ".join(map(str, [min_val, "...", max_val]))
        row = ["%20s" % c, len(vals), txt]
        res.append(row)
    res = pd.DataFrame(res, columns=["col_name", "num", "elems"])
    res.sort_values("num", inplace=True)
    # TODO(gp): Fix this.
    # res = add_count_as_idx(res)
    res = add_pct(
        res,
        "num",
        df.shape[0],
        "[diff %]",
        num_digits=num_digits,
        use_thousands_separator=use_thousands_separator,
    )
    res.reset_index(drop=True, inplace=True)
    return res


def add_pct(
    df: pd.DataFrame,
    col_name: str,
    total: int,
    dst_col_name: str,
    num_digits: int = 2,
    use_thousands_separator: bool = True,
) -> pd.DataFrame:
    """
    Add to df a column "dst_col_name" storing the percentage of values in
    column "col_name" with respect to "total". The rest of the parameters are
    the same as hprint.round_digits().

    :return: updated df
    """
    # Add column with percentage right after col_name.
    pos_col_name = df.columns.tolist().index(col_name)
    df.insert(pos_col_name + 1, dst_col_name, (100.0 * df[col_name]) / total)
    # Format.
    df[col_name] = [
        hprint.round_digits(
            v, num_digits=None, use_thousands_separator=use_thousands_separator
        )
        for v in df[col_name]
    ]
    df[dst_col_name] = [
        hprint.round_digits(
            v, num_digits=num_digits, use_thousands_separator=False
        )
        for v in df[dst_col_name]
    ]
    return df


# #############################################################################
# Pandas data structure stats.
# #############################################################################


# TODO(gp): Explain what this is supposed to do.
def breakdown_table(
    df: pd.DataFrame,
    col_name: str,
    num_digits: int = 2,
    use_thousands_separator: bool = True,
    verbosity: bool = False,
) -> pd.DataFrame:
    if isinstance(col_name, list):
        for c in col_name:
            print(("\n" + hprint.frame(c).rstrip("\n")))
            res = breakdown_table(df, c)
            print(res)
        return None
    #
    if verbosity:
        print(("# col_name=%s" % col_name))
    first_col_name = df.columns[0]
    res = df.groupby(col_name)[first_col_name].count()
    res = pd.DataFrame(res)
    res.columns = ["count"]
    res.sort_values(["count"], ascending=False, inplace=True)
    res = pd.concat([
        res,
        pd.DataFrame([df.shape[0]], index=["Total"], columns=["count"])
    ])
    res["pct"] = (100.0 * res["count"]) / df.shape[0]
    # Format.
    res["count"] = [
        hprint.round_digits(
            v, num_digits=None, use_thousands_separator=use_thousands_separator
        )
        for v in res["count"]
    ]
    res["pct"] = [
        hprint.round_digits(
            v, num_digits=num_digits, use_thousands_separator=False
        )
        for v in res["pct"]
    ]
    if verbosity:
        for k, df_tmp in df.groupby(col_name):
            print((hprint.frame("%s=%s" % (col_name, k))))
            cols = [col_name, "description"]
            with pd.option_context(
                "display.max_colwidth", 100000, "display.width", 130
            ):
                print((df_tmp[cols]))
    return res


def find_common_columns(
    names: List[str], dfs: List[pd.DataFrame]
) -> pd.DataFrame:
    df = []
    for i, df1 in enumerate(dfs):
        df1 = dfs[i].columns
        for j in range(i + 1, len(dfs)):
            df2 = dfs[j].columns
            common_cols = [c for c in df1 if c in df2]
            df.append(
                (
                    names[i],
                    len(df1),
                    names[j],
                    len(df2),
                    len(common_cols),
                    ", ".join(common_cols),
                )
            )
    df = pd.DataFrame(
        df,
        columns=[
            "table1",
            "num_cols1",
            "num_cols2",
            "table2",
            "num_comm_cols",
            "common_cols",
        ],
    )
    return df


# #############################################################################
# Filter.
# #############################################################################


def remove_columns(
    df: pd.DataFrame, cols: Collection[str], log_level: int = logging.DEBUG
) -> pd.DataFrame:
    to_remove = set(cols).intersection(set(df.columns))
    _LOG.log(log_level, "to_remove=%s", hprint.list_to_str(to_remove))
    df.drop(to_remove, axis=1, inplace=True)
    _LOG.debug("df=\n%s", df.head(3))
    _LOG.log(log_level, hprint.list_to_str(df.columns))
    return df


def filter_with_df(
    df: pd.DataFrame, filter_df: pd.DataFrame, log_level: int = logging.DEBUG
) -> pd.Series:
    """
    Compute a mask for DataFrame df using common columns and values in
    "filter_df".
    """
    mask = None
    for c in filter_df:
        hdbg.dassert_in(c, df.columns)
        vals = filter_df[c].unique()
        if mask is None:
            mask = df[c].isin(vals)
        else:
            mask &= df[c].isin(vals)
    mask: pd.DataFrame
    _LOG.log(log_level, "after filter=%s", hprint.perc(mask.sum(), len(mask)))
    return mask


def filter_by_time(
    df: pd.DataFrame,
    lower_bound: hdateti.StrictDatetime,
    upper_bound: hdateti.StrictDatetime,
    inclusive: str,
    ts_col_name: Optional[str],
    log_level: int = logging.DEBUG,
) -> pd.DataFrame:
    """
    Filter data by time between `lower_bound` and `upper_bound`.

    Pass `None` to `ts_col_name` to filter by `DatetimeIndex`.

    :param df: data to filter
    :param lower_bound: left limit point of the time interval
    :param upper_bound: right limit point of the time interval
    :param inclusive: include boundaries
        - "both" to `[lower_bound, upper_bound]`
        - "neither" to `(lower_bound, upper_bound)`
        - "right" to `(lower_bound, upper_bound]`
        - "left" to `[lower_bound, upper_bound)`
    :param ts_col_name: name of a timestamp column to filter with
    :param log_level: the level of logging, e.g. `DEBUG`
    :return: data filtered by time
    """
    hdateti.dassert_is_strict_datetime(lower_bound)
    hdateti.dassert_is_strict_datetime(upper_bound)
    # Time filtering is not working if timezones are different.
    hdateti.dassert_tz_compatible_timestamp_with_df(lower_bound, df, ts_col_name)
    hdateti.dassert_tz_compatible_timestamp_with_df(upper_bound, df, ts_col_name)
    #
    if ts_col_name is None:
        # Filter data by index.
        hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
        # Cast index to `pd.Series` to use the `between` method.
        mask = df.index.to_series().between(lower_bound, upper_bound, inclusive)
    else:
        # Filter data by a specified column.
        hdbg.dassert_in(ts_col_name, df.columns)
        mask = df[ts_col_name].between(lower_bound, upper_bound, inclusive)
    #
    _LOG.log(
        log_level,
        "Filtering between %s and %s with inclusive=`%s`, " "selected rows=%s",
        lower_bound,
        upper_bound,
        inclusive,
        hprint.perc(mask.sum(), df.shape[0]),
    )
    return df[mask]


def filter_by_val(
    df: pd.DataFrame,
    col_name: str,
    min_val: float,
    max_val: float,
    use_thousands_separator: bool = True,
    log_level: int = logging.DEBUG,
) -> pd.DataFrame:
    """
    Filter out rows of df where df[col_name] is not in [min_val, max_val].
    """
    # TODO(gp): If column is ordered, this can be done more efficiently with
    # binary search.
    num_rows = df.shape[0]
    if min_val is not None and max_val is not None:
        hdbg.dassert_lte(min_val, max_val)
    mask = None
    if min_val is not None:
        mask = min_val <= df[col_name]
    if max_val is not None:
        mask2 = df[col_name] <= max_val
        if mask is None:
            mask = mask2
        else:
            mask &= mask2
    res = df[mask]
    hdbg.dassert_lt(0, res.shape[0])
    _LOG.log(
        log_level,
        "Rows kept %s, removed %s rows",
        hprint.perc(
            res.shape[0],
            num_rows,
            use_thousands_separator=use_thousands_separator,
        ),
        hprint.perc(
            num_rows - res.shape[0],
            num_rows,
            use_thousands_separator=use_thousands_separator,
        ),
    )
    return res


# #############################################################################
# PCA
# #############################################################################


def _get_num_pcs_to_plot(num_pcs_to_plot: int, max_pcs: int) -> int:
    """
    Get the number of principal components to coplotti.
    """
    if num_pcs_to_plot == -1:
        num_pcs_to_plot = max_pcs
    hdbg.dassert_lte(0, num_pcs_to_plot)
    hdbg.dassert_lte(num_pcs_to_plot, max_pcs)
    return num_pcs_to_plot


# TODO(gp): Add some stats about how many nans where filled.
def handle_nans(df: pd.DataFrame, nan_mode: str) -> pd.DataFrame:
    if nan_mode == "drop":
        df = df.dropna(how="any")
    elif nan_mode == "fill_with_zero":
        df = df.fillna(0.0)
    elif nan_mode == "abort":
        num_nans = np.isnan(df).sum().sum()
        if num_nans > 0:
            raise ValueError("df has %d nans\n%s" % (num_nans, df))
    else:
        raise ValueError("Invalid nan_mode='%s'" % nan_mode)
    return df


def sample_rolling_df(
    rolling_df: pd.DataFrame, periods: int
) -> Tuple[pd.DataFrame, pd.DatetimeIndex]:
    """
    Given a rolling metric stored as multiindex (e.g., correlation computed by
    pd.ewm) sample `periods` equispaced samples.

    :return: sampled df, array of timestamps selected
    """
    timestamps = rolling_df.index.get_level_values(0)
    ts = timestamps[:: math.ceil(len(timestamps) / periods)]
    _LOG.debug("timestamps=%s", str(ts))
    # rolling_df_out = rolling_df.unstack().reindex(ts).stack(dropna=False)
    rolling_df_out = rolling_df.loc[ts]
    return rolling_df_out, ts


# NOTE:
#   - DRY: We have a rolling corr function elsewhere.
#   - Functional style: This one seems to be able to modify `ret` through
#     `nan_mode`.
def rolling_corr_over_time(
    df: pd.DataFrame, com: float, nan_mode: str
) -> pd.DataFrame:
    """
    Compute rolling correlation over time.

    :return: corr_df is a multi-index df storing correlation matrices with
        labels
    """
    hpandas.dassert_strictly_increasing_index(df)
    df = handle_nans(df, nan_mode)
    corr_df = df.ewm(com=com, min_periods=3 * com).corr()
    return corr_df


def _get_eigvals_eigvecs(
    df: pd.DataFrame, dt: datetime.date, sort_eigvals: bool
) -> Tuple[np.array, np.array]:
    hdbg.dassert_isinstance(dt, datetime.date)
    df_tmp = df.loc[dt].copy()
    # Compute rolling eigenvalues and eigenvectors.
    # TODO(gp): Count and report inf and nans as warning.
    df_tmp.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_tmp.fillna(0.0, inplace=True)
    eigval, eigvec = np.linalg.eigh(df_tmp)
    # Sort eigenvalues, if needed.
    if not (sorted(eigval) == eigval).all():
        _LOG.debug("eigvals not sorted: %s", eigval)
        if sort_eigvals:
            _LOG.debug(
                "Before sorting:\neigval=\n%s\neigvec=\n%s", eigval, eigvec
            )
            _LOG.debug("eigvals: %s", eigval)
            idx = eigval.argsort()[::-1]
            eigval = eigval[idx]
            eigvec = eigvec[:, idx]
            _LOG.debug("After sorting:\neigval=\n%s\neigvec=\n%s", eigval, eigvec)
    #
    if (eigval == 0).all():
        eigvec = np.nan * eigvec
    return eigval, eigvec


def rolling_pca_over_time(
    df: pd.DataFrame, com: float, nan_mode: str, sort_eigvals: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Compute rolling PCAs over time.

    :param sort_eigvals: sort the eigenvalues in descending orders
    :return:
        - eigval_df stores eigenvalues for the different components indexed by
          timestamps
        - eigvec_df stores eigenvectors as multiindex df
    """
    # Compute rolling correlation.
    corr_df = rolling_corr_over_time(df, com, nan_mode)
    # Compute eigvalues and eigenvectors.
    timestamps = corr_df.index.get_level_values(0).unique()
    eigval = np.zeros((timestamps.shape[0], df.shape[1]))
    eigvec = np.zeros((timestamps.shape[0], df.shape[1], df.shape[1]))
    for i, dt in tauton.tqdm(
        enumerate(timestamps),
        total=timestamps.shape[0],
        desc="Computing rolling PCA",
    ):
        eigval[i], eigvec[i] = _get_eigvals_eigvecs(corr_df, dt, sort_eigvals)
    # Package results.
    eigval_df = pd.DataFrame(eigval, index=timestamps)
    hdbg.dassert_eq(eigval_df.shape[0], len(timestamps))
    hpandas.dassert_strictly_increasing_index(eigval_df)
    # Normalize by sum.
    # TODO(gp): Move this up.
    eigval_df = eigval_df.multiply(1 / eigval_df.sum(axis=1), axis="index")
    #
    # pylint ref: github.com/PyCQA/pylint/issues/3139
    eigvec = eigvec.reshape(
        (-1, eigvec.shape[-1])
    )  # pylint: disable=unsubscriptable-object
    idx = pd.MultiIndex.from_product(
        [timestamps, df.columns], names=["datetime", None]
    )
    eigvec_df = pd.DataFrame(
        eigvec, index=idx, columns=range(df.shape[1])
    )  # pylint: disable=unsubscriptable-object
    hdbg.dassert_eq(
        len(eigvec_df.index.get_level_values(0).unique()), len(timestamps)
    )
    return corr_df, eigval_df, eigvec_df


def plot_pca_over_time(
    eigval_df: pd.DataFrame,
    eigvec_df: pd.DataFrame,
    num_pcs_to_plot: int = 0,
    num_cols: int = 2,
) -> None:
    """
    Similar to plot_pca_analysis() but over time.
    """
    # Plot eigenvalues.
    eigval_df.plot(title="Eigenvalues over time", ylim=(0, 1))
    # Plot cumulative variance.
    eigval_df.cumsum(axis=1).plot(
        title="Fraction of variance explained by top PCs over time", ylim=(0, 1)
    )
    # Plot eigenvalues.
    max_pcs = eigvec_df.shape[1]
    num_pcs_to_plot = _get_num_pcs_to_plot(num_pcs_to_plot, max_pcs)
    _LOG.info("num_pcs_to_plot=%s", num_pcs_to_plot)
    if num_pcs_to_plot > 0:
        _, axes = coplotti.get_multiple_plots(
            num_pcs_to_plot,
            num_cols=num_cols,
            y_scale=4,
            sharex=True,
            sharey=True,
        )
        for i in range(num_pcs_to_plot):
            eigvec_df[i].unstack(1).plot(
                ax=axes[i], ylim=(-1, 1), title="PC%s" % i
            )


def plot_time_distributions(
    dts: List[Union[datetime.datetime, pd.Timestamp]],
    mode: str,
    density: bool = True,
) -> mpl.axes.Axes:
    """
    Compute distribution for an array of timestamps `dts`.

    - mode: see below
    """
    hdbg.dassert_type_in(dts[0], (datetime.datetime, pd.Timestamp))
    hdbg.dassert_in(
        mode,
        (
            "time_of_the_day",
            "weekday",
            "minute_of_the_hour",
            "day_of_the_month",
            "month_of_the_year",
            "year",
        ),
    )
    if mode == "time_of_the_day":
        # Convert in minutes from the beginning of the day.
        data = [dt.time() for dt in dts]
        data = [t.hour * 60 + t.minute for t in data]
        # 1 hour bucket.
        step = 60
        bins = np.arange(0, 24 * 60 + step, step)
        vals = pd.cut(
            data,
            bins=bins,
            include_lowest=True,
            right=False,
            retbins=False,
            labels=False,
        )
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = ["%02d:%02d" % (bins[k] / 60, bins[k] % 60) for k in count.index]
    elif mode == "weekday":
        data = [dt.date().weekday() for dt in dts]
        bins = np.arange(0, 7 + 1)
        vals = pd.cut(
            data,
            bins=bins,
            include_lowest=True,
            right=False,
            retbins=False,
            labels=False,
        )
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = "Mon Tue Wed Thu Fri Sat Sun".split()
    elif mode == "minute_of_the_hour":
        vals = [dt.time().minute for dt in dts]
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = list(map(str, list(range(1, 60 + 1))))
    elif mode == "day_of_the_month":
        vals = [dt.date().day for dt in dts]
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = list(map(str, list(range(1, 31 + 1))))
    elif mode == "month_of_the_year":
        vals = [dt.date().month for dt in dts]
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    elif mode == "year":
        vals = [dt.date().year for dt in dts]
        # Count.
        count = pd.Series(vals).value_counts(sort=False)
        # Compute the labels.
        yticks = pd.Series(vals).unique().tolist()
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    hdbg.dassert_eq(count.sum(), len(dts))
    #
    if density:
        count /= count.sum()
    label = "num points=%s" % len(dts)
    ax = count.plot(kind="bar", label=label, figsize=(20, 7))
    ax.set_xticklabels(yticks)
    if density:
        ax.set_ylabel("Probability")
    else:
        ax.set_ylabel("Count")
    ax.legend(loc="best")
    return ax


# TODO(gp): It can't accept ax. Remove this limitation.
def jointplot(
    df: pd.DataFrame,
    predicted_var: str,
    predictor_var: str,
    height: Optional[int] = None,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Perform a scatterplot of two columns of a dataframe using
    seaborn.jointplot().

    :param df: dataframe
    :param predicted_var: y-var
    :param predictor_var: x-var
    :param args, kwargs: arguments passed to seaborn.jointplot()
    """
    hdbg.dassert_in(predicted_var, df.columns)
    hdbg.dassert_in(predictor_var, df.columns)
    df = df[[predicted_var, predictor_var]]
    # Remove non-finite values.
    # TODO(gp): Use explore.dropna().
    mask = np.all(np.isfinite(df.values), axis=1)
    df = df[mask]
    # Plot.
    sns.jointplot(
        x=predictor_var, y=predicted_var, data=df, height=height, *args, **kwargs
    )


def _preprocess_regression(
    df: pd.DataFrame,
    intercept: bool,
    predicted_var: str,
    predicted_var_delay: int,
    predictor_vars: Union[str, List[str]],
    predictor_vars_delay: int,
) -> Optional[Tuple[pd.DataFrame, List[str], List[str]]]:
    """
    Preprocess data in dataframe form in order to perform a regression.
    """
    # Sanity check vars.
    hdbg.dassert_type_is(df, pd.DataFrame)
    hdbg.dassert_lte(1, df.shape[0])
    if isinstance(predictor_vars, str):
        predictor_vars = [predictor_vars]
    hdbg.dassert_type_is(predictor_vars, list)
    # hdbg.dassert_type_is(predicted_var, str)
    hdbg.dassert_not_in(predicted_var, predictor_vars)
    if not predictor_vars:
        # No predictors.
        _LOG.warning("No predictor vars: skipping")
        return None
    #
    col_names = [predicted_var] + predictor_vars
    hdbg.dassert_is_subset(col_names, df.columns)
    df = df[col_names].copy()
    num_rows = df.shape[0]
    # Shift.
    if predicted_var_delay != 0:
        df[predicted_var] = df[predicted_var].shift(predicted_var_delay)
        _LOG.warning("Shifting predicted_var=%s", predicted_var_delay)
    if predictor_vars_delay != 0:
        df[predictor_vars] = df[predictor_vars].shift(predictor_vars_delay)
        _LOG.warning("Shifting predictor_vars=%s", predictor_vars_delay)
    # Remove non-finite values.
    # TODO(gp): Use the function.
    df.dropna(how="all", inplace=True)
    num_rows_after_drop_nan_all = df.shape[0]
    if num_rows_after_drop_nan_all != num_rows:
        _LOG.info(
            "Removed %s rows with all nans",
            hprint.perc(num_rows - num_rows_after_drop_nan_all, num_rows),
        )
    #
    df.dropna(how="any", inplace=True)
    num_rows_after_drop_nan_any = df.shape[0]
    if num_rows_after_drop_nan_any != num_rows_after_drop_nan_all:
        _LOG.warning(
            "Removed %s rows with any nans",
            hprint.perc(num_rows - num_rows_after_drop_nan_any, num_rows),
        )
    # Prepare data.
    if intercept:
        if "const" not in df.columns:
            df.insert(0, "const", 1.0)
        predictor_vars = ["const"] + predictor_vars[:]
    param_names = predictor_vars[:]
    hdbg.dassert(np.all(np.isfinite(df[predicted_var].values)))
    hdbg.dassert(
        np.all(np.isfinite(df[predictor_vars].values)),
        msg="predictor_vars=%s" % predictor_vars,
    )
    # Perform regression.
    if df.shape[0] < 1:
        return None
    return df, param_names, predictor_vars


def ols_regress(
    df: pd.DataFrame,
    predicted_var: str,
    predictor_vars: str,
    intercept: bool,
    print_model_stats: bool = True,
    tsplot: bool = False,
    tsplot_figsize: Optional[Any] = None,
    jointplot_: bool = True,
    jointplot_height: Optional[Any] = None,
    predicted_var_delay: int = 0,
    predictor_vars_delay: int = 0,
    max_nrows: float = 1e4,
) -> Optional[Dict[str, Any]]:
    """
    Perform OLS on columns of a dataframe.

    :param df: dataframe
    :param predicted_var: y variable
    :param predictor_vars: x variables
    :param intercept:
    :param print_model_stats: print or return the model stats
    :param tsplot: plot a time-series if possible
    :param tsplot_figsize:
    :param jointplot_: plot a scatter plot
    :param jointplot_height:
    :param predicted_var_delay:
    :param predictor_vars_delay:
    :param max_nrows: do not plot if there are too many rows, since notebook
        can be slow or hang
    :return:
    """
    obj = _preprocess_regression(
        df,
        intercept,
        predicted_var,
        predicted_var_delay,
        predictor_vars,
        predictor_vars_delay,
    )
    if obj is None:
        return None
    df, param_names, predictor_vars = obj
    hdbg.dassert_lte(1, df.shape[0])
    model = statsmodels.api.OLS(
        df[predicted_var], df[predictor_vars], hasconst=intercept
    ).fit()
    regr_res = {
        "param_names": param_names,
        "coeffs": model.params,
        "pvals": model.pvalues,
        # pylint: disable=no-member
        "rsquared": model.rsquared,
        "adj_rsquared": model.rsquared_adj,
        "model": model,
    }
    if print_model_stats:
        # pylint: disable=no-member
        _LOG.info(model.summary().as_text())
    if tsplot or jointplot_:
        if max_nrows is not None and df.shape[0] > max_nrows:
            _LOG.warning(
                "Skipping plots since df has %d > %d rows", df.shape[0], max_nrows
            )
        else:
            predictor_vars = [p for p in predictor_vars if p != "const"]
            if len(predictor_vars) == 1:
                if tsplot:
                    # Plot the data over time.
                    if tsplot_figsize is None:
                        tsplot_figsize = coplotti.FIG_SIZE
                    df[[predicted_var, predictor_vars[0]]].plot(
                        figsize=tsplot_figsize
                    )
                if jointplot_:
                    # Perform scatter plot.
                    if jointplot_height is None:
                        jointplot_height = coplotti.FIG_SIZE[1]
                    jointplot(
                        df,
                        predicted_var,
                        predictor_vars[0],
                        height=jointplot_height,
                    )
            else:
                _LOG.warning("Skipping plots since there are too many predictors")
    if print_model_stats:
        return None
    return regr_res


# TODO(gp): Redundant with cast_to_series()?
def to_series(obj: Any) -> pd.Series:
    if isinstance(obj, np.ndarray):
        hdbg.dassert_eq(obj.shape, 1)
        srs = pd.Series(obj)
    else:
        srs = obj
    hdbg.dassert_isinstance(srs, pd.Series)
    return srs


def ols_regress_series(
    srs1: pd.Series,
    srs2: pd.Series,
    intercept: bool,
    srs1_name: Optional[Any] = None,
    srs2_name: Optional[Any] = None,
    convert_to_dates: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Regress two series against each other.

    Wrapper around regress() to regress series against each other.
    """
    srs1 = to_series(srs1).copy()
    srs2 = to_series(srs2).copy()
    #
    if convert_to_dates:
        _LOG.warning("Sampling to date")
        srs1.index = [pd.to_datetime(dt).date() for dt in srs1.index]
        srs2.index = [pd.to_datetime(dt).date() for dt in srs2.index]
    #
    hdbg.dassert_array_has_same_type_element(srs1, srs2, only_first_elem=True)
    # Check common indices.
    common_idx = srs1.index.intersection(srs2.index)
    hdbg.dassert_lte(1, len(common_idx))
    # Merge series into a dataframe.
    if srs1_name is None:
        srs1_name = srs1.name if srs1.name is not None else ""
    if srs2_name is None:
        srs2_name = srs2.name if srs2.name is not None else ""
    if srs1_name == srs2_name:
        srs1_name += "_1"
        srs2_name += "_2"
        _LOG.warning("Series have the same name: adding suffix to distinguish")
    df = pd.concat([srs1, srs2], axis=1, join="outer")
    df.columns = [srs1_name, srs2_name]
    #
    val = ols_regress(df, srs1_name, srs2_name, intercept=intercept, **kwargs)
    val = cast(Dict[str, Any], val)
    return val


def pvalue_to_stars(pval: Optional[float]) -> str:
    if np.isnan(pval):
        stars = "NA"
    else:
        hdbg.dassert_lte(0.0, pval)
        hdbg.dassert_lte(pval, 1.0)
        pval = cast(float, pval)
        if pval < 0.005:
            # More than 99.5% confidence.
            stars = "****"
        elif pval < 0.01:
            # More than 99% confidence.
            stars = "***"
        elif pval < 0.05:
            # More than 95% confidence.
            stars = "**"
        elif pval < 0.1:
            # More than 90% confidence.
            stars = "*"
        else:
            stars = "?"
    return stars


def format_ols_regress_results(regr_res: Optional[pd.DataFrame]) -> pd.DataFrame:
    if regr_res is None:
        _LOG.warning("regr_res=None: skipping")
        df = pd.DataFrame(None)
        return df
    row: List[Union[float, str]] = [
        "%.3f (%s)" % (coeff, pvalue_to_stars(pval))
        for (coeff, pval) in zip(regr_res["coeffs"], regr_res["pvals"])
    ]
    row.append(float("%.2f" % (regr_res["rsquared"] * 100.0)))
    row.append(float("%.2f" % (regr_res["adj_rsquared"] * 100.0)))
    col_names = regr_res["param_names"] + ["R^2 [%]", "Adj R^2 [%]"]
    df = pd.DataFrame([row], columns=col_names)
    return df


def robust_regression(
    df: pd.DataFrame,
    predicted_var: str,
    predictor_vars: str,
    intercept: bool,
    jointplot_: bool = True,
    jointplot_figsize: Optional[Any] = None,
    predicted_var_delay: int = 0,
    predictor_vars_delay: int = 0,
) -> None:
    obj = _preprocess_regression(
        df,
        intercept,
        predicted_var,
        predicted_var_delay,
        predictor_vars,
        predictor_vars_delay,
    )
    if obj is None:
        return
    # From http://scikit-learn.org/stable/auto_examples/linear_model/
    #   plot_robust_fit.html#sphx-glr-auto-examples-linear-model-plot-robust-fit-py
    # TODO(gp): Add also TheilSenRegressor and HuberRegressor.

    hdbg.dassert_eq(len(predictor_vars), 1)
    y = df[predicted_var]
    X = df[predictor_vars]
    # Fit line using all data.
    lr = sklearn.linear_model.LinearRegression()
    lr.fit(X, y)
    # Robustly fit linear model with RANSAC algorithm.
    ransac = sklearn.linear_model.RANSACRegressor()
    ransac.fit(X, y)
    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)
    # Predict data of estimated models.
    line_X = np.linspace(X.min().values[0], X.max().values[0], num=100)[
        :, np.newaxis
    ]
    line_y = lr.predict(line_X)
    line_y_ransac = ransac.predict(line_X)
    # Compare estimated coefficients
    _LOG.info("Estimated coef for linear regression=%s", lr.coef_)
    _LOG.info("Estimated coef for RANSAC=%s", ransac.estimator_.coef_)
    if jointplot_:
        if jointplot_figsize is None:
            jointplot_figsize = coplotti.FIG_SIZE
        plt.figure(figsize=jointplot_figsize)
        plt.scatter(
            X[inlier_mask],
            y[inlier_mask],
            color="red",
            marker="o",
            label="Inliers",
        )
        plt.scatter(
            X[outlier_mask],
            y[outlier_mask],
            color="blue",
            marker="o",
            label="Outliers",
        )
        plt.plot(line_X, line_y, color="green", linewidth=2, label="OLS")
        plt.plot(
            line_X, line_y_ransac, color="black", linewidth=3, label="RANSAC"
        )
        plt.legend(loc="best")
        plt.xlabel(", ".join(predictor_vars))
        plt.ylabel(predicted_var)


# #############################################################################
# Printing
# #############################################################################


def display_df(
    df: pd.DataFrame,
    index: bool = True,
    inline_index: bool = False,
    max_lines: int = 5,
    as_txt: bool = False,
    tag: Optional[str] = None,
    mode: Optional[str] = None,
) -> None:
    """
    Display a pandas object (series, df, panel) in a better way than the
    ipython display, e.g.,

        - by printing head and tail of the dataframe
        - by formatting the code

    :param index: whether to show the index or not
    :param inline_index: make the index part of the dataframe. This is used
        when cutting and pasting to other applications, which are not happy
        with the output pandas html form
    :param max_lines: number of lines to print
    :param as_txt: print if True, otherwise render as usual html
    :param mode: use different formats temporarily overriding the default, e.g.,
        - "all_rows": print all the rows
        - "all_cols": print all the columns
        - "all": print the entire df (it could be huge)
    """
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)
    #
    hdbg.dassert_type_is(df, pd.DataFrame)
    hdbg.dassert_eq(
        hlist.find_duplicates(df.columns.tolist()),
        [],
        msg="Find duplicated columns",
    )
    if tag is not None:
        print(tag)
    if max_lines is not None:
        hdbg.dassert_lte(1, max_lines)
        if df.shape[0] > max_lines:
            # log.error("Printing only top / bottom %s out of %s rows",
            #        max_lines, df.shape[0])
            ellipses = pd.DataFrame(
                [["..."] * len(df.columns)], columns=df.columns, index=["..."]
            )
            df = pd.concat(
                [
                    df.head(int(max_lines / 2)),
                    ellipses,
                    df.tail(int(max_lines / 2)),
                ],
                axis=0,
            )
    if inline_index:
        df = df.copy()
        # Copy the index to a column and don't print the index.
        if df.index.name is None:
            col_name = "."
        else:
            col_name = df.index.name
        df.insert(0, col_name, df.index)
        df.index.name = None
        index = False

    # Finally, print / display.
    def _print_display() -> None:
        if as_txt:
            print(df.to_string(index=index))
        else:
            import IPython.core.display

            IPython.core.display.display(
                IPython.core.display.HTML(df.to_html(index=index))
            )

    if mode is None:
        _print_display()
    elif mode == "all_rows":
        with pd.option_context(
            "display.max_rows", None, "display.max_columns", 3
        ):
            _print_display()
    elif mode == "all_cols":
        with pd.option_context(
            "display.max_colwidth", int(1e6), "display.max_columns", None
        ):
            _print_display()
    elif mode == "all":
        with pd.option_context(
            "display.max_rows",
            int(1e6),
            "display.max_columns",
            3,
            "display.max_colwidth",
            int(1e6),
            "display.max_columns",
            None,
        ):
            _print_display()
    else:
        _print_display()
        raise ValueError("Invalid mode=%s" % mode)


def describe_df(
    df: pd.DataFrame,
    ts_col: Optional[str] = None,
    max_col_width: int = 30,
    max_thr: int = 15,
    sort_by_uniq_num: bool = False,
    log_level: int = logging.INFO,
) -> None:
    """
    Improved version of pd.DataFrame.describe()

    :param ts_col: timestamp column
    """
    if ts_col is None:
        _LOG.log(
            log_level,
            "[%s, %s], count=%s",
            min(df.index),
            max(df.index),
            len(df.index.unique()),
        )
    else:
        _LOG.log(
            log_level,
            "%s: [%s, %s], count=%s",
            ts_col,
            min(df[ts_col]),
            max(df[ts_col]),
            len(df[ts_col].unique()),
        )
    _LOG.log(log_level, "num_cols=%s", df.shape[1])
    _LOG.log(log_level, "num_rows=%s", df.shape[0])
    res_df = []
    for c in df.columns:
        uniq = df[c].unique()
        num = len(uniq)
        if num < max_thr:
            vals = " ".join(map(str, uniq))
        else:
            vals = " ".join(map(str, uniq[:10]))
        if len(vals) > max_col_width:
            vals = vals[:max_col_width] + " ..."
        type_str = df[c].dtype
        res_df.append([c, len(uniq), vals, type_str])
    #
    res_df = pd.DataFrame(res_df, columns=["column", "num uniq", "vals", "type"])
    res_df.set_index("column", inplace=True)
    if sort_by_uniq_num:
        res_df.sort("num uniq", inplace=True)
    _LOG.log(log_level, "res_df=\n%s", res_df)


def to_qgrid(df: pd.DataFrame) -> Any:
    import qgrid  # type: ignore

    grid_options = {
        "fullWidthRows": True,
        "syncColumnCellResize": True,
        # This parameter allows to extend column width to readable size a scroll to the left.
        # Is True by default
        "forceFitColumns": False,
        "rowHeight": 28,
        "enableColumnReorder": False,
        "enableTextSelectionOnCells": True,
        "editable": True,
        "autoEdit": False,
    }
    df = df.copy()
    # if not df.index.name:
    #    df.index.name = "index"
    qgrid_widget = qgrid.show_grid(
        df, show_toolbar=True, grid_options=grid_options
    )
    if False:
        # TODO(gp): Make this general.
        # qgrid can only either add a predefined row (list of tuples) or copy
        # the last row of the df. Adding a single empty row is only possible in
        # this way - dataframe must a have numeric index. But since now the
        # last row is empty we can create new rows by duplicating it with qgrid
        # built-in functionality.
        empty_row = [("source_number", df.shape[0])] + [
            (colname, None) for colname in df.columns
        ]
        qgrid_widget.add_row(row=empty_row)
    return qgrid_widget
