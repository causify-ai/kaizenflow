"""
Contain functions used by both `run_config_list.py` and `run_notebook.py` to
run experiments.

Import as:

import dataflow.backtest.dataflow_backtest_utils as dtfbdtfbaut
"""

import argparse
import logging
import os
from typing import List, Optional, Tuple

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hpickle as hpickle

_LOG = logging.getLogger(__name__)


def add_run_experiment_args(
    parser: argparse.ArgumentParser,
    dst_dir_required: bool,
    dst_dir_default: Optional[str] = None,
) -> argparse.ArgumentParser:
    """
    Add common command line options for `run_config_list.py` and notebooks.

    It is used in `run_config_list` but not by `run_config_stub.py`.

    :param parser: parser to add the options to
    :param dst_dir_required: whether the user must specify a destination directory
        or not. If not, a default value should be passed through `dst_dir_default`
    :param dst_dir_default: a default destination dir
    """
    # Add options related to destination dir, e.g., `--dst_dir`, `--clean_dst_dir`.
    parser = hparser.add_dst_dir_arg(
        parser, dst_dir_required=dst_dir_required, dst_dir_default=dst_dir_default
    )
    # Add options related to joblib.
    parser = hparser.add_parallel_processing_arg(parser)
    #
    parser.add_argument(
        "--config_builder",
        action="store",
        required=True,
        help="""
        Full invocation of Python function to create configs, e.g.,
        `nlp.build_configs.build_Task1297_configs(random_seed_variants=[911,2,0])`
        """,
    )
    # TODO(gp): These options should be moved to joblib in
    #  add_parallel_processing_arg.
    parser.add_argument(
        "--index",
        action="store",
        default=None,
        help="Run a single experiment corresponding to the i-th config",
    )
    parser.add_argument(
        "--start_from_index",
        action="store",
        default=None,
        help="Run experiments starting from a specified index",
    )
    return parser  # type: ignore


# #############################################################################


# TODO(gp): There is overlap between the concept of hjoblib.workload and experiment
#  configs here.
#  We would like to unify but it's not easy.
# E.g.,
# - hjoblib has reverse_workload, truncate_workload, etc while here we have the
#   options but applied to configs.
# - hjoblib has an incremental mechanism based on the workload function, while this
#   is based on files representing a successful / failed config.
# One of the problems is that the experiment configs need to be able to be generated
# from command line to kick off the experiments and from each `run_config_stub`
# so that we can keep experiment runner and run experiment in sync.


def setup_experiment_dir(config: cconfig.Config) -> None:
    """
    Set up the directory and the book keeping artifacts for the experiment
    running `config`.

    :return: whether we need to run this config or not
    """
    hdbg.dassert_isinstance(config, cconfig.Config)
    # Create subdirectory structure for experiment results.
    experiment_result_dir = config[("backtest_config", "experiment_result_dir")]
    _LOG.info("Creating experiment dir '%s'", experiment_result_dir)
    hio.create_dir(experiment_result_dir, incremental=True)
    # Prepare book-keeping files.
    file_name = os.path.join(experiment_result_dir, "config.pkl")
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Saving '%s'", file_name)
    # Remove un-pickleable pieces.
    for key in ("dag_runner_object",):
        if key in config:
            if not hintros.is_pickleable(config[key]):
                config[key] = None
    hpickle.to_pickle(config, file_name)
    #
    file_name = os.path.join(experiment_result_dir, "config.txt")
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Saving '%s'", file_name)
    hio.to_file(file_name, str(config))


# TODO(gp): Generalize this logic for hjoblib `parallel_execute`.
#  Each task writes in a directory and if it terminates, the success.txt file is
#  written.
def skip_configs_already_executed(
    config_list: cconfig.ConfigList, incremental: bool
) -> Tuple[cconfig.ConfigList, int]:
    """
    Remove from the list the configs that have already been executed.
    """
    configs_out = []
    num_skipped = 0
    for config in config_list.configs:
        # If there is already a success file in the dir, skip the experiment.
        experiment_result_dir = config[
            ("backtest_config", "experiment_result_dir")
        ]
        file_name = os.path.join(experiment_result_dir, "success.txt")
        if incremental and os.path.exists(file_name):
            idx = config[("backtest_config", "id")]
            _LOG.warning("Found file '%s': skipping run %d", file_name, idx)
            num_skipped += 1
        else:
            configs_out.append(config)
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs_out
    return config_list_out, num_skipped


def select_config(
    config_list: cconfig.ConfigList,
    index: Optional[int],
    start_from_index: Optional[int],
) -> cconfig.ConfigList:
    """
    Select configs to run based on the command line parameters.

    :param config_list: list of configs
    :param index: index of a config to execute, if not `None`
    :param start_from_index: index of a config to start execution from, if not `None`
    :return: list of configs to execute
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    hdbg.dassert_lte(1, len(config_list))
    if index is not None:
        index = int(index)
        _LOG.warning("Only config %d will be executed because of --index", index)
        hdbg.dassert_lte(0, index)
        hdbg.dassert_lt(index, len(config_list))
        configs_out = [config_list[index]]
    elif start_from_index is not None:
        start_from_index = int(start_from_index)
        _LOG.warning(
            "Only configs >= %d will be executed because of --start_from_index",
            start_from_index,
        )
        hdbg.dassert_lte(0, start_from_index)
        hdbg.dassert_lt(start_from_index, len(config_list))
        configs_out = [
            c for idx, c in enumerate(config_list) if idx >= start_from_index
        ]
    else:
        configs_out = config_list.configs
    _LOG.info("Selected %s configs", len(config_list))
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs_out
    hdbg.dassert_isinstance(config_list_out, cconfig.ConfigList)
    return config_list_out


def get_config_list_from_command_line(
    args: argparse.Namespace,
) -> cconfig.ConfigList:
    """
    Return all the (complete) `Config`s to run given the command line
    interface.

    This is used by only `run_config_list.py` and `run_notebook.py` through
    `add_run_experiment_args()`, but not by `run_config_stub.py` which uses
    `cconfig.get_config_from_experiment_list_params()`.

    The configs are patched with all the information from the command line (namely
    `config_builder`, `experiment_builder`, `dst_dir`) from the options that are
    common to both `run_config_list.py` and `run_config_stub.py`.
    """
    # TODO(gp): This part is common to `get_config_list_from_experiment_list_params`.
    # Build the configs from the `ConfigBuilder`.
    config_builder = args.config_builder
    config_list = cconfig.get_config_list_from_builder(config_builder)
    _LOG.info("Generated %d configs from the builder", len(config_list))
    # Patch the configs with the command line parameters.
    params = {
        "config_builder": args.config_builder,
        "dst_dir": args.dst_dir,
    }
    if hasattr(args, "experiment_builder"):
        # `run_notebook.py` flow doesn't always have this.
        # TODO(gp): Check if it's true.
        params["experiment_builder"] = args.experiment_builder
    config_list = cconfig.patch_config_list(config_list, params)
    # Select the configs based on command line options.
    index = args.index
    start_from_index = args.start_from_index
    config_list = select_config(config_list, index, start_from_index)
    _LOG.info("Selected %d configs from command line", len(config_list))
    # Remove the configs already executed.
    incremental = not args.no_incremental
    config_list, num_skipped = skip_configs_already_executed(
        config_list, incremental
    )
    _LOG.info("Removed %d configs since already executed", num_skipped)
    _LOG.info("Need to execute %d configs", len(config_list))
    return config_list


# #############################################################################


def mark_config_as_success(experiment_result_dir: str) -> None:
    """
    Publish an empty file to indicate a successful finish.
    """
    file_name = os.path.join(experiment_result_dir, "success.txt")
    _LOG.info("Creating file_name='%s'", file_name)
    hio.to_file(file_name, "success")


def report_failed_experiments(
    config_list: cconfig.ConfigList, rcs: List[int]
) -> int:
    """
    Report failing experiments.

    :return: return code
    """
    # Get the experiment selected_idxs.
    experiment_ids = [
        int(config[("backtest_config", "id")]) for config in config_list
    ]
    # Match experiment selected_idxs with their return codes.
    failed_experiment_ids = [
        i for i, rc in zip(experiment_ids, rcs) if rc is not None and rc != 0
    ]
    # Report.
    if failed_experiment_ids:
        _LOG.error(
            "There are %d failed experiments: %s",
            len(failed_experiment_ids),
            failed_experiment_ids,
        )
        rc = -1
    else:
        rc = 0
    # TODO(gp): Save on a file the failed experiments' configs.
    return rc
