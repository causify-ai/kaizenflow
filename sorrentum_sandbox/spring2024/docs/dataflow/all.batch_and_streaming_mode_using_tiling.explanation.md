

<!-- toc -->

- [The property of tilability](#the-property-of-tilability)
  * [Temporal tiling](#temporal-tiling)
  * [Cross-sectional tiling](#cross-sectional-tiling)
  * [Temporal and cross-sectional tiling](#temporal-and-cross-sectional-tiling)
  * [Detecting incorrect tiled computations](#detecting-incorrect-tiled-computations)
  * [Benefits of tiled computation](#benefits-of-tiled-computation)
- [Batch vs streaming](#batch-vs-streaming)

<!-- tocstop -->

# The property of tilability

The working principle of a DataFlow computation is that nodes should be able to
compute their outputs from their inputs without a dependency on how the inputs
are partitioned along the dataframe axes of the inputs (e.g., the time and the
feature axes). When this property is valid we call a computation "tilable".

A slightly more formal definition is that a computation $f()$ is tilable if:

$$
f(dfX \cup dfY) = f(dfX) \cup f(dfY)
$$

where:

- $dfX$ and $dfY$ represent input dataframes (which can optionally) overlap
- $\cup$ is an operation of concat along consecutive
- $f()$ is a node operation

TODO(gp): In reality the property requires that feeding data, computing, and
then filtering is invariant, like

f(A, B)

$$
\forall t1 \le t2, t3 \le t4: \exists T:
f(A[t1 - T:t2] \cup A[t3 - T:t4])[t1:t4]
= f(A[t1 - T:t2])[t1:t4] \cup f(A[t3 - T:t4])[t1:t4]
$$

This property resembles linearity, in the sense that a transformation $f()$ is
invariant over partitioning of the data.

A sufficient condition for a DAG computation to be tileable, is for all the DAG
nodes to be tileable. The opposite is not necessarily trye, and not interest in
general, since we are interested in finding ways to describe the computation so
that it is tileable.

A node that has no memory, e.g., whose computation

Nodes can have "memory", where the output for a given tile depends on previous
tile. E.g., a rolling average has memory since samples with different timestamps
are combined together to obtain the results. A node with finite memory is always
tileable, while nodes with infinite memory are not necessarily tileable. If the
computation can be expressed in a recursive form across axes (e.g., an
exponentially weighted moving average for adjacent intervals of times), then it
can be made tileable by adding auxiliary state to store the partial amount of
computatin.

## Temporal tiling

In most computations there is a special axis that represents time and moves only
from past to future. The data along other axes represent (potentially
independent) features.

This is an easy requirement to enforce if the computation has no memory, e.g.,
in the following example of Python code using Pandas
```
df1 =
                      a         b
2023-01-01 08:00:00   10        20
2023-01-01 08:30:00   10        20
2023-01-01 09:00:00   10        20
2023-01-01 09:30:00   10        20

df2 =
                      a         b
2023-01-01 08:00:00   10        20
2023-01-01 08:30:00   10        20
2023-01-01 09:00:00   10        20
2023-01-01 09:30:00   10        20

dfo = df1 + df2
```

DataFlow can partition df1 and df2 in different slices obtaining the same
result, e.g.,
```
df1_0 =
                      a         b
2023-01-01 08:00:00   10        20
2023-01-01 08:30:00   10        20

df2_0 =
                      a         b
2023-01-01 08:00:00   10        20
2023-01-01 08:30:00   10        20

dfo_0 = df1_0 + df2_0

df1_1 =
                      a         b
2023-01-01 09:00:00   10        20
2023-01-01 09:30:00   10        20

df2_1 =
                      a         b
2023-01-01 09:00:00   10        20
2023-01-01 09:30:00   10        20

dfo_1 = df1_1 + df2_1

dfo = pd.concat([dfo_1, dfo_2])
```

Consider the case of a computation that relies on past values
```
dfo = df1.diff()
```

This computation to be invariant to slicing needs to be fed with a certain
amount of previous data
```
df1_0 =
                      a         b
2023-01-01 08:00:00   10        20
2023-01-01 08:30:00   10        20

dfo_0 = df1_0.diff()
dfo_0 = dfo_0["2023-01-01 08:00:00":"2023-01-01 08:30:00"]

df1_1 =
                      a         b
2023-01-01 08:30:00   10        20
2023-01-01 09:00:00   10        20
2023-01-01 09:30:00   10        20

dfo_1 = df1_1.diff()
dfo_1 = dfo_1["2023-01-01 09:00:00":"2023-01-01 09:30:00"]

dfo = pd.concat([dfo_1, dfo_2])
```

In general as long as the computation doesn't have infinite memory (e.g., an
exponentially weighted moving average)

This is possible by giving each nodes data that has enough history

Many interesting computations with infinite memory (e.g., EMA) can also be
decomposed in tiles with using some algebraic manipulations

- TODO(gp): Add an example of EMA expressed in terms of previous

Given the finite nature of real-world computing (e.g., in terms of finite
approximation of real numbers, and bounded computation) any infinite memory
computation is approximated to a finite memory one. Thus the tiling approach
described above is general, within any desired level of approximation.

The amount of history is function of a node

## Cross-sectional tiling

- The same principle can be applied to tiling computation cross-sectionally

- Computation that needs part of a cross-section need to be tiled properly to be
  correct
- TODO(gp): Make an example

## Temporal and cross-sectional tiling

- These two styles of tiling can be composed
- The tiling doesn't even have to be regular, as long as the constraints for a
  correct computation are correct

## Detecting incorrect tiled computations

- One can use the tiling invariance of a computation to verify that it is
  correct
- E.g., if computing a DAG gives different results for different tiled, then the
  amount of history to each node is not correct

## Benefits of tiled computation

- Another benefit of tiled computation is that future peeking (i.e., a fault in
  a computation that requires data not yet available at the computation time)
  can be detected by streaming the data with the same timing as the real-time
  data would do

A benefit of the tiling is that the compute frame can apply any tile safe
transformation without altering the computation, e.g.,

- Vectorization across data frames
- Coalescing of compute nodes
- Coalescing or splitting of tiles
- Parallelization of tiles and nodes across different CPUs
- Select the size of a tile so that the computation fits in memory

# Batch vs streaming

Once a computation can be tiled, the same computation can be performed in batch
mode (e.g., the entire data set is processed at once) or in streaming mode
(e.g., the data is presented to the DAG as it becomes available) yielding the
same result

This allows a system to be designed only once and be run in batch (fast) and
real-time (accurate timing but slow) mode without any change

In general the more data is fed to the system at once, the more likely is to
being able to increase performance through parallelization and vectorization,
and reducing the overhead of the simulation kernel (e.g., assembling/splitting
data tiles, bookkeeping), at the cost of a larger footprint for the working
memory

In general the smaller the chunks of data are fed to the system (with the
extreme condition of feeding data with the same timing as in a real-time
set-up), the more unlikely is a fault in the design it is (e.g., future peeking,
incorrect history amount for a node)

Between these two extremes is also possible to chunk the data at different
resolutions, e.g., feeding one day worth of data at the time, striking different
balances between speed, memory consumption, and guarantee of correctness
