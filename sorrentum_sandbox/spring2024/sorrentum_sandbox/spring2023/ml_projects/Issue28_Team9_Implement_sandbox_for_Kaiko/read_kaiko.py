"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue28_Team9_Implement_sandbox_for_Kaiko.read_kaiko as ssempitisfkrk
"""

import kaiko
import numpy as np
import pandas as pd

# Setting a client with API key
api_key = "1d16b71fdfa506550a8a9cc5faa36fa4"
kc = kaiko.KaikoClient(api_key=api_key)

# Test : TickTrade data
ticktrade = kaiko.TickTrades(
    exchange="cbse",
    instrument="btc-usd",
    start_time="2022-1-1",
    end_time="2022-1-2",
    client=kc,
)
print(ticktrade.df)
