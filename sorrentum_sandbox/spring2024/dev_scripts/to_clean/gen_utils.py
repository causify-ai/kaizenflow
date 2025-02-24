"""
Import as:

import dev_scripts.to_clean.gen_utils as dstcgeut
"""

import bisect
import datetime
import logging
import os
import pprint

import IPython.core.display
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import seaborn as sns
import statsmodels
import utils.debug as dbg
import utils.jos
import utils.jstats
import utils.memoize as memoize
import utils.sorted
import utils.stats

from helpers.csv import to_typed_csv

_LOG = logging.getLogger(__name__)

# #############################################################################
# Python.
# #############################################################################

# def apply_to_one_column_df(f):
#    def wrapper(*args, **kwargs):
#        func_name = f.__name__
#        obj, args_tmp = *args[0], *
#        if isinstance(*args[0], pd.Series):
#            v = f(*args, **kwargs)
#        else:
#            dbg.dassert_type_is(
#        return v
#    return wrapper


def apply_to_dict_panel(
    obj, f, func_name=None, timed=False, progress_bar=False, report_func=False
):
    if report_func:
        _LOG.info("# %s", func_name)
    if timed:
        timer = utils.timer.dtimer_start(0, func_name)
    #
    if func_name is None:
        func_name = f.__name__
    if isinstance(obj, pd.Panel):
        type_ = "panel"
    elif isinstance(obj, dict):
        type_ = "dict"
    else:
        raise ValueError("Invalid type='%s' for %s" % (type(obj), str(f)))
    #
    res = {}
    if progress_bar:
        pb = utils.timer.ProgressBar(0, len(obj), descr=func_name, verbosity=0)
    for k, v in obj.items():
        _LOG.debug("Execute for k=%s", k)
        res[k] = f(v)
        if progress_bar:
            next(pb)
    #
    if type_ == "panel":
        res = pd.Panel(res)
    if timed:
        utils.timer.dtimer_stop(timer)
    return res


# Store the keys for which the execution was parallel in the last invocation.
_keys_for_parallel = None


# TODO(gp): When we run apply_to_dict_panel_parallel() with a lambda func
# filling some arguments for a memoized function, we need to know if the
# memoized function will need eval. So we need to pass the intrinsic function
# and the args to this wrapper.
def apply_to_dict_panel_parallel(
    obj, f, args, func_name=None, timed=False, n_jobs=None, verbose=0
):
    import dill
    from joblib import Parallel, delayed

    if timed:
        timer = utils.timer.dtimer_start(0, func_name)
    dbg.dassert_isinstance(f, utils.memoize.memoized)
    memoized_f = f
    f = f.func
    # Default params.
    if func_name is None:
        func_name = f.__name__
    if n_jobs is None:
        n_jobs = -1
    # Consider the type of the input.
    if isinstance(obj, pd.Panel):
        type_ = "panel"
    elif isinstance(obj, dict):
        type_ = "dict"
    else:
        raise ValueError("Invalid type='%s' for %s" % (type(obj), str(f)))
    #
    res = {}
    keys = list(obj.keys())
    # Execute locally functions already cached.
    _LOG.info("# Execute locally what was cached")
    keys_for_parallel = []
    for k in keys:
        v = obj[k]
        all_args = [v] + args
        needs_eval = memoized_f.needs_eval(*all_args)
        _LOG.debug("k=%s -> needs_eval=%s", k, needs_eval)
        if not needs_eval:
            # Execute locally, since it is already cache.
            _LOG.debug("Execute k=%s locally", k)
            res[k] = memoized_f(*all_args)
        else:
            _LOG.debug("k=%s needs remote execution", k)
            keys_for_parallel.append(k)
    # Execution remotely functions that are not cached.
    _LOG.info(
        "# Execute remotely what was not cached (%s) %s",
        len(keys_for_parallel),
        str(keys_for_parallel),
    )
    global _keys_for_parallel
    _keys_for_parallel = keys_for_parallel[:]
    if keys_for_parallel:
        _LOG.info(
            "Parallel exec starting (len(obj)=%d n_jobs=%d)", len(obj), n_jobs
        )
        f_dill = dill.dumps(f)
        caches = Parallel(n_jobs=n_jobs, max_nbytes=None, verbose=verbose)(
            delayed(memoize.execute_remote_function)(f_dill, *([obj[k]] + args))
            for k in keys_for_parallel
        )
        _LOG.info("Parallel exec ending")
        # Update local cache from remote execution.
        for cache in caches:
            memoize.update_cache(cache)
    # Update results from remote execution.
    _LOG.info("Update results from remote execution")
    for k in keys_for_parallel:
        all_args = [obj[k]] + args
        need_eval = memoized_f.needs_eval(*all_args)
        if utils.memoize.is_memoization_enabled():
            dbg.dassert(not need_eval)
            res[k] = memoized_f(*all_args)
    #
    if type_ == "panel":
        res = pd.Panel(res)
    if timed:
        utils.timer.dtimer_stop(timer)
    return res


# #############################################################################
# Basic python data structures (e.g., dict, set, list) utils.
# #############################################################################


def print_dict(dict_, num_values=5, sort=True):
    dbg.dassert_isinstance(dict_, dict)
    keys = list(dict_.keys())
    if sort:
        keys = sorted(keys)
    if num_values is not None:
        dbg.dassert_lte(1, num_values)
        keys = keys[:num_values]
        pprint.pprint({k: dict_[k] for k in keys})
    print("...")


def pick_first(obj):
    """
    Pick first df from dict of dfs or panel.
    """
    dbg.dassert_in(type(obj), (dict, pd.Panel))
    key = sorted(obj.keys())[0]
    return obj[key]


def head(obj, key=None, max_n=2, tag=None):
    """
    Show head of dict or panel.
    """
    txt = ""
    txt += "# %s\n" % str(type(obj))
    if isinstance(obj, dict):
        txt += "keys=%s\n" % format_list(list(obj.keys()), tag=tag)
        if key is None:
            key = sorted(obj.keys())[0]
        txt += "# key=%s\n" % key
        txt += dbg.space(head(obj[key], key=None, max_n=max_n, tag="value"))
    elif isinstance(obj, pd.Panel):
        txt += describe(obj, max_n=max_n) + "\n"
        txt += "# head=\n"
        txt += dbg.space(str(obj[obj.items[0]].head(max_n)))
    elif isinstance(obj, pd.Series) or isinstance(obj, pd.DataFrame):
        txt += str(obj.head(max_n))
    else:
        raise ValueError("Invalid object %s" % str(obj))
    return txt


def analyze_object(locals_tmp, obj, tag="", max_string_len=1000):
    locals().update(locals_tmp)
    print("obj=", tag)
    print("type(obj)=", type(obj))
    print("str(obj)=", str(obj)[:max_string_len])
    data = []
    for x in dir(obj):
        try:
            val = getattr(obj, x)
            type_ = type(val)
            val = str(val)
        except Exception as e:
            type_ = "exception"
            val = str(e)
        data.append((x, type_, val))
    data = pd.DataFrame(data, columns=["key", "type(val)", "val"])
    data.set_index("key", inplace=True)
    IPython.core.display.display(IPython.core.display.HTML(data.to_html()))


# #############################################################################
# Pandas data structure utils.
# #############################################################################

# /////////////////////////////////////////////////////////////////////////////
# Printing.
# /////////////////////////////////////////////////////////////////////////////


def describe(obj, tag=None, max_n=None):
    txt = ""
    if tag is not None:
        txt += "%s=\n" % tag
    if isinstance(obj, pd.Panel):
        txt += "type=pd.Panel\n"
        txt += format_list(obj.axes[0], max_n=max_n, tag="items") + "\n"
        txt += format_list(obj.axes[1], max_n=2, tag="major") + "\n"
        txt += format_list(obj.axes[2], max_n=max_n, tag="minor") + "\n"
    elif isinstance(obj, pd.DataFrame):
        txt += "type=pd.DataFrame\n"
        txt += format_list(obj.columns, max_n=max_n, tag="columns") + "\n"
        txt += format_list(obj.index, max_n=2, tag="index") + "\n"
    elif isinstance(obj, pd.Series):
        txt += "type=pd.Series\n"
        txt += "name=%s" % obj.name + "\n"
        txt += format_list(obj.index, max_n=2, tag="index") + "\n"
    elif isinstance(obj, list):
        txt += "type=list\n"
        if tag is None:
            tag = ""
        txt += print_list(tag, obj, to_string=True)
    else:
        raise ValueError(str(obj))
    txt = txt.rstrip("\n")
    return txt


def head_tail(df, num_rows=2, as_txt=False):
    # TODO(gp): concat head and tail and add an empty row with all ...
    head = df.head(num_rows)
    head.index.name = "head"
    display_df(head, inline_index=True, as_txt=as_txt)
    #
    print()
    #
    tail = df.tail(num_rows)
    tail.index.name = "tail"
    display_df(tail, inline_index=True, as_txt=as_txt)


def find_common_columns(df):
    cols_cnt = {}
    for c in df.columns:
        cols_cnt[c] = cols_cnt.get(c, 0) + 1
    cols = [c for c in df.columns if cols_cnt[c] > 1]
    return cols


def min_max_index(obj, tag=None):
    index = get_index(obj)
    dbg.dassert(index.is_unique)
    dbg.dassert(index.is_monotonic_increasing)
    txt = ""
    if tag:
        txt += "%s: " % tag
    txt += "[%s, %s], count=%s" % (
        pd.to_datetime(index.values[0]),
        pd.to_datetime(index.values[-1]),
        len(index),
    )
    return txt


def min_max(obj, tag=None):
    # dbg.dassert_in(type(obj), (list, tuple))
    txt = ""
    if tag:
        txt += "%s: " % tag
    if len(obj) > 0:
        if hasattr(obj, "is_monotonic_increasing"):
            min_, max_ = obj.values[0], obj.values[-1]
        else:
            min_, max_ = min(obj), max(obj)
        txt += "[%s, %s], count=%s" % (min_, max_, len(obj))
    else:
        txt += "empty"
    return txt


def columns(df):
    """
    Print df columns vertically.
    """
    dbg.dassert_type_is(df, pd.DataFrame)
    print("columns=")
    print(dbg.space("\n".join(df.columns)))


def exact_rename_df(df, rename_map, axis):
    """
    Same as df.rename() but checking that all columns / index are replaced.
    """
    dbg.dassert_type_is(df, pd.DataFrame)
    if axis == 0:
        vals = df.index
    elif axis == 1:
        vals = df.columns
    else:
        raise ValueError("Invalid axis=%s" % axis)
    dbg.dassert_set_eq(vals, list(rename_map.keys()))
    if axis == 0:
        df = df.rename(index=rename_map)
    elif axis == 1:
        df = df.rename(columns=rename_map)
    else:
        raise ValueError("Invalid axis=%s" % axis)
    return df


# /////////////////////////////////////////////////////////////////////////////
# General and helpers.
# /////////////////////////////////////////////////////////////////////////////


def get_index(obj):
    if isinstance(obj, pd.Index):
        pass
    elif isinstance(obj, pd.DataFrame):
        index = obj.index
    elif isinstance(obj, pd.Series):
        index = obj.index
    elif isinstance(obj, pd.Panel):
        index = obj.axes[1]
    else:
        dbg.dfatal("Invalid type(obj)=%s" % type(obj))
    return index


def check_index_type(series):
    exp_type = None
    for s in series:
        dbg.dassert_type_is(s, pd.Series)
        curr_type = series.index
        # curr_type = type(series.index[0])
        if exp_type is None:
            exp_type = curr_type
        else:
            dbg.dassert_eq(
                exp_type,
                curr_type,
                msg="series '%s' has different index type" % s.name,
            )
    return True


# /////////////////////////////////////////////////////////////////////////////
# Filtering.
# /////////////////////////////////////////////////////////////////////////////


def filter_by_period(
    obj, start_time, end_time, axis=None, mode=None, verbosity=logging.DEBUG
):
    """
    Filter an obj that can be sliced with [start_time:end_time] reporting
    stats.
    """
    _LOG.log(verbosity, "# Filtering in [%s, %s]", start_time, end_time)
    if isinstance(obj, pd.Panel) or isinstance(obj, pd.Panel4D):
        dbg.dassert_is_not(axis, None)
        index = obj.axes[axis]
    elif isinstance(obj, pd.DataFrame):
        index = obj.index
    else:
        raise ValueError("Invalid type(obj)=%s" % type(obj))
    _LOG.log(verbosity, "before=%s", min_max(index))
    # Slice index.
    index_tmp = slice_index(index, start_time, end_time, mode=mode)
    dbg.dassert_lte(1, len(index_tmp))
    # Assign.
    _LOG.log(verbosity, "after=%s", min_max(index_tmp))
    # TODO(gp): Find out how to do it systematically.
    if isinstance(obj, pd.DataFrame):
        if axis == 0:
            obj = obj.loc[index_tmp, :]
        elif axis == 1:
            obj = obj.loc[:, index_tmp]
        else:
            raise ValueError("Invalid axis=%s" % axis)
    elif isinstance(obj, pd.Panel):
        if axis == 0:
            obj = obj.loc[index_tmp, :, :]
        elif axis == 1:
            obj = obj.loc[:, index_tmp, :]
        elif axis == 2:
            obj = obj.loc[:, :, index_tmp]
        else:
            raise ValueError("Invalid axis=%s" % axis)
    elif isinstance(obj, pd.Panel4D):
        if axis == 0:
            obj = obj.loc[index_tmp, :, :, :]
        elif axis == 1:
            obj = obj.loc[:, index_tmp, :, :]
        elif axis == 2:
            obj = obj.loc[:, :, index_tmp, :]
        elif axis == 3:
            obj = obj.loc[:, :, :, index_tmp]
        else:
            raise ValueError("Invalid axis=%s" % axis)
    else:
        raise ValueError("Invalid type(obj)=%s" % type(obj))
    return obj


def filter_on_times(df, start_time, end_time, reverse=False):
    """
    Filter df keeping rows with index times in [start_time, end_times].

    - reverse: reverse the filtering
    """
    dbg.dassert_type_is(df, pd.DataFrame)
    dbg.dassert_type_is(start_time, datetime.time)
    dbg.dassert_type_is(end_time, datetime.time)
    mask = [start_time <= dt.time() <= end_time for dt in df.index]
    if reverse:
        mask = ~mask
    return df[mask]


# def drop_zeros(srs):
#    is_df = False
#    if isinstance(srs, pd.DataFrame):
#        srs = cast_df_to_series(srs)
#        is_df = True
#    dbg.dassert_type_is(srs, pd.Series)
#    mask = srs != 0
#    srs = srs[mask]
#
#    return srs
#
#
# def drop_not_finite(srs):
#    dbg.dassert_type_is(srs, pd.Series)
#    return srs[np.isfinite(srs)]


def sample_index_times(obj, time):
    """
    Sample a pandas obj on a given time.
    """
    dbg.dassert_type_is(time, datetime.time)
    index = get_index(obj)
    # dbg.dassert_type_is(index.values[0].time(), datetime.time)
    mask = [pd.to_datetime(dt).time() == time for dt in index]
    ret = obj[mask].copy()
    dbg.dassert_lte(1, ret.shape[0])
    return ret


def drop_before_first_row_without_nans(df):
    """
    Filter df before the first row without nans.
    """
    return df[df.dropna().index[0] :]


# TODO(gp): -> remove_non_finite()?
# TODO(gp): Extend to work for a general value (e.g., 0.0)
def filter_non_finite(obj, col_names=None, keep_finite=True, print_stats=False):
    """
    Return the filtered obj (data frame, series, numpy array) removing non-
    finite values in any column in col_names.
    """

    # Select what we want to keep.
    def _build_mask(mask, keep_finite):
        if keep_finite:
            mask = finite_mask
        else:
            mask = ~finite_mask
        return mask

    if isinstance(obj, pd.DataFrame):
        # Data frame.
        if col_names is None:
            col_names = obj.columns
        if isinstance(col_names, str):
            col_names = [col_names]
        dbg.dassert_is_subset(col_names, obj.columns)
        finite_mask = np.all(np.isfinite(obj[col_names]), axis=1)
        mask = _build_mask(finite_mask, keep_finite)
        # Save the removed values.
        vals = obj[~mask].values.flatten()
    elif isinstance(obj, pd.Series):
        # Series.
        dbg.dassert_is(col_names, None)
        finite_mask = np.isfinite(obj)
        mask = _build_mask(finite_mask, keep_finite)
        vals = obj[~mask].values.tolist()
    elif isinstance(obj, np.ndarray):
        # Numpy array.
        finite_mask = np.isfinite(obj)
        mask = _build_mask(finite_mask, keep_finite)
        vals = obj[~finite_mask]
    else:
        raise ValueError("Invalid type='%s'" % type(obj))
    # Select what we want to keep.
    obj_tmp = obj[mask]
    # Report stats, if needed.
    if print_stats:
        before_num_cols = obj.shape[0]
        after_num_cols = obj_tmp.shape[0]
        print("filter_non_finite (keep_finite=%s):" % keep_finite)
        print(
            "\tkept rows=%s"
            % dbg.perc(after_num_cols, before_num_cols, printAll=True)
        )

        def _count_non_finite(vals):
            count = {"nan": 0, "-inf": 0, "+inf": 0}
            for v in vals:
                if np.isnan(v):
                    count["nan"] += 1
                elif np.isposinf(v):
                    count["+inf"] += 1
                elif np.isneginf(v):
                    count["-inf"] += 1
            return count

        print("\tvals=%s" % pprint.pformat(_count_non_finite(vals)))
    # Convert back to the correct type.
    if isinstance(obj_tmp, pd.DataFrame):
        dbg.dassert_lte(1, obj_tmp.shape[0])
    elif isinstance(obj_tmp, pd.Series) or isinstance(obj_tmp, np.ndarray):
        dbg.dassert_lte(1, len(obj_tmp))
    else:
        raise ValueError("Invalid type='%s'" % type(obj_tmp))
    return obj_tmp


# /////////////////////////////////////////////////////////////////////////////
# Transform.
# /////////////////////////////////////////////////////////////////////////////


def prepend_df_columns(df, prefix, copy=True):
    if copy:
        df = df.copy()
    df.columns = [prefix + c for c in df.columns]
    return df


def align_to_dt_index(idx, dt):
    dbg.dassert_type_is(idx, pd.DatetimeIndex)
    dbg.dassert(idx.is_monotonic_increasing)
    utc = idx.tz is not None
    dt = pd.to_datetime(dt, utc=utc)
    dt_aligned = idx[bisect.bisect_left(idx, dt)]
    return dt_aligned


def align_to_index(obj, dt):
    idx = get_index(obj)
    return align_to_dt_index(idx, dt)


def slice_index(idx, start_dt, end_dt, mode=None):
    """
    - None means no bound
    """
    dbg.dassert_type_is(idx, pd.DatetimeIndex)
    dbg.dassert(idx.is_monotonic_increasing)
    if mode is None:
        mode = "close"
    utc = idx.tz is not None
    #
    if start_dt is not None:
        start_dt = pd.to_datetime(start_dt, utc=utc)
    else:
        start_dt = idx[0]
    if end_dt is not None:
        end_dt = pd.to_datetime(end_dt, utc=utc)
    else:
        end_dt = idx[-1]
    dbg.dassert_lte(start_dt, end_dt)
    # TODO(gp): Fix this.
    if mode == "open":
        start_idx = bisect.bisect_left(idx, start_dt)
        end_idx = bisect.bisect_left(idx, end_dt)
    elif mode == "close":
        start_idx = bisect.bisect_right(idx, start_dt)
        end_idx = bisect.bisect_right(idx, end_dt)
    else:
        raise ValueError("Invalid mode=%s" % mode)
    return idx[start_idx:end_idx]


def concat_series(series, cols=None, join="outer"):
    dbg.dassert(check_index_type(series))
    if cols is None:
        cols = [srs.name for srs in series]
    dbg.dassert_eq(len(series), len(cols))
    dbg.dassert_no_duplicates(cols)
    srs_tmp = []
    for srs, col in zip(series, cols):
        if isinstance(srs, pd.DataFrame):
            dbg.dassert_eq(len(srs.columns), 1)
            srs = srs[srs.columns[0]]
        srs = srs.copy()
        srs.name = col
        srs_tmp.append(srs)
    df = pd.concat(srs_tmp, join=join, axis=1)
    return df


# TODO(gp): merge with merge().
def concat_to_df(df, obj, overwrite=False):
    """
    Concat df and obj by column.
    """
    if isinstance(obj, pd.Series):
        obj = pd.DataFrame(obj)
    dbg.dassert_type_is(obj, pd.DataFrame)
    #
    if set(obj.columns).issubset(df.columns):
        # df overlaps with obj.
        dbg.dassert(overwrite, msg="Columns already present: one must overwrite")
        df.drop(obj.columns, axis=1, inplace=True)
    # Merge.
    dbg.dassert(not set(df.columns).intersection(set(obj.columns)))
    df = df.merge(obj, how="outer", left_index=True, right_index=True)
    return df


def merge(df1, df2, tag1="1", tag2="2", *args, **kwargs):
    """
    Wrapper around pd.merge() that prepends the name of the columns.
    """
    df1 = prepend_df_columns(df1, tag1 + ".")
    df2 = prepend_df_columns(df2, tag2 + ".")
    df = pd.merge(df1, df2, *args, **kwargs)
    return df


def shuffle_df(df, mode, seed, axis=0):
    df = df.copy()
    np.random.seed(seed)
    idx = df.index.copy()
    if mode == "shuffle_index":
        loc_idx = np.arange(len(idx))
        np.random.shuffle(loc_idx)
        df = df.iloc[loc_idx]
        df.index = idx
    else:
        dbg.dassert_eq(mode, "shuffle_all")
        df.apply(np.random.shuffle, axis=axis)
    dbg.dassert(np.all(df.index == idx))
    return df


def shuffle(obj, mode, seed):
    """
    Shuffle predictors in a dict tag -> feature.
    """
    dbg.dassert_in(type(obj), [dict, pd.Panel])
    for c in list(obj.keys()):
        obj[c] = shuffle_df(obj[c], mode, seed, axis=0)
    return obj


def random(obj, seed):
    dbg.dassert_in(type(obj), [dict, pd.Panel])
    np.random.seed(seed)
    for c in list(obj.keys()):
        idx = obj[c].index
        cols = obj[c].columns
        obj[c] = pd.DataFrame(
            np.random.rand(*obj[c].shape) * 2 - 1.0, index=idx, columns=cols
        )
    return obj


def remove_outliers(
    obj,
    lower_quantile,
    upper_quantile=None,
    mode=None,
    inplace=False,
    print_stats=True,
):
    """
    Remove / winsorize outliers (according to "mode") given lower / upper
    quantile in df[col_name].
    """
    if upper_quantile is None:
        upper_quantile = 1.0 - lower_quantile
    if mode is None:
        mode = "winsorize"
    _LOG.debug("Removing outliers with mode=%s", mode)
    bounds = utils.jstats.get_quantile_bounds(obj, lower_quantile, upper_quantile)
    if print_stats:
        _LOG.debug("bounds=%s", str(bounds))
    if inplace:
        ret = obj
    else:
        ret = obj.copy()
    if mode == "winsorize":
        ret[obj <= bounds[0]] = bounds[0]
        ret[bounds[1] <= obj] = bounds[1]
        if print_stats:
            num = np.sum(obj <= bounds[0]) + np.sum(bounds[1] <= obj)
            _LOG.debug(
                "winsorize: to_process=%s", dbg.perc(num, len(ret), printAll=True)
            )
    else:
        mask = (bounds[0] <= obj) & (obj <= bounds[1])
        if print_stats:
            num = np.sum(mask)
            _LOG.debug(
                "%s: to_process=%s", mode, dbg.perc(num, len(ret), printAll=True)
            )
        if mode == "set_to_nan":
            ret[~mask] = np.nan
            _LOG.debug(
                "overwritten %s / %s elems with nan",
                np.sum(~np.isfinite(ret)),
                np.sum(np.isfinite(obj)),
            )
        elif mode == "set_to_zero":
            ret[~mask] = 0.0
            _LOG.debug(
                "overwritten %s / %s elems with 0", np.sum(~mask), obj.shape[0]
            )
        elif mode == "filter":
            ret = ret[mask].copy()
        else:
            dbg.dfatal("Invalid mode='%s'" % mode)
    return ret, bounds


def remove_outlier_rows_from_df(
    df, lower_quantile, upper_quantile=None, col_names=None, mode=None
):
    """
    Remove outlier rows, i.e., rows where there is at least one outlier in each
    column.
    """
    dbg.dassert_type_is(df, pd.DataFrame)
    num_cols = df.shape[0]
    if col_names is None:
        col_names_to_trim = df.columns
    else:
        col_names_to_trim = col_names
    _LOG.debug("Trimming based on col_names=%s", str(col_names_to_trim))
    # Scan and trim columns.
    trimmed_cols = []
    for col in df.columns:
        if col in col_names_to_trim:
            _LOG.debug("Trimming col %s", col)
            trimmed_col, _ = remove_outliers(
                df[col], lower_quantile, upper_quantile=upper_quantile, mode=mode
            )
        else:
            _LOG.debug("Skipping col %s", col)
            trimmed_col = df[col]
        trimmed_cols.append(trimmed_col)
    ret = pd.concat(trimmed_cols, join="outer", axis=1)
    _LOG.debug("Trimmed %s rows out of %s", num_cols - ret.shape[0], num_cols)
    return ret


def scale_by_std(df, demean=False):
    """
    Align the columns of the df to the last value.
    """
    df = df.copy()
    if demean:
        df -= df.dropna().mean()
    scale = np.abs(df.dropna().std())
    return df / scale


def align_df_to_last_value(df):
    """
    Align the columns of the df to the last value.
    """
    df = df.dropna()
    # df -= df.min()
    df /= df.iloc[-1]
    return df


# /////////////////////////////////////////////////////////////////////////////
# Query and report.
# /////////////////////////////////////////////////////////////////////////////


def get_times(obj):
    index = get_index(obj)
    times = set(dt.time() for dt in index)
    return sorted(times)


def get_time_interval(times):
    """
    Given a set of intervals (e.g., where there are returns, from get_times())
    compute first, last, and count.
    """
    times = sorted(list(times))
    return min(times), max(times), len(times)


def report_nan_nums_for_columns(
    df, display=True, fmt_pct=True, plot=False, title=None, figsize=None
):
    dbg.dassert_type_is(df, pd.DataFrame)
    print("columns=(%s) %s" % (len(df.columns), " ".join(df.columns)))
    print("dates=[%s, %s]" % (df.index[0], df.index[-1]))
    print("num_dates=", df.shape[0])
    # Count nans.
    count = pd.DataFrame(np.isnan(df).sum(axis=0), columns=["nans"])
    col_name = "pct_nans [%]"
    count[col_name] = count["nans"] / df.shape[0] * 100.0
    if fmt_pct:
        count[col_name] = [float("%.1f" % x) for x in count[col_name]]
    # Count zeros.
    count["zeros"] = (df == 0).sum(axis=0)
    col_name = "pct_zeros [%]"
    count[col_name] = count["zeros"] / df.shape[0] * 100.0
    if fmt_pct:
        count[col_name] = [float("%.1f" % x) for x in count[col_name]]
    if plot:
        count_tmp = count.sort(columns=["pct"])
        count_tmp[["pct"]].plot(kind="bar", title=title, figsize=figsize)
    if display:
        display_df(count, as_txt=True)


def report_intraday_stats(rets):
    """
    Assume data frame with datestamps on index and instruments on the columns
    and report for each instrument.
            min_hour  max_hour  min_date  max_date
    inst
    ...
    """
    dbg.dassert_type_is(rets, pd.DataFrame)
    stats_df = []
    count_by_hour = rets.groupby(lambda x: x.time()).count()
    for inst_name in count_by_hour.columns:
        row = [inst_name]
        # Find non-null times.
        hours_non_null = count_by_hour[inst_name].nonzero()[0]
        dbg.dassert_lte(1, len(hours_non_null))
        first_non_zero = hours_non_null[0]
        row.append(count_by_hour[inst_name].index[first_non_zero])
        #
        last_non_zero = hours_non_null[-1]
        row.append(count_by_hour[inst_name].index[last_non_zero])
        # Find first non-null dates.
        dates_non_null = rets[inst_name].notnull().nonzero()[0]
        dbg.dassert_lte(1, len(dates_non_null))
        min_date = rets.index[dates_non_null[0]].date()
        row.append(min_date)
        #
        max_date = rets.index[dates_non_null[-1]].date()
        row.append(max_date)
        #
        stats_df.append(row)
    stats_df = pd.DataFrame(
        stats_df, columns=["inst", "min_hour", "max_hour", "min_date", "max_date"]
    )
    stats_df.set_index("inst", drop=True, inplace=True)
    return stats_df


def plot_intraday_stats(rets):
    inst_names = rets.columns
    plt.figure(figsize=(20, 3 * len(inst_names)))
    for i, inst_name in enumerate(inst_names):
        ax = plt.subplot(len(inst_names) + 1, 1, i + 1)
        rets_tmp = rets[inst_name].astype(float)
        rets_tmp.groupby(lambda x: x.time()).count().plot(ax=ax, title=inst_name)
    plt.plot()


# /////////////////////////////////////////////////////////////////////////////
# Conversion.
# /////////////////////////////////////////////////////////////////////////////


def cast_df_to_series(df):
    """
    Convert one column df into a series.
    """
    dbg.dassert_type_is(df, pd.DataFrame)
    dbg.dassert_eq(df.shape[1], 1)
    return df[df.columns[0]]


def to_pd_timestamp(obj):
    """
    Cast index of a df or srs through pd.to_datetime().
    """
    dbg.dassert_type_in(obj, (pd.DataFrame, pd.Series))
    obj = obj.copy()
    # TODO(gp): Maybe apply or map is faster.
    obj.index = [pd.to_datetime(dt) for dt in obj.index]
    return obj


def to_date(obj, axis=None):
    """
    Cast index of a df or srs through pd.to_datetime().
    """
    dbg.dassert_type_in(obj, (pd.Panel, pd.DataFrame, pd.Series))
    obj = obj.copy()
    if isinstance(obj, pd.Panel):
        dbg.dassert_is_not(axis, None)
        # For some reason .axes[axis] doesn't work for writing but only for
        # reading.
        transform = lambda obj: [dt.date() for dt in obj.axes[axis]]
        if axis == 0:
            obj.items = transform(obj)
        elif axis == 1:
            obj.major_axis = transform(obj)
        elif axis == 2:
            obj.minor_axis = transform(obj)
        else:
            raise ValueError("Invalid axis=%s" % axis)
    else:
        # TODO(gp): Maybe apply or map is faster.
        obj.index = [dt.date() for dt in obj.index]
    return obj


# /////////////////////////////////////////////////////////////////////////////
# Misc.
# /////////////////////////////////////////////////////////////////////////////


def safe_div(x1, x2):
    return x1 / np.where(x2 != 0, x2, 1)


def to_csv(model_df, file_name, overwrite_if_present):
    # Make the path linux friendly and absolute.
    dir_name = os.path.dirname(file_name)
    base_name = os.path.basename(file_name).replace("/", "_")
    file_name = os.path.abspath("%s/%s" % (dir_name, base_name))
    dbg.dassert(
        file_name.endswith(".csv"), msg="Invalid file_name='%s'" % file_name
    )
    # Create dir, if needed.
    utils.jio.create_enclosing_dir(file_name, incremental=True)
    if not overwrite_if_present:
        dbg.dassert(
            not os.path.exists(file_name),
            msg="don't want to overwrite '%s'" % file_name,
        )
    # Save data.
    to_typed_csv(model_df, file_name)
    print("File saved to: %s" % file_name)


def plot_rolling_correlation(df, vmin=-1, vmax=1):
    col_pairs = []
    for i in range(len(df.columns)):
        for j in range(i + 1, len(df.columns)):
            col_pairs.append((df.columns[i], df.columns[j]))
    # Compute the correlations.
    df_corr = []
    df = df.dropna()
    for lbl1, lbl2 in col_pairs:
        srs = pd.rolling_corr(df[lbl1], df[lbl2], window=252)
        srs.name = "%s vs %s" % (lbl1, lbl2)
        df_corr.append(srs)
    df_corr = pd.concat(df_corr, join="outer", axis=1)
    # Plot.
    ax = df_corr.plot(ylim=(vmin, vmax), cmap="rainbow")
    #
    ax.axhline(0, color="gray", linestyle="--", lw=2)
    #
    ax.axhline(-0.5, color="green", linestyle="--", alpha=0.5)
    ax.axhline(0.5, color="green", linestyle="--", alpha=0.5)


def compare_price_timeseries(
    df,
    col_name1,
    col_name2,
    col_names_to_trim=None,
    outliers_thr=None,
    plot_ts=True,
    plot_regress=True,
    print_model_stats=False,
):
    df = df.dropna()
    df = df[[col_name1, col_name2]]
    # Remove outliers based on returns.
    if outliers_thr is not None:
        dbg.dassert_is_not(col_names_to_trim, None)
        mode = "set_to_nan"
        # mode = "set_to_zero"
        df = df.dropna()
        num_cols = df.shape[0]
        col_names_to_trim_tmp = []
        for col_name in col_names_to_trim:
            df[col_name + ".ret"] = df[col_name1].pct_change()
            col_names_to_trim_tmp.append(col_name + ".ret")
        df = remove_outlier_rows_from_df(
            df, outliers_thr, col_names=col_names_to_trim_tmp, mode=mode
        )
        df = df.dropna()
        df = df[[col_name1, col_name2]]
        _LOG.debug("Removed %s out of %s rows", num_cols - df.shape[0], num_cols)
    df = df.dropna()
    df = scale_by_std(df)
    df -= df.min()
    if plot_ts:
        df.plot()
    if plot_regress:
        _ = regress(
            df.pct_change(),
            col_name1,
            col_name2,
            use_intercept=True,
            print_model_stats=print_model_stats,
        )


# #############################################################################
# Plot.
# #############################################################################


def config_matplotlib():
    matplotlib.rcParams.update(
        {
            "axes.labelsize": 15,
            "axes.titlesize": 20,
            #'figure.figsize': [15, 10],
            "figure.figsize": [15, 5],
            "font.size": 12,
            "image.cmap": "rainbow",
            "legend.fontsize": 15,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
        }
    )


small_fig = (15, 2)


def set_same_fig_limits(use_ylim, use_xlim, fig=None):
    if fig is None:
        fig = plt.gcf()
    # Find limits.
    ylim = None
    xlim = None
    for ax in fig.get_axes():
        curr_ylim = ax.get_ylim()
        if ylim is None:
            ylim = curr_ylim
        else:
            ylim = (min(ylim[0], curr_ylim[0]), max(ylim[1], curr_ylim[1]))
        #
        curr_xlim = ax.get_xlim()
        if xlim is None:
            xlim = curr_xlim
        else:
            xlim = (min(xlim[0], curr_xlim[0]), max(xlim[1], curr_xlim[1]))
    # Apply limits.
    for ax in fig.get_axes():
        if use_ylim:
            ax.set_ylim(ylim)
        if use_xlim:
            ax.set_xlim(xlim)


def plot_density(data, color="m", ax=None, figsize=None, title=""):
    if len(data) <= 1:
        _LOG.error("Can't plot density with %s elements", len(data))
        return
    dbg.dassert_lte(1, len(data))
    dbg.dassert_type_is(color, str)
    if isinstance(data, (list, tuple)):
        data = np.array(data)
    data = data[np.isfinite(data)]
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    ax.set_title(title)
    sns.distplot(data, color=color, ax=ax)


# It can't accept ax.
def jointplot(
    df,
    predicted_var,
    predictor_var,
    color="r",
    # TODO(gp): -> figsize?
    size=7,
    kind="reg",
    fit_reg=True,
    intercept=True,
):
    dbg.dassert_in(predicted_var, df.columns)
    dbg.dassert_in(predictor_var, df.columns)
    if not intercept:
        _LOG.error("Can't plot without intercept")
        return
    df = df[[predicted_var, predictor_var]]
    # Remove non-finite values.
    mask = np.all(np.isfinite(df.values), axis=1)
    df = df[mask]
    # Plot.
    sns.jointplot(
        predictor_var,
        predicted_var,
        df,
        kind=kind,
        color=color,
        size=size,
        fit_reg=fit_reg,
    )


def regplot(df, predicted_var, predictor_var, color="r", ax=None):
    """
    Do not show the marginal distributions and pearson coefficient.
    """
    dbg.dassert_in(predicted_var, df.columns)
    dbg.dassert_in(predictor_var, df.columns)
    df = df[[predicted_var, predictor_var]]
    # Remove non-finite values.
    mask = np.all(np.isfinite(df.values), axis=1)
    df = df[mask]
    # Plot.
    ax = sns.regplot(predicted_var, predictor_var, df, color=color, ax=ax)
    # Add info about the fit.
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(
        df[predictor_var].values, df[predicted_var].values
    )
    _ = slope, intercept, std_err
    label = "rho=%.2f pval=%.2f" % (r_value, p_value)
    ax.text(
        0.9,
        0.9,
        label,
        fontsize=20,
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax.transAxes,
    )
    return ax


def plot_acf(data, lags=10, remove_nans=False, figsize=None):
    """
    - autocorrelation is the correlation coefficient of a time series with
      itself at different lags
    - partial autocorrelation controls for values at previous lags
    """
    dbg.dassert_type_is(data, pd.Series)
    if remove_nans:
        mask = np.isnan(data)
        print(
            "Removed %s nans"
            % (dbg.perc(np.sum(mask), len(data), numDigits=2, printAll=True))
        )
        data = data[~mask]
    dbg.dassert_eq(sum(np.isnan(data)), 0, msg="data has nans")
    if figsize is None:
        figsize = (16, 6)
    _, axes = plt.subplots(3, figsize=figsize, sharex=True)
    #
    acf = statsmodels.tsa.stattools.acf(data)[:lags]
    srs = pd.Series(acf, index=list(range(0, lags)))
    srs.name = "acf"
    print("acf=\n%s" % srs.to_string())
    #
    statsmodels.api.graphics.tsa.plot_acf(data, lags=lags, ax=axes[0])
    statsmodels.api.graphics.tsa.plot_pacf(data, lags=lags, ax=axes[1])
    #
    acf_tmp = acf
    acf_tmp[0] = 0.0
    axes[2].plot(np.cumsum(acf_tmp), marker="o")
    axes[2].set_title("Cumsum of acf[1:]")


def plot_ccf(
    data,
    col_name1,
    col_name2,
    min_lag=-3,
    max_lag=10,
    cumsum=False,
    title=None,
    figsize=None,
    max_nrows=None,
):
    if max_nrows is not None and data.shape[0] > max_nrows:
        _LOG.warning("Skipping since df has %s rows", data.shape[0])
        return
    # Sanity check for params.
    dbg.dassert_lte(min_lag, max_lag)
    dbg.dassert_lte(0, max_lag)
    # dbg.dassert_ne(col_name1, col_name2)
    dbg.dassert_in(col_name1, data.columns)
    dbg.dassert_in(col_name2, data.columns)
    suffix = " (cumsum)" if cumsum else ""
    if title is None:
        title = "%s ~ %s" % (col_name1, col_name2)
    title += suffix
    if figsize is None:
        figsize = (16, 4)
    # Extract and prepare the data.
    # data = data[[col_name1, col_name2]].copy()
    # data[col_name2] = data[col_name2].shift(min_lag)
    # data = filter_non_finite(data, [col_name1, col_name2])
    # Compute cross-correlation.
    dbg.dassert_lte(1, data.shape[0])
    ccf = []
    lags = list(range(min_lag, max_lag + 1))
    for lag in lags:
        # Filter non-finite values.
        data_tmp = data[[col_name1, col_name2]].copy()
        data_tmp[col_name2] = data_tmp[col_name2].shift(min_lag)
        # Filter non-finite values.
        data = filter_non_finite(data_tmp, [col_name1, col_name2])
        if lag == 0:
            corr = 1.0
        else:
            corr = data_tmp[col_name1].corr(data_tmp[col_name2])
        ccf.append(corr)
    # ccf = statsmodels.tsa.stattools.ccf(data[col_name1], data[col_name2])
    # print ccf
    # ccf = ccf[:((abs(min_lag) + max_lag))]
    if cumsum:
        ccf = np.cumsum(ccf)
    # Report results.
    df = pd.DataFrame(ccf, columns=["ccf" + suffix], index=lags)
    print(df.to_string())
    # Plot.
    plt.figure(figsize=figsize)
    plt.title(title)
    plt.xlabel("Num lags")
    plt.ylabel("Cross correlation" + suffix)
    dbg.dassert(np.all(np.isfinite(ccf)))
    dbg.dassert_eq(len(lags), len(ccf))
    plt.axhline(0, color="k", linestyle="--")
    plt.plot(lags, ccf, marker="o")
    # - Show all xticks.
    plt.xlim(min_lag, max_lag)
    plt.xticks(list(range(min_lag, max_lag)))
    # Print some stats.
    argmin = lags[np.argmin(ccf)]
    argmax = lags[np.argmax(ccf)]
    print(
        "min: lag=%s (val=%.2f), max: lag=%s val=%.2f"
        % (argmin, ccf[argmin], argmax, ccf[argmax])
    )


def plot_bootstrap_ccf(
    x_to_lag,
    x_fixed,
    label="",
    color=None,
    min_lags=-20,
    max_lags=20,
    conf_int=False,
    samples=200,
    ax=None,
):
    """
    lags describes how many days before / after today should we lag for
    Plot*CrossCorrelation.
    """
    dbg.dassert_eq(
        len(x_to_lag),
        len(x_fixed),
        msg="x_to_lag and x_fixed should have the same shape.",
    )
    dbg.dassert_lt(min_lags, max_lags)
    # We create confidence intervals by computing the correlation
    # over bootstrap samples.
    correlations = []
    # Make sure we have enough samples that we have 10 on either
    # side of the 95% CI.
    BOOTSTRAP_SAMPLES = samples
    lags = max_lags - min_lags
    for bootstrap in range(BOOTSTRAP_SAMPLES):
        N = x_to_lag.shape[0]
        samples = []
        for lag in range(min_lags, max_lags):
            bootstrap = np.random.randint(0, N - 2 * lags, size=N - 2 * lags)
            x1_window = x_to_lag[(lags + lag) : ((lags + lag) + (N - 2 * lags))][
                bootstrap
            ]
            x2_window = x_fixed[lags : (N - lags)][bootstrap]
            samples.append(
                utils.stats.Cor(np.ravel(x1_window), np.ravel(x2_window))
            )
        correlations.append(samples)
    correlations = np.array(correlations)
    means = np.mean(correlations, axis=0)
    if conf_int:
        if False:
            cis = []
            for i in range(correlations.shape[1]):
                ci = utils.stats.Quantile(
                    correlations[:, i], probs=[0.025, 0.5, 0.975]
                )
                # ci = np.std(correlations[:, i]) * 1.96
                cis.append(ci)
        cis = np.std(correlations, axis=0) * 1.96
        cis = np.array(cis)
    else:
        cis = None
    xx = np.array([x for x in range(min_lags, max_lags)])
    # Finally, create a plot with error bars showing confidence intervals on
    # either side.
    if ax is None:
        _, ax = plt.subplots(figsize=(20, 6))
    ax.errorbar(
        xx,
        means,  # (cis[:, 2] + cis[:, 0]) / 2.0,
        marker="o",  # ms=8,
        yerr=cis,  # (cis[:, 2] - cis[:, 0]) / 2.0,
        color=color,
    )
    title = "Cross correlation"
    if label != "":
        title = "%s" % (label,)
    ax.set_title(title)
    plt.axhline(0, color="k", linestyle="--")
    plt.xlabel("Lags")
    ax.set_ylabel("Correlation")
    # ax.grid()
    # Leave it up to the user to plt.show() in case they want to modify the
    # plot.
    return  # (cis[:, 0] + cis[:, 2]) / 2.


def plot_signal_with_envelope(df, col_name, span, n_std, ax=None):
    dbg.dassert_in(col_name, df.columns)
    if ax is None:
        _, ax = plt.subplots(figsize=(20, 6))
    df = df.copy()
    df[col_name + "_ewma"] = pd.ewma(df[col_name], span=span)
    df[col_name + "_ewmstd"] = pd.ewmstd(df[col_name], span=span)
    df[col_name + "_lb"] = (
        df[col_name + "_ewma"] - n_std * df[col_name + "_ewmstd"]
    )
    df[col_name + "_ub"] = (
        df[col_name + "_ewma"] + n_std * df[col_name + "_ewmstd"]
    )
    #
    df[[col_name]].plot(rot=45, color="gray", ax=ax)
    df[col_name + "_ewma"].plot(rot=45, color="r", ax=ax)
    df[col_name + "_lb"].plot(rot=45, color="b", ls="--", ax=ax)
    df[col_name + "_ub"].plot(rot=45, color="b", ls="--", ax=ax)


def compute_correlation(
    df,
    y_col_name,
    x_col_name,
    remove_non_finite=False,
    standardize=False,
    print_stats=False,
):
    tot_num_samples = df.shape[0]
    col_names = [y_col_name, x_col_name]
    dbg.dassert_is_subset(col_names, df.columns.tolist())
    df = df[col_names]
    if remove_non_finite:
        df = filter_non_finite(df, print_stats=print_stats)
    x, y = df[x_col_name], df[y_col_name]
    if standardize:
        x = (x - x.mean()) / x.std()
        y = (y - y.mean()) / y.std()
    rho, p_val = scipy.stats.stats.pearsonr(x, y)
    if print_stats:
        print("num_samples=%s" % dbg.perc(len(x), tot_num_samples, printAll=True))
        print("rho=%.4f" % rho)
        print(
            "2-tailed pvalue=%.4f (%s)"
            % (p_val, utils.jstats.pvalue_to_stars(p_val))
        )
    return rho, p_val
