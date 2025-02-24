import json
import os
import time
from typing import Any, Dict, List

import pandas as pd
import redis
import requests
from get_data import json_to_df, make_query, run_query


def main():
    date = "2023-04-04"
    # limit = 25000
    offset = 0
    data_dfs = []
    # headers = {"X-API-KEY": "BQYNhPk2qKSeVqqYH6I8CyHpwXk6Bihm"}
    for i in range(3):
        # Error message above says there are 61k rows, so 3 iterations by 25k would be enough.
        formatted_query = make_query(date) % offset
        result = run_query(formatted_query)
        df = json_to_df(result["data"]["ethereum"]["dexTrades"])
        data_dfs.append(df)
        offset += 25000
        print(3 - i)

    full_data = pd.concat(data_dfs)

    full_data.to_csv("data.csv", index=False)
    return full_data


if __name__ == "__main__":
    main()

# Comands
# docker build -t bitquery:latest .
# docker run -p 8888:8888 bitquery
