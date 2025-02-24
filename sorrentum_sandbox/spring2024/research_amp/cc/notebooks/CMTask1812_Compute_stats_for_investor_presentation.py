# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import json
import logging

import pandas as pd
import requests

import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()


# %% [markdown]
# # Functions

# %%
def _volume_transformer(vol_str):
    """
    Take the value of `Volume` and cut the end to the point where the first
    000's start.
    """
    vol_str_split = vol_str.split(",")
    last_piece = vol_str_split[-1]
    last_piece = last_piece[0:3]
    result = [p for p in vol_str_split[:-1]]
    result.append(last_piece)
    return ",".join(result)


def clean_up_exchanges(df):
    """
    - `Name` values contains integers at the end that we want to omit.
    - `Volume` values are presented not in a standard way.
    """
    # Names.
    df["Name"] = df["Name"].str.replace("\d+", "")
    # Volumes.
    df["Volume(24h)"] = df["Volume(24h)"].apply(lambda x: _volume_transformer(x))
    df["Volume(24h)"] = df["Volume(24h)"].apply(lambda x: x.replace("$", ""))
    df["Volume(24h)"] = df["Volume(24h)"].apply(lambda x: x.replace(".", ""))
    df["Volume(24h)"] = df["Volume(24h)"].apply(lambda x: x.replace(",", ""))
    df["Volume(24h)"] = pd.to_numeric(df["Volume(24h)"])
    return df


def get_cumulative_volume_ratios(
    df: pd.DataFrame, value_col: str, plot_results: bool, entity: str
) -> pd.Series:
    """
    :param df: Data with volume or market cap
    :param value_col: Specify volume or market cap column
    :param plot_results: plot barplot if True
    :param entity: "exchange" or "coin"
    :return: cumulative value ratios with respect to total sum of values
    """
    cumul_volume = df[value_col].cumsum() / df[value_col].sum()
    num_of_entities = len(cumul_volume[cumul_volume <= 0.9])
    print(
        f"Number of entities that is needed to consitute 90% of total sum: {num_of_entities}"
    )
    if plot_results:
        # TODO(max): plot as bars with the names of the exchanges at the bottom (vertically).
        # cumul_volume.plot(ylim=(0, 1))
        if entity == "exchange":
            plot_df = pd.concat([cumul_volume, df["Name"]], axis=1).set_index(
                "Name"
            )
            xlabel = "Exchanges"
        else:
            plot_df = pd.concat([cumul_volume, df["name"]], axis=1).set_index(
                "name"
            )
            xlabel = "Cryptocurrencies"
        if value_col == "_marketCap":
            title = "Cumulative Market Cap"
        else:
            title = "Cumulative trading volume"
        cplpluti.plot_barplot(
            plot_df.squeeze(),
            title=title,
            xlabel=xlabel,
            unicolor=True,
            annotation_mode="value",
            rotation=45,
        )
    return cumul_volume


def get_general_volume_ratio_df(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    value_col: str,
    col1: str,
    col2: str,
    plot_results: bool,
) -> pd.DataFrame:
    """
    Computes the portions of volume or market cap from two differen subsets
    with respect to full data.

    :param df1: Full data
    :param df2: Subset of full data that is ised for comparison
    :param value_col: Specify volume or market cap column
    :param col1: Name of the subset of full data
    :param col2: Name of the remaining subset of full data
    :param plot_results: Plot barplot if True
    :return: Ratio stats
    """
    value1 = df1[value_col].sum()
    value2 = df2[value_col].sum()
    ratio_df = pd.DataFrame()
    ratio_df.loc[col1, value_col] = value2
    ratio_df.loc[col2, value_col] = value1 - value2
    if plot_results:
        cplpluti.plot_barplot(ratio_df[value_col])
    return ratio_df


# %% [markdown] heading_collapsed=true
# # Exchanges (Spot)

# %% hidden=true
# Original data in /data/shared/CMTask1812_Compute_stats_for_investor_presentation
# # cp -r /data/shared/CMTask1812_Compute_stats_for_investor_presentation .

dir_name = "../../../CMTask1812_Compute_stats_for_investor_presentation"

# Read .html file.
# It was downloaded 2022-05-03 from https://coinmarketcap.com/rankings/exchanges/.
# Contains the snapshot of a table with the descriptive statistics of cryptocurrency exhanges.
file_name_exch = (
    dir_name
    + "/"
    + "Top Cryptocurrency Exchanges Ranked By Volume _ CoinMarketCap.html"
)
file_exch = pd.read_html(file_name_exch)
# Select necessary columns with top-100.
exch_df = file_exch[0][["Name", "Volume(24h)", "Exchange Score", "#"]].loc[:99]

# %% hidden=true
# Clean up the data.
all_exch = clean_up_exchanges(exch_df)

# %% hidden=true
# Select only `good` exchanges.
# Note: `good` exchanges - the ones with the Score > 6.
# `All` exchanges - `good` exchanges + the remaining ones.
good_exch = all_exch[all_exch["Exchange Score"] > 6]
_LOG.info(good_exch.shape)

# %% [markdown] hidden=true
# ## Top-10 `good` exchanges by volume

# %% hidden=true
# Sort by volume.
good_exch = good_exch.sort_values(
    ["Volume(24h)"], ascending=False, ignore_index=True
)
# Plot .
display(good_exch.loc[:9])
cplpluti.plot_barplot(
    good_exch.set_index("Name")["Volume(24h)"].iloc[:10].squeeze(),
    title="Trading volume per exchange",
    xlabel="Exchanges",
    unicolor=True,
    rotation=45,
)

# %% [markdown] hidden=true
# ## Total volume of top-10 `good` exchanges vs. other `good` exchanges

# %% hidden=true
ratio_good = get_general_volume_ratio_df(
    good_exch,
    good_exch.loc[:9],
    "Volume(24h)",
    "Top-10 `good` exchanges",
    "Other `good` exchanges",
    plot_results=True,
)
display(ratio_good)

# %% [markdown] hidden=true
# ## Cumulative volume for all `good` exchanges

# %% hidden=true
good_cumul_volume = get_cumulative_volume_ratios(
    good_exch, "Volume(24h)", plot_results=True, entity="exchange"
)
display(good_cumul_volume.head(5))

# %% [markdown] hidden=true
# ## Total volume of `good` exchanges vs. all other exchanges

# %% hidden=true
ratio_all = get_general_volume_ratio_df(
    all_exch,
    good_exch,
    "Volume(24h)",
    "`Good` exchanges",
    "Other exchanges",
    plot_results=True,
)
display(ratio_all)

# %% [markdown] hidden=true
# ## Cumulative volume of all exchanges

# %% hidden=true
# Sort all exchanges by volume.
all_exch_sorted = all_exch.sort_values(
    ["Volume(24h)"], ascending=False, ignore_index=True
)
# Plot the results.
all_cumul_volume = get_cumulative_volume_ratios(
    all_exch_sorted[:40], "Volume(24h)", plot_results=True, entity="exchange"
)
display(all_cumul_volume.head(5))

# %% [markdown] heading_collapsed=true
# # Exchanges (Derivatives)

# %% hidden=true
# Read .html file.
# It was downloaded 2022-05-03 from https://coinmarketcap.com/rankings/exchanges/derivatives/.
# Contains the snapshot of a table with the descriptive statistics of cryptocurrency derivatives exhanges.
file_name_der = (
    dir_name
    + "/"
    + "Top Cryptocurrency Derivatives Exchanges Ranked _ CoinMarketCap.html"
)
file_der = pd.read_html(file_name_der)
# Select necessary columns with top-100.
exch_der_df = file_der[0][["#", "Name", "Volume(24h)"]]

# %% hidden=true
# Clean up.
exch_der_df = clean_up_exchanges(exch_der_df)
# Sorting.
exch_der_df = exch_der_df.sort_values("Volume(24h)", ascending=False)

# %% [markdown] hidden=true
# ## Top-10 derivative exchanges by volume

# %% hidden=true
display(exch_der_df.loc[:9])
cplpluti.plot_barplot(
    exch_der_df.set_index("Name")["Volume(24h)"].iloc[:10].squeeze(),
    title="Trading volume per exchange",
    xlabel="Exchanges",
    unicolor=True,
    rotation=45,
)

# %% [markdown] hidden=true
# ## Total volume of top-10 derivative exchanges vs. all other derivative exchanges

# %% hidden=true
ratio_der = get_general_volume_ratio_df(
    exch_der_df,
    exch_der_df.loc[:9],
    "Volume(24h)",
    "Top-10 exchanges",
    "Other exchanges",
    plot_results=True,
)
display(ratio_der)

# %% [markdown] hidden=true
# ## Cumulative volume of all derivative exchanges

# %% run_control={"marked": false} hidden=true
all_cumul_der_volume = get_cumulative_volume_ratios(
    exch_der_df[:30], "Volume(24h)", plot_results=True, entity="exchange"
)
display(all_cumul_der_volume.head(5))

# %% [markdown]
# # Cryptocurrencies

# %%
# Load and process the data.
# It is updated with every re-run and is taken from Coinmarketcap API.
# Contains descriptive statistics about cryptocurrencies.
url = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=10081&sortBy=market_cap&sortType=desc&convert=USD&cryptoType=all&tagType=all&audited=false&aux=name,volume_24h"
response = requests.get(url)

crypto_data = json.loads(response.text)
crypto_df = pd.json_normalize(
    crypto_data["data"]["cryptoCurrencyList"],
    "quotes",
    ["name"],
    record_prefix="_",
)
_LOG.info(crypto_df.shape)
crypto_df.head(3)

# %%
# Leave only necessary columns.
crypto_df = crypto_df[["name", "_volume24h", "_marketCap"]].sort_values(
    "_marketCap", ascending=False, ignore_index=True
)
# `Good` crypto = first 100 coins by market cap
good_crypto = crypto_df.iloc[:100]

# %% [markdown]
# ## Market Cap

# %% [markdown]
# ### Top-10 `good` cryptocurrencies by Market Cap

# %%
cplpluti.configure_notebook_for_presentation()

# %%
display(good_crypto.loc[:9])
cplpluti.plot_barplot(
    good_crypto.set_index("name")["_marketCap"].iloc[:10].squeeze(),
    title="Market cap per coin",
    xlabel="Cryptocurrencies",
    unicolor=True,
    rotation=45,
)

# %% [markdown]
# ### Total market cap of top-10 `good` cryptocurrencies vs. other `good` cryptocurrencies

# %%
ratio_cc = get_general_volume_ratio_df(
    good_crypto,
    good_crypto.iloc[:10],
    "_marketCap",
    "Top-10 cryptocurrencies",
    "Other `good` cryptocurrencies",
    plot_results=True,
)
display(ratio_cc)

# %% [markdown]
# ### Cumulative market cap of all `good` cryptocurrencies

# %%
good_cumul_mcap = get_cumulative_volume_ratios(
    good_crypto[:40], "_marketCap", plot_results=True, entity="coin"
)
display(good_cumul_mcap.head(5))

# %% [markdown]
# ## Volume

# %% [markdown]
# ### Top-10 `good` cryptocurrencies by volume

# %%
good_crypto_volume_sorted = good_crypto.sort_values(
    "_volume24h", ascending=False, ignore_index=True
)
display(good_crypto_volume_sorted.iloc[:10])
cplpluti.plot_barplot(
    crypto_df.set_index("name")
    .sort_values("_volume24h", ascending=False)["_volume24h"]
    .iloc[:10]
    .squeeze(),
    title="Trading volume per coin",
    xlabel="Cryptocurrencies",
    unicolor=True,
    rotation=45,
)

# %% [markdown]
# ### Total volume of top-10 `good` cryptocurrencies vs. other `good` cryptocurrencies

# %%
ratio_good_volume = get_general_volume_ratio_df(
    good_crypto_volume_sorted,
    good_crypto_volume_sorted.iloc[:10],
    "_volume24h",
    "Top-10 cryptocurrencies",
    "Other `good` cryptocurrencies",
    plot_results=True,
)
display(ratio_good_volume)

# %% [markdown]
# ### Cumulative volume of all `good` cryptocurrencies

# %%
# Plot the cumulative volume against exchanges.
all_cumul_cc_volume = get_cumulative_volume_ratios(
    good_crypto_volume_sorted[:40], "_volume24h", plot_results=True, entity="coin"
)
display(all_cumul_cc_volume.head(5))

# %% [markdown]
# ## `Good` vs. `Others` Crypto

# %% [markdown]
# - `good` crypto = first 100 coins by market cap
# - `other` crypto = coins outside `good` crypto (±10.000 entities)

# %% [markdown]
# ### Market Cap

# %% [markdown]
# #### Total market cap of all `good` cryptocurrencies vs. other cryptocurrencies

# %%
ratio_good_vs_others_mcap = get_general_volume_ratio_df(
    crypto_df,
    good_crypto,
    "_marketCap",
    "`Good` cryptocurrencies",
    "Other cryptocurrencies",
    plot_results=True,
)
display(ratio_good_vs_others_mcap)

# %% [markdown]
# #### Cumulative market cap of all cryptocurrencies

# %%
# Plot the cumulative volume against exchanges.
good_others_mcap = get_cumulative_volume_ratios(
    crypto_df[:40], "_marketCap", plot_results=True, entity="coin"
)
display(good_others_mcap.head(5))

# %% [markdown]
# ### Volume

# %% [markdown]
# #### Total volume of all `good` cryptocurrencies vs. other cryptocurrencies

# %%
ratio_good_vs_others_mcap = get_general_volume_ratio_df(
    crypto_df,
    good_crypto,
    "_volume24h",
    "`Good` cryptocurrencies",
    "Other cryptocurrencies",
    plot_results=True,
)
display(ratio_good_vs_others_mcap)

# %% [markdown]
# #### Cumulative volume of all cryptocurrencies

# %%
# Plot the cumulative volume against exchanges.
good_others_volume = get_cumulative_volume_ratios(
    crypto_df.sort_values("_volume24h", ascending=False, ignore_index=True)[:40],
    "_volume24h",
    plot_results=True,
    entity="coin",
)
display(good_others_volume.head(5))
