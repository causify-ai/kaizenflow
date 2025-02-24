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

# %% [markdown]
# # Imports

# %% run_control={"marked": true}
import os

import requests

# %%
bearer_token = os.environ["BEARER"]


# %% [markdown]
# # Functions

# %%
def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2RecentSearchPython"
    return r


def connect_to_endpoint(url, params):
    response = requests.get(url, auth=bearer_oauth, params=params)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def main(url, params):
    json_response = connect_to_endpoint(url, params)
    return json_response


# %% [markdown]
# # Downloading data in bulk

# %% [markdown]
# It seems like twitter API does not support bulk data downloading. But we can apply search to full archive with premium access (below).

# %% [markdown]
# # Searching data by hashtag or by search query

# %% [markdown]
# There are two search API endpoints:
#
# Search Tweets (Free): 30-day endpoint → provides Tweets posted within the last 30 days.
#
# Search Tweets (Premium): Full-archive endpoint → provides Tweets from as early as 2006, starting with the first Tweet posted in March 2006.

# %%
search_recent = "https://api.twitter.com/2/tweets/search/recent"
search_all = "https://api.twitter.com/2/tweets/search/all"

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
query_params = {"query": "#bitcoin", "tweet.fields": "author_id"}

# %% [markdown]
# Search recent.

# %%
main(search_recent, query_params)["data"]

# %% [markdown]
# Search historical - will produce error since we don't have an access to the premium URLs.

# %%
main(search_all, query_params)["data"]

# %% [markdown]
# # Getting trending hashtags

# %%
trends_availiable = "https://api.twitter.com/1.1/trends/available.json"
all_places = main(trends_availiable, {})

# %%
all_places[:5]

# %% [markdown]
# Get trends worldwide. Worldwide id = 1

# %%
trends_place = "https://api.twitter.com/1.1/trends/place.json?id=1"
main(trends_place, {})

# %% [markdown]
# # Searching data by topic

# %% [markdown]
# From https://dev.to/suhemparack/how-to-search-for-tweets-about-various-topics-using-the-twitter-api-v2-3p86
# 1) Find the tweet with of the specific topic
# 2) Go to https://tweet-entity-extractor.glitch.me, paste the link to a tweet
# 3) Get the list of entities that were mentioned in a tweet, select the one you need, in this case 131.1007360414114435072="bitcoin cryptocurrency"
# 4) Format the query as `context:131.1007360414114435072`
# 5) Run the search

# %%
query_params = {
    "query": "context:131.1007360414114435072",
    "tweet.fields": "author_id",
}
main(search_recent, query_params)

# %%
