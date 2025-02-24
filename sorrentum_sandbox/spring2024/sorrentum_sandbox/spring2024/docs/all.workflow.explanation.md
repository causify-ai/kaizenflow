

<!-- toc -->

- [KaizenFlow workflow explanation](#kaizenflow-workflow-explanation)
- [Set-up](#set-up)
- [Quant workflows](#quant-workflows)
  * [`DataPull`](#datapull)
  * [`DataFlow`](#dataflow)
    + [Meta](#meta)
    + [DAG](#dag)
    + [System](#system)
- [Quant dev workflows](#quant-dev-workflows)
  * [DataPull](#datapull)
  * [DataFlow](#dataflow)
- [TradingOps workflows](#tradingops-workflows)
  * [Trading execution](#trading-execution)
    + [Intro](#intro)
    + [Components](#components)
    + [Testing](#testing)
    + [Procedures](#procedures)
- [MLOps workflows](#mlops-workflows)
  * [Deploying](#deploying)
  * [Monitoring](#monitoring)
- [Devops workflows](#devops-workflows)

<!-- tocstop -->

# KaizenFlow workflow explanation

This document is a roadmap of most activities that Quants, Quant devs, and
Devops can perform using `KaizenFlow`.

For each activity we point to the relevant resources (e.g., documents in `docs`,
notebooks) in the repo.

A high-level description of KaizenFlow is
[KaizenFlow White Paper](/papers/DataFlow_stream_computing_framework/DataFlow_stream_computing_framework.pdf)

# Set-up

- TODO(gp): Add pointers to the docs we ask to read during the on-boarding

<!-- ####################################################################### -->

# Quant workflows

<!-- ####################################################################### -->

The life of a Quant is spent between:

- Exploring the raw data
- Computing features
- Building models to predict output given features
- Assessing models

These activities are mapped in `KaizenFlow` as follows:

- Exploring the raw data
  - This is performed by reading data using `DataPull` in a notebook and
    performing exploratory analysis
- Computing features
  - This is performed by reading data using `DataPull` in a notebook and
    creating some `DataFlow` nodes
- Building models to predict output given features
  - This is performed by connecting `DataFlow` nodes into a `Dag`
- Assessing models
  - This is performed by running data through a `Dag` in a notebook or in a
    Python script and post-processing the results in an analysis notebook
- Comparing models
  - The parameters of a model are exposed through a `Config` and then sweep over
    `Config` lists

<!-- /////////////////////////////////////////////////////////////////////// -->

## `DataPull`

- General intro to `DataPull`
  - [/docs/datapull/ck.datapull.explanation.md](/docs/datapull/ck.datapull.explanation.md)
  - [/docs/datapull/all.datapull_qa_flow.explanation.md](/docs/datapull/all.datapull_qa_flow.explanation.md)
  - [/docs/datapull/all.datapull_client_stack.explanation.md](/docs/datapull/all.datapull_client_stack.explanation.md)
  - [/docs/datapull/all.datapull_sandbox.explanation.md](/docs/datapull/all.datapull_sandbox.explanation.md)
  - [/docs/datapull/ck.ccxt_exchange_timestamp_interpretation.reference.md](/docs/datapull/ck.ccxt_exchange_timestamp_interpretation.reference.md)

- Onboard new exchange
  - [/docs/datapull/ck.onboarding_new_exchnage.md](/docs/datapull/ck.onboarding_new_exchnage.md)

- Universe explanation
  - [/docs/datapull/ck.universe.explanation.md](/docs/datapull/ck.universe.explanation.md)

- Analyze universe metadata
  - [/im_v2/common/universe/notebooks/Master_universe_analysis.ipynb](/im_v2/common/universe/notebooks/Master_universe_analysis.ipynb)
  - [/im_v2/ccxt/notebooks/Master_universe.ipynb](/im_v2/ccxt/notebooks/Master_universe.ipynb)

- Organize and label datasets
  - Helps to uniquely identify datasets across different sources, types,
    attributes etc.
  - [/data_schema](/data_schema)
  - [/docs/datapull/ck.handle_datasets.how_to_guide.md](/docs/datapull/ck.handle_datasets.how_to_guide.md)

- Inspect RawData
  - [/im_v2/common/notebooks/Master_raw_data_gallery.ipynb](/im_v2/common/notebooks/Master_raw_data_gallery.ipynb)
  - [/im_v2/common/data/client/im_raw_data_client.py](/im_v2/common/data/client/im_raw_data_client.py)

- Convert data types
  - [/im_v2/common/data/transform/convert_csv_to_pq.py](/im_v2/common/data/transform/convert_csv_to_pq.py)
  - [/im_v2/common/data/transform/convert_pq_to_csv.py](/im_v2/common/data/transform/convert_pq_to_csv.py)

- Data download pipelines explanation
  - [/docs/datapull/ck.binance_bid_ask_data_pipeline.explanation.md](/docs/datapull/ck.binance_bid_ask_data_pipeline.explanation.md)
  - [/docs/datapull/ck.binance_ohlcv_data_pipeline.explanation.md](/docs/datapull/ck.binance_ohlcv_data_pipeline.explanation.md)

- Download data in bulk
  - [/im_v2/common/data/extract/download_bulk.py](/im_v2/common/data/extract/download_bulk.py)
  - [/im_v2/ccxt/data/extract/download_exchange_data_to_db.py](/im_v2/ccxt/data/extract/download_exchange_data_to_db.py)
  - TODO(Juraj): technically this could be joined into one script and also
    generalized for more sources

- Download data in real time over a given time interval
  - [/im_v2/ccxt/data/extract/download_exchange_data_to_db_periodically.py](/im_v2/ccxt/data/extract/download_exchange_data_to_db_periodically.py)

- Archive data
  - Helps with optimizing data storage performance/costs by transferring older
    data from a storage like postgres to S3
  - Suitable to apply to high frequency high volume realtime orderbook data
  - [/im_v2/ccxt/db/archive_db_data_to_s3.py](/im_v2/ccxt/db/archive_db_data_to_s3.py)

- Resampling data
  - [/docs/datapull/all.datapull_derived_data.explanation.md](/docs/datapull/all.datapull_derived_data.explanation.md)
  - [/im_v2/common/data/transform/resample_daily_bid_ask_data.py](/im_v2/common/data/transform/resample_daily_bid_ask_data.py)

- ImClient
  - [/docs/datapull/all.im_client.reference.ipynb](/docs/datapull/all.im_client.reference.ipynb)

- MarketData
  - [/docs/datapull/all.market_data.reference.ipynb](/docs/datapull/all.market_data.reference.ipynb)

- How to QA data
  - [/docs/datapull/ck.datapull_data_quality_assurance.reference.md](/docs/datapull/ck.datapull_data_quality_assurance.reference.md)
  - [/im_v2/ccxt/data/qa/notebooks/data_qa_bid_ask.ipynb](/im_v2/ccxt/data/qa/notebooks/data_qa_bid_ask.ipynb)
  - [/im_v2/ccxt/data/qa/notebooks/data_qa_ohlcv.ipynb](/im_v2/ccxt/data/qa/notebooks/data_qa_ohlcv.ipynb)
  - [/im_v2/common/data/qa/notebooks/cross_dataset_qa_ohlcv.ipynb](/im_v2/common/data/qa/notebooks/cross_dataset_qa_ohlcv.ipynb)
  - [/im_v2/common/data/qa/notebooks/cross_dataset_qa_bid_ask.ipynb](/im_v2/common/data/qa/notebooks/cross_dataset_qa_bid_ask.ipynb)
  - [/research_amp/cc/notebooks/Master_single_vendor_qa.ipynb](/research_amp/cc/notebooks/Master_single_vendor_qa.ipynb)
  - [/research_amp/cc/notebooks/Master_cross_vendor_qa.ipynb](/research_amp/cc/notebooks/Master_cross_vendor_qa.ipynb)
  - [/research_amp/cc/notebooks/compare_qa.periodic.airflow.downloaded_websocket_EOD.all.bid_ask.futures.all.ccxt_cryptochassis.all.v1_0_0.ipynb](/research_amp/cc/notebooks/compare_qa.periodic.airflow.downloaded_websocket_EOD.all.bid_ask.futures.all.ccxt_cryptochassis.all.v1_0_0.ipynb)

- How to load `Bloomberg` data
  - [/im_v2/common/notebooks/CmTask5424_market_data.ipynb](/im_v2/common/notebooks/CmTask5424_market_data.ipynb)
  - TODO: Generalize the name and make it Master\_

- Kibot guide
  - [/docs/datapull/ck.kibot_data.explanation.md](/docs/datapull/ck.kibot_data.explanation.md)
  - [/docs/datapull/ck.kibot_timing.reference.md](/docs/datapull/ck.kibot_timing.reference.md)

- Interactive broker guide
  - [/docs/datapull/ck.run_ib_connect.how_to_guide.md](/docs/datapull/ck.run_ib_connect.how_to_guide.md)
  - [/docs/datapull/ck.use_ib_metadata_crawler.how_to_guide.md](/docs/datapull/ck.use_ib_metadata_crawler.how_to_guide.md)

- How to run IM app
  [/docs/datapull/ck.run_im_app.how_to_guide.md](/docs/datapull/ck.run_im_app.how_to_guide.md)

- TODO(gp): Reorg
  ```
  ./research_amp/cc/notebooks/Master_single_vendor_qa.ipynb
  ./research_amp/cc/notebooks/Master_model_performance_analyser.old.ipynb
  ./research_amp/cc/notebooks/Master_machine_learning.ipynb
  ./research_amp/cc/notebooks/Master_cross_vendor_qa.ipynb
  ./research_amp/cc/notebooks/Master_model_performance_analyser.ipynb
  ./research_amp/cc/notebooks/Master_crypto_analysis.ipynb
  ./research_amp/cc/notebooks/Master_model_prediction_analyzer.ipynb
  ./research_amp/cc/notebooks/Master_Analysis_CrossSectionalLearning.ipynb
  ./im/app/notebooks/Master_IM_DB.ipynb
  ./im/ib/metadata/extract/notebooks/Master_analyze_ib_metadata_crawler.ipynb
  ```

<!-- /////////////////////////////////////////////////////////////////////// -->

## `DataFlow`

### Meta

- Best practices for Quant research
  - [/docs/dataflow/ck.research_methodology.explanation.md](/docs/dataflow/ck.research_methodology.explanation.md)
  - TODO(Grisha): `ck.*` -> `all.*`?

- A description of all the available generic notebooks with a short description
  - [/docs/dataflow/ck.master_notebooks.reference.md](/docs/dataflow/ck.master_notebooks.reference.md)
  - TODO(Grisha): does this belong to `DataFlow`?
  - TODO(Grisha): `ck.master_notebooks...` -> `all.master_notebooks`?

### DAG

- General concepts of `DataFlow`
  - Introduction to KaizenFlow, DAG nodes, DataFrame as unit of computation, DAG
    execution
    - [/docs/dataflow/all.computation_as_graphs.explanation.md](/docs/dataflow/all.computation_as_graphs.explanation.md)
  - DataFlow data format
    - [/docs/dataflow/all.dataflow_data_format.explanation.md](/docs/dataflow/all.dataflow_data_format.explanation.md)
  - Different views of System components, Architecture
    - [/docs/dataflow/all.dataflow.explanation.md](/docs/dataflow/all.dataflow.explanation.md)
  - Conventions for representing time series
    - [/docs/dataflow/all.time_series.explanation.md](/docs/dataflow/all.time_series.explanation.md)
  - Explanation of how to debug a DAG
    - [/docs/dataflow/all.dag.explanation.md](/docs/dataflow/all.dag.explanation.md)

- Learn how to build a `DAG`
  - Build a `DAG` with two nodes
    - [/docs/dataflow/all.build_first_dag.tutorial.ipynb](/docs/dataflow/all.build_first_dag.tutorial.ipynb)
  - Build a more complex `DAG` implementing a simple risk model
    - [/docs/dataflow/all.build_simple_risk_model_dag.tutorial.ipynb](/docs/dataflow/all.build_simple_risk_model_dag.tutorial.ipynb)
  - Best practices to follow while building `DAG`
    - [/docs/dataflow/all.best_practice_for_building_dags.explanation.md](/docs/dataflow/all.best_practice_for_building_dags.explanation.md)

- Learn how to run a `DAG`
  - Overview, DagBuilder, Dag, DagRunner
    - [/docs/dataflow/ck.run_batch_computation_dag.explanation.md](/docs/dataflow/ck.run_batch_computation_dag.explanation.md)
  - Configure a simple risk model, build a DAG, generate data and connect data
    source to the DAG, run the DAG
    - [/docs/dataflow/ck.run_batch_computation_dag.tutorial.ipynb](/docs/dataflow/ck.run_batch_computation_dag.tutorial.ipynb)
  - Build a DAG from a Mock2 DagBuilder and run it
    - [/docs/kaizenflow/all.run_Mock2_pipeline_in_notebook.how_to_guide.ipynb](/docs/kaizenflow/all.run_Mock2_pipeline_in_notebook.how_to_guide.ipynb)

- General intro about model simulation
  - Property of tilability, batch vs streaming
    - [/docs/dataflow/all.batch_and_streaming_mode_using_tiling.explanation.md](/docs/dataflow/all.batch_and_streaming_mode_using_tiling.explanation.md)
    - TODO(gp): @paul Review
  - Time semantics, How clock is handled, Flows
    - [/docs/dataflow/all.timing_semantic_and_clocks.md](/docs/dataflow/all.timing_semantic_and_clocks.md)
    - TODO(gp): Review
  - Phases of evaluation of `Dag`s
    - [/docs/dataflow/all.train_and_predict_phases.explanation.md](/docs/dataflow/all.train_and_predict_phases.explanation.md)
  - Event study explanation
    - [/docs/dataflow/ck.event_study.explanation.md](/docs/dataflow/ck.event_study.explanation.md)

- Run a simulation of a `DataFlow` system
  - Overview, Basic concepts, Implementation details
    - [/docs/dataflow/ck.run_backtest.explanation.md](/docs/dataflow/ck.run_backtest.explanation.md)
  - How to build a system, run research backtesting, Process results of
    backtesting, How to run replayed time simulation, Running experiments
    - [/docs/dataflow/ck.run_backtest.how_to_guide.md](/docs/dataflow/ck.run_backtest.how_to_guide.md)
    - TODO(gp): Review
  - Simulation output explanation
    - [/docs/dataflow/all.simulation_output.reference.md](/docs/dataflow/all.simulation_output.reference.md)

- Run a simulation sweep using a list of `Config` parameters
  - [/docs/dataflow/ck.run_backtest.how_to_guide.md](/docs/dataflow/ck.run_backtest.how_to_guide.md#how-to-utilize-the-backtest-analyzer-notebook)
  - TODO(gp): @grisha do we have anything here? It's like the stuff that Dan
    does
  - TODO(Grisha): @Dan, add a link to the doc here once it is ready

- Post-process the results of a simulation
  - Build the Config dict, Load tile results, Compute portfolio bar metrics,
    Compute aggregate portfolio stats
  - [/dataflow/model/notebooks/Master_research_backtest_analyzer.ipynb](/dataflow/model/notebooks/Master_research_backtest_analyzer.ipynb)
  - TODO(Grisha): is showcasing an example with fake data enough? We could use
    Mock2 output

- Analyze a `DataFlow` model in details
  - Build Config, Initialize ModelEvaluator and ModelPlotter
  - [/dataflow/model/notebooks/Master_model_analyzer.ipynb](/dataflow/model/notebooks/Master_model_analyzer.ipynb)
  - TODO(gp): @grisha what is the difference with the other?
  - TODO(Grisha): ask Paul about the notebook

- Analyze features computed with `DataFlow`
  - Read features from a Parquet file and perform some analysis
    - [/dataflow/model/notebooks/Master_feature_analyzer.ipynb](/dataflow/model/notebooks/Master_feature_analyzer.ipynb)
  - TODO(gp): Grisha do we have a notebook that reads data from
    ImClient/MarketData and performs some analysis?
  - TODO(Grisha): create a tutorial notebook for analyzing features using some
    real (or close to real) data

- Mix multiple `DataFlow` models
  - [/dataflow/model/notebooks/Master_model_mixer.ipynb](/dataflow/model/notebooks/Master_model_mixer.ipynb)
  - TODO(gp): add more comments

- Exporting PnL and trades
  - [/dataflow/model/notebooks/Master_save_pnl_and_trades.ipynb](/dataflow/model/notebooks/Master_save_pnl_and_trades.ipynb)
  - [/docs/dataflow/ck.export_alpha_data.explanation.md](/docs/dataflow/ck.export_alpha_data.explanation.md)
  - [/docs/dataflow/ck.export_alpha_data.how_to_guide.md](/docs/dataflow/ck.export_alpha_data.how_to_guide.md)
  - [/docs/dataflow/ck.load_alpha_and_trades.tutorial.ipynb](/docs/dataflow/ck.load_alpha_and_trades.tutorial.ipynb)
  - [/docs/dataflow/ck.load_alpha_and_trades.tutorial.py](/docs/dataflow/ck.load_alpha_and_trades.tutorial.py)
  - TODO(gp): add more comments

### System

- Learn how to build `System`
  - TODO(gp): @grisha what do we have for this?
  - TODO(Grisha): add a tutorial notebook that builds a System and explain the
    flow step-by-step

- Configure a full system using a `Config`
  - Fill the SystemConfig, Build all the components and run the System
  - [/docs/dataflow/system/all.use_system_config.tutorial.ipynb](/docs/dataflow/system/all.use_system_config.tutorial.ipynb)

- Create an ETL batch process using a `System`
  - [/dataflow_amp/system/risk_model_estimation/run_rme_historical_simulation.py](/dataflow_amp/system/risk_model_estimation/run_rme_historical_simulation.py)
  - TODO(Grisha): add an explanation doc and consider converting into a Jupyter
    notebook.

- Create an ETL real-time process
  - DagBuilder, Dag, DagRunner
    - [/docs/dataflow/system/ck.build_real_time_dag.explanation.md](/docs/dataflow/system/ck.build_real_time_dag.explanation.md)
  - Build a DAG that runs in real time
    - [/dataflow_amp/system/realtime_etl_data_observer/scripts/run_realtime_etl_data_observer.py](/dataflow_amp/system/realtime_etl_data_observer/scripts/run_realtime_etl_data_observer.py)
    - TODO(Grisha): consider converting into a Jupyter notebook.
  - Build a `System` that runs in real time
    - [dataflow_amp/system/realtime_etl_data_observer/scripts/DataObserver_template.run_data_observer_simulation.py](/dataflow_amp/system/realtime_etl_data_observer/scripts/DataObserver_template.run_data_observer_simulation.py)
    - TODO(Grisha): consider converting into a Jupyter notebook.

- Batch simulation a Mock2 `System`
  - Description of the forecast system, Description of the System, Run a
    backtest, Explanation of the backtesting script, Analyze the results
  - [/docs/kaizenflow/all.run_Mock2_in_batch_mode.how_to_guide.md](/docs/kaizenflow/all.run_Mock2_in_batch_mode.how_to_guide.md)
  - Build the config, Load tiled results, Compute portfolio bar metrics, Compute
    aggregate portfolio stats
  - [/docs/kaizenflow/all.analyze_Mock2_pipeline_simulation.how_to_guide.ipynb](/docs/kaizenflow/all.analyze_Mock2_pipeline_simulation.how_to_guide.ipynb)

- Run an end-to-end timed simulation of `Mock2` `System`
  - [/docs/kaizenflow/all.run_end_to_end_Mock2_system.tutorial.md](/docs/kaizenflow/all.run_end_to_end_Mock2_system.tutorial.md)
  - [/dataflow_amp/system/mock2/scripts/run_end_to_end_Mock2_system.py](/dataflow_amp/system/mock2/scripts/run_end_to_end_Mock2_system.py)

- TODO(gp): reorg the following files
  ```
  ./oms/notebooks/Master_PnL_real_time_observer.ipynb
  ./oms/notebooks/Master_bid_ask_execution_analysis.ipynb
  ./oms/notebooks/Master_broker_debugging.ipynb
  ./oms/notebooks/Master_broker_portfolio_reconciliation.ipynb
  ./oms/notebooks/Master_c1b_portfolio_vs_portfolio_reconciliation.ipynb
  ./oms/notebooks/Master_dagger_reconciliation.ipynb
  ./oms/notebooks/Master_execution_analysis.ipynb
  ./oms/notebooks/Master_model_qualifier.ipynb
  ./oms/notebooks/Master_multiday_system_reconciliation.ipynb
  ./oms/notebooks/Master_portfolio_vs_portfolio_reconciliation.ipynb
  ./oms/notebooks/Master_portfolio_vs_research_stats.ipynb
  ./oms/notebooks/Master_system_reconciliation_fast.ipynb
  ./oms/notebooks/Master_system_reconciliation_slow.ipynb
  ./oms/notebooks/Master_system_run_debugger.ipynb
  ```

<!-- ####################################################################### -->

# Quant dev workflows

<!-- ####################################################################### -->

<!-- /////////////////////////////////////////////////////////////////////// -->

## DataPull

- Learn how to create a `DataPull` adapter for a new data source
  - [/docs/datapull/all.dataset_onboarding_checklist.reference.md](/docs/datapull/all.dataset_onboarding_checklist.reference.md)
  - [/docs/datapull/ck.add_new_data_source.how_to_guide.md](/docs/datapull/ck.add_new_data_source.how_to_guide.md)
- How to update CCXT version
  - [/docs/datapull/all.update_CCXT_version.how_to_guide.md](/docs/datapull/all.update_CCXT_version.how_to_guide.md)
- Download `DataPull` historical data

- Put a `DataPull` source in production with Airflow
  - [/docs/datapull/ck.create_airflow_dag.tutorial.md](/docs/datapull/ck.create_airflow_dag.tutorial.md)
    - TODO(gp, Juraj): double check
  - [/docs/datapull/ck.develop_an_airflow_dag_for_production.explanation.md](/docs/datapull/ck.develop_an_airflow_dag_for_production.explanation.md)
    - TODO(Juraj): See https://github.com/cryptokaizen/cmamp/issues/6444

- Add QA for a `DataPull` source

- Compare OHLCV bars
  - [/im_v2/ccxt/data/client/notebooks/CmTask6537_One_off_comparison_of_Parquet_and_DB_OHLCV_data.ipynb](/im_v2/ccxt/data/client/notebooks/CmTask6537_One_off_comparison_of_Parquet_and_DB_OHLCV_data.ipynb)
  - TODO(Grisha): review and generalize

- How to import `Bloomberg` historical data
  - [/docs/datapull/ck.process_historical_data_without_dataflow.tutorial.ipynb](/docs/datapull/ck.process_historical_data_without_dataflow.tutorial.ipynb)

- How to import `Bloomberg` real-time data
  - TODO(\*): add doc.

<!-- /////////////////////////////////////////////////////////////////////// -->

## DataFlow

- All software components
  - [/docs/dataflow/ck.data_pipeline_architecture.reference.md](/docs/dataflow/ck.data_pipeline_architecture.reference.md)

<!-- ####################################################################### -->

# TradingOps workflows

<!-- ####################################################################### -->

<!-- /////////////////////////////////////////////////////////////////////// -->

## Trading execution

### Intro

- Binance trading terms
  - [/docs/trade_execution/ck.binance_terms.reference.md](/docs/trade_execution/ck.binance_terms.reference.md)

### Components

- OMS explanation
  - [/docs/trade_execution/ck.oms.explanation.md](/docs/trade_execution/ck.oms.explanation.md)
- CCXT log structure
  - [/docs/trade_execution/ck.ccxt_broker_logs_schema.reference.md](/docs/trade_execution/ck.ccxt_broker_logs_schema.reference.md)

### Testing

- Replayed CCXT exchange explanation
  - [/docs/trade_execution/ck.replayed_ccxt_exchange.explanation.md](/docs/trade_execution/ck.replayed_ccxt_exchange.explanation.md)
- How to generate broker test data
  - [/docs/trade_execution/ck.generate_broker_test_data.how_to_guide.md](/docs/trade_execution/ck.generate_broker_test_data.how_to_guide.md)

### Procedures

- Trading procedures (e.g., trading account information)
  - [/docs/trade_execution/ck.trading.how_to_guide.md](/docs/trade_execution/ck.trading.how_to_guide.md)
- How to run broker only/full system experiments
  - [/docs/trade_execution/ck.trade_execution_experiment.how_to_guide.md](/docs/trade_execution/ck.trade_execution_experiment.how_to_guide.md)
- Execution notebooks explanation
  - [/docs/trade_execution/ck.execution_notebooks.explanation.md](/docs/trade_execution/ck.execution_notebooks.explanation.md)

<!-- ####################################################################### -->

# MLOps workflows

- Encrypt a model
  - [/docs/dataflow/ck.release_encrypted_models.explanation.md](/docs/dataflow/ck.release_encrypted_models.explanation.md)
  - [/docs/dataflow/ck.release_encrypted_models.how_to_guide.md](/docs/dataflow/ck.release_encrypted_models.how_to_guide.md)

<!-- /////////////////////////////////////////////////////////////////////// -->

## Deploying

- Model deployment in production
  - [/docs/deploying/all.model_deployment.how_to_guide.md](/docs/deploying/all.model_deployment.how_to_guide.md)
- Run production system
  - [/docs/deploying/ck.run_production_system.how_to_guide.md](/docs/deploying/ck.run_production_system.how_to_guide.md)
- Model references
  - [/docs/deploying/ck.supported_models.reference.md](/docs/deploying/ck.supported_models.reference.md)

<!-- /////////////////////////////////////////////////////////////////////// -->

## Monitoring

- Monitor system
  - [/docs/monitoring/ck.monitor_system.how_to_guide.md](/docs/monitoring/ck.monitor_system.how_to_guide.md)
- System reconciliation explanation
  - [/docs/monitoring/ck.system_reconciliation.explanation.md](/docs/monitoring/ck.system_reconciliation.explanation.md)
- System Reconciliation How to guide
  - [/docs/monitoring/ck.system_reconciliation.how_to_guide.md](/docs/monitoring/ck.system_reconciliation.how_to_guide.md)

<!-- ####################################################################### -->

# Devops workflows
