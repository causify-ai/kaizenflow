import json
import os
from typing import Any, Dict, List

import pandas as pd
import requests

# function for bitquery query
def make_query(start_date: str):

    start_date = f'"{start_date}"'

    query = (
        """query{
    ethereum(network: ethereum) {
        dexTrades(
        options: {limit: 25000, offset: %d, asc: "timeInterval.minute"}
        date: {since: """
        + start_date
        + """,till:"2023-04-04"}
        exchangeName: {is: "Uniswap"}
        )
        {
        timeInterval {
        minute(count: 1)
        }
        baseCurrency {
        symbol
        address
        }
        baseAmount(in: USD)
        quoteCurrency {
        symbol
        address
        }
        quoteAmount(in: USD)
        trades: count
        quotePrice
        maximum_price: quotePrice(calculate: maximum)
        minimum_price: quotePrice(calculate: minimum)
        open_price: minimum(of: block, get: quote_price)
        close_price: maximum(of: block, get: quote_price)
        }
    }
    }
    """
    )
    return query


def run_query(query: str):
    # header here just for easy use
    headers = {"X-API-KEY": "BQYNhPk2qKSeVqqYH6I8CyHpwXk6Bihm"}
    request = requests.post(
        "https://graphql.bitquery.io", json={"query": query}, headers=headers
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(
            "Query failed and return code is {}.      {}".format(
                request.status_code, query
            )
        )


def json_to_df(data: List[Dict[Any, Any]]) -> pd.DataFrame:
    """
    Transform the data to Dataframe and set the time index.
    """
    df = pd.json_normalize(data, sep="_")
    df = df.set_index("timeInterval_minute")
    return df
