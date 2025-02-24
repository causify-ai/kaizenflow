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

# %% [markdown] heading_collapsed=true
# # Imports

# %% hidden=true
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe as imvcounun

# %% hidden=true
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown] heading_collapsed=true
# # One time download okx data to DB

# %% [markdown] hidden=true
# ## OHLCV

# %% hidden=true language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 17:30:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_ohlcv_futures' \
#     --s3_path 's3://cryptokaizen-data-test/' \
#     --data_type 'ohlcv' \
#     --data_format 'postgres' \
#     --contract_type 'futures'
#

# %% [markdown] hidden=true
# ### Errors

# %% [markdown] hidden=true
# Next currency pairs is not presented in the okx:
# - UNFI_USDT
# - RUNE/USDT
# - OGN/USDT
#

# %% [markdown] hidden=true
# ## Bid ask

# %% hidden=true language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_bid_ask_futures_raw' \
#     --s3_path 's3://cryptokaizen-data-test/' \
#     --data_type 'bid_ask' \
#     --data_format 'postgres' \
#     --contract_type 'futures'
#

# %% [markdown] hidden=true
# ### Warinings

# %% [markdown] hidden=true
# There is no progress bars.

# %% [markdown] hidden=true
# ## Trades

# %% hidden=true language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_trades_futures' \
#     --s3_path 's3://cryptokaizen-data-test/' \
#     --data_type 'trades' \
#     --data_format 'postgres' \
#     --contract_type 'futures'

# %% [markdown] hidden=true
# ### Warnings

# %% [markdown] hidden=true
# - trades tables didn't found - skipping

# %% [markdown] heading_collapsed=true
# # Run periodical download okx - websockets

# %% [markdown] hidden=true
# ## OHLCV

# %% hidden=true language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db_periodically.py \
#     --download_mode 'periodic_1min' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_ohlcv_futures' \
#     --aws_profile 'ck' \
#     --data_type 'ohlcv' \
#     --data_format 'postgres' \
#     --contract_type 'futures' \
#     --interval_min '1' \
#     --start_time "$(date -d 'today + 1 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --stop_time "$(date -d 'today + 3 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --method 'websocket'

# %% [markdown] hidden=true
# ### Read data from postgres

# %% hidden=true
signature = "bulk.manual.downloaded_1min.postgres.ohlcv.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp.now() - pd.Timedelta(minutes=10)
end_timestamp = pd.Timestamp.now()

# %% hidden=true
ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
ohlcv_data.head()

# %% hidden=true
ohlcv_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% [markdown] heading_collapsed=true
# # Run a one time bulk parquet downoad

# %% [markdown] hidden=true
# ## OHLCV

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 17:30:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --incremental \
#     --data_type 'ohlcv' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ## Bid_ask

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --incremental \
#     --data_type 'bid_ask' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ### Warnings

# %% [markdown] hidden=true
# - no progress bar

# %% [markdown] hidden=true
# ## Trades

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-02-14 00:30:00+07:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ### Warnings

# %% [markdown] hidden=true
# - CCXT didn't download the trades data properly. It gets the data irrespectively to the given date-time range.

# %% hidden=true
import ccxt

import helpers.hdatetime as hdateti

extractor = ccxt.okx()
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp("2023-01-01 10:00:00+00:00")
)
data = extractor.fetch_trades("BTC/USDT", since=start_timestamp)

# %% hidden=true
df = pd.DataFrame(data)

# %% hidden=true
df["timestamp"].agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %% [markdown] heading_collapsed=true
# # Load a preview of the downloaded data - rest

# %% hidden=true

# %% [markdown] hidden=true
# ## OHLCV

# %% hidden=true
signature = "bulk.manual.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 17:30:00+00:00")

# %% hidden=true
ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
ohlcv_data

# %% hidden=true
ohlcv_data.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %% hidden=true
pd.Series(ohlcv_data.index).agg(["min", "max"])

# %% [markdown] hidden=true
# ## airflow - OHLCV

# %% hidden=true
signature = "bulk.airflow.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2021-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2021-04-01 17:30:00+00:00")

# %% hidden=true
ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
ohlcv_data.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")b

# %% hidden=true
ohlcv_data.shape

# %% [markdown] hidden=true
# ## Bid_ask

# %% hidden=true
signature = "bulk.manual.downloaded_1min.parquet.bid_ask.futures.v7_3.crypto_chassis.okex.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 20:30:00+00:00")

# %% hidden=true
bid_ask_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
bid_ask_data

# %% hidden=true
start_timestamp = pd.Timestamp("2023-02-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-02-28 00:00:00+00:00")
reader.read_data(start_timestamp, end_timestamp)

# %% [markdown] hidden=true
# ### Errors

# %% [markdown] hidden=true
# - wrong timestamps

# %% [markdown] heading_collapsed=true hidden=true
# ## Trades

# %% hidden=true
signature = "bulk.manual.downloaded_1min.parquet.trades.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 20:30:00+00:00")

# %% hidden=true
reader.read_data(start_timestamp, end_timestamp)

# %% [markdown] hidden=true
# ### Errors

# %% [markdown] hidden=true
# - no data

# %% [markdown] heading_collapsed=true
# # Crypto_chassis

# %% [markdown] hidden=true
# ## Preview availability	 of the symbols

# %% hidden=true
import requests

resp = requests.get("https://api.cryptochassis.com/v1/information?exchange=okex&dataType=market-depth")


# %% hidden=true
data = pd.DataFrame(resp.json())

# %% hidden=true
data.head().availability[0]

# %% hidden=true
data.head()

# %% hidden=true
data.instrument.unique()

# %% [markdown] hidden=true
# ### Compare symbols sets

# %% hidden=true
data_frequency = "T"
vendor_name = "crypto_chassis"
mode = "download"
version = "v7.3"
exchange_id = "okex"
universe = imvcounun.get_vendor_universe(
    vendor_name,
    mode,
    version=version)

# %% hidden=true
symbols = pd.Series(universe[exchange_id]).str.lower()

# %% hidden=true
symbols = symbols.str.replace("_", "-")

# %% hidden=true
symbols

# %% hidden=true
symbols[symbols.isin(data.instrument)]

# %% [markdown] hidden=true
# ## Download to parquet and preview

# %% [markdown] hidden=true
# ### Bid_ask

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okex' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'bid_ask' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ### Preview bid_ask

# %% hidden=true
signature = "bulk.manual.downloaded_1min.parquet.bid_ask.spot.v7_3.crypto_chassis.okex.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 20:30:00+00:00")

# %% hidden=true
bid_ask_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
bid_ask_data.head()

# %% [markdown] hidden=true
# ### trades

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okex' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] heading_collapsed=true hidden=true
# ### trades preview

# %% hidden=true
signature = "bulk.manual.downloaded_1min.parquet.trades.spot.v7_3.crypto_chassis.okex.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 20:30:00+00:00")

# %% hidden=true
trades_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
trades_data.head()

# %% [markdown] heading_collapsed=true
# # QA checks

# %% hidden=true
data_frequency = "T"
vendor_name = "CCXT"
mode = "download"
version = "v7.3"
exchange_id = "okx"
start_timestamp = pd.Timestamp("2023-01-01 10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-01 17:30:00+00:00")
universe = imvcounun.get_vendor_universe(
    vendor_name,
    mode,
    version=version)
universe_list = universe[exchange_id]


# %% hidden=true
qa_check_list = [
    imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        start_timestamp,
        end_timestamp,
        data_frequency
    ),
    imvcdqqach.NaNChecks(),
    imvcdqqach.OhlcvLogicalValuesCheck(),
    imvcdqqach.FullUniversePresentCheck(universe_list)
]
dataset_validator = imvcdqdava.SingleDataFrameDatasetValidator(qa_check_list)


# %% hidden=true
dataset_validator.run_all_checks([ohlcv_data], _LOG)

# %% hidden=true
len(ohlcv_data[ohlcv_data.volume == 0])

# %% hidden=true
len(ohlcv_data)

# %% [markdown] heading_collapsed=true
# # CmTask3791: airflow download bulk  - QA

# %% [markdown] hidden=true
# ## OHLCV - futures

# %% hidden=true
signature = "bulk.airflow.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2021-01-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-05-01 00:00:00+00:00")

# %% hidden=true
ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
ohlcv_data

# %% hidden=true
data_frequency = "T"
vendor_name = "CCXT"
mode = "download"
version = "v7.3"
exchange_id = "okx"
universe = imvcounun.get_vendor_universe(
    vendor_name,
    mode,
    version=version)
universe_list = universe[exchange_id]


# %% hidden=true
qa_check_list = [
    imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        start_timestamp,
        end_timestamp,
        data_frequency
    ),
    imvcdqqach.NaNChecks(),
    imvcdqqach.OhlcvLogicalValuesCheck(),
    imvcdqqach.FullUniversePresentCheck(universe_list)
]
dataset_validator = imvcdqdava.SingleDataFrameDatasetValidator(qa_check_list)


# %% hidden=true
dataset_validator.run_all_checks([ohlcv_data], _LOG)

# %% hidden=true
len(ohlcv_data[ohlcv_data.volume == 0])

# %% [markdown] hidden=true
# ## bid_ask - spot

# %% [markdown] hidden=true
# ### bid_ask - probe download

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okex' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'bid_ask' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% hidden=true

# %% [markdown] hidden=true
# ### bid_ask - preview

# %% hidden=true
signature = "bulk.airflow.downloaded_1min.parquet.bid_ask.spot.v4.crypto_chassis.okex.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-01-06 00:00:00+00:00")

# %% hidden=true
bid_ask_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
bid_ask_data.head()

# %% hidden=true
bid_ask_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="s")

# %% hidden=true
bid_ask_data.columns

# %% hidden=true
bid_ask_data.currency_pair.unique()

# %% hidden=true
bid_ask_data.exchange_id.unique()

# %% [markdown] hidden=true
# ## trades - spot

# %% [markdown] hidden=true
# ### trades - probe download

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-01-01 10:00:00+00:00' \
#     --end_timestamp '2023-01-01 20:30:00+00:00' \
#     --exchange_id 'okex' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ### trades - preview

# %% hidden=true
signature = "bulk.airflow.downloaded_1min.parquet.trades.spot.v4.crypto_chassis.okex.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-02-01 00:00:00+00:00")

# %% hidden=true
trades_data = reader.read_data(start_timestamp, end_timestamp)

# %% hidden=true
trades_data.head()

# %% hidden=true
trades_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="s")

# %% hidden=true
trades_data.columns

# %% hidden=true
trades_data.currency_pair.unique()

# %% hidden=true
trades_data.exchange_id.unique()
