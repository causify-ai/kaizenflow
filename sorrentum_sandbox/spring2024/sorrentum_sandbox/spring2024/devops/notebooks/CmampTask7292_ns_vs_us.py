# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# TODO(Vlad): TODO(Samarth): convert the notebook into unit tests CmTask7331

# %% [markdown]
# The notebook demonstrates current behavior of various parquet functions with respect to
# different time units.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
from typing import List

import pandas as pd
import pyarrow

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hparquet as hparque
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)
_LOG = logging.getLogger(__name__)
_LOG.info("%s", henv.get_system_signature()[0])
hprint.config_notebook()

# %%
pyarrow.__version__

# %% [markdown]
# # Test data

# %%
timestamp_us = pd.Timestamp("2022-01-01 00:00:00.123456", tz="America/New_York")
index = [timestamp_us for _ in range(6)]
initial_df = pd.DataFrame(
    {
        "n_legs": [2, 2, 4, 4, 5, 100],
        "animal": [
            "Flamingo",
            "Parrot",
            "Dog",
            "Horse",
            "Brittle stars",
            "Centipede",
        ],
        "year": [2001, 2002, 2001, 2003, 2003, 2001],
    },
    index=index,
)
initial_df

# %%
initial_df.index.unit


# %%
def test_write_and_read_partition_parquet_with_unit(
    initial_df: pd.DataFrame,
    partition_columns: List[str],
    dst_dir: str,
    unit: str,
    *,
    clean_up: bool = False,
) -> None:
    """
    Write the provided DataFrame to partitioned Parquet files and read it back,
    verifying the retention of time unit information in the index.

    :param initial_df: dataframe to write
    :param dst_dir: root folder to write partition parquet
    :param partition_columns: partition columns to write
    :param unit: initial time unit in the index
    :param clean_up: delete parquet folder at the end
    """
    current_df = initial_df.copy()
    _LOG.info("Initial DF unit: %s", current_df.index.unit)
    _LOG.info("Converting DF unit from ns to: %s", unit)
    current_df.index = current_df.index.as_unit(unit)
    _LOG.info(
        "DF Unit before writing to parquet files: %s", current_df.index.unit
    )
    # The `to_partitioned_parquet` saves the given dataframe as Parquet
    # files partitioned along the given columns.
    hparque.to_partitioned_parquet(current_df, partition_columns, dst_dir)
    # Generates the DF from parquet files in the `dst_dir`.
    df = hparque.from_parquet(dst_dir)
    print("\n")
    print("DF from parquet files")
    print(df)
    _LOG.info("DF Unit after reading from parquet files: %s", df.index.unit)
    if clean_up:
        hio.delete_dir(dst_dir)
    print("\n")


# %%
def test_write_and_read_parquet_file_with_unit(
    initial_df: pd.DataFrame, file_name: str, unit: str, *, clean_up: bool = False
) -> None:
    """
    Write the provided DataFrame to Parquet file and read it back, verifying
    the retention of time unit information in the index.

    :param initial_df: dataframe to write
    :param file_name: destination parquet file name
    :param unit: initial time unit in the index
    :param clean_up: delete parquet file at the end
    """
    current_df = initial_df.copy()
    _LOG.info("Initial DF unit: %s", current_df.index.unit)
    _LOG.info("Converting DF unit from ns to: %s", unit)
    current_df.index = current_df.index.as_unit(unit)
    _LOG.info(
        "Unit before writing to single parquet file: %s", current_df.index.unit
    )
    # The `to_parquet` function writes a DF to a single parquet file without
    # any partition.
    hparque.to_parquet(current_df, file_name)
    df = hparque.from_parquet(file_name)
    print("\n")
    print("DF from single parquet file")
    print(df)
    _LOG.info("DF Unit after reading from parquet file: %s", df.index.unit)
    if clean_up:
        hio.delete_file(file_name)
    print("\n")


# %%
# Columns to partition on.
partition_columns = ["year", "n_legs"]
# Testing on different time units.
test_units = ["ms", "us", "ns"]

# %% [markdown]
# # Overview
#
# The upcoming 3 sections shows the working of parquet functions with different condition described in each section.
# The behavior is different based on if we are writing/reading a partitioned parquet files from root dir or just a single parquet file.

# %% [markdown]
# # Current behavior
#
#
# This includes what we have in the current master

# %% [markdown]
# ## `hparque.to_partitioned_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:885
# ```python
#         pq.write_to_dataset(
#             table,
#             dst_dir,
#             partition_cols=partition_columns,
#             # partition_filename_cb=partition_filename,
#             filesystem=filesystem,
#         )
# ```

# %% [markdown]
# ## `hparque.to_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:266
#
# The dictionary introduced by GP
#
# ```python
#         # This is needed to handle:
#         # ```
#         # pyarrow.lib.ArrowInvalid: Casting from timestamp[ns, tz=America/New_York]
#         #   to timestamp[us] would lose data: 1663595160000000030
#         # ```
#         parquet_args = {
#             "coerce_timestamps": "us",
#             "allow_truncated_timestamps": True,
#         }
#         pq.write_table(table, file_name, filesystem=filesystem, **parquet_args)
# ```

# %% [markdown]
# ## `hparque.from_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:172
#
# The hacks we applied in the version 14 upgrade
#
# ```python
#             # Convert timestamp columns to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             df = table.to_pandas(coerce_temporal_nanoseconds=True)
#             # Convert timestamp indices to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             if isinstance(df.index, pd.DatetimeIndex):
#                 df.index = df.index.as_unit("ns")
# ```

# %%
dst_dir = "tmp.pyarrow_current"
_LOG.info("\n" + hprint.frame("Testing partition write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where DF is partitioned in multiple PQ files.
    # Under the hood we are calling `to_partioned_parquet` function
    # as we use `partition_columns`.
    #
    # While writing to parquet, the unit is preserved.
    # While reading from the parquet, the unit is always `ns`.
    test_write_and_read_partition_parquet_with_unit(
        initial_df, partition_columns, dst_dir, unit, clean_up=True
    )

# %%
file_name = "tmp_current.parquet"
_LOG.info("\n" + hprint.frame("Testing file write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where a Df is converted to single PQ file without any
    # partition. Under the hood, we call `to_parquet` function which has
    # GP's dictionary.
    #
    # While writing to parquet, the unit is always `us` because of GP's  dictionary.
    # While reading from parquet, the unit is always ns.
    test_write_and_read_parquet_file_with_unit(
        initial_df, file_name, unit, clean_up=True
    )

# %% [markdown]
#
# # Remove hacks from the `hparque.from_parquet()`
#
# This includes removing ns v/s us hacks but keeping the GP's dictionary

# %% [markdown]
# ## `hparque.to_partitioned_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:885
# ```python
#         pq.write_to_dataset(
#             table,
#             dst_dir,
#             partition_cols=partition_columns,
#             # partition_filename_cb=partition_filename,
#             filesystem=filesystem,
#         )
# ```

# %% [markdown]
# ## `hparque.to_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:266
# ```python
#         # This is needed to handle:
#         # ```
#         # pyarrow.lib.ArrowInvalid: Casting from timestamp[ns, tz=America/New_York]
#         #   to timestamp[us] would lose data: 1663595160000000030
#         # ```
#         parquet_args = {
#             "coerce_timestamps": "us",
#             "allow_truncated_timestamps": True,
#         }
#         pq.write_table(table, file_name, filesystem=filesystem, **parquet_args)
# ```

# %% [markdown]
# ## `hparque.from_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:172
# ```python
#             table = dataset.read_pandas(columns=columns)
#             # Convert timestamp columns to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             # df = table.to_pandas(coerce_temporal_nanoseconds=True)
#             df = table.to_pandas()
#             # Convert timestamp indices to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             # if isinstance(df.index, pd.DatetimeIndex):
#                 # df.index = df.index.as_unit("ns")
# ```

# %%
dst_dir = "tmp.pyarrow_current"
_LOG.info("\n" + hprint.frame("Testing partition write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where DF is partitioned in multiple PQ files.
    # Under the hood we are calling `to_partioned_parquet` function
    # as we use `partition_columns`.
    #
    # While writing to parquet, the unit is preserved.
    # While reading from the parquet, the unit is preserved.
    test_write_and_read_partition_parquet_with_unit(
        initial_df, partition_columns, dst_dir, unit, clean_up=True
    )

# %%
file_name = "tmp_current.parquet"
_LOG.info("\n" + hprint.frame("Testing file write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where a Df is converted to single PQ file without any
    # partition. Under the hood, we call `to_parquet` function which has
    # GP's dictionary.
    #
    # While writing to parquet, the unit is always `us` because of GP's  dictionary.
    # While reading from parquet, the unit is preserved. In this case it will be `us` only.
    test_write_and_read_parquet_file_with_unit(
        initial_df, file_name, unit, clean_up=True
    )

# %% [markdown]
# # Remove both hacks
#
#
# This includes removing GP's dictionary and ns v/s us hacks introduced in the verison 14 upgrade

# %% [markdown]
# ## `hparque.to_partitioned_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:885
# ```python
#         pq.write_to_dataset(
#             table,
#             dst_dir,
#             partition_cols=partition_columns,
#             # partition_filename_cb=partition_filename,
#             filesystem=filesystem,
#         )
# ```

# %% [markdown]
# ## `hparque.to_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:266
# ```python
#         table = pa.Table.from_pandas(df)
#         # This is needed to handle:
#         # ```
#         # pyarrow.lib.ArrowInvalid: Casting from timestamp[ns, tz=America/New_York]
#         #   to timestamp[us] would lose data: 1663595160000000030
#         # ```
#         # parquet_args = {
#         #     "coerce_timestamps": "us",
#         #     "allow_truncated_timestamps": True,
#         # }
#         pq.write_table(table, file_name, filesystem=filesystem)
#         # pq.write_table(table, file_name, filesystem=filesystem, **parquet_args)
#
# ```

# %% [markdown]
# ## `hparque.from_parquet()`

# %% [markdown]
# amp/helpers/hparquet.py:172
# ```python
#             table = dataset.read_pandas(columns=columns)
#             # Convert timestamp columns to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             # df = table.to_pandas(coerce_temporal_nanoseconds=True)
#             df = table.to_pandas()
#             # Convert timestamp indices to `ns` resolution to keep the old
#             # behaviour with pyarrow=10.0.0 as opposed to pyarrow>=14.0.0
#             # which preserves the returned resolution.
#             # See CmTask7097 for details. https://github.com/cryptokaizen/cmamp/issues/7097
#             # if isinstance(df.index, pd.DatetimeIndex):
#                 # df.index = df.index.as_unit("ns")
# ```

# %%
dst_dir = "tmp.pyarrow_current"
_LOG.info("\n" + hprint.frame("Testing partition write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where DF is partitioned in multiple PQ files.
    # Under the hood we are calling `to_partioned_parquet` function
    # as we use `partition_columns`.
    #
    # While writing to parquet, the unit is preserved.
    # While reading from the parquet, the unit is preserved.
    test_write_and_read_partition_parquet_with_unit(
        initial_df, partition_columns, dst_dir, unit, clean_up=True
    )

# %%
file_name = "tmp_current.parquet"
_LOG.info("\n" + hprint.frame("Testing file write and read"))
for unit in test_units:
    _LOG.info("\n" + hprint.frame(f"Unit: {unit}"))
    # The case where a Df is converted to single PQ file without any
    # partition. Under the hood, we call `to_parquet` function which do not have
    # GP's dictionary.
    #
    # While writing to parquet, the unit is preserved.
    # While reading from the parquet, the unit is preserved.
    test_write_and_read_parquet_file_with_unit(
        initial_df, file_name, unit, clean_up=True
    )
