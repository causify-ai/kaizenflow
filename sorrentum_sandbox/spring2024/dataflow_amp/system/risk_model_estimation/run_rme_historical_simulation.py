#!/usr/bin/env python
import logging

import numpy as np
import pandas as pd

import dataflow.backtest.backtest_api as dtfbabaapi
import dataflow.system as dtfsys
import dataflow_amp.system.risk_model_estimation.rme_forecast_system as dtfasrmerfs
import helpers.hdbg as hdbg


# TODO(Grisha): could go to a more general lib, e.g., `core/finance/market_data_example.py`.
def get_random_data(
    n_assets: int,
    n_features: int,
    n_periods: int,
    period_start: str,
    freq: str,
    seed: int,
) -> pd.DataFrame:
    """
    Generate a dataframe of random returns and random features.

    ```
                                ret_0                   x_1
                                100         101         100         101
    2022-01-01 09:31:00+00:00   0.330437    0.377605    0.345584    2.117839
    2022-01-01 09:32:00+00:00   0.446375    0.663063    1.303157    2.042772
    2022-01-01 09:33:00+00:00   0.364572    0.167465    0.536953    0.514006
    ```
    """
    # Create datetime index for dataframe.
    idx = pd.date_range(start=period_start, periods=n_periods, freq=freq)
    # Create columns names for the X matrix.
    cols = [f"x_{k}" for k in range(1, n_features + 1)]
    cols = cols + ["ret_0"]
    # Instantiate random number generator.
    rng = np.random.default_rng(seed)
    dfs = {}
    for n in range(n_assets):
        asset_id = 100 + n
        dfs[asset_id] = pd.DataFrame(
            rng.standard_normal((n_periods, n_features + 1)), idx, cols
        )
    df = pd.concat(dfs, axis=1).swaplevel(axis=1).sort_index(axis=1)
    return df


if __name__ == "__main__":
    # Set model params.
    dag_builder_ctor_as_str = "dataflow_amp.pipelines.risk_model_estimation.rme_pipeline.SimpleRiskModel_DagBuilder"
    fit_at_beginning = False
    train_test_mode = "ins"
    # backtest_config = "ccxt_v7-all.5T.2022-09-01_2022-11-30"
    backtest_config = "rme.5T.2022-01-01_2022-02-01"
    # Set dir params.
    dst_dir = None
    dst_dir_tag = "run0"
    clean_dst_dir = True
    no_confirm = True
    # Set config params.
    index = None
    start_from_index = None
    config_update = None
    # config_update = cconfig.Config.from_dict(
    #     {
    #         "dag_builder_class": "C1b_DagBuilder",
    #         "dag_config": {
    #             "resample": {
    #                 "transformer_kwargs": {
    #                     "rule": "1T",
    #                 },
    #             },
    #         },
    #     },
    # )
    # Set execution params.
    abort_on_error = True
    num_threads = "serial"
    num_attempts = 1
    dry_run = False
    backend = "asyncio_threading"
    # Set logger.
    log_level = logging.DEBUG
    hdbg.init_logger(
        verbosity=log_level,
        use_exec_path=True,
        # report_memory_usage=True,
    )
    # 1) Get input data.
    n_assets = 4
    n_features = 2
    n_periods = 7200
    freq = "B"
    period_start = "2022-01-01T00:00:00+00:00"
    rng_seed = 1
    df = get_random_data(
        n_assets,
        n_features,
        n_periods,
        period_start,
        freq,
        rng_seed,
    )
    # TODO(Dan): Move System building to `rme_forecast_system_example.py`.
    # 2) Build a `System` object.
    system = dtfasrmerfs.RME_NonTime_Df_ForecastSystem(df)
    # 3) Apply backtest config.
    system = dtfsys.apply_backtest_config(system, backtest_config)
    # 4) Apply tile config.
    system = dtfsys.apply_backtest_tile_config(system)
    # 5) Apply market data config.
    system = dtfsys.apply_Df_MarketData_config(system)
    # Run.
    dtfbabaapi.run_backtest(
        # Model params.
        system,
        config_update,
        # Dir params.
        dst_dir,
        dst_dir_tag,
        clean_dst_dir,
        no_confirm,
        # Config params.
        index,
        start_from_index,
        # Execution params.
        abort_on_error,
        num_threads,
        num_attempts,
        dry_run,
        backend,
    )
