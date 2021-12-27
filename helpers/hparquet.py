"""
Import as:

import helpers.hparquet as hparque
"""

import logging
import os
from typing import Any, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import helpers.dbg as hdbg
import helpers.introspection as hintros
import helpers.io_ as hio
import helpers.timer as htimer

_LOG = logging.getLogger(__name__)


def to_parquet(
    df: pd.DataFrame,
    file_name: str,
    *,
    log_level: int = logging.DEBUG,
) -> None:
    """
    Save a dataframe as Parquet.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_isinstance(file_name, str)
    hdbg.dassert_file_extension(file_name, ["pq", "parquet"])
    #
    hio.create_enclosing_dir(file_name, incremental=True)
    _LOG.debug("df.shape=%s", str(df.shape))
    mem = df.memory_usage().sum()
    _LOG.debug("df.memory_usage=%s", hintros.format_size(mem))
    # Save data.
    with htimer.TimedScope(logging.DEBUG, "To parquet '%s'" % file_name) as ts:
        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_name)
    # Report stats.
    file_size = hintros.format_size(os.path.getsize(file_name))
    _LOG.log(
        log_level,
        "Saved '%s' (size=%s, time=%.1fs)",
        file_name,
        file_size,
        ts.elapsed_time,
    )


# TODO(gp): What's the difference with read_pq? Maybe we use pandas there,
# while here we use PQ directly with Dataset.
def from_parquet(
    file_name: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Any]] = None,
    *,
    log_level: int = logging.DEBUG,
) -> pd.DataFrame:
    """
    Load a dataframe from a Parquet file.
    """
    hdbg.dassert_isinstance(file_name, str)
    hdbg.dassert_file_extension(file_name, ["pq", "parquet"])
    # Load data.
    with htimer.TimedScope(logging.DEBUG, "From parquet '%s'" % file_name) as ts:
        filesystem = None
        dataset = pq.ParquetDataset(
            file_name,
            filesystem=filesystem,
            filters=filters,
            use_legacy_dataset=False,
        )
        # To read also the index we need to use `read_pandas()`, instead of `read_table()`.
        # See https://arrow.apache.org/docs/python/parquet.html#reading-and-writing-single-files.
        table = dataset.read_pandas(columns=columns)
        df = table.to_pandas()
    # Report stats.
    file_size = hintros.format_size(os.path.getsize(file_name))
    _LOG.log(
        log_level,
        "Loaded '%s' (size=%s, time=%.1fs)",
        file_name,
        file_size,
        ts.elapsed_time,
    )
    # Report stats about the df.
    _LOG.debug("df.shape=%s", str(df.shape))
    mem = df.memory_usage().sum()
    _LOG.debug("df.memory_usage=%s", hintros.format_size(mem))
    return df


# TODO(Nikola): Remove in favor of transform utils module.
def partition_dataset(
    df: pd.DataFrame, partition_cols: List[str], dst_dir: str
) -> None:
    """
    Partition given dataframe indexed on datetime and save as Parquet dataset.

    In case of date partition, file layout format looks like:
    ```
    dst_dir/
        date=20211230/
            data.parquet
        date=20211231/
            data.parquet
        date=20220101/
            data.parquet
    ```

    :param df: dataframe with datetime index
    :param partition_cols: partition columns, e.g. ['asset']
    :param dst_dir: location of partitioned dataset
    """
    hdbg.dassert_is_subset(partition_cols, df.columns)
    with htimer.TimedScope(logging.DEBUG, "Save data"):
        table = pa.Table.from_pandas(df)
        pq.write_to_dataset(
            table,
            dst_dir,
            partition_cols=partition_cols,
            partition_filename_cb=lambda x: "data.parquet",
        )


# TODO(Nikola): Remove in favor of transform utils module.
def add_date_partition_cols(
    df: pd.DataFrame, partition_mode: str = "no_partition"
) -> pd.DataFrame:
    """
    Add partition columns like year, month, day from datetime index.
    "no_partition" means partitioning by entire date, e.g. "20211201".

    :param df: original dataframe
    :param partition_mode: date unit to partition, e.g. 'year'
    :return: DataFrame with date partition cols added
    """
    date_col_names = ["year", "month", "day"]
    msg = f"Invalid partition mode `{partition_mode}`!"
    hdbg.dassert_in(partition_mode, [*date_col_names, "no_partition"], msg)
    with htimer.TimedScope(logging.DEBUG, "Create partition indices"):
        if partition_mode != "no_partition":
            for name in date_col_names:
                df[name] = getattr(df.index, name)
                if name == partition_mode:
                    break
        else:
            df["date"] = df.index.strftime("%Y%m%d")
    return df
