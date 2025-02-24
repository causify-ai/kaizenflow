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
# # Description

# %% [markdown]
# Adapted from docs/dataflow/ck.run_batch_computation_dag.tutorial.ipynb
#
# Build and run Mock2

# %% [markdown]
# # Imports

# %%
import logging

import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Build DAG

# %% [markdown]
# Build a `DagBuilder` object that defines a model's configuration
# - `get_config_template()`: creates a configuration for each DAG Node
# - `_get_dag()`: specifies all the DAG Nodes and builds a DAG using these Nodes

# %%
import dataflow_amp.pipelines.mock2.mock2_pipeline as dapmmopi

dag_builder = dapmmopi.Mock2_DagBuilder()
dag_config = dag_builder.get_config_template()
print(dag_config)

# %%
# Plot the model.
dag = dag_builder.get_dag(dag_config)
dtfcore.draw(dag)

# %% [markdown]
# # Add a node with data

# %% [markdown]
# ## Build im_client

# %%
import im_v2.common.data.client.historical_pq_clients as imvcdchpcl

root_dir = "s3://cryptokaizen-data-test/v3/bulk"

im_client_config_dict = {
    "vendor": "bloomberg",
    "universe_version": "v1",
    "root_dir": root_dir,
    "partition_mode": "by_year_month",
    "dataset": "ohlcv",
    "contract_type": "spot",
    "data_snapshot": "",
    "download_mode": "manual",
    "downloading_entity": "",
    "aws_profile": "ck",
    "resample_1min": False,
    "version": "v1_0_0",
    "download_universe_version": "v1",
    "tag": "resampled_1min",
}

im_client = imvcdchpcl.HistoricalPqByCurrencyPairTileClient(
    **im_client_config_dict
)

# %%
# Show how to read the raw data through the `ImClient`.
full_symbols = ["us_market::MSFT"]
start_ts = end_ts = None
columns = None
filter_data_mode = "assert"
datapull_data = im_client.read_data(
    full_symbols, start_ts, end_ts, columns, filter_data_mode
)
display(datapull_data)

# %% [markdown]
# ## Read universe

# %%
import dataflow.universe as dtfuniver

universe_str = "bloomberg_v1-top1"
full_symbols = dtfuniver.get_universe(universe_str)
asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)

print(asset_ids)

# %% [markdown]
# ## Build market_data

# %%
import market_data as mdata

columns = None
columns_remap = None
market_data = mdata.get_HistoricalImClientMarketData_example1(
    im_client, asset_ids, columns, columns_remap
)

# %%
# Print data in market data format.
timestamp_column_name = "end_ts"
tmp_data = market_data.get_data_for_interval(
    start_ts, end_ts, timestamp_column_name, asset_ids
)
display(tmp_data)

# %% [markdown]
# ## Build a HistoricalDataSource

# %%
stage = "read_data"
multiindex_output = True
col_names_to_remove = ["start_ts"]
timestamp_column_name = "end_ts"
node = dtfsys.HistoricalDataSource(
    stage,
    market_data,
    timestamp_column_name,
    multiindex_output,
    col_names_to_remove=col_names_to_remove,
)

# %%
# Data in dataflow format.
node.fit()["df_out"]

# %%
dag.insert_at_head(node)
dtfcore.draw(dag)

# %%
# Run the DAG.
dag_runner = dtfcore.FitPredictDagRunner(dag)
dag_runner.set_fit_intervals(
    [
        (
            tmp_data.index.min(),
            tmp_data.index.max(),
        )
    ],
)
fit_result_bundle = dag_runner.fit()
#
result_df = fit_result_bundle.result_df
result_df.head()

# %%
result_df.dropna()
