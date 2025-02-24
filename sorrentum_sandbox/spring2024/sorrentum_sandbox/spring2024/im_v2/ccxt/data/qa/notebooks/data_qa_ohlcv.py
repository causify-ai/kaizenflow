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
# # OHLCV Data QA
#
# This notebook is used to perform quality assurance of OHLCV data
# As displayed below, the notebook assumes environment variables for the data QA parameters. The intended usage
# is via invoke target `dev_scripts.lib_tasks_data_qa.run_single_dataset_qa_notebook`

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
    # bid_ask_accuracy needs to be cast to int if its defined
    config["bid_ask_accuracy"] = (
        int(config["bid_ask_accuracy"]) if config["bid_ask_accuracy"] else None
    )
    # bid_ask_depth needs to be cast to int if its defined
    # config["bid_ask_depth"] = int(config["bid_ask_depth"]) if config["bid_ask_depth"] else None
    _LOG.warning("Using config from env vars")
else:
    config_dict = {
        "stage": "test",
        "start_timestamp": "2024-02-12T00:00:00+00:00",
        "end_timestamp": "2024-02-13T00:00:00+00:00",
        "aws_profile": "ck",
        "dataset_signature": "periodic_daily.manual.downloaded_1min.postgres.ohlcv.futures.v8.ccxt.okx.v1_0_0",
        "data_type": "ohlcv",
    }
    config = cconfig.Config.from_dict(config_dict)
config

# %% [markdown]
# ### Parse dataset signature
#
# 1. Load dataset schema
# 2. Validate dataset signature
# 3. Parse dataset attributes to drive some of the QA configuration

# %%
dataset_schema = dsdascut.get_dataset_schema()
dsdascut.validate_dataset_signature(config["dataset_signature"], dataset_schema)

# %%
dataset_signature_as_dict = dsdascut.parse_dataset_signature_to_args(
    config["dataset_signature"], dataset_schema
)
dataset_signature_as_dict

# %% [markdown]
# ## Load Data

# %%
raw_data_client = imvcdcimrdc.RawDataReader(
    config["dataset_signature"], stage=config["stage"]
)

# %%
data = raw_data_client.read_data(
    pd.Timestamp(config["start_timestamp"]), pd.Timestamp(config["end_timestamp"])
)

# %%
data.head()

# %% [markdown]
# ### Preprocess raw data
# - remove ID column (postgres artifact)
# - remove duplicates

# %%
data = data.drop("id", axis=1)

# %%
data = data.drop_duplicates()

# %%
data.head()

# %% [markdown]
# ## Initialize QA checks

# %%
# TODO(Juraj): this behavior should be encapsulated in some utility function
data_frequency = "T" if "1min" in dataset_signature_as_dict["action_tag"] else "S"
vendor_name = dataset_signature_as_dict["vendor"].upper()
mode = "download"
version = dataset_signature_as_dict["universe"].replace("_", ".")
exchange_id = dataset_signature_as_dict["exchange_id"]
universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
universe_list = universe[exchange_id]

# %%
qa_check_list = [
    imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        config["start_timestamp"], config["end_timestamp"], data_frequency
    ),
    imvcdqqach.NaNChecks(),
    imvcdqqach.OhlcvLogicalValuesCheck(),
    imvcdqqach.FullUniversePresentCheck(universe_list),
]

# %% [markdown]
# ## Initialize QA validator

# %%
dataset_validator = imvcdqdava.DataFrameDatasetValidator(qa_check_list)

# %% [markdown]
# ## Run QA

# %%
try:
    dataset_validator.run_all_checks([data])
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
