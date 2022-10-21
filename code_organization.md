<!--ts-->
   * [Code organization of amp](#code-organization-of-amp)
      * [Conventions](#conventions)
      * [Finding deps](#finding-deps)
         * [Using grep](#using-grep)
         * [Using Pydeps](#using-pydeps)
      * [Component dirs](#component-dirs)
      * [dataflow dependencies](#dataflow-dependencies)
      * [Top level dirs](#top-level-dirs)
         * [helpers](#helpers)
         * [core](#core)
         * [dataflow](#dataflow)
         * [im](#im)
         * [market_data](#market_data)
         * [oms](#oms)
         * [research_amp](#research_amp)
   * [All Python files](#all-python-files)
   * [Invariants](#invariants)
   * [Misc](#misc)



<!--te-->

# Code organization of `amp`

## Conventions

- In this code organization files we use the following conventions:
  - Comments: `"""foobar is ..."""`
  - Dirs and subdirs: `/foobar`
  - Files: `foobar.py`
  - Objects: `FooBar`
  - Markdown files: `foobar.md`

- The directories, subdirectory, objects are listed in order of their
  dependencies (from innermost to outermost)

- When there is a dir in one repo that has the same role of a dir in an included
  repo we add the suffix from the repo to make them unique
  - E.g., a `dataflow` dir in `lemonade` is called `dataflow_lem`

- We assume that there is no filename repeated across different repos
  - This holds for notebooks, tests, and Python files
  - To disambiguate we add a suffix to make it unique (e.g., `_lem`)

- Since the code is split in different repos for access protection reason, we
  assume that if the repos could be merged into a single one, then the
  corresponding dirs could be collapsed (e.g., `//amp/dataflow` and
  `//lime/dataflow_lem`) without violating the dependencies
  - TODO(gp): Not sure about this

- E.g.,
  - We want to build a `HistoricalDataSource` (from
    `//amp/dataflow/system/source_nodes.py`) with inside an
    `IgReplayedTimeMarketDataInterface` (from
    `//lime/market_data_lime/eg_market_data.py`)
  - The object could be called `IgHistoricalDataSource` since it's a
    specialization of an `HistoricalDataSource` using IG data
  - The file:
    - Can't go in `//lime/market_data` since `dataflow_lime` depends on
      `market_data`
    - Needs to go in `//lime/dataflow_lime/system`
    - Can be called `eg_historical_data_source.py`

## Finding deps

### Using `invoke find_dependency`

  ```
  > i find_dependency --module-name "amp.dataflow.model" --mode "find_lev2_deps" --ignore-helpers --only-module dataflow
  ```

### Using grep

- To check for dependencies between one module (e.g., `dataflow/model`) and
  another (e.g., `dataflow/system`):
  ```
  > (cd dataflow/model/; jackpy "import ") | grep -v notebooks | grep -v test | grep -v __init__ | grep "import dataflow.system" | sort
  ```

### Using Pydeps

- Install
  ```
  > pip install pydeps pip install dot
  ```

- Test on a small part of the repo:
  ```
  > pydeps . --only helpers -v --show-dot -o deps.dot
  ```

- Run on helpers
  ```
  > pydeps --only helpers -x helpers.test -x helpers.old -x
  > helpers.telegram_notify -vv --show-dot -o deps.html --max-bacon 2 --reverse
  ```

## Component dirs

- `/helpers`
  - """Low-level helpers that are general and not specific of this project"""

- `/core`
  - """Low-level helpers that are specific of this project"""
  - `/config`
    - `Config`
      - """An dict-like object that allows to configure workflows"""
  - `/event_study`
  - `artificial_signal_generators.py`
  - `features.py`
  - `finance.py`
  - `signal_processing.py`
  - `statitstics.py`

- `/devops`
- `/dev_scripts`
- `/documentation`

- `/im`
- `/im_v2`
  - """Instrument Master"""
  - `ImClient`
  - """Vendor specific `ImClient`s"""

- `/market_data`
  - """Interface to read price data"""
  - `MarketData`
  - `ImClientMarketData`
  - `RealTimeMarketData`
  - `ReplayedMarketData`

- `/dataflow`
  - """DataFlow module"""
  - `/core`
    - `/nodes`
      - """Implementation of DataFlow nodes that don't depend on anything
        outside of this directory"""
      - `base.py`
        - `FitPredictNode`
        - `DataSource`
      - `sources`
        - `FunctionDataSource`
        - `DfDataSource`
        - `ArmaDataSource`
      - `sinks.py`
        - `WriteCols`
        - `WriteDf`
      - `transformers.py`
      - `volatility_models.py`
      - `sklearn_models.py`
      - `unsupervided_sklearn_models.py`
      - `supervided_sklearn_models.py`
      - `regression_models.py`
      - `sarimax_models.py`
      - `gluonts_models.py`
      - `local_level_models.py`
      - `Dag`
      - `DagBuilders`
      - `DagRunners`
      - `ResultBundle`
  - `/pipelines`
    - """DataFlow pipelines that use only `core` nodes"""
    - `/event_study`
    - `/features`
      - """General feature pipelines"""
    - `/price`
      - """Pipelines computing prices"""
    - `/real_times`
      - TODO(gp): -> dataflow/system
    - `/returns`
      - """Pipelines computing returns"""
    - `dataflow_example.py`
      - `NaivePipeline`
  - `/system`
    - """DataFlow pipelines with anything that depends on code outside of
      DataFlow"""
    - `source_nodes.py`
      - `DataSource`
      - `HistoricalDataSource`
      - `RealTimeDataSource`
    - `sink_nodes.py`
      - `ProcessForecasts`
    - `RealTimeDagRunner`
  - `/model`
    - """Code for evaluating a DataFlow model"""

- `/oms`
  - """Order management system"""
  - `architecture.md`
  - `Broker`
  - `Order`
  - `OrderProcessor`
  - `Portfolio`
  - `ForecastProcessor`

- `/optimizer`

- `/research_amp`

## dataflow dependencies

- `dataflow/core`
  - Should not depend on anything in `dataflow`
- `dataflow/pipelines`
  - -> `core` since it needs the nodes
- `dataflow/model`
  - -> `core`
- `dataflow/backtest`
  - """contain all the code to run a backtest"""
  - -> `core`
  - -> `model`
- `dataflow/system`
  - -> `core`
  - -> `backtest`
  - -> `model`
  - -> `pipelines`

- TODO(gp): Move backtest up

## Top level dirs

```text
(cd amp; tree -L 1 -d --charset=ascii -I "*test*|*notebooks*" 2>&1 | tee /tmp/tmp)
.
|-- core
|-- dataflow
|-- helpers
|-- im
|-- im_v2
|-- infra
|-- market_data
|-- oms
|-- optimizer
`-- research_amp
```

### helpers

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" helpers 2>&1 | tee /tmp/tmp)

helpers
|-- README.md
|-- __init__.py
|-- build_helpers_package.sh
|-- cache.md
|-- cache.py
|-- csv_helpers.py
|-- dataframe.py
|-- datetime_.py
|-- dbg.py
|-- dict.py
|-- docker_manager.py
|-- env.py
|-- git.py
|-- hasyncio.py
|-- hnumpy.py
|-- hpandas.py
|-- hparquet.py
|-- htqdm.py
|-- htypes.py
|-- introspection.py
|-- io_.py
|-- joblib_helpers.md
|-- joblib_helpers.py
|-- jupyter.py
|-- lib_tasks.py
|-- list.py
|-- network.py
|-- numba_.py
|-- old
|   |-- __init__.py
|   |-- conda.py
|   |-- env2.py
|   |-- tunnels.py
|   `-- user_credentials.py
|-- open.py
|-- parser.py
|-- pickle_.py
|-- playback.md
|-- playback.py
|-- printing.py
|-- s3.py
|-- send_email.py
|-- sql.py
|-- system_interaction.py
|-- table.py
|-- telegram_notify
|   |-- README.md
|   |-- __init__.py
|   |-- config.py
|   |-- get_chat_id.py
|   `-- telegram_notify.py
|-- timer.py
|-- traceback_helper.py
|-- translate.py
|-- versioning.py
`-- warnings_helpers.py
```

### core

```test
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" core 2>&1 | tee /tmp/tmp)

core
|-- __init__.py
|-- architecture.md
|-- artificial_signal_generators.py
|-- bayesian.py
|-- config
|   |-- __init__.py
|   |-- builder.py
|   |-- config_.py
|   `-- utils.py
|-- covariance_shrinkage.py
|-- data_adapters.py
|-- event_study
|   |-- __init__.py
|   |-- core.py
|   `-- visualization.py
|-- explore.py
|-- feature_analyzer.py
|-- features.py
|-- finance.py
|-- information_bars
|   |-- __init__.py
|   `-- bars.py
|-- optimizer_baseline.py
|-- pandas_helpers.py
|-- plotting.py
|-- real_time.py
|-- real_time_example.py
|-- real_time_simple_model.py
|-- residualizer.py
|-- signal_processing.py
|-- statistics.py
`-- timeseries_study.py
```

### dataflow

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" dataflow 2>&1 | tee /tmp/tmp)

dataflow
|-- __init__.py
|-- core
|   |-- __init__.py
|   |-- dag_builder.py
|   |-- dag_builder_example.py
|   |-- dag.py
|   |-- dag_adapter.py
|   |-- node.py
|   |-- nodes
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- gluonts_models.py
|   |   |-- local_level_model.py
|   |   |-- regression_models.py
|   |   |-- sarimax_models.py
|   |   |-- sinks.py
|   |   |-- sklearn_models.py
|   |   |-- sources.py
|   |   |-- transformers.py
|   |   |-- types.py
|   |   |-- unsupervised_sklearn_models.py
|   |   `-- volatility_models.py
|   |-- result_bundle.py
|   |-- dag_runner.py
|   |-- utils.py
|   |-- visitors.py
|   `-- visualization.py
|-- dataflow_design.md
|-- model
|   |-- __init__.py
|   |-- architecture.md
|   |-- dataframe_modeler.py
|   |-- incremental_single_name_model_evaluator.py
|   |-- master_experiment.py
|   |-- model_evaluator.py
|   |-- model_plotter.py
|   |-- regression_analyzer.py
|   |-- run_experiment.py
|   |-- run_experiment_stub.py
|   |-- run_prod_model_flow.py
|   |-- stats_computer.py
|   `-- utils.py
|-- pipelines
|   |-- __init__.py
|   |-- dataflow_example.py
|   |-- event_study
|   |   |-- __init__.py
|   |   `-- pipeline.py
|   |-- features
|   |   |-- __init__.py
|   |   `-- pipeline.py
|   |-- price
|   |   |-- __init__.py
|   |   `-- pipeline.py
|   |-- real_time
|   |   `-- __init__.py
|   `-- returns
|       |-- __init__.py
|       `-- pipeline.py
|-- scripts
|   `-- process_experiment_result.py
`-- system
    |-- __init__.py
    |-- real_time_dag_adapter.py
    |-- real_time_dag_runner.py
    |-- research_dag_adapter.py
    |-- sink_nodes.py
    `-- source_nodes.py
```

### im

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" im 2>&1 | tee /tmp/tmp)

im
|-- Makefile
|-- README.md
|-- __init__.py
|-- airflow
                                - TODO(gp): Obsolete
|-- app
                                - TODO(gp): Obsolete
|-- architecture.md
|-- ccxt
|   |-- __init__.py
|   |-- data
|   |   `-- __init__.py
|   `-- db
|       `-- __init__.py
|-- code_layout.md
|-- common
|   |-- __init__.py
|   |-- data
|   |   |-- __init__.py
|   |   |-- extract
|   |   |   |-- __init__.py
|   |   |   `-- data_extractor.py
|   |   |-- load
|   |   |   |-- __init__.py
|   |   |   |-- abstract_data_loader.py
|   |   |   `-- file_path_generator.pyj
|   |   |-- transform
|   |   |   |-- __init__.py
|   |   |   |-- s3_to_sql_transformer.py
|   |   |   `-- transform.py
|   |   `-- types.py
|   |-- metadata
|   |   |-- __init__.py
|   |   `-- symbols.py
|   `-- sql_writer.py
|-- cryptodatadownload
|   `-- data
|       |-- __init__.py
|       `-- load
|           |-- __init__.py
|           `-- loader.py
|-- devops.old
                                - TODO(gp): Obsolete
|-- devops.old2
                                - TODO(gp): Obsolete
|-- eoddata
|   |-- __init__.py
|   `-- metadata
|       |-- __init__.py
|       |-- extract
|       |   `-- download_symbol_list.py
|       |-- load
|       |   |-- __init__.py
|       |   `-- loader.py
|       `-- types.py
|-- ib
|-- kibot
                                - TODO(gp): Move to im_v2
```

### market_data

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" market_data 2>&1 | tee /tmp/tmp)

market_data
|-- __init__.py
|-- market_data_client.py
|-- market_data_client_example.py
|-- market_data_interface.py
`-- market_data_interface_example.py
```

### oms

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" oms 2>&1 | tee /tmp/tmp)

oms
|-- __init__.py
|-- api.py
|-- architecture.md
|-- broker.py
|-- broker_example.py
|-- call_optimizer.py
|-- devops
|   |-- __init__.py
    ...
|-- invoke.yaml
|-- locates.py
|-- oms_db.py
|-- oms_lib_tasks.py
|-- oms_utils.py
|-- order.py
|-- order_example.py
|-- order_processor.py
|-- pnl_simulator.py
|-- pnl_simulator.py.numba
|-- portfolio.py
|-- portfolio_example.py
|-- process_forecasts.py
`-- tasks.py
```

### research_amp

```text
(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" research_amp 2>&1 | tee /tmp/tmp)

research_amp
`-- cc
    |-- __init__.py
    |-- detect_outliers.py
    |-- statistics.py
    `-- volume.py
```

# All Python files

```text
(cd amp; tree -v --prune --charset=ascii -P "*.py" -I "*test*|*notebooks*" 2>&1 | tee /tmp/tmp)

.
|-- __init__.py
|-- core
|   |-- __init__.py
|   |-- artificial_signal_generators.py
|   |-- bayesian.py
|   |-- config
|   |   |-- __init__.py
...
|-- setup.py
`-- tasks.py
```

# Invariants

- We assume that there is no file with the same name either in the same repo or
  across different repos
  - In case of name collision, we prepend as many dirs as necessary to make the
    filename unique
  - E.g., the files below should be renamed:

    ```bash
    > ffind.py utils.py | grep -v test
    ./amp/core/config/utils.py
      -> amp/core/config/config_utils.py

    ./amp/dataflow/core/utils.py
      -> amp/dataflow/core_config.py

    ./amp/dataflow/model/utils.py
      -> amp/dataflow/model/model_utils.py
    ```
  - Note that this rule makes the naming of files depending on the history, but
    it minimizes churn of names

# Misc

- To execute a vim command, go on the line

  ```bash
  :exec '!'.getline('.')
  :read /tmp/tmp
  ```

- To inline in vim

  ```bash
  !(cd amp; tree -v --charset=ascii -I "*test*|*notebooks*" market_data 2>&1 | tee /tmp/tmp)
  :read /tmp/tmp
  ```

- Print only dirs

  ```bash
  > tree -d
  ```

- Print only dirs up to a certain level

  ```bash
  > tree -L 1 -d
  ```

- Sort alphanumerically

  ```bash
  > tree -v
  ```

- Print full name so that one can also grep

  ```bash
  > tree -v -f --charset=ascii -I "*test*|*notebooks*" | grep amp | grep -v dev_scripts

  `-- dataflow/system
      |-- dataflow/system/__init__.py
      |-- dataflow/system/real_time_dag_adapter.py
      |-- dataflow/system/real_time_dag_runner.py
      |-- dataflow/system/research_dag_adapter.py
      |-- dataflow/system/sink_nodes.py
      `-- dataflow/system/source_nodes.py
  ```
