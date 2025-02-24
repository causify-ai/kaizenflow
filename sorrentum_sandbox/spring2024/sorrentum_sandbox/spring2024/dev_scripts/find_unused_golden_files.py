#!/usr/bin/env python

import argparse
import collections
import logging
import os
import pprint
import re
from typing import Dict, List, Set, Tuple

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def get_test_methods_from_files(dir_name: str) -> List[str]:
    """
    Get test methods with existing golden outcomes.

    :param dir_name: the head dir to get the test methods from
    :return: test methods, e.g. ["dir/test/outcomes/TestClass.test1",
        "dir/test/outcomes/TestClass.test2"]
    """
    test_methods = []
    for root, dirs, _ in os.walk(dir_name):
        if root.endswith("test/outcomes"):
            # Get names of the dirs with golden test outcomes.
            test_method_dirs = [
                f"{root}/{d}"
                for d in dirs
                if d.startswith("Test") and os.path.isdir(f"{root}/{d}/output")
            ]
            test_methods.extend(test_method_dirs)
    # Drop duplicates.
    test_methods = sorted(set(test_methods))
    return test_methods


def get_python_test_files(dir_name: str) -> List[str]:
    """
    Get names of Python files with tests.

    :param dir_name: the head dir to get the .py test files from
    :return: names of .py files with tests, e.g. ["dir/test/test_lib.py"]
    """
    test_py_files = []
    for root, dirs, files in os.walk(dir_name):
        if root.endswith("test") and "outcomes" in dirs:
            # Get names of the Python files with tests.
            cur_test_py_files = [
                f"{root}/{f}"
                for f in files
                if f.startswith("test_") and f.endswith(".py")
            ]
            test_py_files.extend(cur_test_py_files)
    # Drop duplicates.
    test_py_files = sorted(set(test_py_files))
    return test_py_files


def parse_test_code(
    code: str, test_py_file: str
) -> Tuple[List[str], Dict[str, str]]:
    """
    Extract test methods from the code of a test file.

    :param code: the code of the test file
    :param test_py_file: the name of the .py file with tests
    :return:
        - test methods, e.g. ["dir/test/outcomes/TestClass.test1",
          "dir/test/outcomes/TestClass.test2"]
        - a mapping between test classes and the name of the .py file
          with these tests, e.g. {"dir/test/outcomes/TestClass": "dir/test/test_lib.py"}
    """
    dir_ = os.path.dirname(test_py_file)
    test_methods: List[str] = []
    class_to_test_file: Dict[str, str] = {}
    # Extract the test classes.
    classes = re.split(r"class (Test.+)\(.+\):\n", code)
    if len(classes) == 1:
        return test_methods, class_to_test_file
    classes_grouped = [
        classes[1:][i : i + 2] for i in range(0, len(classes[1:]), 2)
    ]
    for test_class_name, test_class_code in classes_grouped:
        # Store the class-filename mapping.
        class_to_test_file[f"{dir_}/outcomes/{test_class_name}"] = test_py_file
        # Extract the test methods.
        methods = re.split(r"def (.+)\(", test_class_code)
        if len(methods) == 1:
            continue
        methods_grouped = [
            methods[1:][i : i + 2] for i in range(0, len(methods[1:]), 2)
        ]
        # Find methods with a `check_string` call that are likely to be helpers.
        helper_names: Set[str] = set()
        for _ in range(2):
            for test_method_name, test_method_code in methods_grouped:
                if (
                    "self.check_string(" in test_method_code
                    or "self.check_dataframe(" in test_method_code
                    or any(f"self.{n}(" in test_method_code for n in helper_names)
                ) and not test_method_name.startswith("test"):
                    helper_names.add(test_method_name)
        for test_method_name, test_method_code in methods_grouped:
            if (
                "self.check_string(" in test_method_code
                or "self.check_dataframe(" in test_method_code
                or any(f"self.{n}(" in test_method_code for n in helper_names)
            ) and test_method_name not in helper_names:
                # Store non-helper methods with `check_string` calls or calls to
                # helper methods with `check_string`.
                test_methods.append(
                    f"{dir_}/outcomes/{test_class_name}.{test_method_name}"
                )
    return test_methods, class_to_test_file


def get_test_methods_from_code(
    dir_name: str,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Get test methods that require golden outcomes.

    Test methods are extracted from the code of .py files with tests.

    :param dir_name: the head dir to get the test methods from
    :return:
        - test methods, e.g. ["dir/test/outcomes/TestClass.test1",
          "dir/test/outcomes/TestClass.test2"]
        - a mapping between test classes and the names of .py files
          with these tests, e.g. {"dir/test/outcomes/TestClass": "dir/test/test_lib.py"}
    """
    # Get the names of .py files with tests.
    test_py_files = get_python_test_files(dir_name)
    #
    test_methods = []
    class_to_test_file = {}
    for test_py_file in test_py_files:
        code = hio.from_file(test_py_file)
        # Extract the test methods that require golden outcomes.
        cur_test_methods, cur_class_to_test_file = parse_test_code(
            code, test_py_file
        )
        test_methods.extend(cur_test_methods)
        class_to_test_file.update(cur_class_to_test_file)
    # Drop duplicates.
    test_methods = sorted(set(test_methods))
    return test_methods, class_to_test_file


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dir_name",
        action="store",
        default=".",
        help="Dir to explore",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(args.log_level)
    # Get test methods that have golden outcome files.
    test_methods_from_files = get_test_methods_from_files(args.dir_name)
    # Get test methods that require golden outcome files.
    test_methods_from_code, class_to_test_file = get_test_methods_from_code(
        args.dir_name
    )
    # Get methods that require golden file but do not have them.
    # These methods are likely to be disabled.
    missing_goldens = sorted(
        set(test_methods_from_code) - set(test_methods_from_files)
    )
    missing_goldens_out = collections.defaultdict(list)
    for g in missing_goldens:
        g_class = ".".join(g.split(".")[:-1])
        test_file = class_to_test_file.get(g_class, "_other_")
        missing_goldens_out[test_file].append(g)
    _LOG.info(
        "\nTest methods with 'check_string' and without golden outcome files:\n%s",
        pprint.pformat(missing_goldens_out),
    )
    # Get methods that have golden files but no `check_string` call.
    extra_goldens = sorted(
        set(test_methods_from_files) - set(test_methods_from_code)
    )
    extra_goldens_out = collections.defaultdict(list)
    for g in extra_goldens:
        g_class = ".".join(g.split(".")[:-1])
        test_file = class_to_test_file.get(g_class, "_other_")
        extra_goldens_out[test_file].append(g)
    _LOG.info(
        "\nTest methods without 'check_string' and with golden outcome files:\n%s",
        pprint.pformat(extra_goldens_out),
    )


if __name__ == "__main__":
    _main(_parse())
