#!/usr/bin/env python
"""
Poetry sometimes can't solve the package specification because one package
requires dependencies that are not satisfiable with others.

This tool allows us to run Poetry incrementally for different configurations of
packages to help debug what package creates convergence problem of Poetry solver.

We separate packages in:
- necessary: our code heavily depends on those packages (e.g., `pandas`)
- optional: we could find a workaround and not use those packages

The use cases are:
- run all the necessary packages as basic sanity (necessary, optional)
- run all the necessary packages adding one by one, in order of importance
    (which is encoded in the order of the packages in the list)
    to see if there is one that makes poetry not converge (necessary_incremental)
- run all the necessary packages, adding one by one the optional ones (optional_incremental)

By default, script is terminated if `poetry lock` exceeds specified minutes of runtime.
Runtime can be controlled by `max_runtime_minutes` argument.

Final step is analyzing log outputs from `poetry lock` command that will
produce file with stats.
"""

import argparse
import logging
import multiprocessing
import os
import re
import time
from typing import Dict, List, Union

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.htimer as htimer

_LOG = logging.getLogger(__name__)


def get_debug_poetry_dir() -> str:
    """
    Get working directory of Poetry tool.
    """
    amp_path = hgit.get_amp_abs_path()
    poetry_debug_dir = os.path.join(amp_path, "dev_scripts/poetry")
    hdbg.dassert_dir_exists(poetry_debug_dir)
    return poetry_debug_dir


class PoetryDebugger:
    def __init__(self, debug_mode: str, max_runtime_minutes: int) -> None:
        """
        Constructor.

        :param debug_mode:
            - `necessary` - list of necessary packages in one shot
            - `necessary_incremental` - list of necessary packages one by one
                - i.e. add 1 package, run poetry, save the output, add another one, run poetry, etc.
            - `optional` - list of necessary and optional packages in one shot
            - `optional_incremental` - list of necessary packages in one shot,
                while optional are run one by one
        :param max_runtime_minutes: error out after breach of the allowed runtime
        """
        self._debug_mode = debug_mode
        self._max_runtime_minutes = max_runtime_minutes
        self._poetry_debug_dir = get_debug_poetry_dir()
        self._debug_mode_dir = os.path.join(
            self._poetry_debug_dir, self._debug_mode
        )

    def run(self) -> None:
        """
        Run poetry debug with various options.
        """
        # Get Python packages to debug.
        necessary_packages = self._get_necessary_packages()
        optional_packages = (
            self._get_optional_packages()
            if self._debug_mode in ("optional", "optional_incremental")
            else []
        )
        all_packages = necessary_packages + optional_packages
        # Pick desired debug option.
        if self._debug_mode == "necessary_incremental":
            # TODO(Grisha): can we factor out this part?
            # Add necessary packages one by one.
            current_necessary_packages = []
            for necessary_package in necessary_packages:
                current_necessary_packages.append(necessary_package)
                _LOG.info(
                    "Adding necessary incremental packages=`%s`",
                    current_necessary_packages,
                )
                self._run_wrapper(
                    current_necessary_packages,
                    last_package=necessary_package,
                )
        elif self._debug_mode == "optional_incremental":
            # Add optional packages one by one, after necessary ones in one shot.
            current_optional_packages = []
            for optional_package in optional_packages:
                current_optional_packages.append(optional_package)
                _LOG.info(
                    "Adding optional incremental packages=`%s`",
                    current_optional_packages,
                )
                self._run_wrapper(
                    necessary_packages + current_optional_packages,
                    last_package=optional_package,
                )
        elif self._debug_mode in ("necessary", "optional"):
            # Add packages in one shot.
            _LOG.info("Adding packages in one shot=`%s`", all_packages)
            self._run_wrapper(all_packages)
        else:
            raise ValueError(f"Unsupported debug mode `{self._debug_mode}`!")

    @staticmethod
    def _run_lock_cmd(dir_path: str) -> None:
        """
        Run `poetry lock` in verbose mode.

        :param dir_path: path of directory where command is run
        """
        # Prepare log file.
        log_file_name = "poetry.log"
        log_file_path = os.path.join(dir_path, log_file_name)
        # Prepare `poetry lock` command that is run in the same directory
        # where `pyproject.toml` and `poetry.toml` are stored.
        cmd = f"cd {dir_path}; poetry lock -vv"
        _LOG.info("Resolving poetry dependencies cdm=`%s`", cmd)
        # Run `poetry lock` command.
        hsystem.system(cmd, suppress_output=False, output_file=log_file_path)

    @staticmethod
    def _get_necessary_packages() -> List[str]:
        """
        Get necessary Python packages.
        """
        necessary_packages = [
            'python = "^3.8"',
            'pandas = "*"',
            'jupyter = "*"',
            'awscli = "1.22.17"',
            'jupyter_contrib_nbextensions = "*"',
            'jupyter_nbextensions_configurator = "*"',
            'matplotlib = "*"',
            'networkx = "*"',
            'psycopg2-binary = "*"',
            'pyarrow = "*"',
            'pytest = "*"',
            'pytest-cov = "*"',
            'pytest-instafail = "*"',
            'pytest-rerunfailures = "*"',
            'pytest-timeout = "*"',
            'pytest-xdist = "*"',
            'python-dotenv = "*"',
            'pywavelets = "*"',
            's3fs = "*"',
            'seaborn = "*"',
            'sklearn = "*"',
            'statsmodels = "*"',
            'tqdm = "*"',
        ]
        return necessary_packages

    @staticmethod
    def _get_optional_packages() -> List[str]:
        """
        Get optional Python packages.
        """
        optional_packages = [
            'boto3 = "*"',
            'invoke = "*"',
            'jsonpickle = "*"',
            'moto = "*"',
            'psutil = "*"',
            'pygraphviz = "*"',
            'requests = "*"',
        ]
        return optional_packages

    def _run_with_time_constraint(self, dir_path: str) -> None:
        """
        Command `poetry lock` is started as a separate process so runtime can
        be measured and stopped if needed.

        :param dir_path: path of directory where command is run
        """
        # Run as a separate process.
        poetry_lock = multiprocessing.Process(
            target=self._run_lock_cmd, args=(dir_path,)
        )
        poetry_lock.start()
        # Apply time constraint.
        timer = htimer.Timer()
        while poetry_lock.is_alive():
            if timer.get_total_elapsed() > self._max_runtime_minutes * 60:
                poetry_lock.kill()
                raise RuntimeError(
                    f"Constraint of {self._max_runtime_minutes} minutes is breached!"
                )
            timer.resume()
            time.sleep(1)
        # Cleanup.
        poetry_lock.join()
        poetry_lock.close()

    def _run_wrapper(
        self,
        python_packages: List[str],
        *,
        last_package: str = "",
    ) -> None:
        """
        Wrapper around `poetry lock`.

        :param python_packages: list of packages to be written in `pyproject.toml` file
        :param last_package: last package in `pyproject.toml` that is useful for
            creating different log files in incremental run
        """
        # Base directory path without subdirectories.
        dir_path = self._debug_mode_dir
        # Use clean package name, if package name is provided.
        if last_package:
            # `pandas = "*"` will become `pandas`.
            last_package = last_package.split(" ")[0]
            # Add last package as subdirectory.
            dir_path = os.path.join(dir_path, last_package)
        # Write `*.toml` files.
        self._write_poetry_toml_file(dir_path)
        self._write_pyproject_toml(python_packages, dir_path)
        # Start as a separate process.
        self._run_with_time_constraint(dir_path)

    def _write_pyproject_toml(self, packages: List[str], dir_name: str) -> None:
        """
        Write a `pyproject.toml` that orchestrate project metadata and its
        dependencies.

        :param packages: list of Python packages
        :param dir_name: name of directory where `pyproject.toml` is saved
        """
        beginning_of_file = """
        [tool.poetry]
        name = "amp"
        version = "1.0.0"
        description = ""
        authors = ["Your Name <you@example.com>"]

        [tool.poetry.dependencies]
        """
        end_of_file = """

        [tool.poetry.dev-dependencies]

        [build-system]
        requires = ["poetry-core>=1.0.0"]
        build-backend = "poetry.core.masonry.api"
        """
        packages = "\n".join(packages)
        file_content = "".join(
            [
                hprint.dedent(beginning_of_file),
                hprint.dedent(packages),
                "\n",
                hprint.dedent(end_of_file),
            ]
        )
        file_path = os.path.join(
            self._poetry_debug_dir, dir_name, "pyproject.toml"
        )
        _LOG.info("Writing `pyproject.toml` to file=`%s`", file_path)
        hio.to_file(file_path, file_content)

    def _write_poetry_toml_file(self, dir_name: str) -> None:
        """
        Write a `poetry.toml` that contains specific configuration for Poetry
        run.

        :param dir_name: name of directory where `poetry.toml` is saved
        """
        file_content = """
        cache-dir = "tmp.pypoetry"
        experimental.new-installer = true
        installer.parallel = true
        # We don't want poetry to automatically create / manage virtual environment.
        virtualenvs.create = false
        virtualenvs.in-project = true
        """
        file_content = hprint.dedent(file_content)
        file_path = os.path.join(self._poetry_debug_dir, dir_name, "poetry.toml")
        _LOG.info("Writing `poetry.toml` to file=`%s`", file_path)
        hio.to_file(file_path, file_content)


POETRY_STATS = Dict[str, Union[str, Dict[str, str]]]


class PoetryDebugStatsComputer:
    def run(self) -> None:
        """
        Inspect all logs generated by `poetry lock` one by one.

        At the end of inspection stats are saved in current directory.
        """
        stats: POETRY_STATS = {}
        working_directory = get_debug_poetry_dir()
        pattern = "poetry.log"
        only_files = False
        use_relative_paths = False
        # Collect all logs.
        log_paths = hio.listdir(
            working_directory, pattern, only_files, use_relative_paths
        )
        for log_path in log_paths:
            # Parse log path to extract debug mode directories.
            # `.../poetry/necessary_incremental/pandas/poetry.log`.
            debug_mode_path = log_path.split(f"poetry{os.sep}")[-1]
            # `necessary_incremental/pandas/poetry.log` -> ["necessary_incremental", "pandas"].
            debug_mode_dirs = debug_mode_path.split(os.sep)[:-1]
            # Analyze log.
            log_file = hio.from_file(log_path)
            time_info = self._get_execution_time_from_log(log_file)
            # Update stats.
            self._update_poetry_run_stats(stats, debug_mode_dirs, time_info)
        # Save stats.
        filename = "poetry_debugger_stats.json"
        hio.to_json(os.path.join(working_directory, filename), stats)

    @staticmethod
    def _update_poetry_run_stats(
        stats: POETRY_STATS, debug_mode_dirs: List[str], time_info: str
    ) -> None:
        """
        On each log inspection, new stats are appended.

        :param debug_mode_dirs: specific per each debug mode
        :param time_info: time information in seconds as string or message
        """
        if "incremental" in debug_mode_dirs[0]:
            # If we are in incremental run, first dir is debug_mode, second is
            # last package name from incremental run.
            # {
            #     "necessary_incremental": {
            #         "pandas": "0.123",
            #         "jupyter": "0.345",
            #     }
            # }
            if stats.get(debug_mode_dirs[0], None) is None:
                # TODO(Nikola): Simpler init, default dict?
                stats[debug_mode_dirs[0]] = {}
            # TODO(Grisha): once this part is simplified make sure that lint
            #  has gone away `[amp_mypy] error: Unsupported target for indexed
            #  assignment ("Union[str, Dict[str, str]]")  [index]`.
            stats[debug_mode_dirs[0]].update({debug_mode_dirs[1]: time_info})
        else:
            # If we are in regular non-incremental run, there is only one dir.
            # {
            #     "necessary": "35.57"
            # }
            stats[debug_mode_dirs[0]] = time_info

    @staticmethod
    def _get_execution_time_from_log(log_file: str) -> str:
        """
        Log file is checked for certain patterns that will provide valuable
        info for stats file.

        :param log_file: content of log file in string format
        :return: execution time information
        """
        time_info = "No time information!"
        # Get total seconds.
        time_info_list = re.findall(r"solving took (.*?) seconds", log_file)
        if time_info_list:
            time_info = time_info_list[-1]
        return time_info


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--debug_mode",
        action="store",
        type=str,
        required=True,
        help="Run poetry with desired list of packages",
    )
    parser.add_argument(
        "--max_runtime_minutes",
        action="store",
        type=int,
        default=10,
        help="Error out after breach of the allowed runtime",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    debug_mode = args.debug_mode
    max_runtime_minutes = args.max_runtime_minutes
    # TODO(Grisha): get rid of `try - finally` if possible.
    try:
        # Initialize and start debugger.
        poetry_debugger = PoetryDebugger(debug_mode, max_runtime_minutes)
        poetry_debugger.run()
    finally:
        # Initialize and start debugger analyzer.
        poetry_debugger_analyzer = PoetryDebugStatsComputer()
        poetry_debugger_analyzer.run()


if __name__ == "__main__":
    _main(_parse())
