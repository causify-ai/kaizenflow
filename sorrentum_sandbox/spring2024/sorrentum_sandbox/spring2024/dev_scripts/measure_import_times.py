#!/usr/bin/env python

"""
Calculate execution time of imports.

Import as:

import dev_scripts.measure_import_times as dsmeimti
"""

import argparse
import datetime
import logging
import re
from typing import Dict, List, Tuple, Union

from tqdm import tqdm

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem
from helpers.htimer import Timer

_LOG = logging.getLogger(__name__)


class ImportTimeChecker:
    """
    Class for measure execution time for imports.
    """

    def __init__(self, dir_name: str) -> None:
        """
        :param dir_name: directory name to search python files
        """
        self.dir_name = dir_name
        # Store all the modules with execution time (module: elapsed_time).
        self.checked_modules: Dict[str, float] = {}
        # Store error messages for modules (module: error_message).
        self.error_messages: Dict[str, str] = {}
        # instance of class for measure elapsed time.
        # Pattern for finding modules in file.
        self.match_pattern = (
            r"(?m)^\s*(?:from|import)\s+([a-zA-Z0-9_.]+(?:\s*,\s*\w+)*)"
        )

    def find_modules_from_file(self, file_name: str) -> List[str]:
        """
        Search modules in a given file.

        :param file_name: filename where need to search modules
        :return: list of all found module name
        """
        _LOG.debug("file_name=%s", file_name)
        text = hio.from_file(file_name)
        modules = re.findall(self.match_pattern, text)
        _LOG.debug("  -> modules=%s", modules)
        return modules

    def measure_time(self, module: str) -> Union[str, float]:
        """
        Measures execution time for a given module and save in
        self.checked_modules.

        :param module: module name
        :return: elapsed time to execute import
            or error message if import failed
        """
        # TODO(Grisha): unclear if the `python -c "import X"` is a viable approach, see the discussion in CmTask4968.
        # TODO(Grisha): consider separating local modules vs 3rd party modules vs native Python libs.
        # Execute python "import module" to measure.
        if module not in self.checked_modules:
            timer = Timer()
            rc, output = hsystem.system_to_string(f'python -c "import {module}"', abort_on_error=False)
            timer.stop()
            if rc == 0:
                # Save execution time.
                elapsed_time = round(timer.get_elapsed(), 3)
                self.checked_modules[module] = elapsed_time
                ret = elapsed_time
                # TODO(Grisha): consider catching exactly `ModuleNotFoundError`.
            else:
                # Save the errors.
                _LOG.warning(output)
                self.error_messages[module] = str(output)
                ret = output
        else:
            ret = self.checked_modules[module]
        return ret

    def measure_time_for_all_modules(self) -> None:
        """
        Traverse files and directory and find all modules and measure execution time
        :return: None
        """
        pattern = "*.py"
        only_files = True
        use_relative_paths = False
        file_names = hio.listdir(
            self.dir_name, pattern, only_files, use_relative_paths
        )
        modules = set()
        for file_name in file_names:
            _LOG.debug("filename: %s", file_name)
            modules_tmp = self.find_modules_from_file(file_name)
            modules.update(set(modules_tmp))
        #
        modules = sorted(list(modules))
        _LOG.info("Found %d modules", len(modules))
        for module in tqdm(modules):
            self.measure_time(module)

    def output_modules_time(self, sort: bool = False) -> None:
        """
        Print and save to a files all measured modules.

        :param sort: defines whether sort output or not
        :return: None
        """
        if sort:
            self._sort_by_time()
        for module, elapsed_time in self.checked_modules.items():
            print(f"{module} {elapsed_time} s")
        # Save modules time to a file.
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tmp_import_time_{timestamp}.txt"
        lines = [
            f"{module} {elapsed_time} s"
            for module, elapsed_time in self.checked_modules.items()
        ]
        hio.to_file(filename, "\n".join(lines))
        # Save errors to a file.
        errors_filename = f"tmp_errors_import_time_{timestamp}.txt"
        error_lines = [
            f"{module} {error_message}"
            for module, error_message in self.error_messages.items()
        ]
        hio.to_file(errors_filename, "\n".join(error_lines))

    def get_total_time(self) -> float:
        """
        Calculates total time spend for importing
        :return: float
        """
        total_time = 0
        for time in self.checked_modules.values():
            total_time += time
        return total_time

    def get_list(self) -> List[Tuple[str, float]]:
        """
        Return self.checled_modules in list format
        :return: list
        """
        return list(self.checked_modules.items())

    def _sort_by_time(self) -> None:
        """
        Sort time in descending order in self.checked_modules
        :return: None
        """
        output = sorted(
            self.checked_modules.items(), reverse=True, key=lambda x: x[1]
        )
        self.checked_modules = dict(output)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        help="search directory (default: current directory)",
        default=".",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    checker = ImportTimeChecker(args.directory)
    checker.measure_time_for_all_modules()
    checker.output_modules_time(sort=True)
    #
    total_time = checker.get_total_time()
    print(f"Total time for importing: {total_time}")


if __name__ == "__main__":
    _main(_parse())
