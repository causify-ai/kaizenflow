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

# %% [markdown]
# # Cross dataset OHLCV Data QA
#
# This notebook is used to perform quality assurance of cross dataset OHLCV data.
# As displayed below, the notebook assumes environment variables for the data QA parameters. The intended usage
# is via invoke target `dev_scripts.lib_tasks_data_qa.run_cross_dataset_qa_notebook`

# %% [markdown]
# ## Imports and logging

# %%
import logging

import pandas as pd

import core.config as cconfig
import data_schema.dataset_schema_utils as dsdascut
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hprint as hprint
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe.universe as imvcounun

# %% [markdown]
# ### Logging

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# ## QA parameters
#
# To assist debugging you can override any of the parameters after its loaded and rerun QA

# %%
env_var_name = "CK_DATA_RECONCILIATION_CONFIG"
config = cconfig.Config.from_env_var(env_var_name)

# %%
if config:
    config = config.to_dict()
else:
    config = {
        "stage": "preprod",
        "start_timestamp": "2024-01-03T20:12:00+00:00",
        "end_timestamp": "2024-01-03T20:50:00+00:00",
        "aws_profile": "ck",
        "dataset_signature1": "realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7_3.ccxt.binance.v1_0_0",
        "dataset_signature2": "periodic_daily.airflow.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.binance.v1_0_0",
        "bid_ask_accuracy": 1,
    }
# bid_ask_accuracy needs to be cast to int if its defined
config["bid_ask_accuracy"] = (
    int(config["bid_ask_accuracy"]) if config["bid_ask_accuracy"] else None
)
# bid_ask_depth needs to be cast to int if its defined
# config["bid_ask_depth"] = int(config["bid_ask_depth"]) if config["bid_ask_depth"] else None
config

# %% [markdown]
# ### Parse dataset signature
#
# 1. Load dataset schema
# 2. Validate dataset signature
# 3. Parse dataset attributes to drive some of the QA configuration

# %%
dataset_schema = dsdascut.get_dataset_schema()
dsdascut.validate_dataset_signature(config["dataset_signature1"], dataset_schema)
dsdascut.validate_dataset_signature(config["dataset_signature2"], dataset_schema)

# %%
dataset_signature_as_dict1 = dsdascut.parse_dataset_signature_to_args(
    config["dataset_signature1"], dataset_schema
)
dataset_signature_as_dict1

# %%
dataset_signature_as_dict2 = dsdascut.parse_dataset_signature_to_args(
    config["dataset_signature2"], dataset_schema
)
dataset_signature_as_dict2

# %% [markdown]
# ## Load Data
#
# TODO(Juraj): At the moment assume that first dataset argument is a DB dataset and second is from S3 because of small preprocessing operations needed before performing QA

# %% [markdown]
# ### First dataset

# %%
raw_data_client = imvcdcimrdc.RawDataReader(
    config["dataset_signature1"], stage=config["stage"]
)
data1 = raw_data_client.read_data(
    pd.Timestamp(config["start_timestamp"]), pd.Timestamp(config["end_timestamp"])
)

# %%
data1.head()

# %% [markdown]
# ### Second dataset

# %%
raw_data_client = imvcdcimrdc.RawDataReader(
    config["dataset_signature2"], stage=config["stage"]
)
data2 = raw_data_client.read_data(
    pd.Timestamp(config["start_timestamp"]), pd.Timestamp(config["end_timestamp"])
)
data2 = data2.reset_index(drop=True)

# %%
data2.head()

# %% [markdown]
# ### Preprocess raw data
# - remove columns unimportant for QA
# - remove duplicates

# %%
cols_to_keep = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency_pair",
    "exchange_id",
]
data1 = data1[cols_to_keep].sort_values(
    ["currency_pair", "timestamp"], ascending=True, ignore_index=True
)
data2 = data2[cols_to_keep].sort_values(
    ["currency_pair", "timestamp"], ascending=True, ignore_index=True
)

# %%
data1 = data1.drop_duplicates()
data2 = data2.drop_duplicates()

# %%
data1.head()

# %%
data2.head()

# %% [markdown]
# ## Initialize QA checks

# %% [markdown]
# ### Single dataset checks

# %%
datasets = [data1, data2]
signatures = [dataset_signature_as_dict1, dataset_signature_as_dict2]
qa_check_lists = []

# %%
for signature in signatures:
    # TODO(Juraj): this behavior should be encapsulated in some utility function
    data_frequency = "T" if "1min" in signature["action_tag"] else "S"
    vendor_name = signature["vendor"].upper()
    mode = "download"
    version = signature["universe"].replace("_", ".")
    exchange_id = signature["exchange_id"]
    universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
    universe_list = universe[exchange_id]
    qa_check_list = [
        imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
            config["start_timestamp"], config["end_timestamp"], data_frequency
        ),
        imvcdqqach.NaNChecks(),
        imvcdqqach.OhlcvLogicalValuesCheck(),
        imvcdqqach.FullUniversePresentCheck(universe_list),
        imvcdqqach.DuplicateDifferingOhlcvCheck(),
    ]
    qa_check_lists.append(qa_check_list)

# %% [markdown]
# ### Cross dataset checks

# %%
cross_qa_check_list = [imvcdqqach.OuterCrossOHLCVDataCheck()]

# %% [markdown]
# ## Initialize QA validators

# %%
dataset_validator1 = imvcdqdava.DataFrameDatasetValidator(qa_check_lists[0])
dataset_validator2 = imvcdqdava.DataFrameDatasetValidator(qa_check_lists[1])
cross_dataset_validator = imvcdqdava.DataFrameDatasetValidator(
    cross_qa_check_list
)

# %% [markdown]
# ## Run QA

# %%
full_error_msgs = []
status = "SUCCESS"
_LOG.info("First dataset QA:")
error_msgs = dataset_validator1.run_all_checks([data1], abort_on_error=False)
if error_msgs:
    full_error_msgs.append(error_msgs)
    _LOG.info(error_msgs)
    status = "FAILED"
_LOG.info("Second dataset QA:")
error_msgs = dataset_validator1.run_all_checks([data2], abort_on_error=False)
if error_msgs:
    full_error_msgs.append(error_msgs)
    _LOG.info(error_msgs)
    status = "FAILED"
_LOG.info("Cross dataset QA:")
error_msgs = cross_dataset_validator.run_all_checks(datasets, abort_on_error=False)
if error_msgs:
    full_error_msgs.append(error_msgs)
    _LOG.info(error_msgs)
    status = "FAILED"
# If no exception was raised mark the QA as successful.
data_qa_outcome = status
full_error_msgs = '\n'.join(full_error_msgs)

# %%
if data_qa_outcome == "FAILED":
    hdbg.dfatal(f"QA Check unsuccessful for atleast one of the dataset, with the following errors:\n {full_error_msgs}")


# %%
# This can be read by the invoke task to find out if QA was successful.
hio.to_file("/app/ck_data_reconciliation_outcome.txt", data_qa_outcome)

# %%
