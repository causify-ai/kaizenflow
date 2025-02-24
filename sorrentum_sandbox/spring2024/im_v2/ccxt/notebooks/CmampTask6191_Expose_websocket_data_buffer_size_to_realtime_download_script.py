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

# %%
import pandas as pd

import helpers.hdatetime as hdateti
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import oms.broker.ccxt.ccxt_execution_quality as obccexqu

# %%
signature = "periodic_daily.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.binance.v1_0_0"

# %%
data_reader = imvcdcimrdc.RawDataReader(signature, stage="test")

# %%
start_time = pd.Timestamp("2023-11-17 09:02:00+00:00")
end_time = pd.Timestamp("2023-11-17T09:22:00+00:00")
df = data_reader.read_data(start_time, end_time)

# %%
df.head()

# %%
df["exchange_timestamp"] = df.index.to_series().apply(
    lambda x: hdateti.convert_unix_epoch_to_timestamp(x)
)

# %%
len(df)

# %%
df = df.sort_values(by=['currency_pair', 'knowledge_timestamp'])

# %%
df = df.drop_duplicates(subset=['currency_pair', 'exchange_timestamp'], keep='first')

# %%
time = df[["exchange_timestamp", "end_download_timestamp", "knowledge_timestamp"]]

# %%
time.head()

# %%
df.head()

# %%
len(df)

# %%
time = time.sort_index()

# %%
time_delays = obccexqu.get_time_delay_between_events(time)
time_delays.boxplot(rot=45, ylabel="Time delay")

# %%
time_delays[time_delays["end_download_timestamp"] > 0.3]

# %%
# Get duplicates per asset
subset_columns = df.columns.difference(
    [
        "end_download_timestamp",
        "knowledge_timestamp",
        "currency_pair",
    ]
)
duplicates_count = (
    df.groupby(["currency_pair"] + list(subset_columns))
    .size()
    .reset_index(name="count")
)

# %%
duplicate_rows = duplicates_count[duplicates_count["count"] > 1]

# %%
duplicate_rows.groupby("currency_pair")["count"].count()

# %%
duplicate_groups = df.groupby(["currency_pair"] + list(subset_columns))
limit = 10
for (row, group) in duplicate_groups:
    if limit == 0:
        break
    if len(group) > 1:
        print(group.head())
        limit -= 1

# %%
