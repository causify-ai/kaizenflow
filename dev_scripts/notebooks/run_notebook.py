#!/usr/bin/env python
r"""
Run a notebook given a config or a list of configs.

# Use example:
> run_notebook.py \
    --notebook nlp/notebooks/NLP_RP_pipeline.ipynb \
    --config_builder "nlp.build_configs.build_PTask1088_configs()" \
    --dst_dir nlp/test_results \
    --num_threads 2

Import as:

import dev_scripts.notebooks.run_notebook as dsnoruno
"""

import argparse
import logging
import os
from typing import Optional

import nbformat

import core.config as cconfig
import dataflow.backtest.dataflow_backtest_utils as dtfbaexuti
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hjoblib as hjoblib
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


# #############################################################################


# TODO(Grisha): Consider adding `allow_notebook_errors` switch.
def _run_notebook(
    config: cconfig.Config,
    notebook_file: str,
    publish: bool,
    allow_notebook_errors: bool,
    #
    incremental: bool,
    num_attempts: int,
) -> Optional[int]:
    """
    Run a notebook for a specific `Config`.

    :param config: config for the experiment
    :param notebook_file: path to file with experiment template
    :param num_attempts: maximum number of times to attempt running the
        notebook
    :param publish: publish the notebook if `True`
    :param allow_notebook_errors: if `True`, the notebook is executed until
        the end, regardless of any error encountered during the execution;
        otherwise, raise an error if any cell in a notebook fails
    :return: if notebook is skipped ("success.txt" file already exists), return
        `None`; otherwise, return `rc`
    """
    _ = incremental
    dtfbaexuti.setup_experiment_dir(config)
    # Prepare the destination file.
    idx = config[("backtest_config", "id")]
    experiment_result_dir = config[("backtest_config", "experiment_result_dir")]
    dst_file = os.path.join(
        experiment_result_dir,
        os.path.basename(notebook_file).replace(".ipynb", ".%s.ipynb" % idx),
    )
    _LOG.info("dst_file=%s", dst_file)
    dst_file = os.path.abspath(dst_file)
    # Export config function and its `id` to the notebook.
    config_builder = config[("backtest_config", "config_builder")]
    dst_dir = config[("backtest_config", "dst_dir")]
    # Note the quotation marks, `config_builder` should be surrounded by single
    # quotes so that the potential strings in `config_builder` params are
    # parsed correctly. E.g.,
    # `export __CONFIG_BUILDER__='amp.oms.reconciliation.build_reconciliation_configs("20221128_101500", "20221128_1210", "scheduled")'`.
    cmd = [
        f"export __CONFIG_BUILDER__='{config_builder}';",
        f'export __CONFIG_IDX__="{idx}";',
        f'export __CONFIG_DST_DIR__="{dst_dir}"',
        f'; jupyter nbconvert {notebook_file}',
        '--execute',
        '--to notebook',
        f'--output {dst_file}',
        '--ExecutePreprocessor.kernel_name=python',
        # From https://github.com/ContinuumIO/anaconda-issues/issues/877
        '--ExecutePreprocessor.timeout=-1',
        f'--ExecutePreprocessor.allow_errors={allow_notebook_errors}',
    ]
    cmd = " ".join(cmd)
    # Prepare the log file.
    log_file = os.path.join(experiment_result_dir, "run_notebook.%s.log" % idx)
    log_file = os.path.abspath(os.path.abspath(log_file))
    _LOG.info("log_file=%s", log_file)
    # TODO(gp): Repeating a command n-times is an idiom that we could move to
    #  system_interaction.
    # Try running the notebook up to `num_attempts` times.
    hdbg.dassert_lte(1, num_attempts)
    rc: Optional[int] = None
    for n in range(1, num_attempts + 1):
        if n > 1:
            _LOG.warning(
                "Run the notebook: %d / %d attempt",
                n,
                num_attempts,
            )
        _LOG.info("cmd='%s'", cmd)
        rc = hsystem.system(cmd, output_file=log_file, abort_on_error=False)
        if rc == 0:
            _LOG.info("Running notebook was successful")
            break
    if publish:
        # TODO(Grisha): Consider adding a switch to publish regardless of errors, e.g.,
        # `publish_even_if_fails`.
        # Convert to HTML and publish a notebook.
        if rc != 0:
            # The goal is to publish a notebook regardless of errors. However,
            # the execution fails there is no `ipynb` file to publish. So a file is
            # read and written back just to be able to publish it.
            with open(notebook_file) as f:
                nb = nbformat.read(f, as_version=4)
            with open(dst_file, mode='w', encoding='utf-8') as f:
                nbformat.write(nb, f)
        _LOG.info("Publishing notebook %d", idx)
        html_subdir_name = os.path.join(
            os.path.basename(dst_dir), experiment_result_dir
        )
        # TODO(gp): Look for the script.
        amp_dir = hgit.get_amp_abs_path()
        script_path = os.path.join(
            amp_dir, "dev_scripts/notebooks", "publish_notebook.py"
        )
        cmd = (
            f"python {script_path}"
            + f" --file {dst_file}"
            + f" --target_dir {html_subdir_name}"
            + " --action publish"
        )
        log_file = log_file.replace(".log", ".html.log")
        hsystem.system(cmd, output_file=log_file)
    if rc == 0:
        dtfbaexuti.mark_config_as_success(experiment_result_dir)
    else:
        msg = f"Execution failed for experiment {idx}"
        _LOG.error(msg)
        raise RuntimeError(msg)
    return rc


def _get_workload(args: argparse.Namespace) -> hjoblib.Workload:
    """
    Prepare the workload using the parameters from command line.
    """
    # Get the configs to run.
    config_list = dtfbaexuti.get_config_list_from_command_line(args)
    # Get the notebook file.
    notebook_file = os.path.abspath(args.notebook)
    hdbg.dassert_path_exists(notebook_file)
    #
    publish = args.publish_notebook
    allow_notebook_errors = args.allow_errors
    # Prepare the tasks.
    tasks = []
    for config in config_list:
        task: hjoblib.Task = (
            # args.
            (config, notebook_file, publish, allow_notebook_errors),
            # kwargs.
            {},
        )
        tasks.append(task)
    #
    func_name = "_run_notebook"
    workload = (_run_notebook, func_name, tasks)
    hjoblib.validate_workload(workload)
    return workload


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Add common experiment options.
    parser = dtfbaexuti.add_run_experiment_args(parser, dst_dir_required=True)
    # Add notebook options.
    parser.add_argument(
        "--notebook",
        action="store",
        required=True,
        help="File storing the notebook to iterate over",
    )
    parser.add_argument(
        "--publish_notebook",
        action="store_true",
        help="Publish each notebook after it executes",
    )
    parser.add_argument(
        "--allow_errors",
        action="store_true",
        help="Run the notebook until the end, regardless of any error in it",
    )
    parser = hparser.add_verbosity_arg(parser)
    # TODO(gp): For some reason, not even this makes mypy happy.
    # cast(argparse.ArgumentParser, parser)
    return parser  # type: ignore


# TODO(gp): Make the notebook save the config that it sees. This might
#  make the code simpler and more robust.
# TODO(gp): We could try to serialize/deserialize the config and pass to the notebook
#  a pointer to the file.


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Create the dst dir.
    dst_dir, clean_dst_dir = hparser.parse_dst_dir_arg(args)
    _ = clean_dst_dir
    # Prepare the workload.
    workload = _get_workload(args)
    # Parse command-line options.
    dry_run = args.dry_run
    num_threads = args.num_threads
    incremental = not args.no_incremental
    abort_on_error = not args.skip_on_error
    num_attempts = args.num_attempts
    # Prepare the log file.
    timestamp = hdateti.get_current_timestamp_as_string("naive_ET")
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
    )
    #
    _LOG.info("dst_dir='%s'", dst_dir)
    _LOG.info("log_file='%s'", log_file)
    # TODO(gp): Move this inside the framework.
    # # Report failing experiments.
    # rc = dtfmoexuti.report_failed_experiments(configs, rcs)
    # sys.exit(rc)


if __name__ == "__main__":
    _main(_parse())