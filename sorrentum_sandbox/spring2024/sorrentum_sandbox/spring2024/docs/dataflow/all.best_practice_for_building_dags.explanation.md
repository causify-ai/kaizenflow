

<!-- toc -->

- [Config](#config)
  * [Config builders](#config-builders)
- [DAG builders](#dag-builders)
  * [DAG builder methods](#dag-builder-methods)
  * [DAG and Nodes](#dag-and-nodes)
  * [Keeping `config` and `DagBuilder` in sync](#keeping-config-and-dagbuilder-in-sync)
  * [`DagBuilder` idiom](#dagbuilder-idiom)
  * [Invariants](#invariants)
  * [Make code easy to wrap code into `Nodes`](#make-code-easy-to-wrap-code-into-nodes)
  * [`ColumnTransformer`](#columntransformer)
  * [One vs multiple graphs](#one-vs-multiple-graphs)
  * [How to handle multiple features for a single instrument](#how-to-handle-multiple-features-for-a-single-instrument)
  * [How to handle multiple instruments?](#how-to-handle-multiple-instruments)
  * [How to handle multiple features with multiple instruments](#how-to-handle-multiple-features-with-multiple-instruments)
  * [Irregular DAGs](#irregular-dags)
  * [Namespace vs hierarchical config](#namespace-vs-hierarchical-config)
  * [How to know what is configurable](#how-to-know-what-is-configurable)
  * [DAG extension vs copying](#dag-extension-vs-copying)
  * [Reusing parameters across nodes' configs](#reusing-parameters-across-nodes-configs)
  * [Composing vs deriving objects](#composing-vs-deriving-objects)

<!-- tocstop -->

# Config

## Config builders

`Config`s can be built through functions that can complete a "template" config
with some parameters passed from the user

E.g.,

```python
def get_kibot_returns_config(symbol: str) -> cfg.Config:
    """
    A template configuration for `get_kibot_returns_dag()`.
    """
    ...
```

Config builders can be nested.

You can use put `nid_prefix` in the `DagBuilder` constructor, since `nid_prefix`
acts as a namespace to avoid `nid` collisions

# DAG builders

## DAG builder methods

- DAG builders accept a Config and return a DAG
- E.g.,

```python
def get_kibot_returns_dag(config: cfg.Config, dag: dtf.DAG) -> dtf.DAG:
"""

Build a DAG (which in this case is a linear pipeline) for loading Kibot
data and generating processed returns.

The stages are:
- read Kibot price data
- compute returns
- resample returns (optional)
- zscore returns (optional)
- filter returns by ATH (optional)
- `config` must reference required stages and conform to specific node
  interfaces
"""
```

Some DAG builders can also add nodes to user-specified or inferred nodes (e.g.,
a unique sink node) of an existing DAG. Thus builders allow one to build a
complex DAG by adding in multiple steps subgraphs of nodes.

DAG builders give meaningful `nid` names to their nodes. Collisions in graphs
built from multiple builders are avoided by the user through the judicious use
of namespace-like nid prefixes.

## DAG and Nodes

The DAG structure does not know about what data is exchanged between nodes.

- Structural assumptions, e.g., column names, can and should be expressed
  through the config
- `dataflow/core.py` does not impose any constraints on the type of data that
  can be exchanged
- In practice (e.g., all concrete classes for nodes), we assume that
  `pd.DataFrame`s are propagated

The DAG `node`s are wrappers around Pandas dataframes

- E.g., if a node receives a column multi-index dataframe (e.g., with multiple
  instruments and multiple features per instruments), the node should, assuming
  a well-defined DAG and config, know how to melt and pivot columns

## Keeping `config` and `DagBuilder` in sync

- `Config` asserts if a `DagBuilder` tries to access a hierarchical parameter
  that doesn't exist and reports a meaningful error of what the problem is
- `Config` tracks what parameters are accessed by `DagBuilder` function
  - A method `sanity_check` is called after the DAG is completely built and
    reports a warning for all the parameters that were not used
  - This is mostly for a sanity check and debugging, so we don't assert

## `DagBuilder` idiom

When we build DAGs we use `DagBuilder` that call a constructor from `get_dag()`
with params from the `get_config()`
```
dag_builder = DagBuilder()
template_config = dag_builder.get_template_config()
# Complete the config.
config = template_config[...]
dag = dag_builder.get_dag(config)
```

## Invariants

Nodes of the DAG propagate dataframes

Dataframes can be column multi-index to represent higher dimensionality datasets
(e.g., multiple instruments, multiple features for each instrument)

The index of each dataframe is always composed of `datatime.datetime`

- For performance reasons, we prefer to use a single time zone (e.g., ET) in the
  name of the columns rather than using `datetimes` with `tzinfo`

We assume that dataframes are aligned in terms of timescale

- I.e., the DAG has nodes that explicitly merge / align dataframes
- When data sources have different time resolutions, typically we perform outer
  merges either leaving nans or filling with forward fills

## Make code easy to wrap code into `Nodes`

We strive to write functions (e.g., from `signal_processing.py`) that:

- Can be wrapped in `Node`s

- Operate on `pd.Series` and can be easily applied to `pd.DataFrame` columns
  when needed using `apply_to_df` decorator, or operate on `pd.DataFrame`
  directly

- Return information about the performed operation, so that we can store this
  information in the `Node` info

- E.g., refer to `process_outliers()` as an example

## `ColumnTransformer`

`ColumnTransformer` is a very flexible `Node` class that can wrap a wide variety
of functions

- The function to use is passed to the `ColumnTransformer` constructor in the
  DAG builder

- Arguments to forward to the function are passed through `transformer_kwargs`

- Currently `ColumnTransformer` does not allow index-modifying changes (we may
  relax this constraint but continue to enforce it by default)

- `DataframeMethodRunner` can run any `pd.DataFrame` method supported and
  forwards kwargs

## One vs multiple graphs

- We still don't have a final answer about this design issue
- Pros of one graph:
  - Everything is in one place
  - One config for the whole graph
- Pros of multiple graphs:
  - Easier to parallelize
  - Easier to manage memory
  - Simpler to configure (maybe), e.g., templatize config
  - One connected component (instead of a number depending upon the number of
    tickers)

## How to handle multiple features for a single instrument

- E.g., `close` and `volume` for a single futures instrument
- In this case we can use a dataframe with two columns `close_price` and
  `volume`
- The solution is to keep columns in the same dataframe either if they are
  processed in the same way (i.e., vectorized) or if the computing node needs to
  have both features available (like sklearn model)
- If close_price and volume are "independent", they should go in different
  branches of the graph using a "Y" split

## How to handle multiple instruments?

- E.g., `close` price for multiple futures
- We pass a dataframe with one column per instrument
- All the transformations are then performed on a column-basis
- We assume that the timeseries are aligned explicitly

## How to handle multiple features with multiple instruments

- E.g., close price, high price, volume for multiple energy futures instrument
- In this case we can use a dataframe with hierarchical columns, where the first
  dimension is the instrument, and the second dimension is the feature

## Irregular DAGs

- E.g., if we have 10 instruments that need to use different models, we could
  build a DAG, instantiating 10 different pipelines

- In general, we try to use vectorization any time that is possible

- E.g., if the computation is the same, instantiate a single DAG working on all
  the 10 instruments in a single dataframe (i.e., vectorization)

- E.g,. if the computation is the same up to until a point, vectorize the common
  part, and then split the dataframe and use different pipelines

## Namespace vs hierarchical config

- We recognize that sometimes we might want to call the same `DagBuilder`
  function multiple times (e.g., a DAG that is built with a loop)
- In this case it's not clear if it would be better to prefix the names of each
  node with a tag to make them unique or use hierarchical DAG
- It seems simpler to use prefix for the tags, which is supported

## How to know what is configurable

- By design, DataFlow can loosely wrap Python functions

- Any argument of the Python function could be a configuration parameter

- `ColumnTransformer` is an example of an abstract node that wraps python
  functions that operate on columns independently

- Introspection to determine what is configurable would be best

- Manually specifying function parameters in config may be a reasonable approach
  for now

- This could be coupled with moving some responsibility to the `Config` class,
  e.g., specifying "mandatory" parameters along with methods to indicate which
  parameters are "dummies"

- Introspection on config should be easy (but may be hard in full generality on
  DAG building code)

- Having the builder completely bail out is another possible approach

- Dataflow provides mechanisms for conceptually organizing config and mapping
  config to configurable functions. This ability is more important than making
  it easy to expose all possible configuration parameters.

## DAG extension vs copying

- Currently DAG builders are chained by progressively extending an existing DAG

- Another approach is to chain builders by constructing a new DAG from smaller
  component DAGs

- On the one hand, this
  - May provide cleaner abstractions
  - Is functional

- On the other hand, this approach may require some customization of deep copies
  (to be determined)

- If we have clean configs and builders for two DAGs to be merged / unioned,
  then we could simply rebuild by chaining

- If one of the DAGs was built through, e.g., notebook experimentation, then a
  graph-introspective deep copy approach is probably needed

- If we perform deep copies, do we want to create new "uninitialized" nodes, or
  also copy state?

- The answer may depend upon the use case, e.g., notebooks vs production

- Extending DAGs node by node is in fact how they are built under the hood

## Reusing parameters across nodes' configs

- The same parameter might need to be used by different objects / functions and
  DAG nodes and kept in sync somehow

- E.g., the `start_datetime` for the reading node and for the `ReplayedTime`
- Solution #1:
  - A "late binding" approach: in the config there is a `ConfigParam` specifying
    the path of the corresponding value to use
- Solution #2:
  - A "meta_parameter" Config key with all the parameters used by multiple nodes

## Composing vs deriving objects

We have a lot of composition of objects to create specialized versions of
objects E.g., there is an `HistoricalDataSource` node that allows to connect an
`AbstractMarketDataInterface` to a graph

**Approach 1)**

We could create a class for each specialization of `DataSource` object

```python
class EgHistoricalDataSource(HistoricalDataSource):
  """
  A `HistoricalDataSource` with a `EgReplayedTimeMarketDataInterface` inside.
  """

  def __init__(
     self,
     nid: dtfcore.NodeId,
     market_data_interface: vltabaretimbar.EgReplayedTimeMarketDataInterface,
     ):
```

In this case we use inheritance

Pros:

- This specialized an `HistoricalDataSource` fixing some parameters that need to
  be fixed Cons:
- It does the cross-product of objects
- It introduces a new name that we need to keep track of

We can have further builder methods like `get_..._example1()` to create specific
objects for testing purposes

**Approach 2)**

We could create a builder method, like `get_EgHistoricalDataSource(params)`,
instead of a class In this case we use composition

This is in practice the same approach as 1), even from the way it is called
```python # This is an instance of class `EgHistoricalDataSource`. obj =
EgHistoricalDataSource(nid, ...)

     # This is an instance of class `HistoricalDataSource`.
     obj = get_EgHistoricalDataSource(nid, ...)
    ```

We can use both approaches 1) and 2) in the `DagBuilder` approach

Personally I prefer approach 2) since it avoids to create more classes An OOP
adage says "prefer composition over inheritance when possible"
