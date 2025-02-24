"""
Entry point for `run_config_list.py`.

Import as:

import dataflow.backtest.master_backtest as dtfbamabac
"""

import logging
import os
from typing import Optional

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hpickle as hpickle
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# TODO(gp): -> backtest_drivers.py


def _get_single_system_config(
    system_config_list: dtfsys.SystemConfigList,
) -> dtfsys.System:
    """
    Return the single System from a list of System configs.
    """
    # Create the DAG runner customizing the System with the specific config.
    hdbg.dassert_isinstance(system_config_list, dtfsys.SystemConfigList)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("system_config_list=\n%s", system_config_list)
    system_config = system_config_list.get_only_config()
    #
    system = system_config_list.system
    system.set_config(system_config)
    return system


def _save_tiled_output(
    system_config: cconfig.Config,
    result_df: pd.DataFrame,
    *,
    tag: Optional[str] = None,
) -> None:
    """
    Serialize the results of a tiled experiment.

    :param result_df: DAG results to save
    """
    start_timestamp = system_config["backtest_config", "start_timestamp"]
    end_timestamp = system_config["backtest_config", "end_timestamp"]
    # Sanity check for the tile borders.
    hdbg.dassert_lte(start_timestamp, end_timestamp)
    hdateti.dassert_has_tz(start_timestamp)
    hdateti.dassert_has_tz(end_timestamp)
    hdbg.dassert_eq(
        start_timestamp.tzinfo,
        end_timestamp.tzinfo,
        "start_timestamp=%s end_timestamp=%s",
        start_timestamp,
        end_timestamp,
    )
    # Extract the part of the simulation for this tile `[start_timestamp,
    # end_timestamp]` discarding the warm-up period, i.e., the data in
    # `[start_timestamp_with_lookback, start_timestamp]`
    # Note that we need to save the resulting data with the same timezone as the
    # tile boundaries to ensure that there is no overlap.
    # E.g., assume that the resulting data for a tile falls into
    # `[2022-06-01 00:00:00-00:00, 2022-06-30 23:55:00-00:00]`
    # If it's saved in ET timezone it's going to become
    # `[2022-05-31 20:00:00-04:00, 2022-06-30 19:55:00-04:00]` so it's going to
    # span two months potentially overwriting some other tile.
    result_df = result_df.loc[start_timestamp:end_timestamp]
    result_df.index = result_df.index.tz_convert(start_timestamp.tzinfo)
    # Convert the result into Parquet.
    df = result_df.stack()
    asset_id_col_name = system_config["market_data_config", "asset_id_col_name"]
    df.index.names = ["end_ts", asset_id_col_name]
    df = df.reset_index(level=1)
    df["year"] = df.index.year
    df["month"] = df.index.month
    # The results are saved in the subdir `tiled_results` of the experiment list.
    tiled_dst_dir = os.path.join(
        system_config["backtest_config", "dst_dir"], "tiled_results"
    )
    if tag:
        tiled_dst_dir += "." + tag
    hparque.to_partitioned_parquet(
        df, [asset_id_col_name, "year", "month"], dst_dir=tiled_dst_dir
    )
    _LOG.info("Tiled results written in '%s'", tiled_dst_dir)


# #############################################################################
# run_in_sample_tiled_backtest
# #############################################################################


# TODO(gp): -> run_ins_tiled_backtest
def run_in_sample_tiled_backtest(
    system_config_list: dtfsys.SystemConfigList,
) -> None:
    """
    Run a backtest in in-sample mode.

    This is done by:
    - creating a DAG from the passed `system.config`
    - running the DAG: fit and predict on the same dataset (i.e. in-sample
      prediction)
    - saving the generated `ResultBundle`

    All parameters are passed through a `system.config`.
    """
    # Create the `System`.
    system = _get_single_system_config(system_config_list)
    # Prepare the `DagRunner`.
    dag_runner = system.dag_runner
    hdbg.dassert_isinstance(dag_runner, dtfcore.FitPredictDagRunner)
    # TODO(gp): Even this should go in the DAG creation in the builder.
    dag_runner.set_fit_intervals(
        [
            (
                system.config["backtest_config", "start_timestamp_with_lookback"],
                system.config["backtest_config", "end_timestamp"],
            )
        ],
    )
    # Run.
    fit_result_bundle = dag_runner.fit()
    # Save results.
    result_df = fit_result_bundle.result_df
    _save_tiled_output(system.config, result_df)


# #############################################################################
# run_ins_oos_backtest
# #############################################################################


def run_ins_oos_tiled_backtest(system_config_list: cconfig.ConfigList) -> None:
    """
    Run a backtest in in-sample / out-of-sample mode.

    This is done by:
    - creating a DAG from the passed `system.config`
    - running the DAG: fit on a train dataset, predict on a test dataset
    - saving the generated `ResultBundle` for both fit and predict stages

    An example of a dir layout is:

    ```
    /build_tile_configs.C1b.ccxt_v7_4-all.5T.2022-01-01_2022-07-01.run0
        /result0
        /tiled_results.fit
        /tiled_results.predict
    ```

    All parameters are passed through a `system.config`.
    """
    # Create the `System`.
    system = _get_single_system_config(system_config_list)
    # Prepare the `DagRunner`.
    dag_runner = system.dag_runner
    hdbg.dassert_isinstance(dag_runner, dtfcore.FitPredictDagRunner)
    hdbg.dassert_eq(system.train_test_mode, "ins_oos")
    # Fit.
    fit_interval = (
        system.config["backtest_config", "start_timestamp"],
        system.config["backtest_config", "oos_start_timestamp"],
    )
    dag_runner.set_fit_intervals([fit_interval])
    fit_result_bundle = dag_runner.fit()
    # Save results.
    fit_result_df = fit_result_bundle.result_df
    _save_tiled_output(system.config, fit_result_df, tag="fit")
    # Predict.
    predict_interval = (
        system.config["backtest_config", "oos_start_timestamp"],
        system.config["backtest_config", "end_timestamp"],
    )
    dag_runner.set_predict_intervals([predict_interval])
    predict_result_bundle = dag_runner.predict()
    # Save results.
    predict_result_df = predict_result_bundle.result_df
    _save_tiled_output(system.config, predict_result_df, tag="predict")


# #############################################################################
# run_rolling_tiled_backtest
# #############################################################################


def run_rolling_tiled_backtest(
    system_config_list: dtfsys.SystemConfigList,
) -> None:
    """
    Run a backtest in rolling mode.

    This is done by:
    - creating a DAG from the passed `system.config`
    - running the DAG by periodic fitting on previous history and evaluating
         on new data, see `RollingFitPredictDagRunner` for details
    - saving the generated `ResultBundle`

    The output looks like:

    ```
    > find build_tile_configs.E8f.eg_v2_0-top3.5T.2020-01-01_2020-03-01.run1/ | sort
    build_tile_configs.run1/
    build_tile_configs.run1/fit_results
    build_tile_configs.run1/fit_results/fit_0_20191208_000000
    build_tile_configs.run1/fit_results/fit_0_20191208_000000/fit_result_df.parquet
    build_tile_configs.run1/fit_results/fit_0_20191208_000000/fit_result_df.pq
    build_tile_configs.run1/fit_results/fit_0_20191208_000000/fit_state.json
    build_tile_configs.run1/fit_results/fit_0_20191208_000000/fit_state.pkl
    build_tile_configs.run1/fit_results/fit_1_20191215_000000
    build_tile_configs.run1/fit_results/fit_1_20191215_000000/fit_result_df.parquet
    ...
    build_tile_configs.run1/result_0
    build_tile_configs.run1/result_0/config.pkl
    build_tile_configs.run1/result_0/config.txt
    build_tile_configs.run1/result_0/run_config_list.0.log
    build_tile_configs.run1/tiled_results
    build_tile_configs.run1/tiled_results/egid=10025
    build_tile_configs.run1/tiled_results/egid=10025/year=2020
    build_tile_configs.run1/tiled_results/egid=10025/year=2020/month=1
    build_tile_configs.run1/tiled_results/egid=10025/year=2020/month=1/data.parquet
    ...
    ```
    """
    # Create the `System`.
    system = _get_single_system_config(system_config_list)
    # Prepare the `DagRunner`.
    dag_runner = system.dag_runner
    hdbg.dassert_isinstance(dag_runner, dtfcore.RollingFitPredictDagRunner)
    #
    dst_dir = os.path.join(
        system.config["backtest_config", "dst_dir"], "fit_results"
    )
    # This loop corresponds to evaluating the model on a tile, but it's done in
    # chunks to do fit / predict.
    pred_rbs = []
    for idx, data in enumerate(dag_runner.fit_predict()):
        training_datetime_str, fit_rb, pred_rb = data
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("idx training_datetime_str"))
            _LOG.debug("fit_rb df=\n%s", hpandas.df_to_str(fit_rb.result_df))
            _LOG.debug("pred_rb df=\n%s", hpandas.df_to_str(pred_rb.result_df))
        # After each training session, we want to save all the info from
        # training and the model stats (including weights) into an extra
        # directory.
        # Note that the fit `result_df` form overlapping tiles so save them as
        # they are.
        dag = dag_runner.dag
        fit_state = dtfcore.get_fit_state(dag)
        dst_dir_tmp = os.path.join(dst_dir, f"fit_{idx}_{training_datetime_str}")
        file_name = os.path.join(dst_dir_tmp, "fit_state.pkl")
        hpickle.to_pickle(fit_state, file_name, log_level=logging.DEBUG)
        file_name = os.path.join(dst_dir_tmp, "fit_state.json")
        hpickle.to_json(file_name, str(fit_state))
        # Save fit data.
        file_name = os.path.join(dst_dir_tmp, "fit_result_df.parquet")
        result_df = fit_rb.result_df
        hparque.to_parquet(result_df, file_name, log_level=logging.DEBUG)
        # Save predict data.
        file_name = os.path.join(dst_dir_tmp, "predict_result_df.parquet")
        result_df = pred_rb.result_df
        hparque.to_parquet(result_df, file_name, log_level=logging.DEBUG)
        # Concat prediction output to convert into a tile.
        pred_rbs.append(pred_rb.result_df)
    # Concatenating all the OOS prediction one should get exactly a tile.
    pred_rb = pd.concat(pred_rbs, axis=0)
    # Save results.
    _save_tiled_output(system.config, pred_rb)
