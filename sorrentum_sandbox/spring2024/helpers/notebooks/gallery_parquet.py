# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# Show Parquet / Pyarrow API.

# %% [markdown]
# ## Imports

# %%
import logging
import os
import random

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

import helpers.hdbg as hdbg
import helpers.hio as hio

hdbg.init_logger(verbosity=logging.INFO)
_LOG = logging.getLogger(__name__)


# %%
def get_df() -> pd.DataFrame:
    """
    Create pandas random data, like:

    ```
                idx instr  val1  val2
    2000-01-01    0     A    99    30
    2000-01-02    0     A    54    46
    2000-01-03    0     A    85    86
    ```
    """
    instruments = "A B C D E".split()
    "id stock val1 val2".split()
    df_idx = pd.date_range(
        pd.Timestamp("2000-01-01"), pd.Timestamp("2000-01-15"), freq="1D"
    )
    # print(df_idx)
    random.seed(1000)

    df = []
    for idx, inst in enumerate(instruments):
        df_tmp = pd.DataFrame(
            {
                "idx": idx,
                "instr": inst,
                "val1": [random.randint(0, 100) for k in range(len(df_idx))],
                "val2": [random.randint(0, 100) for k in range(len(df_idx))],
            },
            index=df_idx,
        )
        # print(df_tmp)
        df.append(df_tmp)
    df = pd.concat(df)
    return df


# %%
def df_to_str(df: pd.DataFrame) -> str:
    txt = ""
    txt += "# df=\n%s" % df.head(3)
    txt += "\n# df.shape=\n%s" % str(df.shape)
    txt += "\n# df.dtypes=\n%s" % str(df.dtypes)
    return txt


# %% [markdown]
# # Save and load all data in one file

# %%
df = get_df()
# print(df.head())
print(df_to_str(df))

# %%
table = pa.Table.from_pandas(df)

print("table=\n%s" % table)

# %%
# Save.
file_name = "df_in_one_file.pq"
pq.write_table(table, file_name)

# %%
# Load.
df2 = pq.read_table(file_name)
print(df2)

df2 = df2.to_pandas()
print(df_to_str(df2))

# %% [markdown]
# ## Read a subset of columns

# %%
df2 = pq.read_table(file_name, columns=["idx", "val1"])
print(df2)

df2 = df2.to_pandas()
print(df_to_str(df2))

# %% [markdown]
# ## Partitioned dataset
#
# from https://arrow.apache.org/docs/python/dataset.html#reading-partitioned-data
#
# - A dataset can exploit a nested structure, where the sub-dir names hold information about which subset of the data is stored in that dir
# - E.g., "Hive" patitioning scheme "key=vale" dir names

# %%
df = get_df()
print(df_to_str(df))

# %%
base = "."
dir_name = os.path.join(base, "parquet_dataset_partitioned")
os.system("rm -rf %s" % dir_name)

pq.write_to_dataset(table, dir_name, partition_cols=["idx"])

# %%
# !ls parquet_dataset_partitioned

# %%
# Read data back.
dataset = ds.dataset(dir_name, format="parquet", partitioning="hive")

print("\n".join(dataset.files))

# %%
# Read everything.
df2 = dataset.to_table().to_pandas()

print(df_to_str(df2))

# %%
# Load part of the data.

df2 = dataset.to_table(filter=ds.field("idx") == 1).to_pandas()
print(df_to_str(df2))

df2 = dataset.to_table(filter=ds.field("idx") < 3).to_pandas()
print(df_to_str(df2))

# %% [markdown]
# ## Add year-month partitions

# %%
df = get_df()
df["year"] = df.index.year
df["month"] = df.index.month

print(df_to_str(df))

# %%
table = pa.Table.from_pandas(df)

print("table=\n%s" % table)

# %%
base = "."
dir_name = os.path.join(base, "pq_partitioned2")
os.system("rm -rf %s" % dir_name)

pq.write_to_dataset(table, dir_name, partition_cols=["idx", "year", "month"])

# %%
# !ls $dir_name

# %%
# !ls $dir_name/idx=0/year=2000/month=1

# %%
# Read data back.
dataset = ds.dataset(dir_name, format="parquet", partitioning="hive")

print("\n".join(dataset.files))

# %%
# Read data back.
dataset = ds.dataset(dir_name, format="parquet", partitioning="hive")

df2 = dataset.to_table(filter=ds.field("idx") == 2).to_pandas()
print(df_to_str(df2))

# %%
# We could scan manually and create the dirs manually if we don't want to add
# add a new dir.
base = "."
dir_name = os.path.join(base, "parquet_dataset_partitioned2")
os.system("rm -rf %s" % dir_name)

schemas = []

schema = pa.Table.from_pandas(df).schema
print(schema)
# assert 0
# idx: int64
# instr: string
# val1: int64
# val2: int64
# year: int64
# month: int64

# grouped = df.groupby(lambda x: x.day)
group_by_idx = df.groupby("idx")
for idx, df_tmp in group_by_idx:
    _LOG.debug("idx=%s -> df.shape=%s", idx, str(df_tmp.shape))
    #
    group_by_year = df_tmp.groupby(lambda x: x.year)
    for year, df_tmp2 in group_by_year:
        _LOG.debug("year=%s -> df.shape=%s", year, str(df_tmp2.shape))
        #
        group_by_month = df_tmp2.groupby(lambda x: x.month)
        for month, df_tmp3 in group_by_month:
            _LOG.debug("month=%s -> df.shape=%s", month, str(df_tmp3.shape))
            # file_name = "df_in_one_file.pq"
            # pq.write_table(table, file_name)
            # /app/data/idx=0/year=2000/month=1/02e3265d515e4fb88ebe1a72a405fc05.parquet
            subdir_name = os.path.join(
                dir_name, f"idx={idx}", f"year={year}", f"month={month}"
            )
            table = pa.Table.from_pandas(df_tmp3, schema=schema)
            schemas.append(table.schema)
            # print(df_tmp3)
            # print(table.schema)
            #             pq.write_to_dataset(table,
            #                     subdir_name, schema=schema)
            file_name = os.path.join(subdir_name, "df_out.pq")
            hio.create_enclosing_dir(file_name)
            pq.write_table(table, file_name)

# %%
schemas[0] == schemas[4]

# %%
schemas

# %%

# %%
# !ls $dir_name/idx=0/year=2000/month=1

# %%
# Read data back.
# https://github.com/dask/dask/issues/4194
# src_dir = f"{dir_name}/idx=0/year=2000/month=1"
src_dir = f"{dir_name}/idx=0/year=2000"
dataset = ds.dataset(src_dir, format="parquet", partitioning="hive")

df2 = dataset.to_table().to_pandas()
# print(df_to_str(df2))
print("\n".join(dataset.files))

# %% [markdown]
# ## Partition manually

# %%
from pyarrow.dataset import DirectoryPartitioning

partitioning = DirectoryPartitioning(
    pa.schema([("year", pa.int16()), ("month", pa.int8()), ("day", pa.int8())])
)
print(partitioning.parse("/2009/11/3"))

# partitioning.discover()

# %%
# !ls /app/data

# %%
dir_name = "/app/data"

# Read data back.
dataset = ds.dataset(dir_name, format="parquet", partitioning="hive")

print("\n".join(dataset.files))

# %%
# Read everything.
df2 = dataset.to_table().to_pandas()

print(df_to_str(df2))

# %%
print(df2["instr"].unique())
print(df2.index)
