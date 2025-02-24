# Model Deployment

<!-- toc -->

- [Prerequisites](#prerequisites)
- [Add unit tests](#add-unit-tests)
  * [System tests](#system-tests)
  * [Tiled tests](#tiled-tests)
  * [Reconciliation unit tests](#reconciliation-unit-tests)
- [Manual test run](#manual-test-run)
  * [Paper trading run](#paper-trading-run)
  * [System reconciliation](#system-reconciliation)
- [AirFlow scheduling](#airflow-scheduling)
  * [AirFlow DAGs](#airflow-dags)
  * [Add a new model](#add-a-new-model)
- [Implementation stages checklist](#implementation-stages-checklist)

<!-- tocstop -->

# Prerequisites

1. Research Stage Completion:
   - Ensure all necessary experiments have been successfully conducted for the
     model
2. Accessibility:
   - Storage: All models are currently stored in a private repository
   - Encryption and Accessibility: Models are encrypted and then moved to an
     accessible repository like `orange`. See
     [`/docs/dataflow/ck.release_encrypted_models.explanation.md`](/docs/dataflow/ck.release_encrypted_models.explanation.md)

# Add unit tests

\# TODO(Nina): move to a separate doc.

To ensure a model runs as expected in different modes, it is covered by unit
tests.

## System tests

- NonTime system tests\
  Run a model in the historical mode, i.e. there is no clock.

  Run `NonTime_ForecastSystem` DAG with the specified fit / predict method and
  using the backtest parameters from `SystemConfig`.

- Time system tests\
  Run a model with a replayed clock. Run `Time_ForecastSystem` with predict method:
  - Without `Portfolio`
  - With `DataFramePortfolio`
  - With `DatabasePortfolio` and `OrderProcessor`

See the full list of test cases:
[`/dataflow/system/system_test_case.py`](/dataflow/system/system_test_case.py).

See an implementation example for the toy model:
[`/dataflow_amp/system/mock1/test/test_mock1_forecast_system.py`](/dataflow_amp/system/mock1/test/test_mock1_forecast_system.py).

## Tiled tests

The goal is run a model using tiled backtest and check that an output is a valid
tiled result.

See the test case:
[`/dataflow/backtest/backtest_test_case.py`](/dataflow/backtest/backtest_test_case.py).

See implementation example for the toy model:
[`/dataflow_amp/system/mock1/test/test_mock1_tiledbacktest.py`](/dataflow_amp/system/mock1/test/test_mock1_tiledbacktest.py).

## Reconciliation unit tests

- NonTime system vs Time system

  Make sure that `NonTime_ForecastSystem` and `Time_ForecastSystem` produce the
  same predictions

- Time system with research portfolio vs Time system with DataFramePortfolio

  Reconcile `Time_ForecastSystem` and
  `Time_ForecastSystem_with_DataFramePortfolio`.

  It is expected that research PnL is strongly correlated with the PnL from
  Portfolio. 2 versions of PnL may differ by a constant so we use correlation to
  compare them instead of comparing the values directly.

  Add `ForecastEvaluatorFromPrices` to `Time_ForecastSystem` to compute research
  PnL.

- Time system with `DataFramePortfolio` vs Time system with `DatabasePortfolio`
  and `OrderProcessor`

  Test that the outcome is the same when running a `System` with a
  `DataFramePortfolio` vs running one with a `DatabasePortfolio`.

# Manual test run

Before scheduling via Airflow, perform a manual test run to ensure basic sanity
and reveal any obvious problems.

## Paper trading run

Run a model in the paper trading mode (mocked `Broker`) for a reasonable amount
of time (e.g., 1 hour) to check that the production system works well with a new
model.

The script to run a production system:
[`/dataflow_amp/system/Cx/scripts/run_Cx_prod_system.py`](/dataflow_amp/system/Cx/scripts/run_Cx_prod_system.py).

Replace `DAG_BUILDER_CTOR_AS_STR` with a path to a new model.

An example of a command line to run:

\# TODO(Nina): move to "prod_system.how_to_guide.md".

```bash
export RUN_DATE=$(date +'%Y%m%d')

# Path to a model and its short name.
export DAG_BUILDER_CTOR_AS_STR="dataflow_amp.pipelines.mock1.mock1_pipeline.Mock1_DagBuilder"
export DAG_BUILDER_NAME="Mock1"

# Run mode.
export RUN_MODE="paper_trading"

/app/amp/dataflow_amp/system/Cx/scripts/run_Cx_prod_system.py \
    --dag_builder_ctor_as_str $DAG_BUILDER_CTOR_AS_STR \
    --run_mode $RUN_MODE \
    --trade_date ${RUN_DATE} \
    --strategy $DAG_BUILDER_NAME \
    --liveness CANDIDATE \
    --exchange 'binance' \
    --instance_type PROD \
    --stage 'preprod' \
    --account_type 'trading' \
    --secret_id 3 \
    # For how long to run in seconds.
    --run_duration 3600 \
    --dst_dir ./system_log_dir_${RUN_DATE} \
    --log_file_name ./log_${RUN_DATE}.txt \
```

## System reconciliation

Run the system reconciliation flow to ensure that the replayed time simulation
produces the same results as the paper trading run.

It is expected that the paper trading PnL perfectly matches the one computed by
replayed time simulation.

See an example of a command line to run:
[`/docs/monitoring/ck.system_reconciliation.how_to_guide.md#run-the-whole-reconciliation-flow`](/docs/monitoring/ck.system_reconciliation.how_to_guide.md#run-the-whole-reconciliation-flow)

# AirFlow scheduling

Before adding a new model:

1. Run a 24-hour test (i.e. paper trading and system reconciliation) and review
   the system reconciliation notebook
2. Implement daily runs

## AirFlow DAGs

There is an existing AirFlow DAG that runs that the paper trading system and the
system reconciliation flow.

DAGs:

- Paper trading DAG:
  [`/docs/monitoring/ck.monitor_system.how_to_guide.md#paper-trading-system-dag`](/docs/monitoring/ck.monitor_system.how_to_guide.md#paper-trading-system-dag)
- PnL observer DAG
  [`/docs/monitoring/ck.monitor_system.how_to_guide.md#master-pnl-observer-dag`](/docs/monitoring/ck.monitor_system.how_to_guide.md#master-pnl-observer-dag)

## Add a new model

To add a new model, an AirFlow developer should include a new task in the DAG.
This essentially involves copying and pasting the command lines for execution
but replacing `dag_builder_ctor_as_str` (i.e., the full path to an existing
model) with the path to the new model.

See how to create new AirFlow DAG:
[`/docs/datapull/ck.create_airflow_dag.tutorial.md`](/docs/datapull/ck.create_airflow_dag.tutorial.md)

# Implementation stages checklist

- [ ] `SystemTestCase` unit tests
  - [ ] Non-time system unit tests
  - [ ] Time system unit tests
- [ ] TiledBacktest unit tests
- [ ] System reconciliation unit tests
  - [ ] Non-time system vs time system
  - [ ] Time system with research portfolio vs Time system with
        `DataFramePortfolio`
  - [ ] Time system with `DataFramePortfolio` vs Time system with
        `DatabasePortfolio` and `OrderProcessor`
- [ ] Manual paper trading run from dev server
- [ ] Scheduled AirFlow paper trading DAG
- [ ] PnL observer AirFlow DAG
- [ ] Multiday system reconciliation AirFlow DAG
