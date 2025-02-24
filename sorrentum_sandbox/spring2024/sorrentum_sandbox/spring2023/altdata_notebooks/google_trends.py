# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install pytrends)"

# %% [markdown]
# # Imports

# %%
import pandas as pd
from pytrends.request import TrendReq

# %% [markdown]
# # Get pytrends

# %%
pytrends = TrendReq(hl="en-US", tz=360)

# %% [markdown]
# Define keywords list.

# %%
kw_list = ["Bitcoin"]

# %% [markdown]
# # Historical interest

# %% [markdown]
#  `Cat` is the search category which can be found at https://github.com/pat310/google-trends-api/wiki/Google-Trends-Categories. Category 0 means no category filter.
#
#  `Geo` is  search country abbreviation which follows the ISO-3166 country code naming scheme, e.g. 'US' or 'US-AL' for Alabama state. Defaults to 'World'.
#
#  `Gprop` describes what Google property to filter to. Can be `images`, `news`, `youtube` or `froogle`.

# %% [markdown]
# Let's find the start date of historical data, try year 2005, when Bitcoin and Etherium didn't exist.

# %%
hist_int_old = pytrends.get_historical_interest(
    kw_list,
    year_start=2005,
    month_start=1,
    day_start=1,
    hour_start=0,
    year_end=2010,
    month_end=12,
    day_end=20,
    hour_end=20,
    cat=0,
    geo="",
    gprop="",
    sleep=0,
)

# %% [markdown]
# Google Trends normalizes search data to make comparisons between terms easier. Search results are normalized to the time and location of a query by the following process:
#
# - Each data point is divided by the total searches of the geography and time range it represents to compare relative popularity. Otherwise, places with the most search volume would always be ranked highest.
#
# - The resulting numbers are then scaled on a range of 0 to 100 based on a topic’s proportion to all searches on all topics.
#
# - Different regions that show the same search interest for a term don't always have the same total search volumes.

# %% [markdown]
# Plot the result and let's check when Bitcoin appears in google trends.

# %%
hist_int_old.plot(figsize=(20, 12))

hist_int_old.plot(subplots=True, figsize=(20, 12))

# %%
hist_int_old[hist_int_old["Bitcoin"] != 0]

# %% [markdown]
# But how could `Bitcoin` appear in Google Trends in 2005 if it was created in 2008? Strange!

# %% [markdown]
# ## Real-time data

# %%
hist_int_new = pytrends.get_historical_interest(
    kw_list,
    year_start=2022,
    month_start=1,
    day_start=1,
    hour_start=0,
    year_end=2022,
    month_end=12,
    day_end=22,
    hour_end=23,
    cat=0,
    geo="",
    gprop="",
    sleep=0,
)

# %%
hist_int_new.plot(figsize=(20, 12))

hist_int_new.plot(subplots=True, figsize=(20, 12))

# %% [markdown]
# Let's look when the data ends.

# %%
hist_int_new.tail()

# %% [markdown]
# It looks like the data is delivered once an hour.

# %% [markdown]
# # Related queries

# %%
related_q = pytrends.related_queries()

# %%
related_q["Bitcoin"]["top"]

# %%
related_q["Bitcoin"]["rising"]

# %% [markdown]
# # Related topics

# %%
related_t = pytrends.related_topics()

# %%
related_t["Bitcoin"]["top"]

# %%
related_t["Bitcoin"]["rising"]
