#!/usr/bin/env python
"""
Convert a directory storing Parquet files organized by dates into a Parquet
dataset organized by assets.

A Parquet file organized by dates looks like:
```
src_dir/
    date1/
        data.parquet
    date2/
        data.parquet
```

A Parquet file organized by assets looks like:
```
dst_dir/
    year1/
        month1/
            day1/
                asset1/
                    data.parquet
                asset2/
                    data.parquet
...
    year2/
        month2/
            day2/
                asset1/
                    data.parquet
                asset2/
                    data.parquet
```

# Example:
> transform_pq_by_date_to_by_asset.py \
    --src_dir im_v2/common/data/transform/test_data_by_date \
    --dst_dir im_v2/common/data/transform/test_data_by_asset \
    --num_threads 2

# To process Parquet data for LimeTask317:
> im_v2/common/data/transform/transform_pq_by_date_to_by_asset.py \
    --src_dir 's3://<ck-data>/unit_test/parquet/' \
    --dst_dir 's3://<ck-data>/unit_test/parquet/test_out/' \
    --no_incremental --force \
    --num_threads serial \
    --prepare_tasks_func_name lime317_prepare_tasks \
    --execute_task_func_name lime317_execute_task \
    --aws_profile 'ck'
    -v DEBUG
"""

import argparse
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from tqdm.autonotebook import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hjoblib as hjoblib
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hs3 as hs3

_LOG = logging.getLogger(__name__)


# Since different Parquet files require different transformations, we package all
# the specifics in custom functions to prepare the tasks and do perform the tasks
# See example for LimeTask317.


# #############################################################################
# LimeTask317
# #############################################################################

# The input Parquet files are organized by-date:
# ```
# src_dir
#   /20220110
#       /data.parquet
#   /20220111
#       /data.parquet
#   /20220112
#       /data.parquet
#   ...
# ```
#
# Each Parquet file looks like:
# ```
# shape=(5500357, 50)
# df.memory_usage=2.0 GB
#    vendor_date interval  start_time    end_time asset_id ticker open  close ...
# 0  2022-01-10        60  1641823200  1641823260      123      A  NaN    NaN
# 1  2022-01-10        60  1641823200  1641823260      234     AA  NaN    NaN
# 2  2022-01-10        60  1641823200  1641823260      345    AAA  NaN    NaN
# ...
# ```
#
# Our use case is to read:
# - only a subset of assets (e.g., a set of fixed asset universes)
# - a subset of the period (e.g., mostly 5-10 years of consecutive data)

# The original by-date organization of the data:
# - allows to read a subset of period effectively
# - is ineffective at reading a (fixed) subset of assets, since the assets are
#   aligned along rows instead of columns which is the direction that Parquet
#   subsets the data.

# A solution is to pre-process the data and organize it by-asset so that we can
# read the fixed universe efficiently.
# The problem is that the amount of data to process is very large (in order of
# 4 TBs) so we can't read all the data at once, reorganize it, and save it.

# Instead we can use the hive partitioning of Parquet data.
# We want to create Parquet partition aggregating consecutive days so that:
# - Each partition should be computed by a single thread fitting the data in memory
# - We can use 7-30 days so that each executor needs ~ 2 * 5 = 10GB
# Each thread:
# - Runs in parallel
# - Saves the data in the same directories but in different partitions


def lime317_prepare_tasks(
    src_file_names: List[str],
    asset_ids: List[int],
    asset_id_col_name: str,
    columns: Optional[List[str]],
    read_parquet_data_func: Callable,
    chunk_mode: str,
    args_num_threads: str,
    dst_dir: str,
) -> List[hjoblib.Task]:
    """
    Each task processes a consecutive chunk of data (e.g., week or month).

    :param src_file_names: list of all Parquet files to process, with the name
        encoding the date
    :param asset_ids: assets to process
    :param columns: columns to process. `None` means all
    :param chunk_mode: how to aggregate data, e.g., by week or by month
    :param args_num_threads: string from command line representing how many threads
        to employ
    :param dst_dir: directory where to save the data
    :return: list of joblib tasks
    """
    hdbg.dassert_container_type(src_file_names, list, str)
    num_executing_threads = hjoblib.get_num_executing_threads(args_num_threads)
    _LOG.info(
        "Number of executing threads=%s (%s)",
        num_executing_threads,
        args_num_threads,
    )
    # `src_file_names` looks like:
    #  ['./tmp.s3/20220103/data.parquet',
    #   './tmp.s3/20220104/data.parquet',
    #   './tmp.s3/20220110/data.parquet',
    #   './tmp.s3/20220111/data.parquet']
    # Build a map from key (e.g., `(week, year)` or `(month, year)`) to the list of
    # dates corresponding to that period of time.
    key_to_dates: Dict[Tuple[str, ...], List[str]] = {}
    for src_file_name in tqdm(src_file_names):
        # Extract "20220111" from "./tmp.s3/20220111/data.parquet".
        suffix = "/data.parquet"
        hdbg.dassert(
            src_file_name.endswith(suffix),
            "Invalid file_name='%s'",
            src_file_name,
        )
        path = src_file_name[: -len(suffix)]
        # path = './tmp.s3/20220111'
        dir_name = os.path.basename(path)
        # dir_name = '20220111'
        _LOG.debug(hprint.to_str("src_file_name path dir_name"))
        date = pd.Timestamp(dir_name)
        # Build the (week, year) key.
        if chunk_mode == "by_year_week":
            week_number = date.strftime("%U")
            key = (date.year, week_number)
        elif chunk_mode == "by_year_month":
            key = (date.year, date.month)
        else:
            raise ValueError("Invalid chunk_mode='%s'" % chunk_mode)
        _LOG.debug(hprint.to_str("key"))
        # Insert in the map.
        if key not in key_to_dates:
            key_to_dates[key] = []
        key_to_dates[key].append(src_file_name)
    # Sort by dates.
    _LOG.debug(hprint.to_str("key_to_dates"))
    filenames_for_tasks = [key_to_dates[k] for k in sorted(key_to_dates.keys())]
    # Each element of `filenames_for_tasks` represents the dates to be processed by
    # a single task.
    # filenames_for_tasks=[
    #   ['./tmp.s3/20220103/data.parquet', './tmp.s3/20220104/data.parquet'],
    #   ['./tmp.s3/20220110/data.parquet', './tmp.s3/20220111/data.parquet']]
    _LOG.debug(hprint.to_str("filenames_for_tasks"))
    # Build a task for each list of tasks.
    tasks = []
    for filenames in filenames_for_tasks:
        # Build the `Task`, i.e., the parameters for the function call below:
        #   lime317_execute_task(
        #       src_file_names: List[str],
        #       asset_ids: List[int],
        #       read_parquet_data_func: Callable,
        #   ...
        filenames = sorted(filenames)
        task: hjoblib.Task = (
            # args.
            (
                filenames,
                asset_ids,
                asset_id_col_name,
                columns,
                read_parquet_data_func,
                chunk_mode,
                dst_dir,
            ),
            # kwargs.
            {},
        )
        tasks.append(task)
    # # Split the chunks by thread.
    # chunked_dates_per_thread = hjoblib.split_list_in_tasks(
    #     dates_tasks,
    #     num_threads,
    #     keep_order=True,
    # )
    # _LOG.debug(hprint.to_str("chunked_dates_per_thread"))
    # _LOG.info("Prepared %s tasks", len(chunked_dates_per_thread))
    return tasks


def lime317_execute_task(
    src_file_names: List[str],
    asset_ids: List[int],
    asset_id_col_name: str,
    columns: Optional[List[str]],
    read_parquet_data_func: Callable,
    chunk_mode: str,
    dst_dir: str,
    incremental: bool,
    num_attempts: int,
) -> None:
    """
    Process a task by:

    - transforming df (e.g., converting epoch "start_time" into a timestamp)
    - merging multiple Parquet files corresponding to a date interval
    - writing it into `dst_dir` (partitioning by assets using Parquet datasets)

    :param src_file_names: a list of files to merge together
    """
    # This function only supports non-incremental mode and no re-try.
    hdbg.dassert(not incremental)
    hdbg.dassert_eq(num_attempts, 1)
    # Process the list of files.
    hdbg.dassert_container_type(src_file_names, list, str)
    dfs = []
    for src_file_name in sorted(src_file_names):
        # Read Parquet df.
        df = read_parquet_data_func(src_file_name, asset_ids, columns)
        # Append.
        dfs.append(df)
    # Concat.
    df = pd.concat(dfs, axis=0)
    if chunk_mode == "by_year_week":
        # Add year and week partition columns.
        df, partition_columns = hparque.add_date_partition_columns(
            df, "by_year_week"
        )
        # Check that all data is for the same year and week.
        years = df["year"].unique()
        hdbg.dassert_eq(len(years), 1, "years=%s", str(years))
        weeks = df["weekofyear"].unique()
        hdbg.dassert_eq(len(weeks), 1, "weeks=%s", str(weeks))
    elif chunk_mode == "by_year_month":
        # Add year and month partition columns.
        df, partition_columns = hparque.add_date_partition_columns(
            df, "by_year_month"
        )
        # Check that all data is for the same year and month.
        years = df["year"].unique()
        hdbg.dassert_eq(len(years), 1, "years=%s", str(years))
        months = df["month"].unique()
        hdbg.dassert_eq(len(months), 1, "months=%s", str(months))
    else:
        raise ValueError("Invalid chunk_mode='%s'" % chunk_mode)
    _LOG.debug("after df=\n%s", hpandas.df_to_str(df.head(3)))
    # Partition also over the asset column.
    partition_columns.insert(0, asset_id_col_name)
    # Write.
    hparque.to_partitioned_parquet(df, partition_columns, dst_dir)


# #############################################################################
# Generic processing of files.
# #############################################################################


def _prepare_tasks(src_file_names: List[str], args: Any) -> List[hjoblib.Task]:
    # Build the src -> dst file mapping.
    src_dst_file_name_map = []
    for src_file_name in src_file_names:
        # ./tmp.s3/20220111/data.parquet
        # ->
        # ./tmp.s3_out/data.parquet
        dst_file_name = args.dst_dir
        _LOG.debug("%s -> %s", src_file_name, dst_file_name)
        src_dst_file_name_map.append((src_file_name, dst_file_name))
    # Remove the tasks already processed, if in incremental mode.
    incremental = not args.no_incremental
    if incremental:
        src_dst_file_name_map = hjoblib.apply_incremental_mode(
            src_dst_file_name_map
        )
    # Prepare the tasks from the src -> dst mapping.
    num_threads = hjoblib.get_num_executing_threads(args.num_threads)
    _LOG.info(
        "Number of executing threads=%s (%s)", num_threads, args.num_threads
    )
    chunked_srd_dst_file_name_map = hjoblib.split_list_in_tasks(
        src_dst_file_name_map,
        num_threads,
        keep_order=not args.no_keep_order,
        num_elems_per_task=args.num_func_per_task,
    )
    _LOG.info("Prepared %s tasks", len(chunked_srd_dst_file_name_map))
    tasks = []
    for src_dst_file_names in chunked_srd_dst_file_name_map:
        _LOG.debug(hprint.to_str("src_dst_file_names"))
        # The interface for the function called is:
        # def _process_chunk(src_dst_file_names: List[Tuple[str, str]])
        # TODO(Nikola): Reintroduce _process_chunk?
        task: hjoblib.Task = (
            # args.
            (src_dst_file_names,),
            # kwargs.
            {},
        )
        tasks.append(task)
    return tasks


# #############################################################################


def _run(args: argparse.Namespace) -> None:
    incremental = not args.no_incremental
    # Prepare the destination dir.
    if args.aws_profile:
        # TODO(Nikola): CMTask1439 Add S3 support to hparser's `create_incremental_dir`.
        raise NotImplementedError("Incremental on S3 is not implemented!")
    else:
        hparser.create_incremental_dir(args.dst_dir, args)
    # Get the input files to process.
    pattern = "*.parquet"
    only_files = True
    use_relative_paths = False
    src_file_names = hs3.listdir(
        args.src_dir,
        pattern,
        only_files,
        use_relative_paths,
        aws_profile=args.aws_profile,
    )
    hdbg.dassert_lte(1, len(src_file_names))
    _LOG.info("Found %s Parquet files in '%s'", len(src_file_names), args.src_dir)
    # Prepare the tasks.
    func = hintros.get_function_from_string(args.prepare_tasks_func_name)
    hdbg.dassert_isinstance(func, Callable)
    tasks = func(src_file_names, args)
    # Prepare the workload.
    func = hintros.get_function_from_string(args.execute_task_func_name)
    hdbg.dassert_isinstance(func, Callable)
    func_name = func.__name__
    workload = (func, func_name, tasks)
    hjoblib.validate_workload(workload)
    # Prepare the log file.
    timestamp = hdateti.get_current_timestamp_as_string("ET")
    log_dir = os.getcwd()
    log_file = os.path.join(log_dir, f"log.{timestamp}.txt")
    _LOG.info("log_file='%s'", log_file)
    # Execute the workload using command lines.
    abort_on_error = not args.skip_on_error
    hjoblib.parallel_execute(
        workload,
        args.dry_run,
        args.num_threads,
        incremental,
        abort_on_error,
        args.num_attempts,
        log_file,
    )


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_dir",
        action="store",
        type=str,
        required=True,
        help="Source directory where original Parquet files are stored",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        type=str,
        required=True,
        help="Destination directory where transformed Parquet files will be stored",
    )
    parser.add_argument(
        "--aws_profile",
        action="store",
        required=True,
        type=str,
        help="The AWS profile to use for `.aws/credentials` or for env vars",
    )
    parser = hparser.add_parallel_processing_arg(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args)


if __name__ == "__main__":
    _main(_parse())
