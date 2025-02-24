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

# %%
import logging

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe as imvcounun

# %load_ext autoreload
# %autoreload 2

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
# Imports

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe as imvcounun

# %load_ext autoreload
# %autoreload 2

hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Test _subscribe_to_websocket_trades

# %%
exchange_id = "binance"
contract_type = "futures"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)
extractor._async_exchange.has["watchTrades"]

# %%
currency_pair = "BTC/USDT"
since = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp.now() + pd.Timedelta(seconds=15)
)
await extractor._subscribe_to_websocket_bid_ask(
    exchange_id,
    currency_pair,
    bid_ask_depth=10
    #     since
)

# %% [markdown]
# ## Test _download_websocket_trades(

# %%
extractor._download_websocket_bid_ask(
    exchange_id,
    currency_pair,
)

# %% [markdown]
# # Download by script

# %% language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db_periodically.py \
#     --download_mode 'realtime' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1sec' \
#     --vendor 'ccxt' \
#     --exchange_id 'binance' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_bid_ask_futures_raw' \
#     --aws_profile 'ck' \
#     --data_type 'bid_ask' \
#     --data_format 'postgres' \
#     --contract_type 'futures' \
#     --start_time "$(date -d 'today + 1 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --stop_time "$(date -d 'today + 3 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --method 'websocket'
#

# %% [markdown]
# ## Check by reader

# %%
signature = "realtime.airflow.downloaded_1sec.postgres.bid_ask.futures.v7_3.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-04-19 00:40:00+00:00")
end_timestamp = pd.Timestamp("2023-04-19 23:40:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)

# %%
trades

# %%
trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
