# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Cross dataset Bid/Ask Data QA
#
# This notebook is used to perform quality assurance of cross dataset Bid/Ask data.
# As displayed below, the notebook assumes environment variables for the data QA parameters. The intended usage
# is via invoke target `dev_scripts.lib_tasks_data_qa.run_cross_dataset_qa_notebook`

# %% [markdown]
# ## Imports and logging

# %%
import argparse
import logging

import pandas as pd

import core.config as cconfig
import data_schema.dataset_schema_utils as dsdascut
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hprint as hprint
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.extract.data_qa as imvcdedaqa
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
config = config.to_dict()
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
#
# \#TODO(Juraj): It is assumed that the first dataset signature refers to the Postgres DB data

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
data2["timestamp"] = data2["timestamp"] * 1000

# %%
data2.head()

# %% [markdown]
# ### Preprocess raw data
# - remove columns unimportant for QA
# - remove duplicates

# %%
cols_to_keep = imvcdqqach.get_multilevel_bid_ask_column_names() + [
    "timestamp",
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
    vendor_name = signature["vendor"]
    vendor_name = vendor_name.upper() if vendor_name == "ccxt" else vendor_name
    mode = "download"
    version = signature["universe"].replace("_", ".")
    exchange_id = signature["exchange_id"]
    universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
    universe_list = universe[exchange_id]
    qa_check_list = [
        imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
            config["start_timestamp"], config["end_timestamp"], data_frequency
        ),
        imvcdqqach.FullUniversePresentCheck(universe_list),
    ]
    qa_check_lists.append(qa_check_list)

# %% [markdown]
# ### Cross dataset checks

# %%
# Set up accuracy threshold dict for bid/ask columns
# TODO(Juraj): Add support in the invocation to pass different values for different columns
accuracy_threshold_dict = {
    col: config["bid_ask_accuracy"]
    for col in imvcdqqach.get_multilevel_bid_ask_column_names()
}

# %%
cross_qa_check_list = [
    imvcdqqach.BidAskDataFramesSimilarityCheck(accuracy_threshold_dict)
]

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
try:
    # TODO(Juraj): bid/ask data quality is very variable when collected in realtime for a big universe.
    # _LOG.info("First dataset QA:")
    # dataset_validator1.run_all_checks([data1])
    _LOG.info("Second dataset QA:")
    dataset_validator2.run_all_checks([data2])
    _LOG.info("Cross dataset QA:")
    cross_dataset_validator.run_all_checks(datasets)
except Exception as e:
    # Pass information about success or failure of the QA
    #  back to the task that invoked it.
    data_qa_outcome = str(e)
    raise e
# If no exception was raised mark the QA as successful.
data_qa_outcome = "SUCCESS"

# %%
# This can be read by the invoke task to find out if QA was successful.
hio.to_file("/app/ck_data_reconciliation_outcome.txt", data_qa_outcome)
