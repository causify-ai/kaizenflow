# DataFlow

<!-- toc -->

  * [Config](#config)
    + [Config representation and properties](#config-representation-and-properties)
    + [Assigning and getting Config items](#assigning-and-getting-config-items)
  * [Time semantics](#time-semantics)
  * [Different views of System components](#different-views-of-system-components)
  * [Architecture](#architecture)
    + [Component invariants](#component-invariants)
  * [DataFlow computing](#dataflow-computing)
    + [Template configs](#template-configs)
  * [DataFlow Computation Semantics](#dataflow-computation-semantics)

<!-- tocstop -->

TODO(gp): Add an example of df with forecasts explaining the timing

## Different views of System components

**Different implementations of a component**. A DataFlow component is described
in terms of an interface and can have several implementations at different
levels of detail.

**Reference implementation**. A reference implementation is vendor-agnostic
implementation of a component (e.g., DataFrameImClient, DataFrameBroker)

**Vendor implementation**. A vendor implementation is a vendor-specific
implementation of a component (e.g., CcxtImClient, CcxtBroker).

**Mocked implementation**. A mocked implementation is a simulated version of a
vendor-specific component (e.g., a DataFrameCcxtBroker). A mocked component can
have the same timing semantics as the real-component (e.g., an asynchronous or
reactive implementation) or not.

## Architecture

In this section we summarize the responsibilities and the high level invariants
of each component of a `System`.

A `System` is represented in terms of a `Config`.

- Each piece of a `Config` refers to and configures a specific part of the
  `System`
- Each component should be completely configured in terms of a `Config`

### Component invariants

All data in components should be indexed by the knowledge time (i.e., when the
data became available to that component) in terms of current time.

Each component has a way to know:

- what is the current time (e.g., the real-time machine time or the simulated
  one)
- the timestamp of the current data bar it's working on

Each component

- should print its state so that one can inspect how exactly it has been
  initialized
- can be serialized and deserialized from disk
- can be mocked for simulating
- should save data in a directory as it executes to make the system observable

Models are described in terms of DAGs using the DataFlow framework

**Misc**. Models read data from historical and real-time data sets, typically
not mixing these two styles.

Raw data is typically stored in S3 bucket in the same format as it comes or in
Parquet format.

## DataFlow computing

Resampling VWAP (besides potential errors). This implies hardcoded formula in a
mix with resampling functions.

```python
vwap_approach_2 = (
        converted_data["close"] *
      converted_data["volume"]).resample(resampling_freq)
    ).mean() /
    converted_data["volume"].resample(resampling_freq).sum()
vwap_approach_2.head(3)
```

- TODO(gp): Explain this piece of code


### Template configs

- Are incomplete configs, with some "mandatory" parameters unspecified but
  clearly identified with `cconfig.DUMMY` value
- Have reasonable defaults for specified parameters
  - This facilitates config extension (e.g., if we add additional parameters /
    flexibility in the future, then we should not have to regenerate old
    configs)
- Leave dummy parameters for frequently-varying fields, such as `ticker`
- Should be completable and be completed before use
- Should be associated with a `Dag` builder

**DagBuilder**. It is an object that builds a DAG and has a
`get_config_template()` and a `get_dag()` method to keep the config and the Dag
in sync.

The client:

- calls `get_config_template()` to receive the template config
- fills / modifies the config
- uses the final config to call `get_dag(config)` and get a fully built DAG

A `DagBuilder` can be passed to other objects instead of `Dag` when the template
config is fully specified and thus the `Dag` can be constructed from it.

**DagRunner**. It is an object that allows to run a `Dag`. Different
implementations of a `DagRunner` allow to run a `Dag` on data in different ways,
e.g.,

- `FitPredictDagRunner`: implements two methods `fit` / `predict` when we want
  to learn on in-sample data and predict on out-of-sample data
- `RollingFitPredictDagRunner`: allows to fit and predict on some data using a
  rolling pattern
- `IncrementalDagRunner`: allows to run one step at a time like in real-time
- `RealTimeDagRunner`: allows to run using nodes that have a real-time semantic


