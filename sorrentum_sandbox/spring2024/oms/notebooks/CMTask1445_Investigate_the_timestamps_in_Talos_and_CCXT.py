# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports

# %%
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hsql as hsql
import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
import im_v2.im_lib_tasks as imvimlita

# %% [markdown]
# ## Functions

# %%
def get_data_from_ccxt_client(start_time, end_time):
    # Specify the params.
    full_symbol_binance = "binance::BTC_USDT"
    start_time = pd.to_datetime(start_time)
    end_time = pd.to_datetime(end_time)
    df = ccxt_client._read_data_for_one_symbol(
        full_symbol_binance, start_time, end_time
    )
    return df


# %% [markdown]
# # Current CCXT client

# %%
# Specify the params.
vendor = "CCXT"
universe_version = "v3"
root_dir = "s3://alphamatic-data/data"
extension = "csv.gz"
aws_profile_ccxt = "am"
# Initialize CCXT client.
ccxt_client = imvcdccccl.CcxtCddCsvParquetByAssetClient(
    vendor,
    universe_version,
    True,
    root_dir,
    extension,
    aws_profile=aws_profile_ccxt,
)

# %% run_control={"marked": false}
data_ccxt_client = get_data_from_ccxt_client(
    "2020-01-01 10:00:02", "2020-01-01 10:08:00"
)

# %%
display(data_ccxt_client.head(3))
display(data_ccxt_client.tail(3))

# %% [markdown]
# ### Current CCXT client summary

# %% [markdown]
# Beginning
# - If proposing query for __a complete minute__ (e.g., __10:00:00__) - it starts with __exactly mentioned timestamp__ (i.e., __10:00:00+00:00__).
# - If proposing query for __an incomplete minute__ (e.g., __10:00:36 or 10:00:24__) - it starts with __mentioned timestamp + 1min__ (i.e., __10:01:00__).
#    - - Since the ohlcv output is available, one can check through volume or prices data that changing the query within a minute (e.g., 10:00:02 or 10:00:45) doesn't affect the numbers, so it means that the timestamp indicates the end of time period.
#
# End
# - If proposing query for __a complete minute__ (e.g., __10:07:00__) - it starts with __exactly mentioned timestamp__ (i.e., 10:07:00).
# - If proposing query for __an incomplete minute__ (e.g., __10:07:36 or 10:07:24__) - it starts with __exactly mentioned timestamp__ (i.e., __10:07:00__).
# - If proposing query for __previous minute + 1min__ (e.g., __10:08:00__) - it starts with __exactly mentioned timestamp__ (i.e., __10:08:00__).
