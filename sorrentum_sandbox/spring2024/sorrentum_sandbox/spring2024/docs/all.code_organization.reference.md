

<!-- toc -->

- [Code organization of `amp`](#code-organization-of-amp)
  * [Conventions](#conventions)
  * [Finding deps](#finding-deps)
    + [Using `invoke find_dependency`](#using-invoke-find_dependency)
    + [Using grep](#using-grep)
    + [Using Pydeps](#using-pydeps)
  * [Component dirs](#component-dirs)
    + [`helpers/`](#helpers)
    + [`core/`](#core)
    + [`devops/`](#devops)
    + [`dev_scripts/`](#dev_scripts)
    + [`im/`](#im)
    + [`market_data/`](#market_data)
    + [`dataflow/`](#dataflow)
  * [dataflow dependencies](#dataflow-dependencies)
  * [Top level dirs](#top-level-dirs)
- [Invariants](#invariants)
- [Misc](#misc)

<!-- tocstop -->

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

Useful utilities are:
```
> dev_scripts/vi_all_py.sh im

> tree.sh -d 1 -p im_v2/ccxt/data
im_v2/ccxt/data/
|-- client/
|-- extract/
|-- qa/
`-- __init__.py

4 directories, 1 file
```

### `helpers/`

- `helpers/`
  - """Low-level helpers that are general and not specific of this project"""

### `core/`

- `core/`
  - """Low-level helpers that are specific of this project"""
  - `/config`
    - `Config`
      - """A dict-like object that allows to configure workflows"""
  - `event_study/`
  - `artificial_signal_generators.py`
  - `features.py`
  - `finance.py`
  - `signal_processing.py`
  - `statistics.py`

### `devops/`

- `devops/`
  - TODO(gp): reorg

### `dev_scripts/`

- `/dev_scripts`
  - TODO(gp): reorg

### `im/`

- `sorrentum_sandbox/`
  - `common/`
    - `validate.py`: implement `QaCheck` and `DatasetValidator`
    - TODO(gp): Move this to im_v2

- `im/`
  - TODO(gp): Merge with im_v2

- `im_v2/`
  - TODO(gp): Rename `im_v2` to `datapull`
  - `airflow/`
    - """Airflow DAGs for downloading, archiving, QA, reconciliation"""
    - `airflow_utils/`
  - `aws/`
    - """Deploy Airflow DAGs definition"""
    - `aws_update_task_definition.py`
  - `binance/`
    - """ETL for Binance data"""
  - `bloomberg/`
    - """ETL for Bloomberg data"""
  - `ccxt/`
    - """ETL for CCXT"""
    - `data/`
      - `client`
      - `extract`
        - `extractor.py`
      - `qa`
    - `db/`
    - `universe/`
    - `utils.py`
  - `common/`
    - `data/`
      - `client/`
        - """Objects to read data from ETL pipeline"""
      - `extract/`
        - """Scripts and utils to perform various extract functions"""
        - `extract_utils.py`: library functions
      - `qa/`
        - """Utils to perform QA checks"""
      - `transform/`
        - """Scripts and utils to transform data"""
        - E.g., convert PQ to CSV, resample data
        - `transform_utils.py`
    - `data_snapshot/`
    - `db/`
      - `db_utils.py`: manage IM Postgres DB
    - `extract/`
      - `extract_utils.py`
    - `universe/`
      - `full_symbol.py`: implement full symbol (e.g., `binance:BTC_USDT`)
      - `universe.py`: get universe versions and components
      - `universe_utils.py`
  - `crypto_chassis/`
    - """ETL for CryptoChassis"""
  - `devops/`
  - `ig/`
  - `kibot/`
  - `mock1/`

### `market_data/`

- `market_data/`
  - """Interface to read price data"""
  - `MarketData`
  - `ImClientMarketData`
  - `RealTimeMarketData`
  - `ReplayedMarketData`
  - TODO(gp): Move market_data to `datapull/market_data`

### `dataflow/`

- `dataflow/`
  - """DataFlow module"""
  - `core/`
    - `nodes/`
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
  - `pipelines/`
    - """DataFlow pipelines that use only `core` nodes"""
    - `event_study/`
    - `features/`
      - """General feature pipelines"""
    - `price/`
      - """Pipelines computing prices"""
    - `real_times/`
      - TODO(gp): -> dataflow/system
    - `returns/`
      - """Pipelines computing returns"""
    - `dataflow_example.py`
      - `NaivePipeline`
  - `system/`
    - """DataFlow pipelines with anything that depends on code outside of
      DataFlow"""
    - `source_nodes.py`
      - `DataSource`
      - `HistoricalDataSource`
      - `RealTimeDataSource`
    - `sink_nodes.py`
      - `ProcessForecasts`
    - `RealTimeDagRunner`
  - `model/`
    - """Code for evaluating a DataFlow model"""

- `oms/`
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
