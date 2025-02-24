

<!-- toc -->

- [KaizenFlow computing](#kaizenflow-computing)
  * [Introduction](#introduction)
  * [DAG Node](#dag-node)
    + [DAG node examples](#dag-node-examples)
  * [DataFrame as unit of computation](#dataframe-as-unit-of-computation)
- [DAG execution](#dag-execution)
  * [Simulation kernel](#simulation-kernel)
  * [Implementation of simulation kernel](#implementation-of-simulation-kernel)
  * [Nodes ordering for execution](#nodes-ordering-for-execution)
  * [Heuristics for splitting code in nodes](#heuristics-for-splitting-code-in-nodes)

<!-- tocstop -->

# KaizenFlow computing

## Introduction

`KaizenFlow` is a computing framework to build and test AI/machine learning
models that can run:

- Without any changes in batch (i.e., historical) vs streaming mode (i.e.,
  real-time)
- Without any changes between replayed simulation (where events from a real or
  synthetic execution are played back) vs real-time (where the events are coming
  from a real-world time source)
- At different abstraction levels to trade off timing accuracy and speed, e.g.,
  - Timed (aka event-accurate) simulation
  - Non-timed (aka vectorized) simulation

The working principle underlying `DataFlow` is to run a model in terms of time
slices of data so that both batch/historical and streaming/real-time semantics
can be accommodated without any change in the model description.

Some of the advantages of the DataFlow approach are:

- Adapt a procedural description of a model to a reactive/streaming semantic
- Tiling to fit in memory
- Cached computation
- A clear timing semantic, which includes support for knowledge time and
  detection of future peeking
- Ability to replay and debug model executions

## DAG Node

A DAG Node is a unit of computation in the DataFlow model.

A DAG Node has:

- Inputs
- Outputs
- A unique node id (aka `nid`)
- A (optional) state Inputs and outputs to a DAG Node are dataframes
  (represented as `Pandas` dataframes). DAG node uses the inputs to compute the
  output (e.g., using `Pandas` and `Sklearn` libraries). A DAG node can execute
  in multiple "phases", referred to through the corresponding methods called on
  the DAG (e.g., `fit`, `predict`, `save_state`, `load_state`). A DAG node
  stores an output value for each output and method name.

TODO(gp): circle with inputs and outputs

### DAG node examples

Examples of operations that may be performed by nodes include:

- Loading data (e.g., market or alternative data)
- Resampling data bars (e.g., OHLCV data, tick data in finance)
- Computing rolling average (e.g., TWAP/VWAP, volatility of returns)
- Adjusting returns by volatility
- Applying EMAs (or other filters) to signals
- Performing per-feature operations, each requiring multiple features
- Performing cross-sectional operations (e.g., factor residualization, Gaussian
  ranking)
- Learning/applying a machine learning model (e.g., using sklearn)
- Applying custom (user-written) functions to data

Further examples include nodes that maintain relevant trading state, or that
interact with an external environment:

- Updating and processing current positions
- Performing portfolio optimization
- Generating trading orders
- Submitting orders to an API

**DataFlow model**. A DataFlow model (aka `DAG`) is a direct acyclic graph
composed of DataFlow nodes

It allows to connect, query the structure, ...

Running a method on a DAG means running that method on all its nodes in
topological order, propagating values through the DAG nodes.

TODO(gp): Add picture.

**DagConfig**. A `Dag` can be built assembling Nodes using a function
representing the connectivity of the nodes and parameters contained in a Config
(e.g., through a call to a builder `DagBuilder.get_dag(config)`).

A DagConfig is hierarchical and contains one subconfig per DAG node. It should
only include `Dag` node configuration parameters, and not information about
`Dag` connectivity, which is specified in the `Dag` builder part.

## DataFrame as unit of computation

The basic unit of computation of each node is a "dataframe". Each node takes
multiple dataframes through its inputs, and emits one or more dataframes as
outputs.

In mathematical terms, a DataFrame can be described as a two-dimensional labeled
data structure, similar to a matrix but with more flexible features.

A DataFrame $\mathbf{df}$ can be represented as:

$$
\mathbf{df} = \left[ \begin{array}{cccc}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn} \\
\end{array} \right]
$$

Where:

- $m$ is the number of rows (observations).
- $n$ is the number of columns (variables).
- $a_{ij}$ represents the element of the DataFrame in the $i$-th row and $j$-th
  column.

Some characteristics of dataframes are:

1. Labeled Axes:
   - Rows and columns are labeled, typically with strings, but labels can be of
     any hashable type.
   - Rows are often referred to as indices and columns as column headers.

2. Heterogeneous Data Types:
   - Each column $j$ can have a distinct data type, denoted as $dtype_j$
   - Common data types include integers, floats, strings, and datetime objects.

3. Mutable Size:
   - Rows and columns can be added or removed, meaning the size of $mathbf{df}$
     is mutable.
   - This adds to the flexibility compared to a traditional matrix.

4. Alignment and Operations:
   - DataFrames support alignment and arithmetic operations along rows and
     columns.
   - Operations are often element-wise but can be customized with aggregation
     functions.

5. Missing Data Handling:
   - DataFrames can contain missing data, denoted as `NaN` or a similar
     placeholder.
   - They provide tools to handle, fill, or remove missing data.

# DAG execution

## Simulation kernel

A computation graph is a directed graph where nodes represent operations or
variables, and edges represent dependencies between these operations.

For example, in a computation graph for a mathematical expression, nodes would
be operations like addition or multiplication, and edges would indicate which
operations need to be completed before others.

KaizenFlow simulation kernel schedules nodes according to their dependencies.

## Implementation of simulation kernel

The most general case of simulation consists of multiple loops:

1. Multiple DAG computations, each one inferred through a config belonging to a
   list of configs describing the entire workload

- Each DAG computation is independent, although pieces of computations can be
  common across the workload. These computations will be cached automatically as
  part of the framework execution

2. For each simulation, multiple train/predict loops can represent different
   learning styles (e.g., in-sample vs out-of-sample, cross-validation, rolling
   window)
   - This accommodates nodes with state

3. Each single DAG execution runs over a period of time
   - The time dimension is partitioned in tiles, as explained in other sections
     (see XYZ)
   - Note that tiles over time might overlap to accommodate the amount of memory
     needed by each node (see XYZ), thus each timestamp will be covered by at
     least tile. In the case of DAG nodes with no memory, then time is
     partitioned in non-overlapping tiles.
   - The tiling pattern over time doesn't affect the result as long as the
     system is properly designed (see XYZ)

4. Each temporal slice can be computed in terms of multiple sections across the
   horizontal dimension of the dataframe inputs
   - This is constrained by nodes that compute features cross-sectionally, which
     require the entire space slice to be computed at once

5. Finally a topological sorting based on the specific DAG connectivity is
   performed in order to execute nodes in the proper order

Note that it is possible to represent all the above constraints in a single
"scheduling graph" and use this graph to schedule executions in a global
fashion.

Parallelization across CPUs comes naturally from the previous approach, since
computations that are independent in the scheduling graph can be executed in
parallel.

Incremental and cached computation is built-in in the scheduling algorithm since
it's possible to memoize the output by checking for a hash of all the inputs and
of the code in each node.

Even though the computation DAG is required to have no loops, a System (see XYZ)
can have components introducing loops in the computation (e.g., a Portfolio
component in a trading system, where a DAG computes forecasts which are acted
upon based on the available funds). In this case, the simulation kernel needs to
enforce dependencies in the time dimension.

## Nodes ordering for execution

TODO(gp, Paul): Extend this to the multiple loop.

Topological sorting is a linear ordering of the vertices of a directed graph
such that for every directed edge from vertex u to vertex v, u comes before v in
the ordering. This sorting is only possible if the graph has no directed cycles,
i.e., it must be a Directed Acyclic Graph (DAG).

```python
def topological_sort(graph):
    visited = set()
    post_order = []

    def dfs(node):
        if node in visited:
            return
        visited.add(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor)
        post_order.append(node)

    for node in graph:
        dfs(node)

    return post_order[::-1]  # Reverse the post-order to get the topological order
```

## Heuristics for splitting code in nodes

There are degrees of freedom in splitting the work between various nodes of a
graph E.g., the same DataFlow computation can be described with several nodes or
with a single node containing all the code

The trade-off is often between several metrics:

- Observability
  - More nodes make it easier to:
    - Observe and debug intermediate the result of complex computation
    - Profile graph executions to understand performance bottlenecks
- Latency/throughput
  - More nodes:
    - Allow for better caching of computation
    - Allow for smaller incremental computation when only one part of the inputs
      change
    - Prevent optimizations performed across nodes
    - Incur in more simulation kernel overhead for scheduling
    - Allow more parallelism between nodes being extracted and exploited
- Memory consumption
  - More nodes:
    - Allow to partition the computation in smaller chunks requiring less
      working memory

A possible heuristics is to start with smaller nodes, where each node has a
clear function, and then merge nodes if this is shown to improve performance
