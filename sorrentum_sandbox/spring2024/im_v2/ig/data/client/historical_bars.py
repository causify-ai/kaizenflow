"""
Expose a layer of free-standing stateless functions, interacting with IG infra
for retrieving bar data.

Import as:

import im_v2.ig.data.client.historical_bars as imvidchiba
"""

import concurrent.futures
import datetime
import functools
import logging
import os
import pytest
import tempfile
from typing import List, Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as parquet
from tqdm.autonotebook import tqdm

import helpers.hcache as hcache
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.htimer as htimer
import helpers.htqdm as htqdm
import im_v2.ig.ig_utils as imvigigut

_LOG = logging.getLogger(__name__)


# #############################################################################
# Historical flow.
# #############################################################################

# The schema of the historical data is:
# - vendor_date
# - interval
# - start_time
# - end_time
# - ticker
# - currency
# - open
# - close
# - low
# - high
# - volume
# - notional
# - last_trade_time
# - all_day_volume
# - all_day_notional
# - day_volume
# - day_notional
# - day_vol_prc_sqr
# - day_num_trade
# - bid
# - ask
# - bid_size
# - ask_size
# - good_bid
# - good_ask
# - good_bid_size
# - good_ask_size
# - day_spread
# - day_num_spread
# - day_low
# - day_high
# - last_trade
# - last_trade_volume
# - bid_high
# - ask_high
# - bid_low
# - ask_low
# - sided_bid_count
# - sided_bid_shares
# - sided_bid_notional
# - day_sided_bid_count
# - day_sided_bid_shares
# - day_sided_bid_notional
# - sided_ask_count
# - sided_ask_shares
# - sided_ask_notional
# - day_sided_ask_count
# - day_sided_ask_shares
# - day_sided_ask_notional
# - igid


def date_to_file_path(date: datetime.date, root_data_dir: str) -> str:
    ig_date = imvigigut.convert_to_ig_date(date)
    hdbg.dassert_isinstance(root_data_dir, str)
    path = os.path.join(root_data_dir, ig_date, "data.parquet")
    return path


def _convert_string_to_timestamp(
    df: pd.DataFrame, in_col_name: str, out_col_name: str, tz_zone: Optional[str]
) -> pd.DataFrame:
    """
    Add column `out_col_name` with timestamps in ET corresponding to df
    `in_col_name`.

    :param tz_zone: `None` means no conversion
    """
    hdbg.dassert_in(in_col_name, df.columns)
    srs = df[in_col_name]
    if not srs.empty:
        # with htimer.TimedScope(log_level, "fromtimestamp"):
        srs = srs.apply(datetime.datetime.fromtimestamp)
        # with htimer.TimedScope(log_level, "pd.to_datetime"):
        # This is slower than `pd.to_datetime()`.
        # srs = srs.apply(pd.to_datetime)
        srs = pd.to_datetime(srs, utc=True)
        # with htimer.TimedScope(log_level, "tz_convert"):
        if tz_zone:
            srs = srs.dt.tz_convert(tz_zone)
        df[out_col_name] = srs
    else:
        _LOG.warning("Column '%s' in df is empty", in_col_name)
    return df


def normalize_bar_data(
    df: pd.DataFrame,
    tz_zone: Optional[str],
) -> pd.DataFrame:
    """
    Process bar data coming from IG PQ files into a DataFrame suitable for
    DataFlow.

    The input data looks like:
    ```
         end_time ticker   asset_id  close
    0  1640613660   AAPL  17085    NaN
    1  1640613720   AAPL  17085    NaN
    2  1640613780   AAPL  17085    NaN
    ```

    The transformations that are applied are:
    - `start_time`, `end_time` are converted from epochs into ET-localized
      timestamps
    - data is indexed by `end_time` timestamp

    The output data looks like:
    ```
                              ticker   asset_id  close ...
    end_time
    2021-12-27 09:01:00-05:00   AAPL  17085    NaN
    2021-12-27 09:02:00-05:00   AAPL  17085    NaN
    2021-12-27 09:03:00-05:00   AAPL  17085    NaN
    ```
    """
    _LOG.debug("before normalize df=\n%s", hpandas.df_to_str(df.head(3)))
    # Add new TZ-localized datetime columns for research and readability.
    # log_level = logging.INFO
    # with htimer.TimedScope(log_level, "all"):
    for col_name in ["start_time", "end_time"]:
        if col_name in df.columns:
            # Not all the dfs have these columns, since it depends on what we
            # load from the Parquet file.
            df = _convert_string_to_timestamp(df, col_name, col_name, tz_zone)
    hdbg.dassert_in("end_time", df.columns)
    df.set_index("end_time", inplace=True, drop=True)
    _LOG.debug("after normalize df=\n%s", hpandas.df_to_str(df.head(3)))
    return df


# #############################################################################


@functools.lru_cache()
def get_available_dates(
    root_data_dir: str,
    aws_profile: str,
) -> List[datetime.date]:
    """
    Return list of all the available dates in the IG bar data.

    :return: sorted available dates
    """
    # > aws s3 ls \
    #   --profile sasm \
    #   s3://iglp-core-data/ds/ext/bars/taq/v1.0-prod/60
    # PRE 20031002/
    # PRE 20031003/
    # PRE 20031006/
    # ...
    s3fs_ = hs3.get_s3fs(aws_profile)
    _LOG.debug("root_data_dir=%s aws_profile=%s", root_data_dir, aws_profile)
    files = s3fs_.ls(root_data_dir)
    # Extract the basename which corresponds to the dir storing the data for a
    # given date.
    dates = map(os.path.basename, files)
    dates = [pd.Timestamp(date).date() for date in dates]
    dates = sorted(dates)
    _LOG.debug("Available dates=%s [%s, %s]", len(dates), min(dates), max(dates))
    return dates


# #############################################################################


def get_raw_bar_data_from_file(
    path: str,
    asset_ids: Optional[List[int]],
    asset_id_name: str,
    columns: Optional[List[str]],
    aws_profile: str,
    *,
    download_locally: bool = False,
) -> pd.DataFrame:
    """
    :param download_locally: force to download the file locally from S3 before
        reading it
    """
    _LOG.debug(hprint.to_str("path asset_ids asset_id_name columns"))
    # Compute the Parquet filter.
    if asset_ids is None:
        filters = None
    else:
        # Build the Parquet filter, which is an OR of AND constraints. In this
        # case the AND is a single equality constraint (see
        # https://stackoverflow.com/questions/56522977).
        filters = []
        for asset_id in asset_ids:
            filters.append([(asset_id_name, "=", asset_id)])
    # Load the data as a pd.DataFrame.
    # _LOG.debug("filters=%s", filters)
    s3fs_ = hs3.get_s3fs(aws_profile) if path.startswith("s3://") else None
    if (s3fs_ and download_locally) or aws_profile == "sasm":
        # For "sasm" we need to cache data locally to work around a
        # slowdown of accessing the data directly from S3, due to some format
        # change.
        # tmp_file_name = tempfile.NamedTemporaryFile().name
        tmp_file_name = "/tmp/" + "_".join(path.split("/")[-2:])
        _LOG.info("Downloading %s to %s", path, tmp_file_name)
        # For some reason downloading with s3fs is 3-5x slower than using the
        # command directly.
        # s3fs_.download(path, tmp_file_name)
        if hserver.is_ig_prod():
            # When running in production we let the Docker container decide
            # the AWS profile to use.
            opts = ""
        else:
            opts = f" --profile {aws_profile}"
        cmd = f"aws s3 cp{opts} {path} {tmp_file_name}"
        hsystem.system(cmd)
        path = tmp_file_name
        s3fs_ = None
    dataset = parquet.ParquetDataset(
        path,
        filesystem=s3fs_,
        filters=filters,
        use_legacy_dataset=False,
    )
    _LOG.debug("columns=%s", columns)
    table = dataset.read(columns=columns)
    df = table.to_pandas()
    if df is None:
        raise RuntimeError(f"Received empty data for path={path}")
    return df


# TODO(gp): Change the order of the params (asset_ids, date, columns) everywhere.
@pytest.mark.requires_aws 
@pytest.mark.requires_ck_infra
def get_raw_bar_data_for_date(
    date: datetime.date,
    root_data_dir: str,
    aws_profile: str,
    columns: Optional[List[str]],
    asset_id: Optional[List[int]],
    asset_id_name: str,
    abort_on_error: bool,
) -> pd.DataFrame:
    """
    Get data from the S3 backend for a single date, and multiple asset_id and
    columns.

    The data is stored in a by-date Parquet format.
    """
    _LOG.debug("# date=%s", date)
    # Prepare file path.
    # ig_date = vlieguti.convert_to_ig_date(date)
    # hdbg.dassert_isinstance(root_data_dir, str)
    # path = os.path.join(root_data_dir, ig_date, "data.parquet")
    path = date_to_file_path(date, root_data_dir)
    try:
        df = get_raw_bar_data_from_file(
            path, asset_id, asset_id_name, columns, aws_profile
        )
    except Exception as e:
        txt = []
        txt.append("date=%s" % date)
        txt.append("asset_id=%s" % str(asset_id))
        txt.append("columns=%s" % str(columns))
        txt.append("aws_profile=%s" % str(aws_profile))
        txt.append("exception=\n%s" % str(e))
        txt = "\n".join(txt)
        _LOG.error(txt)
        if abort_on_error:
            raise RuntimeError(txt)
        _LOG.error("Continuing...")
    return df


def get_bar_data_for_dates(
    asset_ids: Optional[List[int]],
    asset_id_name: str,
    dates: List[datetime.date],
    columns: Optional[List[str]],
    normalize: bool,
    tz_zone: Optional[str],
    abort_on_error: bool,
    root_data_dir: str,
    aws_profile: str,
    num_concurrent_requests: int,
) -> pd.DataFrame:
    """
    Get data for a set of dates and multiple asset_ids and columns.

    This function:
    - parallelizes the access through `_get_raw_bar_data_for_date()` to the S3 files
    - normalizes the data

    The returned data looks like:
    ```
                               close  volume   asset_id
    end_time
    2021-06-21 09:01:00-04:00    NaN       0  17085
    2021-06-21 09:01:00-04:00    NaN       0  15224
    2021-06-21 09:01:00-04:00    NaN       0  10971
    ```

    The IG "start_time", "end_time" columns are converted from int64's to
    timestamps with ET timezone.

    :param asset_ids: list of requested asset_ids
        - `None` for requesting all the asset_ids
    :param dates: the dates to access
    :param columns: the columns of data to access. `None` means the minimum
        subset of columns, i.e., "close", "volume", "asset_id"
    :param normalize: normalize the data if needed
    :param abort_on_error: whether to stop or not the computation if an error
        occur
    :param root_data_dir: the directory containing the data. `None` means the
        default location
    :param num_concurrent_requests: the number of parallel requests to S3
    :return: df with bar data
    """
    if asset_ids is not None:
        if isinstance(asset_ids[0], str):
            asset_ids = list(map(int, asset_ids))
        # Check that `asset_ids` are valid.
        hdbg.dassert_container_type(asset_ids, List, int)
        hdbg.dassert_no_duplicates(asset_ids)
        asset_ids = sorted(asset_ids)
    # Check the dates.
    hdbg.dassert_container_type(dates, List, datetime.date)
    hdbg.dassert_no_duplicates(dates)
    dates = sorted(dates)
    # Initialize columns.
    if columns is not None:
        hdbg.dassert_container_type(columns, List, str)
        # `end_time` is required since it's the index.
        hdbg.dassert_in("end_time", columns)
    #
    func = lambda date: get_raw_bar_data_for_date(
        date,
        root_data_dir,
        aws_profile,
        columns,
        asset_ids,
        asset_id_name,
        abort_on_error,
    )
    # TODO(gp): Use the code in `joblib_helpers` or copy/paste the version with the
    #  progress bar.
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    # Serial.
    # for date in tqdm_out(dates, desc="Retrieving TAQ data"):
    #     df = func(date)
    #     dfs.append(df)
    # Parallel.
    hdbg.dassert_lte(1, num_concurrent_requests)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=num_concurrent_requests
    ) as executor:
        dfs = list(
            tqdm(
                executor.map(func, dates),
                file=tqdm_out,
                total=len(dates),
                desc="Reading historical data from S3",
            )
        )
    # Different implementation.
    # dfs = []
    # with tqdm(file=tqdm_out, total=len(dates)) as pbar:
    #     with concurrent.futures.ThreadPoolExecutor(
    #       max_workers=num_concurrent_requests) as executor:
    #         futures = {executor.submit(func, arg): arg for arg in dates}
    #         _LOG.debug("done submitting")
    #         for future in concurrent.futures.as_completed(futures):
    #             df = future.result()
    #             dfs.append(df)
    #             pbar.update(1)
    # Concat all the data.
    with htimer.TimedScope(logging.INFO, "Process pd data"):
        df = pd.concat(dfs, axis=0)
        # Sort.
        sorting_keys = ["end_time", asset_id_name]
        hdbg.dassert_is_subset(sorting_keys, df.columns)
        df = df.sort_values(by=sorting_keys, ascending=[True] * len(sorting_keys))
        if normalize:
            _LOG.debug("Normalize bar data")
            df = normalize_bar_data(df, tz_zone)
            # Ensure that the retrieved data is included in [start_date, end_date].
            if not df.empty:
                hdbg.dassert_lte(min(dates), df.index.min().date())
                hdbg.dassert_lte(df.index.max().date(), max(dates))
    return df


def get_bar_data_for_date_interval(
    asset_ids: List[int],
    asset_id_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    columns: Optional[List[str]],
    normalize: bool,
    tz_zone: Optional[str],
    root_data_dir: str,
    aws_profile: str,
    *,
    abort_on_error: bool = True,
    num_concurrent_requests: int = 10,
) -> pd.DataFrame:
    """
    Return bar data for `asset_ids` in the date interval [`start_date`,
    `end_date`].
    """
    # Get the available dates in the data set.
    available_dates = get_available_dates(root_data_dir, aws_profile)
    # Filter in the given interval.
    dates = imvigigut.filter_dates(start_date, end_date, available_dates)
    # Retrieve data.
    df = get_bar_data_for_dates(
        asset_ids,
        asset_id_name,
        dates,
        columns,
        normalize,
        tz_zone,
        abort_on_error,
        root_data_dir,
        aws_profile,
        num_concurrent_requests,
    )
    return df


# #############################################################################
# Cached layer
# #############################################################################


# TODO(gp): -> def get_cached_bar_data_for_dates(
@hcache.cache(set_verbose_mode=True)
def get_bar_data(
    asset_ids: Optional[List[int]],
    asset_id_name: str,
    dates: List[datetime.date],
    columns: Optional[List[str]],
    root_data_dir: str,
    aws_profile: str,
    *,
    abort_on_error: bool = True,
    num_concurrent_requests: int = 10,
) -> pd.DataFrame:
    """
    Extract bar data for the requested `asset_id`s concatenating across
    `dates`.

    The returned data looks like:
    ```
                               close  volume   asset_id
    end_time
    2021-06-21 09:01:00-04:00    NaN       0  17085
    2021-06-21 09:01:00-04:00    NaN       0  15224
    2021-06-21 09:01:00-04:00    NaN       0  10971
    ```

    The IG "start_time", "end_time" columns are converted from int64's to
    timestamps with ET timezone.

    :param asset_ids: list of requested asset_ids
        - `None` for requesting all the asset_ids
    :param dates: the dates to access
    :param columns: the columns of data to access. `None` means the minimum
        subset of columns, i.e., "close", "volume", "asset_id"
    :param abort_on_error: whether to stop or not the computation if an error
        occur
    :param root_data_dir: the directory containing the data
    :return: df with bar data
    """
    normalize = True
    tz_zone = "America/New_York"
    return get_bar_data_for_dates(
        asset_ids,
        asset_id_name,
        dates,
        columns,
        normalize,
        tz_zone,
        abort_on_error,
        root_data_dir,
        aws_profile,
        num_concurrent_requests,
    )


# TODO(gp): Maybe cache this.
def get_cached_bar_data_for_date_interval(
    asset_ids: List[int],
    asset_id_name: str,
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    columns: Optional[List[str]],
    root_data_dir: str,
    aws_profile: str,
    *,
    # TODO(gp): -> normalize
    abort_on_error: bool = True,
    num_concurrent_requests: int = 10,
) -> pd.DataFrame:
    """
    Return bar data for `asset_ids` in the date interval [`start_date`,
    `end_date`].

    :param start_date, end_date: date to start / end or `None` for no limit
    """
    # Get the available dates in the data set.
    available_dates = get_available_dates(root_data_dir, aws_profile)
    # Filter in the given interval.
    dates = imvigigut.filter_dates(start_date, end_date, available_dates)
    # Retrieve data.
    df = get_bar_data(
        asset_ids,
        asset_id_name,
        dates,
        columns,
        root_data_dir,
        aws_profile,
        abort_on_error=abort_on_error,
        num_concurrent_requests=num_concurrent_requests,
    )
    return df


# #############################################################################
# Connection to MarketDataInterface
# #############################################################################


# TODO(gp): -> cached_historical_bars.py


def _prepare_get_bar_data_cache(cache_dir: str) -> None:
    """
    Prepare the cache.

    We need to pass the parameters through the functions since
    configuration of the cache needs to happen at execution time and not
    when the configuration is executed.
    """
    hdbg.dassert_is_not(cache_dir, None)
    # _LOG.warning("Using function-specific cache in '%s'", cache_dir)
    get_bar_data.set_function_cache_path(cache_dir)
    get_bar_data.enable_read_only(True)


def load_single_instrument_data(
    asset_id: int,
    asset_id_name: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    columns: Optional[List[str]],
    root_data_dir: str,
    aws_profile: str,
    *,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    if isinstance(start_datetime, datetime.datetime):
        start_date = start_datetime.date()
    else:
        hdbg.dassert_isinstance(start_datetime, datetime.date)
        start_date = start_datetime
    if isinstance(end_datetime, datetime.datetime):
        end_date = end_datetime.date()
    else:
        hdbg.dassert_isinstance(end_datetime, datetime.date)
        end_date = end_datetime
    if cache_dir is not None:
        _prepare_get_bar_data_cache(cache_dir)
    asset_ids = [asset_id]
    # TODO(gp): This needs to match how the cache was generated, until we
    #  implement the logic to ignore some parameters in the caching framework.
    num_concurrent_requests = 20
    df = get_cached_bar_data_for_date_interval(
        asset_ids,
        asset_id_name,
        start_date,
        end_date,
        columns,
        root_data_dir,
        aws_profile,
        num_concurrent_requests=num_concurrent_requests,
    )
    # _LOG.debug("price_stats=\n%s", compute_bar_data_stats(df, [asset_id]))
    return df


def _load_multiple_instrument_data(
    asset_ids: List[int],
    asset_id_name: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    columns: Optional[List[str]],
    root_data_dir: str,
    aws_profile: str,
    *,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load multiple columns of data for multiple instruments.

    :return: a dataframe with a datetime row index and two level multiindex
        columns
        - The top (outermost) level has attributes (e.g., close, volume)
        - The innermost level has the name identifier
    """
    if cache_dir is not None:
        _prepare_get_bar_data_cache(cache_dir)
    with htimer.TimedScope(logging.INFO, "Load multiple instrument data"):
        # use_parallel = True
        use_parallel = False
        if use_parallel:
            num_concurrent_requests = 5
            func = lambda asset_id: load_single_instrument_data(
                asset_id,
                asset_id_name,
                start_datetime,
                end_datetime,
                columns,
                root_data_dir,
                aws_profile,
                cache_dir=cache_dir,
            )
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_concurrent_requests
            ) as executor:
                dfs = list(executor.map(func, asset_ids))
            dfs = dict(zip(asset_ids, dfs))
        else:
            dfs = {}
            for asset_id in tqdm(asset_ids, "load_multiple_instrument_data"):
                data = load_single_instrument_data(
                    asset_id,
                    asset_id_name,
                    start_datetime,
                    end_datetime,
                    columns,
                    root_data_dir,
                    aws_profile,
                    cache_dir=cache_dir,
                )
                if data.empty:
                    _LOG.warning("No data available for asset_id=%s", asset_id)
                    continue
                dfs[asset_id] = data
    with htimer.TimedScope(logging.INFO, "Concat"):
        # Reorganize the data into the desired format.
        df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    with htimer.TimedScope(logging.INFO, "Swap"):
        df = df.swaplevel(i=0, j=1, axis=1)
    with htimer.TimedScope(logging.INFO, "sort_index"):
        df.sort_index(axis=1, level=0, inplace=True)
    return df


@hcache.cache(set_verbose_mode=True)
def load_multiple_instrument_data(
    asset_ids: List[int],
    asset_id_name: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    columns: Optional[List[str]],
    root_data_dir: str,
    aws_profile: str,
    *,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    return _load_multiple_instrument_data(
        asset_ids,
        asset_id_name,
        start_datetime,
        end_datetime,
        columns,
        root_data_dir,
        aws_profile,
        cache_dir=cache_dir,
    )


# #############################################################################


def clean_bars(df: pd.DataFrame, thr: float = 0.001) -> pd.DataFrame:
    """
    Non-causal outlier removal.

    Not to be used in production.
    """
    df = df.copy()
    for column in ["good_ask", "good_bid", "close"]:
        lower_bound = df[column].quantile(thr)
        upper_bound = df[column].quantile(1.0 - thr)
        mask = (df[column] <= lower_bound) | (df[column] >= upper_bound)
        df[mask] = np.nan
        _LOG.info(
            "column=%s -> removed=%s",
            column,
            hprint.perc(mask.sum(), df.shape[0]),
        )
    return df


def compute_bar_data_stats(
    df: pd.DataFrame,
    asset_ids: Optional[List[int]],
    asset_id_name: str,
) -> str:
    """
    Compute stats about bar data.
    """
    txt = []
    if df.empty:
        txt = str(df)
        return txt
    #
    txt.append("min index=%s" % min(df.index))
    txt.append("max index=%s" % max(df.index))
    txt.append("num unique index=%s" % len(df.index.unique()))
    txt.append("df.shape=%s" % str(df.shape))
    txt.append("asset_ids=%s" % str(asset_ids))
    found_asset_ids = df[asset_id_name].unique()
    txt.append("found asset_ids=%d" % len(found_asset_ids))
    #
    if asset_ids is not None:
        txt.append("requested asset_ids=%d" % len(asset_ids))
        # Check that the returned asset_ids are included in the requested ones.
        hdbg.dassert_is_subset(found_asset_ids, asset_ids)
        # Report asset_ids that are without any data.
        asset_ids_without_data = sorted(
            list(set(asset_ids) - set(found_asset_ids))
        )
        if asset_ids_without_data:
            msg = "Found %s asset_ids without data: %s" % (
                hprint.perc(len(asset_ids_without_data), len(asset_ids)),
                ",".join(map(str, asset_ids_without_data)),
            )
            _LOG.warning(msg)
            txt.append(msg)
    return "\n".join(txt)
