

<!-- toc -->

- [Description of the forecast system](#description-of-the-forecast-system)
- [Description of the System](#description-of-the-system)
- [Run a backtest](#run-a-backtest)
  * [Explanation of the backtesting script](#explanation-of-the-backtesting-script)
- [Analyze the results](#analyze-the-results)

<!-- tocstop -->

The goal is to run a simple system (Mock2) end-to-end in batch mode and compute
PnL. This is the typical flow that Quants run to estimate performance of a
model.

# Description of the forecast system

- A notebook running the forecast system interactively is
  [/docs/kaizenflow/all.run_Mock2_pipeline_in_notebook.how_to_guide.ipynb](/docs/kaizenflow/all.run_Mock2_pipeline_in_notebook.how_to_guide.ipynb)

- The `Mock2` pipeline is described in
  [/dataflow_amp/pipelines/mock2/mock2_pipeline.py](/dataflow_amp/pipelines/mock2/mock2_pipeline.py)
  - `Mock2_DagBuilder` is a `DagBuilder` with
    - A `get_config_template()` to expose the parameters that can be configured
      for each node; and
    - A `_get_dag()` to build the entire DAG from a fully specified `Config`

- The notebook assembles a complete `DAG` including:
  - An `ImClient` (which reads the raw data adapting to the `MarketData`
    semantics)
  - A `MarketData` (which provides an abstractions to get data on intervals)
  - A `HistoricalDataSource` (which adapts `MarkatData` to the `DataFlow`
    semantics)

- Finally the entire `DAG` is run

# Description of the System

- The same `System` can be built using various utilities from
  dataflow/system/system.py

- A `Mock2_NonTime_ForecastSystem`
  - Is built in
    [/dataflow_amp/system/mock2/mock2_forecast_system.py](/dataflow_amp/system/mock2/mock2_forecast_system.py)
  - Contains an `HistoricalMarketData`
  - A non-timed DAG since it runs in batch mode

- Concrete fully-configured `System`s are built in
  [/dataflow_amp/system/mock2/mock2_forecast_system_example.py](/dataflow_amp/system/mock2/mock2_forecast_system_example.py)

# Run a backtest

Pull the latest `master`
```
> git checkout master
> git pull
```

- Run backtest
```
> i docker_bash
> dataflow_amp/system/mock2/run_backtest.sh
```

- The script runs a backtest for a simple dummy "strategy" using equities data
  for 1 month (2023-08) and 1 asset (MSFT). Trading frequency is 5 minutes.

## Explanation of the backtesting script

- Inside `docker_bash`

  ```bash
  tag="mock2"
  backtest_config="bloomberg_v1-top1.5T.2023-08-01_2023-08-31"
  config_builder="dataflow_amp.system.mock2.mock2_tile_config_builders.build_Mock2_tile_config_list(\"${backtest_config}\")"

  dst_dir="build_Mock2_tile_config_list.${tag}.${backtest_config}.run1"

  ./dataflow/backtest/run_config_list.py \
      --experiment_builder "dataflow.backtest.master_backtest.run_in_sample_tiled_backtest" \
      --config_builder $config_builder \
      --dst_dir $dst_dir \
      $OPTS 2>&1 | tee run_config_list.txt
  ```

- `backtest_config` is used to configure `_get_Mock2_NonTime_ForecastSystem()`

- The code in `dataflow_amp/system/mock2/mock2_tile_config_builders.py` is used
  to create the config list to run sweeps

- The basic type of experiment is configured through
  `dataflow.backtest.master_backtest.run_in_sample_tiled_backtest`

- See
  [/docs/dataflow/ck.run_backtest.how_to_guide.md](/docs/dataflow/ck.run_backtest.how_to_guide.md)
  for more details

# Analyze the results

- ```
  > i docker_jupyter
  ```

- Run the notebook
  [/docs/kaizenflow/all.analyze_Mock2_pipeline_simulation.how_to_guide.ipynb](/docs/kaizenflow/all.analyze_Mock2_pipeline_simulation.how_to_guide.ipynb)
  top-to-bottom

- The notebook computes a portfolio given the predictions and computes model
  performance metrics
- Note: make sure that dir_name in `Build the config section` points to the
  right output
  `/app/build_Mock2_tile_config_list.mock2.bloomberg_v1-top1.5T.2023-08-01_2023-08-31.run1/tiled_results`

- See more on how to run a Jupyter here under Start a Jupyter server. The flow
  is:
  - Open a web-browser
  - Use the IP of your machine
  - Get the port from the output of `i docker_jupyter`
