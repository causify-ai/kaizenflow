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
# # DataFlow

# %% [markdown]
# ## Introduction

# %% [markdown]
# ### Purpose

# %% [markdown]
# DataFlow is a framework designed to
# - facilitate rapid and flexible prototyping
# - deploy pipelines from research to production without software re-writes
# - make complex data transformations understandable, repeatable, and debuggable

# %% [markdown]
# Though beyond the scope of this cookbook, we note that DataFlow
# - can simulate the entire flow from reading market data to placing trades
# - supports both point-in-time (to eliminate future peeking) and vectorized (for speed) simulations
# - supports parameter sweeps (e.g., a suite parametrized backtests)
# - utilizes caching and data tiling for time/memory optimization
# - provides detailed logging, with intermediate results and computational performance information

# %% [markdown]
# ### Key Concepts

# %% [markdown]
# DataFlow is a graph computing framework. The fundamental object is a DAG
# (Directed Acyclic Graph) that consists of Nodes (input/output or computational).

# %% [markdown]
# Many data transformations common in quantitative finance may be
# implemented by a DAG with a single source and a single sink.
# In these pipelines, data (e.g., market data) enters the
# pipeline through the source node and then proceeds to flow from
# one node to the next, never to revisit a previously visited node.

# %% [markdown]
# ### Features

# %% [markdown]
# Examples of operations that may be performed by nodes include:
# - Loading market data
# - Resampling OHLCV bars
# - Computing TWAP/VWAP when resampling
# - Calculating volatility of returns
# - Adjusting returns by volatility
# - Applying EMAs (or other filters) to signals
# - Performing per-asset operations, each requiring multiple features
# - Performing cross-sectional operations (e.g., factor residualization, Gaussian ranking)
# - Learning/applying a machine learning model (e.g., using `sklearn`)
# - Applying custom (user-written) functions to data

# %% [markdown]
# Further examples include nodes that maintain relevant trading
# state, or that interact with an external environment:
# - Updating and processing current positions
# - Performing portfolio optimization
# - Generating orders
# - Submitting orders to an API

# %% [markdown]
# ### Cookbook Outline

# %% [markdown]
# This cookbook provides examples of how to use DataFlow in quantitative finance.
#
# We first introduce the standard supported data format. Next we show how to
# build and run a DAG in a notebook. Finally, we provide examples of nodes
# and pipelines geared toward quantitative finance.

# %% [markdown]
# # Notebook imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
#

# %% [markdown]
# # The DataFlow data format

# %% [markdown]
# We begin by loading synthetic OHLCV bar data.
#
# Note that the asset ID's are integers.

# %%
# Generate synthetic OHLCV data.
tz = "America/New_York"
start_datetime = pd.Timestamp("2023-01-03 09:30:00", tz=tz)
end_datetime = pd.Timestamp("2023-01-03 11:30:00", tz=tz)
asset_ids = [101, 201, 301]
bar_duration = "5T"
#
random_ohlcv_bars = cofinanc.generate_random_ohlcv_bars(
    start_datetime,
    end_datetime,
    asset_ids,
    bar_duration=bar_duration,
)
_LOG.debug(hpandas.df_to_str(random_ohlcv_bars))

# %% [markdown]
# Next we
# - drop the "start_datetime" and "timestamp_df" columns
# - use "end_datetime" as the dataframe index
# - pivot on "asset_id" so that the dataframe has two levels of column indices
#   - the first level consists of features
#   - the second level consists of asset ids

# %%
# Put the synthetic data into "DataFlow format".
market_data = random_ohlcv_bars.drop(
    columns=["start_datetime", "timestamp_db"]
).pivot(index="end_datetime", columns="asset_id")
_LOG.debug(hpandas.df_to_str(market_data))

# %%
# The asset features appear as column level `0`:
display(market_data.columns.levels[0])
# The asset ids appear as column level `1`:
display(market_data.columns.levels[1])

# %% [markdown]
# # DataFlow DAGs and Nodes

# %% [markdown]
# ## Working with single nodes

# %% [markdown]
# DataFlow nodes can be used stand-alone outside of any DAG.
# Because every nontrivial DAG has at least one node, we introduce
# nodes before DAGs.

# %% [markdown]
# ### Wrapping a dataframe in a source node

# %% [markdown]
# A dataframe may be wrapped in a DataFlow source node. This functionality is
# useful in prototyping in a notebook and in writing unit tests.

# %%
# `nid` is short for "node id"
nid = "df_data_source"
df_data_source = dtfcore.DfDataSource(nid, market_data)

# %% [markdown]
# Two of the most important methods on a dataflow are `fit` and `predict`.
# These methods only differ if the node learns state, e.g., fits a
# smoothing parameter or learns regression coefficients. In those cases,
# setting appropriate `fit` and `predict` time intervals is important.
# This functionality will be demonstrated later in the cookbook.

# %% [markdown]
# The output of a dataflow node is a dictionary of dataframes. In most cases,
# the node has a single output, and "df_out" is the default dictionary key.

# %%
df_out_fit = df_data_source.fit()["df_out"]
_LOG.debug(hpandas.df_to_str(df_out_fit))

# %%
df_out_predict = df_data_source.predict()["df_out"]
_LOG.debug(hpandas.df_to_str(df_out_predict))

# %%
# Note that the two outputs agree, as expected.
(df_out_fit - df_out_predict).abs().sum().sum()

# %% [markdown]
# ### Using a single node to transform data

# %% [markdown]
# #### Example

# %% [markdown]
# Here we show how to use a single node to perform the operation of
# computing return from price.
#
# To perform this task, we use a general type of transformer node called
# `GroupedColDfToDfTransformer`. This node allows us to
# - specify features to analyze
# - perform an operation using those features per-asset
# - define the per-asset operation as a function that operates on a single-column-level dataframe
# - configure column names for the output(s)
#
# The user-define function can be specified as a regular python function or as a lambda.

# %%
# Prepare a DataFlow transformer node to compute percentage returns.
nid = "compute_rets_node"
compute_rets_node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=lambda x: x.pct_change(),
    in_col_groups=[("close",)],
    out_col_group=(),
    col_mapping={"close": "ret_0"},
)

# %%
# Run the node on the dataframe `market_data`.
compute_rets_df_out = compute_rets_node.fit(market_data)["df_out"]
_LOG.debug(hpandas.df_to_str(compute_rets_df_out))

# %% [markdown]
# Note that, by default, columns are appended. This behavior is configurable
# so that, if desired, input columns are discarded and only explicit outputs
# are preserved.

# %%
# Prepare a DataFlow transformer node to compute percentage returns
#  and only return percentage returns.
nid = "compute_rets_node_v2"
compute_rets_node_v2 = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=lambda x: x.pct_change(),
    in_col_groups=[("close",)],
    out_col_group=(),
    col_mapping={"close": "ret_0"},
    # This var is `True` by default.
    join_output_with_input=False,
)

# %%
compute_rets_v2_df_out = compute_rets_node_v2.fit(market_data)["df_out"]
_LOG.debug(hpandas.df_to_str(compute_rets_v2_df_out))


# %% [markdown]
# #### Example

# %% [markdown]
# Next we demonstrate a transformer node that requires multiple
# columns as input.

# %% run_control={"marked": true}
def compute_high_low_mean(df: pd.DataFrame) -> pd.DataFrame:
    result = (df["high"] + df["low"]) / 2
    result.name = "high_low_mean"
    return result.to_frame()


# %%
nid = "compute_high_low_mean_node"
compute_high_low_mean_node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=compute_high_low_mean,
    in_col_groups=[
        ("high",),
        ("low",),
    ],
    out_col_group=(),
)

# %%
compute_high_low_mean_df_out = compute_high_low_mean_node.fit(market_data)[
    "df_out"
]
_LOG.debug(hpandas.df_to_str(compute_high_low_mean_df_out))

# %% [markdown]
# ## Working with DAGs

# %% [markdown]
# We now introduce DataFlow DAGs.
#
# We begin by constructing an empty DAG. Next, we sequentially add
# computation nodes to the DAG. In this process, we will demonstrate
# ways to work with DAGs interactively in a notebook.

# %% [markdown]
# ### Instantiating a DAG

# %%
name = "my_dag"
dag = dtfcore.DAG(name=name)
# Note that DAG objects can print information about their state.
display(dag)

# %% [markdown]
# ### Adding nodes to a DAG

# %% [markdown]
# For single-sink DAGs, the method `append_to_tail()` may
# be used to add nodes to a DAG. If the DAG is empty, this simply
# adds the node to the DAG as its only node.
#
# Complementing `append_to_tail()` is the method `insert_to_head()`,
# valid for single-source DAGs. This can be useful in cases where one
# wants to build a DAG independent of a particular data source (and
# then insert a data source as the last step prior to execution).
#
# Adding nodes for more complicated DAG topologies involves calling two
# methods: (1) `add_node()`, which registers the node with the DAG, and
# (2) `connect()`, which requires specifying parent and child nids for
# creating a directed edge from `parent` to `child`.

# %%
nid = "df_data_source"
df_data_source = dtfcore.DfDataSource(nid, market_data)
dag.append_to_tail(df_data_source)

# %% [markdown]
# Note that appending a node is not idempotent, i.e., invoking
# `dag.append_to_tail(df_data_source)` a second time will attempt to
# add the `df_data_source` node to the graph a second time, appending it
# to the existing `df_data_source` node. In this particular example,
# the operation will fail because the `nid` is the same (DAGs are
# prohibited from having two nodes with the same node id).

# %%
# The node "df_data_source" now appears in the DAG string representation.
dag

# %% [markdown]
# Next, we append a return computation node to the DAG and again
# display the DAG's string representation.

# %%
nid = "compute_rets_node"
compute_rets_node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=lambda x: x.pct_change(),
    in_col_groups=[("close",)],
    out_col_group=(),
    col_mapping={"close": "ret_0"},
)

# %%
dag.append_to_tail(compute_rets_node)

# %%
dag

# %% [markdown]
# Whether a DAG has a single source may be determined by calling
# `has_single_source()`.
# The source nid of a single-source DAG may be identified by calling
# `get_unique_source()`.
# If the source is in fact not unique, then the method will assert.
#
# Analogous functions exist for determining whether a single sink
# exists and for extracting its nid in the event that it does.

# %%
# `dag` has a unique source.
dag.has_single_sink()

# %%
# This function returns the `nid` of the unique source.
dag.get_unique_source()

# %%
# `dag` has a unique sink.
dag.has_single_sink()

# %%
# This function returns the `nid` of the unique sink.
dag.get_unique_sink()

# %% [markdown]
# ### Visualizing a DAG

# %% [markdown]
# We may display the DAG in a notebook in the following way.

# %%
dtfcore.draw(dag)

# %% [markdown]
# The convenience function `dtfcore.draw_to_file()` may be used to save
# the image of the graph of a ".png" file.

# %% [markdown]
# ### Executing DAGs

# %% [markdown]
# DAGs are executed by specifying
# - the node whose results are desired
# - the mode of operation ("fit" or "predict")
#
# The function used for execution is `run_leq_node()`. As the naming
# suggests, all ancestor nodes of the result node specified are
# executed (always respecting topological order).
#
# Unless one deliberately introduces random effects in a DAG node,
# DAG execution is deterministic and idempotent, i.e.,
# running the same DAG in the same way on the same data
# yields the same results.

# %%
# An example DAG execution.
dag_df_out = dag.run_leq_node("compute_rets_node", "fit")["df_out"]
_LOG.debug(hpandas.df_to_str(dag_df_out))

# %% [markdown]
# Note that one need not specify the sink node when executing a DAG.
# Specifying execution up to an intermediate node or even source node
# is useful for verifying the correctness of data transformations and
# debugging potential issues or unexpected behavior.
#
# In the following example, we specify the source node.

# %%
dag_source_df_out = dag.run_leq_node("df_data_source", "fit")["df_out"]
_LOG.debug(hpandas.df_to_str(dag_source_df_out))

# %% [markdown]
# ### Interactive DAG construction in a notebook

# %% [markdown]
# In this section we introduce a feature of DAGs that can be particularly
# useful in interactive notebook sessions.
#
# A common workflow is to rapidly develop a prototype of a data transformation
# step in a notebook, then wrap the transformation in a DAG node or break it
# into a handful of steps, each with its own node.
#
# This process often involves some level of experimentation. For example, one
# may begin by wrapping a large transformation into a single node, only to
# decide later to split it into multiple nodes. Alternatively, one may decide
# to add a preprocessing step to the computational pipeline. In either case,
# the update requires making a change to the DAG.
#
# Changing the DAG can always be accomplished by re-instatiating the object
# and repeating the necessary construction steps. However, sometimes it is
# more convenient to alter the DAG in-place.
#
# The most basic ways to alter the DAG in-place are to use the following methods:
# - `add_node()`
# - `connect()`
# - `remove_node()`
#
# We note that calling `remove_node()` removes all connections to or from the
# node to be removed.
#
# In the default DAG mode, `mode="strict"`, `add_node()` is not idempotent.
# Calling it twice with the same node will result in an assertion.
# If, however, the DAG is instantiated with `mode="loose"`, then `add_node()`
# becomes idempotent in the sense that the DAG will be the same whether the
# method is invoked one time or multiple times.
#
# Beyond that behavior, invoking `add_node()` on a node that already belongs
# to the DAG will
# - Remove the node to be added
# - Remove all of that node's successors and incident edges
# - Re-add the node to the graph (but not incident edges or successors)
#
# This behavior makes it easier to re-run DAG construction notebook cells
# without requiring a complete re-instantiation and re-build. In order
# to take advantages of this behavior, one must use the lower-level methods
# `add_node()` and `connect()` rather than the convenience method `append_to_tail()`.

# %% [markdown]
# In the following, we demonstrate how to build a DAG with these methods
# and show how the behavior is idempotent.

# %%
name = "my_dag"
# The default `mode` is "strict".
mode = "loose"
dag = dtfcore.DAG(name=name, mode=mode)
# Note that DAG objects can print information about their state.
display(dag)

# %%
# Specify the data source node.
nid = "df_data_source"
df_data_source = dtfcore.DfDataSource(nid, market_data)
# Add the data source node to the DAG.
dag.add_node(df_data_source)
# Draw the DAG.
dtfcore.draw(dag)

# %%
# Call `add_node()` a second time.
dag.add_node(df_data_source)
# Draw the DAG.
dtfcore.draw(dag)

# %%
# Specify a return computation node.
nid = "compute_rets_node"
compute_rets_node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=lambda x: x.pct_change(),
    in_col_groups=[("close",)],
    out_col_group=(),
    col_mapping={"close": "ret_0"},
)
# Draw the DAG.
dtfcore.draw(dag)

# %%
# Add the return computation node to the graph.
dag.add_node(compute_rets_node)
# Connect the data source node to the return computation node.
dag.connect("df_data_source", "compute_rets_node")
# Draw the DAG.
dtfcore.draw(dag)

# %%
# Call `add_node()` a second time with `compute_rets_node`.
dag.add_node(compute_rets_node)
# Draw the DAG.
dtfcore.draw(dag)

# %%
# Re-connect the data source node to the return computation node.
dag.connect("df_data_source", "compute_rets_node")
# Draw the DAG.
dtfcore.draw(dag)

# %% [markdown]
# # Cookbook Examples

# %% [markdown]
# ## Resampling OHLCV bars

# %% [markdown]
# In this example, we resample OHLCV data, returning OHLCV columns as
# well as TWAP and VWAP prices computed from the input "close" prices.
#
# The output frequency of the data is specified with a string following
# pandas' semantics, e.g,. "10T" would denote 10 minutes, and "1B" would
# denote 1 business day.
#
# The resampling example provided here is not the only way to implement
# resampling. Any user-defined resampling procedure could be used instead.

# %%
# This controls the output data frequency.
resampling_rule = "30T"
# This is a configuration for the resampling node.
# - "in_col_groups" specifies the input columns to feed to the node
# - "out_col_group" is unused and should be set to an empty tuple
# - "transformer_kwargs" consists of arguments to be forward to `transformer_func`,
#   which in this case is `cofinanc.resample_bars()`. This may be replaced with any
#   user-defined function as desired.
# - "reindex_like_input" is `True` by default, but set to `False` here, because a
#   resampling operation in general changes the index
# - "join_output_with_input" is `True` by default (columns are appended), but set
#   to `False` here, since we wish to replace the input data with the resampled data
node_config = {
    "in_col_groups": [
        ("close",),
        ("high",),
        ("low",),
        ("open",),
        ("volume",),
    ],
    "out_col_group": (),
    "transformer_kwargs": {
        "rule": resampling_rule,
        "resampling_groups": [
            ({"close": "close"}, "last", {}),
            ({"high": "high"}, "max", {}),
            ({"low": "low"}, "min", {}),
            ({"open": "open"}, "first", {}),
            (
                {"volume": "volume"},
                "sum",
                {"min_count": 1},
            ),
            (
                {
                    "close": "twap",
                },
                "mean",
                {},
            ),
        ],
        "vwap_groups": [
            ("close", "volume", "vwap"),
        ],
    },
    "reindex_like_input": False,
    "join_output_with_input": False,
}
nid = "resample"
node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=cofinanc.resample_bars,
    **node_config,
)

# %%
# Execute the node.
df_out = node.fit(market_data)["df_out"]
_LOG.debug(hpandas.df_to_str(df_out))

# %%
