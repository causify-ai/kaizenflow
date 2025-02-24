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

# %%
import logging
import helpers.hdbg as hdbg
import helpers.hprint as hprint

import pandas as pd
import helpers.hparquet as hparque

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %%
merged_data = pd.read_csv("/shared_data/juraj_CmTask6864/2023_merged-Data.csv", nrows=50000)

# %%
merged_data.head()


# %%
def read_csv_and_get_timestamp_summary(file_path, chunksize=50000):
    """
    Read a CSV file in chunks and calculate the minimum and maximum timestamp for each unique value in a specified column.

    Parameters:
    - file_path (str): Path to the CSV file.
    - chunksize (int): Number of rows to read in each chunk.

    Returns:
    - pd.DataFrame: DataFrame containing unique values, min_timestamp, and max_timestamp for each unique value.
    """
    column_name = "#RIC"
    # Initialize an empty DataFrame to store results
    result_df = []

    # Initialize a dictionary to store min and max timestamps for each unique value
    timestamps_dict = {}

    # Use the Pandas read_csv function with chunksize
    chunks = pd.read_csv(file_path, chunksize=chunksize)

    # Process each chunk
    for i, chunk in enumerate(chunks):
        chunk["timestamp"] = pd.to_datetime(chunk["Date-Time"]) - pd.to_timedelta(chunk['GMT Offset'], unit='h')
        # Iterate over unique values in the specified column
        for unique_value in chunk[column_name].unique():
            # Get or initialize min and max timestamps for the current unique value
            min_timestamp, max_timestamp = timestamps_dict.get(unique_value, (pd.Timestamp.max.tz_localize('UTC'), pd.Timestamp.min.tz_localize('UTC')))

            # Update min and max timestamps based on the current chunk
            min_timestamp = min(min_timestamp, chunk.loc[chunk[column_name] == unique_value, 'timestamp'].min())
            max_timestamp = max(max_timestamp, chunk.loc[chunk[column_name] == unique_value, 'timestamp'].max())

            # Store the updated timestamps in the dictionary
            timestamps_dict[unique_value] = (min_timestamp, max_timestamp)
        print(f"Chunk processd {i}")

    # Convert the timestamps dictionary to a DataFrame
    for unique_value, (min_timestamp, max_timestamp) in timestamps_dict.items():
        result_df.append([unique_value, min_timestamp, max_timestamp])

    return result_df


# %%
merged_data_summary = read_csv_and_get_timestamp_summary("/shared_data/juraj_CmTask6864/2023_merged-Data.csv")

# %%
merged_data_summary = pd.DataFrame(merged_data_summary, columns=["currency_pair", "min_timestamp", "max_timestamp"])
merged_data_summary

# %%
estu = pd.read_csv("/shared_data/juraj_CmTask6864/estu_2023.csv.gz", nrows=50000)

# %%
estu.head()

# %%
estu_no_na = estu.dropna(how="all", axis=1)

# %%
estu_no_na.head()

# %%
estu_summary = read_csv_and_get_timestamp_summary("/shared_data/juraj_CmTask6864/estu_2023.csv.gz") 

# %%
estu_summary = pd.DataFrame(estu_summary, columns=["currency_pair", "min_timestamp", "max_timestamp"])
estu_summary

# %%
backfill = pd.read_csv("/shared_data/juraj_CmTask6864/backfill_2023.csv.gz", nrows=50000)

# %%
backfill.head()

# %%
backfill_no_na = backfill.dropna(how="all", axis=1)

# %%
backfill_no_na.head()

# %%
backfill_summary = read_csv_and_get_timestamp_summary("/shared_data/juraj_CmTask6864/backfill_2023.csv.gz")

# %%
backfill_summary = pd.DataFrame(backfill_summary, columns=["currency_pair", "min_timestamp", "max_timestamp"])
backfill_summary


# %%
def find_overlap(df1, df2):
    """
    Find overlaps in currency pairs and their corresponding time frames between two DataFrames.

    Parameters:
    - df1 (pd.DataFrame): First DataFrame with columns ['currency_pair', 'min_timestamp', 'max_timestamp'].
    - df2 (pd.DataFrame): Second DataFrame with columns ['currency_pair', 'min_timestamp', 'max_timestamp'].

    Returns:
    - pd.DataFrame: DataFrame containing overlaps in currency pairs and their corresponding time frames.
    """
    # Merge the two DataFrames on the 'currency_pair' column
    merged_df = pd.merge(df1, df2, on='currency_pair', how='inner', suffixes=('_df1', '_df2'))

    # Filter rows where there is an overlap in time frames
    overlap_df = merged_df[(merged_df['max_timestamp_df1'] >= merged_df['min_timestamp_df2']) & (merged_df['min_timestamp_df1'] <= merged_df['max_timestamp_df2'])]

    return overlap_df


# %%
find_overlap(backfill_summary, estu_summary)

# %%
find_overlap(backfill_summary, merged_data_summary)

# %%
find_overlap(estu_summary, merged_data_summary)


# %%
def get_single_currency_pair_info(file_path, currency_pair):
    column_name = "#RIC"
    # Initialize an empty DataFrame to store results
    result_df = []

    # Use the Pandas read_csv function with chunksize
    chunks = pd.read_csv(file_path, chunksize=50000)

    # Process each chunk
    for i, chunk in enumerate(chunks):
        chunk = chunk.dropna(how="all", axis=1)
        chunk["timestamp"] = pd.to_datetime(chunk["Date-Time"]) - pd.to_timedelta(chunk['GMT Offset'], unit='h')
        chunk = chunk[chunk[column_name] == currency_pair]
        result_df.append(chunk)
        print(f"Chunk processd {i}")
    
    result_df = pd.concat(result_df, ignore_index=True)
    return result_df


# %%
backfill_AGNI = get_single_currency_pair_info("/shared_data/juraj_CmTask6864/backfill_2023.csv.gz", "MIND.O")

# %%
estu_AGNI = get_single_currency_pair_info("/shared_data/juraj_CmTask6864/estu_2023.csv.gz", "MIND.O")

# %%
import numpy as np
def compare_single_asset_data(data1, data2):
    
    def _is_valid_row(row: pd.Series) -> bool:
        for col in cols:
            if np.isnan(row[col + "_A"]) and np.isnan(row[col + "_B"]):
                continue
            if row[col + "_A"] != row[col + "_B"]:
                return False
        return True
    
    data1 = data1.set_index(['timestamp'], drop=True)
    data2 = data2.set_index(['timestamp'], drop=True)
    
    cols = ['Open', 'High', 'Low', 'Last', 'Volume', 'No. Trades', 'Open Bid', 'High Bid', 'Low Bid', 'Close Bid', 'No. Bids', 'Open Ask', 'High Ask', 'Low Ask', 'Close Ask', 'No. Asks', 'Open Bid Size', 'High Bid Size', 'Low Bid Size', 'Close Bid Size', 'Open Ask Size', 'High Ask Size', 'Low Ask Size', 'Close Ask Size']
    
    data1 = data1[cols]
    data2 = data2[cols]
    
    print(f"Size of data1 : {len(data1)}, Size of data2: {len(data2)}")
    merged_df = pd.merge(data1, data2, on=['timestamp'], how='inner', suffixes=('_A', '_B'))
    merged_df["QAcheck"] = merged_df.apply(_is_valid_row, axis=1)
    print(len(merged_df))
    return merged_df
    


# %%
comparison = compare_single_asset_data(backfill_AGNI, estu_AGNI)
comparison

# %%
comparison[comparison["QAcheck"] == False]

# %%
backfill_AGNI[["Domain", "Type"]].value_counts()
 

# %%
backfill_assets_set = set(backfill_summary["currency_pair"])
etsu_assets_set = set(estu_summary["currency_pair"])
backfill_etsu_assets = backfill_assets_set.union(etsu_assets_set)
merged_assets_set = set(merged_data_summary["currency_pair"])

only_in_backfill_estu = backfill_etsu_assets.difference(merged_assets_set)

print(f"Total backfill and estu assets : {len(backfill_etsu_assets)}, Total merged : {len(merged_assets_set)}, only_in_backfill_etsu : {len(only_in_backfill_etsu)}") 
                          

# %%
set(merged_data_summary["currency_pair"]).difference(set(backfill_summary["currency_pair"]).union(set(estu_summary["currency_pair"])))

# %%
len((set(backfill_summary["currency_pair"]).union(set(estu_summary["currency_pair"]))))

# %%
