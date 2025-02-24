# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Description
#
# Analyze bar prices

# %%
import datetime

import pandas as pd
import s3fs
import seaborn as sns
import statsmodels
import statsmodels.api
from pyarrow import parquet

# %% [markdown]
# # Load data to compare

# %%
# Load one day of data: 2019-01-07 is a Monday.

path = "s3://.../20190107/data.parquet"
columns = None
filesystem = s3fs.S3FileSystem() if path.startswith("s3://") else None
dataset = parquet.ParquetDataset(path, filesystem=filesystem)
table = dataset.read(columns=columns)
df_taq_bars = table.to_pandas()
# .to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)

# %%
print("df_taq_bars.shape=", df_taq_bars.shape)

print(df_taq_bars.columns)

print("tickers=", len(df_taq_bars["ticker"].unique()))

print("asset_id=", len(df_taq_bars["asset_id"].unique()))

print("currency=", df_taq_bars["currency"].unique())

# %%
# print("\n".join(map(str, df_taq_bars.iloc[0].values)))

# %%
display(df_taq_bars.head(3))

display(df_taq_bars.tail(3))

# %%
# Get AAPL data for a subset of columns.
mask = df_taq_bars["ticker"] == "AAPL"
df_new = df_taq_bars[mask]
print(df_new.shape)

columns = [
    "start_time",
    "end_time",
    "ticker",
    "currency",
    "open",
    "close",
    "low",
    "high",
    "volume",
]
df_new = df_new[columns]

df_new.head(3)


# %%
def to_et(df, col_name):
    df = df.copy()
    vals = df[col_name].apply(datetime.datetime.fromtimestamp)
    # print(vals)
    vals = vals.dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    df[col_name] = vals
    return df


df_new2 = to_et(df_new, "start_time")
df_new2 = to_et(df_new2, "end_time")
df_new2.set_index("start_time", drop=True, inplace=True)

display(df_new2.head())
# display(df_new2.tail())
# display(df_new2[df_new2.index > "2019-01-07 09:20"].head())
# display(df_new2[df_new2.index < "2019-01-07 16:03"].tail())

# %%
display(df_new2[df_new2.index > "2019-01-07 09:27"].head())

# %%
display(df_new2[df_new2.index < "2019-01-07 16:03"].tail())

# %%
df_new2["close"].plot()

# %%
df_new2["volume"].plot()

# %% [markdown]
# # Load ref data

# %%
file_name = "/app/aapl.csv"
df_ref = pd.read_csv(file_name)
display(df_ref.head())

df_ref["datetime"] = pd.to_datetime(df_ref["datetime"])
# df_ref["datetime"] = df_ref["datetime"].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
df_ref["datetime"] = df_ref["datetime"].dt.tz_localize("America/New_York")
df_ref.set_index("datetime", inplace=True, drop=True)
# df_ref = df_ref[(df_ref.index >= "2019-01-07") & (df_ref.index < "2019-01-08")]
df_ref = df_ref[
    (df_ref.index >= "2019-01-07 09:30") & (df_ref.index <= "2019-01-07 16:00")
]
df_ref.rename({"vol": "volume"}, axis="columns", inplace=True)

display(df_ref.head())
display(df_ref.tail())

# %%
# display(df_ref[df_ref.index > "2019-01-07 09:27"].head())

# display(df_ref[df_ref.index < "2019-01-07 16:03"].tail())

# %%
df_ref["close"].plot()

# %%
df_ref["volume"].plot()

# %% [markdown]
# # Comparison

# %%
display(df_new2.head())
display(df_ref.head())

# %%
# Notice how the 16:00:00 bars differ
display(df_new2.dropna().tail())
display(df_ref.dropna().tail())

# %%
target_col_name = "close"

# %%
col_names = [target_col_name]
df_all = df_new2[col_names].merge(
    df_ref[col_names],
    left_index=True,
    right_index=True,
    how="outer",
    suffixes=["_new", "_ref"],
)
df_all.head()

# %%
# Notice that the precisions appear to be different across the two columns
#   (and within the same day for the "_new" column)
display(df_all.dropna().head())
display(df_all.dropna().tail())

# %%
df_all.dropna().tail()

# %%
df_all.plot()

# %%
df_all.columns[0]


# %%
def calculate_diffs(df, shifts=0):
    df = df.diff()
    df["diff_of_diffs"] = df[df.columns[0]] - df[df.columns[1]].shift(shifts)
    return df


# %%
diffs = calculate_diffs(df_all, 0)

# %%
diffs.dropna()

# %%
diffs["diff_of_diffs"].plot()

# %%
diffs["diff_of_diffs"].cumsum().plot()

# %%
diffs["diff_of_diffs"].hist(bins=30)

# %%
diffs["diff_of_diffs"].mean(), diffs["diff_of_diffs"].std()

# %%
diffs["diff_of_diffs"].apply(abs).sum()

# %%
# Force all the data to be centered around 100.
df_all -= df_all.mean(axis=0)
df_all += 100.0

df_all.plot()

# %%
rets = df_all.pct_change()

rets.plot()

# %%
# df_all[col_names].loc["2019-01-07 09:30":"2019-01-07 12:00"].plot()
# df_all[col_names].loc["2019-01-07 09:30":"2019-01-07 09:35"].plot()
df_all.loc["2019-01-07 09:35":"2019-01-07 09:40"].plot()

# %%
predicted_var = diffs.columns[0]
predictor_var = diffs.columns[1]

df = diffs[[predicted_var, predictor_var]].copy()
df[predicted_var] = df[predicted_var].shift(0)
df = df.dropna()

intercept = True
model = statsmodels.api.OLS(
    df[predicted_var], df[predictor_var], hasconst=intercept
).fit()
print(model.summary().as_text())

sns.jointplot(x=predictor_var, y=predicted_var, data=df)

# %%
