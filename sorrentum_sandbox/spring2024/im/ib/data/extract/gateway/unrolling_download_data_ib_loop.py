"""
Import as:

import im.ib.data.extract.gateway.unrolling_download_data_ib_loop as imideguddil
"""

import logging
import os
from typing import Any, List, Optional, Tuple, Union

import helpers.hpandas as hpandas

try:
    import ib_insync
except ModuleNotFoundError:
    print("Can't find ib_insync")

import pandas as pd

# from tqdm.notebook import tqdm
from tqdm import tqdm

# import core.explore as coexplor
import helpers.hdbg as hdbg
import helpers.hlist as hlist
import helpers.hprint as hprint
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)


# #############################################################################

_SIX_PM = (18, 0, 0)


def _get_hh_mm_ss(ts: pd.Timestamp) -> Tuple[int, int, int]:
    """
    Return the hour, minute, second part of a timestamp.
    """
    # Round to seconds.
    ts = ts.round("1s")
    return ts.hour, ts.minute, ts.second


def _set_to_six_pm(ts: pd.Timestamp) -> pd.Timestamp:
    """
    Set the hour, minute, second part of a timestamp to 18:00:00.
    """
    ts = ts.replace(hour=18, minute=0, second=0)
    return ts


def _align_to_six_pm(
    ts: pd.Timestamp, align_right: bool
) -> Tuple[pd.Timestamp, List[pd.Timestamp]]:
    """
    Align a timestamp to the previous / successive 6pm, unless it's already
    aligned.

    :param ts: timestamp to align
    :param align_right: align on right or left
    :return: return the aligned timestamp and the previous unaligned timestamp
    """
    _LOG.debug("ts='%s'", ts)
    if _get_hh_mm_ss(ts) > _SIX_PM:
        dates = [ts]
        # Align ts to 18:00.
        ts = _set_to_six_pm(ts)
    elif _get_hh_mm_ss(ts) < _SIX_PM:
        dates = [ts]
        # Align ts to 18:00 of the day before.
        ts = _set_to_six_pm(ts)
        if align_right:
            ts += pd.DateOffset(days=1)
        else:
            ts -= pd.DateOffset(days=1)
    else:
        # ts is already aligned.
        dates = [ts]
    _LOG.debug("-> ts='%s' dates=%s", ts, dates)
    return ts, dates


def _start_end_ts_to_ET(
    start_ts: pd.Timestamp, end_ts: pd.Timestamp
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Convert to timestamps with timezone, if needed.
    """
    hdbg.dassert_lt(start_ts, end_ts)
    _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
    start_ts = imidegaut.to_ET(start_ts, as_datetime=False)
    end_ts = imidegaut.to_ET(end_ts, as_datetime=False)
    _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
    return start_ts, end_ts


def _ib_date_range_sanity_check(
    start_ts: pd.Timestamp, end_ts: pd.Timestamp, dates: List[pd.Timestamp]
) -> List[pd.Timestamp]:
    # Remove some weird pandas artifacts (e.g., 'freq=2D') related to sampling.
    dates = [pd.Timestamp(ts.to_pydatetime()) for ts in dates]
    # Remove duplicates.
    dates = hlist.remove_duplicates(dates)
    _LOG.debug("-> dates=%s", dates)
    # Sanity check.
    hdbg.dassert_eq(sorted(dates), dates)
    hdbg.dassert_eq(len(set(dates)), len(dates))
    # Using each date as end of intervals [date - days(2), date], we should
    # cover the entire interval [start_ts, end_ts].
    hdbg.dassert_lte(dates[0] - pd.DateOffset(days=2), start_ts)
    hdbg.dassert_lte(end_ts, dates[-1])
    return dates


def _ib_date_range(
    start_ts: pd.Timestamp, end_ts: pd.Timestamp
) -> List[pd.Timestamp]:
    """
    Compute a date range covering [start_ts, end_ts] using the IB loop-style.

    The IB loop-style consists of iterating among days aligned on 6pm.
    """
    start_ts, end_ts = _start_end_ts_to_ET(start_ts, end_ts)
    # Align start_ts and end_ts to 6pm to create a date interval that includes
    # [start_ts, end_ts].
    start_ts_tmp, start_dates = _align_to_six_pm(start_ts, align_right=False)
    # Compute a range of dates aligned to 6pm that includes
    # [start_ts_tmp, end_ts_tmp].
    _LOG.debug("start_ts_tmp='%s' end_ts='%s'", start_ts_tmp, end_ts)
    hdbg.dassert_eq(_get_hh_mm_ss(start_ts_tmp), _SIX_PM)
    hdbg.dassert_lt(start_ts_tmp, end_ts)
    dates = pd.date_range(start=start_ts_tmp, end=end_ts, freq="1D").tolist()
    # If the first date is before start_ts, then we don't need since the interval
    # [date - days(1), date] doesn't overlap with [start_ts, end_ts].
    if dates[0] < start_ts:
        dates = dates[1:]
    # If the last date
    if dates[-1] < end_ts:
        dates.append(end_ts)
    dates = _ib_date_range_sanity_check(start_ts, end_ts, dates)
    return dates


def get_historical_data_workload(
    contract: ib_insync.Contract,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    bar_size_setting: str,
    what_to_show: str,
    use_rth: bool,
) -> Tuple[
    List[Tuple[ib_insync.Contract, pd.Timestamp, str, str, str, bool]],
    List[pd.Timestamp],
]:
    """
    Compute the workload needed to get data in [start_ts, end_ts].
    """
    _LOG.debug(
        "contract='%s', start_ts='%s', end_ts='%s', bar_size_setting='%s', "
        "what_to_show='%s', use_rth='%s'",
        contract,
        start_ts,
        end_ts,
        bar_size_setting,
        what_to_show,
        use_rth,
    )
    start_ts, end_ts = _start_end_ts_to_ET(start_ts, end_ts)
    hdbg.dassert_lte(3, (end_ts - start_ts).days)
    dates = _ib_date_range(start_ts, end_ts)
    # duration_str = "2 D"
    duration_str = "1 D"
    tasks = []
    for end in dates:
        task = (
            contract,
            end,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        )
        _LOG.debug("date='%s' -> task='%s'", end, task)
        tasks.append(task)
    return tasks, dates


def get_historical_data_from_tasks(
    client_id: int,
    tasks: List[Tuple[ib_insync.Contract, pd.Timestamp, str, str, str, bool]],
    use_prograss_bar: bool = False,
) -> pd.DataFrame:
    """
    Execute the workload serially.
    """
    df = []
    ib = imidegaut.ib_connect(client_id, is_notebook=False)
    if use_prograss_bar:
        tasks = tqdm(tasks, desc="Getting historical data from tasks")
    for task in tasks:
        _LOG.debug("task='%s'", task)
        (
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        ) = task
        df_tmp = imidegaut.req_historical_data(
            ib,
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        )
        hpandas.dassert_monotonic_index(df_tmp)
        _LOG.debug("%s -> df_tmp=%s", end_ts, imidegaut.get_df_signature(df_tmp))
        df.append(df_tmp)
    #
    ib.disconnect()
    #
    df = pd.concat(df)
    # There can be overlap between the first 2 chunks.
    df.sort_index(inplace=True)
    df.drop_duplicates(inplace=True)
    return df


# #############################################################################


def _task_to_filename(
    contract,
    end_ts,
    duration_str,
    bar_size_setting,
    what_to_show,
    use_rth,
    dst_dir,
):
    # Create the filename.
    symbol = contract.symbol
    bar_size_setting = bar_size_setting.replace(" ", "_")
    duration_str = duration_str.replace(" ", "_")
    file_name = f"{symbol}.{imidegaut.to_timestamp_str(end_ts)}.{duration_str}.{bar_size_setting}.{what_to_show}.{use_rth}.csv"
    file_name = os.path.join(dst_dir, file_name)
    return file_name


def _execute_ptask(
    client_id,
    contract,
    end_ts,
    duration_str,
    bar_size_setting,
    what_to_show,
    use_rth,
    file_name,
):
    ib = imidegaut.ib_connect(client_id, is_notebook=False)
    df = imidegaut.req_historical_data(
        ib,
        contract,
        end_ts,
        duration_str,
        bar_size_setting,
        what_to_show,
        use_rth,
    )
    ib.disconnect()
    hpandas.dassert_monotonic_index(df)
    _LOG.debug("%s -> df=%s", end_ts, imidegaut.get_df_signature(df))
    if not df.empty:
        df.to_csv(file_name)


def get_historical_data_parallel(tasks, num_threads, incremental, dst_dir):
    """
    Execute the workload in parallel.
    """
    # Prepare parallel tasks.
    ptasks = []
    cnt_skip = 0
    for task in tasks:
        _LOG.debug("task='%s'", task)
        (
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        ) = task
        file_name = _task_to_filename(
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
            dst_dir,
        )
        if incremental and os.path.exists(file_name):
            _LOG.debug(
                "Found file %s: skipping corresponding workload", file_name
            )
            cnt_skip += 1
            continue
        ptask = (
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
            file_name,
        )
        ptasks.append(ptask)
    _LOG.warning(
        "Found %s tasks already executed on disk: skipping",
        hprint.perc(cnt_skip, len(tasks)),
    )
    # Execute parallel workload.
    if num_threads == "serial":
        client_id = 0
        for ptask in tqdm(ptasks):
            (
                contract,
                end_ts,
                duration_str,
                bar_size_setting,
                what_to_show,
                use_rth,
                file_name,
            ) = ptask
            _execute_ptask(
                client_id,
                contract,
                end_ts,
                duration_str,
                bar_size_setting,
                what_to_show,
                use_rth,
                file_name,
            )
    else:
        # -1 is interpreted by joblib like for all cores.
        _LOG.info(
            "Using %s threads", num_threads if num_threads > 0 else "all CPU"
        )
        import joblib

        joblib.Parallel(n_jobs=num_threads, verbose=50)(
            joblib.delayed(_execute_ptask)(
                client_id + 1,
                contract,
                end_ts,
                duration_str,
                bar_size_setting,
                what_to_show,
                use_rth,
                file_name,
            )
            for client_id, (
                contract,
                end_ts,
                duration_str,
                bar_size_setting,
                what_to_show,
                use_rth,
                file_name,
            ) in enumerate(ptasks)
        )
    # Load the data back.
    df = []
    for ptask in ptasks:
        _LOG.debug("ptask='%s'", ptask)
        (
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
            file_name,
        ) = ptask
        # If job was completed succesfully, read dataframe.
        if os.path.exists(file_name):
            df_tmp = imidegddil.load_historical_data(file_name)
        df.append(df_tmp)
    #
    df = pd.concat(df)
    # There can be overlap between the first 2 chunks.
    df.sort_index(inplace=True)
    df.drop_duplicates(inplace=True)
    return df


# #############################################################################


def get_historical_data(
    client_id: int,
    contract: ib_insync.Contract,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    bar_size_setting: str,
    what_to_show: str,
    use_rth: bool,
    mode: str,
    num_threads: Union[str, int] = "serial",
    incremental: bool = False,
    dst_dir: Optional[Any] = None,
    use_progress_bar: bool = False,
    return_ts_seq: bool = False,
) -> Tuple[pd.DataFrame, List[pd.Timestamp]]:
    _LOG.debug(
        "client_id='%s', contract='%s', end_ts='%s', duration_str='%s', bar_size_setting='%s', "
        "what_to_show='%s', use_rth='%s'",
        client_id,
        contract,
        start_ts,
        end_ts,
        bar_size_setting,
        what_to_show,
        use_rth,
    )
    start_ts, end_ts = _start_end_ts_to_ET(start_ts, end_ts)
    tasks, dates = get_historical_data_workload(
        contract, start_ts, end_ts, bar_size_setting, what_to_show, use_rth
    )
    _LOG.debug("dates=%s", dates)
    if mode == "in_memory":
        df = get_historical_data_from_tasks(
            client_id, tasks, use_prograss_bar=use_progress_bar
        )
    elif mode == "on_disk":
        df = get_historical_data_parallel(
            tasks, num_threads, incremental, dst_dir
        )
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    #
    if not df.empty:
        # import helpers.hunit_test as hunitest
        # hunitest.diff_df_monotonic(df)
        hpandas.dassert_monotonic_index(df)
        end_ts3 = end_ts - pd.DateOffset(seconds=1)
        _LOG.debug("start_ts= %s end_ts3=%s", start_ts, end_ts3)
        df = df[start_ts:end_ts3]
    #
    if return_ts_seq:
        return df, dates
    return df
