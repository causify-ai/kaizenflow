"""
Import as:

import dataflow.backtest.backtest_api as dtfbabaapi
"""

import logging
import os
from typing import Optional

import core.config as cconfig
import dataflow.backtest.dataflow_backtest_utils as dtfbdtfbaut
import dataflow.backtest.master_backtest as dtfbamabac
import dataflow.core as dtfcore

# TODO(gp): Use only dtfsys.
import dataflow.system as dtfsys
import dataflow.system.system as dtfsyssyst
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hjoblib as hjoblib
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################
# run_backtest_for_single_config
# #############################################################################


def _run_backtest_for_system_config_list(
    config_list: dtfsys.SystemConfigList, train_test_mode: str
) -> None:
    """
    Run backtest given config list of `System`s and `train_test_mode`.

    :param config_list: system config list to run backtest for
    :param train_test_mode: see `run_backtest()`
    """
    if train_test_mode == "ins":
        dtfbamabac.run_in_sample_tiled_backtest(config_list)
    elif train_test_mode == "ins_oos":
        dtfbamabac.run_ins_oos_tiled_backtest(config_list)
    elif train_test_mode == "rolling":
        dtfbamabac.run_rolling_tiled_backtest(config_list)
    else:
        raise ValueError(f"Unsupported train_test_mode='{train_test_mode}'")


def _get_default_dst_dir(
    system: dtfsys.System,
) -> str:
    """
    Get default destination dir by extracting parameters from the `System`.

    See param descriptions in `run_backtest()`.

    :return: dst dir, e.g.,
        `build_tile_configs.C3a.ccxt_v7_4-all.5T.2022-06-01_2022-06-02.ins`
    """
    # Extract information from the System to build the destination dir.
    # The format is like:
    #   `build_tile_configs.{dag_builder_name}.{universe_str}.
    #       {trading_period_str}.{time_interval_str}.{train_test_mode}`
    # e.g.,
    #   `build_tile_configs.C3a.ccxt_v7_4-all.5T.2022-06-01_2022-06-02.ins`
    prefix = "./build_tile_configs"
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        system.config["dag_builder_class"]
    )
    universe_str = system.config["backtest_config", "universe_str"]
    trading_period_str = system.config["backtest_config", "trading_period_str"]
    time_interval_str = system.config["backtest_config", "time_interval_str"]
    train_test_mode = system.train_test_mode
    # Create the destination dir.
    dst_dir = ".".join(
        [
            prefix,
            dag_builder_name,
            universe_str,
            trading_period_str,
            time_interval_str,
            train_test_mode,
        ]
    )
    return dst_dir


def run_backtest_for_single_config(
    config_list: dtfsys.SystemConfigList,
    train_test_mode: str,
    #
    incremental: bool,
    num_attempts: int,
) -> None:
    """
    Run backtest for a single SystemConfig.

    :param config_list: system config list to run backtest for
    :param train_test_mode: see `run_backtest()`
    """
    hdbg.dassert_isinstance(config_list, dtfsys.SystemConfigList)
    _ = incremental
    hdbg.dassert_eq(1, num_attempts, "Multiple attempts not supported yet")
    #
    config = config_list.get_only_config()
    dtfbdtfbaut.setup_experiment_dir(config)
    # Extract params from config.
    _LOG.info("config=\n%s", config)
    idx = config[("backtest_config", "id")]
    _LOG.info("\n%s", hprint.frame(f"Executing backtest for config {idx}"))
    experiment_result_dir = config[("backtest_config", "experiment_result_dir")]
    # Run backtest.
    try:
        _run_backtest_for_system_config_list(config_list, train_test_mode)
    except Exception as e:
        # Display the type of occurring error.
        _LOG.error("The error is: %s", e)
        msg = f"Execution failed for backtest {idx}"
        _LOG.error(msg)
        raise RuntimeError(msg) from e
    else:
        _LOG.info("Execution successful for backtest %s", idx)
        dtfbdtfbaut.mark_config_as_success(experiment_result_dir)


# #############################################################################
# run_backtest
# #############################################################################


def _patch_config_lists(
    config_list: cconfig.ConfigList,
    dst_dir: str,
    index: Optional[int],
    start_from_index: Optional[int],
    incremental: bool,
) -> cconfig.ConfigList:
    """
    Patch the configs with the necessary info to run the workload.

    See param descriptions in `run_backtest()`.
    """
    # Patch the configs with the command line parameters.
    params = {"dst_dir": dst_dir}
    config_list = cconfig.patch_config_list(config_list, params)
    # Select the configs based on command line options.
    config_list = dtfbdtfbaut.select_config(config_list, index, start_from_index)
    _LOG.info("Selected %d configs from command line", len(config_list))
    # Remove the configs already executed.
    config_list, num_skipped = dtfbdtfbaut.skip_configs_already_executed(
        config_list, incremental
    )
    _LOG.info("Removed %d configs since already executed", num_skipped)
    _LOG.info("Need to execute %d configs", len(config_list))
    return config_list


def _get_joblib_workload(
    system: dtfsys.System,
    config_update: Optional[cconfig.Config],
    dst_dir: str,
    index: Optional[int],
    start_from_index: Optional[int],
    incremental: bool,
) -> hjoblib.Workload:
    """
    Prepare the joblib workload by building all the Configs.

    See param descriptions in `run_backtest()`.
    """
    if config_update is not None:
        hdbg.dassert_isinstance(config_update, cconfig.Config)
        # Update config parameters.
        # TODO(Grisha): should the system.config be write-protected?
        system.config.update(config_update)
    # Get configs to run.
    train_test_mode = system.train_test_mode
    config_list = build_tile_config_list(system, train_test_mode)
    _LOG.info("Generated %d configs", len(config_list))
    # Patch configs with information needed to run.
    config_list = _patch_config_lists(
        config_list,
        dst_dir,
        index,
        start_from_index,
        incremental,
    )
    # Prepare one task per config to run.
    tasks = []
    for config in config_list.configs:
        # Even though the goal is to run a single config, pass a config
        # as a `SystemConfigList` object because it also carries the `System`
        # which is required by a backtest runner.
        config_list_copy = config_list.copy()
        config_list_copy.configs = [config]
        task: hjoblib.Task = (
            # args.
            (
                config_list_copy,
                train_test_mode,
            ),
            # kwargs.
            {},
        )
        tasks.append(task)
    #
    func_name = "run_backtest_for_single_config"
    workload = (run_backtest_for_single_config, func_name, tasks)
    hjoblib.validate_workload(workload)
    return workload


# TODO(Dan): Add `oos_start_date_as_str`.
def run_backtest(
    # Model params.
    system: dtfsys.System,
    config_update: Optional[cconfig.Config],
    # Dir params.
    dst_dir: Optional[str],
    dst_dir_tag: Optional[str],
    clean_dst_dir: bool,
    no_confirm: bool,
    # Config params.
    index: Optional[int],
    start_from_index: Optional[int],
    # Execution params.
    # TODO(Grisha): make sure that aborting on error works.
    # Probably it does not work out of the box.
    abort_on_error: bool,
    # TODO(Grisha): make sure it works with multiple parallel threads.
    num_threads: int,
    num_attempts: int,
    dry_run: bool,
    backend: str,
) -> None:
    """
    Run backtest and save the results.

    :param system: the system for the backtest, typically a non-time system,
        `NonTimeForecastSystem`.
    :param config_update: config with values to update system config
    :param dst_dir: backtest results destination directory,
        e.g., `build_tile_configs.C3a.ccxt_v7_4-all.5T.2022-06-01_2022-06-02.ins/`
    :param dst_dir_tag: a tag to add to the backtest results directory
    :param clean_dst_dir: opposite of `incremental` form `hio.create_dir()`
    :param no_confirm: opposite of `ask_to_delete` form `hio.create_dir()`
    :param index: index of a config to execute, if not `None`
    :param start_from_index: index of a config to start execution from,
        if not `None`
    :param abort_on_error: when True, if one task asserts then stop executing
        the workload and return the error for the failing task
        - If False, the execution continues in case of failing errors
    :param num_threads: how many threads to use
    :param dry_run: if True, print the workload and exit without executing it
    :param backend: same as in `joblib.Parallel()`
    """
    hdbg.dassert_isinstance(system, dtfsyssyst.System)
    # Set destination dir.
    if not dst_dir:
        # Use the default destination dir, if not specified.
        dst_dir = _get_default_dst_dir(system)
    # Add a tag, if needed.
    if dst_dir_tag:
        dst_dir = ".".join([dst_dir, dst_dir_tag])
    # TODO(Grisha): We could use `incremental` and `ask_to_delete` directly,
    # keeping `clean_dst_dir` and `no_confirm` so that the interface look like
    # the one from `run_config_list.py`.
    incremental = not clean_dst_dir
    ask_to_delete = not no_confirm
    hio.create_dir(dst_dir, incremental, ask_to_delete=ask_to_delete)
    # Prepare the workload.
    workload = _get_joblib_workload(
        system,
        config_update,
        dst_dir,
        index,
        start_from_index,
        incremental,
    )
    # Prepare the log file.
    timestamp = hdateti.get_current_timestamp_as_string("naive_ET")
    # TODO(Grisha): have a detailed log with info about each backtest,
    # now the log contains only the high-level info, i.e. a config and if
    # an backtest failed or not.
    log_file = os.path.join(dst_dir, f"log.{timestamp}.txt")
    _LOG.info("log_file='%s'", log_file)
    # Execute.
    hjoblib.parallel_execute(
        workload,
        dry_run,
        num_threads,
        incremental,
        abort_on_error,
        num_attempts,
        log_file,
        backend=backend,
    )
    _LOG.info("dst_dir='%s'", dst_dir)
    _LOG.info("log_file='%s'", log_file)
    # TODO(Dan): Add archiving on S3.


# TODO(Dan): Consider renaming due to func with the same name in `dataflow.system`.
def build_tile_config_list(
    system: dtfsys.System, train_test_mode: str
) -> dtfsys.SystemConfigList:
    """
    Build a `SystemConfigList` object based on `train_test_mode`.

    :param system: the system for the backtest, typically a non-time system
    :param train_test_mode: same as in `Cx_NonTime_ForecastSystem`
    """
    hdbg.dassert_isinstance(system, dtfsyssyst.System)
    if train_test_mode in ["ins", "rolling"]:
        # Partition by time and asset_ids.
        system_config_list = dtfsys.build_tile_config_list(system)
    elif train_test_mode == "ins_oos":
        # TODO(Grisha): consider partitioning by asset_ids in case of
        # memory issues.
        # TODO(Grisha): P1, document why not using `dtfsys.build_tile_config_list(system)`.
        system_config_list = dtfsys.SystemConfigList.from_system(system)
    else:
        raise ValueError(f"Invalid train_test_mode='{train_test_mode}'")
    return system_config_list
