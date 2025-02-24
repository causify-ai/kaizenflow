# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import datetime
import os

import pandas as pd
import s3fs
from pyarrow import parquet

# import helpers.hs3 as hs3
import im_v2.ig.data.client.historical_bars as imvidchiba

# %%
# #!aws s3 ls --profile default s3://iglp-core-data/ds/ext/bars/taq/v1.0-prod/60/

# %%
root_path = "s3://iglp-core-data/ds/ext/bars/taq/v1.0-prod/60/"

# filesystem = s3fs.S3FileSystem(profile="default") if path.startswith('s3://') else None
# filesystem.ls(path)
# dataset = parquet.ParquetDataset(args.path, filesystem=filesystem)

s3 = s3fs.S3FileSystem(profile="default")

# s3.ls(path)

# %%
# path = "s3://iglp-core-data/ds/ext/bars/taq/v1.0-prod/60/"

# #s3 = hs3.get_s3fs(aws_profile="sasm")
# s3 = hs3.get_s3fs(aws_profile="default")
# print(s3)
# #s3.ls("s3://iglp-core-data/")
# #dates = hs3.listdir(PATH, mode="non-recursive", aws_profile="sasm")

# dates = s3.ls(path)

# %%
filesystem = s3fs.S3FileSystem()
igid = 11000
filters = []
for igid in range(igid, igid + 2000):
    filters.append([("igid", "=", igid)])
print(len(filters))
date = "20200106"
columns = "start_time end_time ticker close volume".split()

path = os.path.join(root_path, date, "data.parquet")
dataset = parquet.ParquetDataset(
    path, filesystem=filesystem, filters=filters, use_ligacy_dataset=False
)
# table = dataset.read()#columns=columns)
table = dataset.read(columns=columns)
df = table.to_pandas()
print(df.shape)
print(len(df["igid"].unique()))

# %%
filesystem = s3fs.S3FileSystem()
igid = 10971
filters = [("igid", "=", igid)]
print(len(filters))
date = "20200106"
columns = "start_time end_time ticker close volume igid".split()

path = os.path.join(root_path, date, "data.parquet")
dataset = parquet.ParquetDataset(
    path, filesystem=filesystem, filters=filters, use_ligacy_dataset=False
)
# table = dataset.read()#columns=columns)
table = dataset.read(columns=columns)
df = table.to_pandas()
print(df.shape)
print(len(df["igid"].unique()))

# %%
filesystem = s3fs.S3FileSystem()
date = "20210106"
columns = "start_time end_time ticker close volume igid".split()
filters = None
path = os.path.join(root_path, date, "data.parquet")
dataset = parquet.ParquetDataset(
    path, filesystem=filesystem, filters=filters, use_ligacy_dataset=False
)
# table = dataset.read()#columns=columns)
table = dataset.read(columns=columns)
df = table.to_pandas()
print(df.shape)
print(len(df["igid"].unique()))

# %%
df.head()

# %%
df.dropna(inplace=True)

# %%
imvidchiba.process_data(df)

# %%
ticker_map = df[["igid", "ticker"]].groupby("igid").first()["ticker"]

ticker_map

# %%
igid_by_trading_vol.head(100)["ticker"].to_csv("top_100_by_trading_volume.csv")

# %%
df_tmp.loc[13684]

# %%
# igids = None
igids = [13684]
dates = [datetime.date(2021, 1, 6)]
columns = ["close", "volume", "ticker"]

df = imvidchiba.get_cached_bar_data_for_date_interval(
    igids, dates, columns=columns
)

# %%
print(imvidchiba.compute_bar_data_stats(df, igid))

# %%
df.head(3)

# %%
volume = df.groupby("igid")[["volume"]].sum()
price = df.groupby("igid")[["close"]].mean()
ticker_map = df.groupby("igid")[["ticker"]].first()

df_tmp = pd.concat([volume, price, ticker_map], axis=1)
print(df_tmp.head())

df_tmp["notional"] = df_tmp["volume"] * df_tmp["close"]

igid_by_trading_vol = df_tmp.sort_values(by="notional", ascending=False)

igid_by_trading_vol.head(100)
