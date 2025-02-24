"""
Import as:

import helpers.lib_tasks_find as hlitafin
"""

import functools
import glob
import logging
import os
import re
from typing import Iterator, List, Optional, Tuple

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hlist as hlist
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access

# #############################################################################
# Find test.
# #############################################################################


def _find_test_files(
    dir_name: Optional[str] = None, use_absolute_path: bool = False
) -> List[str]:
    """
    Find all the files containing test code in `abs_dir`.
    """
    dir_name = dir_name or "."
    hdbg.dassert_dir_exists(dir_name)
    _LOG.debug("abs_dir=%s", dir_name)
    # Find all the file names containing test code.
    _LOG.info("Searching from '%s'", dir_name)
    path = os.path.join(dir_name, "**", "test_*.py")
    _LOG.debug("path=%s", path)
    file_names = glob.glob(path, recursive=True)
    _LOG.debug("Found %d files: %s", len(file_names), str(file_names))
    hdbg.dassert_no_duplicates(file_names)
    # Test files should always under a dir called `test`.
    for file_name in file_names:
        if "/old/" in file_name:
            continue
        if "/compute/" in file_name:
            continue
        hdbg.dassert_eq(
            os.path.basename(os.path.dirname(file_name)),
            "test",
            "Test file '%s' needs to be under a `test` dir ",
            file_name,
        )
        hdbg.dassert_not_in(
            "notebook/",
            file_name,
            "Test file '%s' should not be under a `notebook` dir",
            file_name,
        )
    # Make path relatives, if needed.
    if use_absolute_path:
        file_names = [os.path.abspath(file_name) for file_name in file_names]
    #
    file_names = sorted(file_names)
    _LOG.debug("file_names=%s", file_names)
    hdbg.dassert_no_duplicates(file_names)
    return file_names


# TODO(gp): -> find_class since it works also for any class.
def _find_test_class(
    class_name: str, file_names: List[str], exact_match: bool = False
) -> List[str]:
    """
    Find test file containing `class_name` and report it in pytest format.

    E.g., for "TestLibTasksRunTests1" return
    "test/test_lib_tasks.py::TestLibTasksRunTests1"

    :param exact_match: find an exact match or an approximate where `class_name`
        is included in the class name
    """
    # > jackpy TestLibTasksRunTests1
    # test/test_lib_tasks.py:60:class TestLibTasksRunTests1(hut.TestCase):
    regex = r"^\s*class\s+(\S+)\s*\("
    _LOG.debug("regex='%s'", regex)
    res: List[str] = []
    # Scan all the files.
    for file_name in file_names:
        _LOG.debug("file_name=%s", file_name)
        txt = hio.from_file(file_name)
        # Search for the class in each file.
        for i, line in enumerate(txt.split("\n")):
            # _LOG.debug("file_name=%s i=%s: %s", file_name, i, line)
            # TODO(gp): We should skip ```, """, '''
            m = re.match(regex, line)
            if m:
                found_class_name = m.group(1)
                _LOG.debug("  %s:%d -> %s", line, i, found_class_name)
                if exact_match:
                    found = found_class_name == class_name
                else:
                    found = class_name in found_class_name
                if found:
                    res_tmp = f"{file_name}::{found_class_name}"
                    _LOG.debug("-> res_tmp=%s", res_tmp)
                    res.append(res_tmp)
    res = sorted(list(set(res)))
    return res


# TODO(gp): Extend this to accept only the test method.
# TODO(gp): Have a single `find` command with multiple options to search for different
#  things, e.g., class names, test names, pytest_mark, ...
@task
def find_test_class(ctx, class_name, dir_name=".", pbcopy=True, exact_match=False):  # type: ignore
    """
    Report test files containing `class_name` in a format compatible with
    pytest.

    :param class_name: the class to search
    :param dir_name: the dir from which to search (default: .)
    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    hlitauti.report_task(txt="class_name abs_dir pbcopy")
    hdbg.dassert(class_name != "", "You need to specify a class name")
    _ = ctx
    file_names = _find_test_files(dir_name)
    res = _find_test_class(class_name, file_names, exact_match)
    res = " ".join(res)
    # Print or copy to clipboard.
    hlitauti._to_pbcopy(res, pbcopy)


# //////////////////////////////////////////////////////////////////////////////////


@functools.lru_cache()
def _get_python_files(subdir: str) -> List[str]:
    pattern = "*.py"
    only_files = False
    use_relative_paths = False
    python_files = hio.listdir(subdir, pattern, only_files, use_relative_paths)
    # Remove tmp files.
    python_files = [f for f in python_files if not f.startswith("tmp")]
    return python_files


# File, line number, line, info1, info2
_FindResult = Tuple[str, int, str, str, str]
_FindResults = List[_FindResult]


def _scan_files(python_files: List[str]) -> Iterator:
    for file_ in python_files:
        _LOG.debug("file=%s", file_)
        txt = hio.from_file(file_)
        for line_num, line in enumerate(txt.split("\n")):
            # TODO(gp): Skip commented lines.
            # _LOG.debug("%s:%s line='%s'", file_, line_num, line)
            yield file_, line_num, line


def _find_short_import(iterator: Iterator, short_import: str) -> _FindResults:
    """
    Find imports in the Python files with the given short import.

    E.g., for dtfcodarun dataflow/core/test/test_builders.py:9:import
    dataflow.core.dag_runner as dtfcodarun returns
    """
    # E.g.,
    # `import dataflow.core.dag_runner as dtfcodarun`
    regex = rf"import\s+(\S+)\s+as\s+({short_import})"
    regex = re.compile(regex)
    #
    results: _FindResults = []
    for file_, line_num, line in iterator:
        m = regex.search(line)
        if m:
            # E.g.,
            # dataflow/core/test/test_builders.py:9:import dataflow.core.dag_runner as dtfcodarun
            _LOG.debug("  --> line:%s=%s", line_num, line)
            long_import_txt = m.group(1)
            short_import_txt = m.group(2)
            full_import_txt = f"import {long_import_txt} as {short_import_txt}"
            res = (file_, line_num, line, short_import_txt, full_import_txt)
            # E.g.,
            _LOG.debug("  => %s", str(res))
            results.append(res)
    return results


def _find_func_class_uses(iterator: Iterator, regex: str) -> _FindResults:
    regexs = []
    # E.g.,
    # `dag_runner = dtfsys.RealTimeDagRunner(**dag_runner_kwargs)`
    regexs.append(rf"\s+(\w+)\.(\w*{regex})\(")
    # `dag_builder: dtfcodabui.DagBuilder`
    regexs.append(rf":\s*(\w+)\.(\w*{regex})")
    #
    _LOG.debug("regexs=%s", str(regexs))
    regexs = [re.compile(regex_) for regex_ in regexs]
    #
    results: _FindResults = []
    for file_, line_num, line in iterator:
        _LOG.debug("line='%s'", line)
        m = None
        for regex_ in regexs:
            m = regex_.search(line)
            if m:
                # _LOG.debug("--> regex matched")
                break
        if m:
            _LOG.debug("  --> line:%s=%s", line_num, line)
            short_import_txt = m.group(1)
            obj_txt = m.group(2)
            res = (file_, line_num, line, short_import_txt, obj_txt)
            # E.g.,
            # ('./helpers/lib_tasks.py', 10226, 'dtfsys', 'RealTimeDagRunner')
            # ('./dataflow/core/test/test_builders.py', 70, 'dtfcodarun', 'FitPredictDagRunner')
            # ('./dataflow/core/test/test_builders.py', 157, 'dtfcodarun', 'FitPredictDagRunner')
            _LOG.debug("  => %s", str(res))
            results.append(res)
    return results


def _process_find_results(results: _FindResults, how: str) -> List:
    filtered_results: List = []
    if how == "remove_dups":
        # Remove duplicates.
        for result in results:
            (_, _, _, info1, info2) = result
            filtered_results.append((info1, info2))
        filtered_results = hlist.remove_duplicates(filtered_results)
        filtered_results = sorted(filtered_results)
    elif how == "all":
        filtered_results = sorted(results)
    else:
        raise ValueError(f"Invalid how='{how}'")
    return filtered_results


@task
def find(ctx, regex, mode="all", how="remove_dups", subdir="."):  # type: ignore
    """
    Find symbols, imports, test classes and so on.

    Example:
    ```
    > i find DagBuilder
    ('dtfcodabui', 'DagBuilder')
    ('dtfcore', 'DagBuilder')
    ('dtfcodabui', 'import dataflow.core.dag_builder as dtfcodabui')
    ('dtfcore', 'import dataflow.core as dtfcore')
    ```

    :param regex: function or class use to search for
    :param mode: what to look for
        - `symbol_import`: look for uses of function or classes
          E.g., `DagRunner`
          returns
          ```
          ('cdataf', 'PredictionDagRunner')
          ('cdataf', 'RollingFitPredictDagRunner')
          ```
        - `short_import`: look for the short import
          E.g., `'dtfcodabui'
          returns
          ```
          ('dtfcodabui', 'import dataflow.core.dag_builder as dtfcodabui')
          ```
    :param how: how to report the results
        - `remove_dups`: report only imports and calls that are the same
    """
    hlitauti.report_task(txt=hprint.to_str("regex mode how subdir"))
    _ = ctx
    # Process the `where`.
    python_files = _get_python_files(subdir)
    iter_ = _scan_files(python_files)
    # Process the `what`.
    if mode == "all":
        for mode_tmp in ("symbol_import", "short_import"):
            find(ctx, regex, mode=mode_tmp, how=how, subdir=subdir)
        return
    if mode == "symbol_import":
        results = _find_func_class_uses(iter_, regex)
        filtered_results = _process_find_results(results, "remove_dups")
        print("\n".join(map(str, filtered_results)))
        # E.g.,
        # ('cdataf', 'PredictionDagRunner')
        # ('cdataf', 'RollingFitPredictDagRunner')
        # Look for each short import.
        results = []
        for short_import, _ in filtered_results:
            iter_ = _scan_files(python_files)
            results.extend(_find_short_import(iter_, short_import))
    elif mode == "short_import":
        results = _find_short_import(iter_, regex)
    else:
        raise ValueError(f"Invalid mode='{mode}'")
    # Process the `how`.
    filtered_results = _process_find_results(results, how)
    print("\n".join(map(str, filtered_results)))


# #############################################################################
# Find test decorator.
# #############################################################################


# TODO(gp): decorator_name -> pytest_mark
def _find_test_decorator(decorator_name: str, file_names: List[str]) -> List[str]:
    """
    Find test files containing tests with a certain decorator
    `@pytest.mark.XYZ`.
    """
    hdbg.dassert_isinstance(file_names, list)
    # E.g.,
    #   @pytest.mark.slow(...)
    #   @pytest.mark.qa
    string = f"@pytest.mark.{decorator_name}"
    regex = rf"^\s*{re.escape(string)}\s*[\(]?"
    _LOG.debug("regex='%s'", regex)
    res: List[str] = []
    # Scan all the files.
    for file_name in file_names:
        _LOG.debug("file_name=%s", file_name)
        txt = hio.from_file(file_name)
        # Search for the class in each file.
        for i, line in enumerate(txt.split("\n")):
            # _LOG.debug("file_name=%s i=%s: %s", file_name, i, line)
            # TODO(gp): We should skip ```, """, '''. We can add a function to
            # remove all the comments, although we need to keep track of the
            # line original numbers.
            m = re.match(regex, line)
            if m:
                _LOG.debug("  -> found: %d:%s", i, line)
                res.append(file_name)
    #
    res = sorted(list(set(res)))
    return res


@task
def find_test_decorator(ctx, decorator_name="", dir_name="."):  # type: ignore
    """
    Report test files containing `class_name` in pytest format.

    :param decorator_name: the decorator to search
    :param dir_name: the dir from which to search
    """
    hlitauti.report_task()
    _ = ctx
    hdbg.dassert_ne(decorator_name, "", "You need to specify a decorator name")
    file_names = _find_test_files(dir_name)
    res = _find_test_decorator(decorator_name, file_names)
    res = " ".join(res)
    print(res)


# #############################################################################
# Find / replace `check_string`.
# #############################################################################


@task
def find_check_string_output(  # type: ignore
    ctx, class_name, method_name, as_python=True, fuzzy_match=False, pbcopy=True
):
    """
    Find output of `check_string()` in the test running
    class_name::method_name.

    E.g., for `TestResultBundle::test_from_config1` return the content of the file
        `./core/dataflow/test/TestResultBundle.test_from_config1/output/test.txt`

    :param as_python: if True return the snippet of Python code that replaces the
        `check_string()` with a `assert_equal`
    :param fuzzy_match: if True return Python code with `fuzzy_match=True`
    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    hlitauti.report_task()
    _ = ctx
    hdbg.dassert_ne(class_name, "", "You need to specify a class name")
    hdbg.dassert_ne(method_name, "", "You need to specify a method name")
    # Look for the directory named `class_name.method_name`.
    cmd = f"find . -name '{class_name}.{method_name}' -type d"
    # > find . -name "TestResultBundle.test_from_config1" -type d
    # ./core/dataflow/test/TestResultBundle.test_from_config1
    _, txt = hsystem.system_to_string(cmd, abort_on_error=False)
    file_names = txt.split("\n")
    if not txt:
        hdbg.dfatal(f"Can't find the requested dir with '{cmd}'")
    if len(file_names) > 1:
        hdbg.dfatal(f"Found more than one dir with '{cmd}':\n{txt}")
    dir_name = file_names[0]
    # Find the only file underneath that dir.
    hdbg.dassert_dir_exists(dir_name)
    cmd = f"find {dir_name} -name 'test.txt' -type f"
    _, file_name = hsystem.system_to_one_line(cmd)
    hdbg.dassert_file_exists(file_name)
    # Read the content of the file.
    _LOG.info("Found file '%s' for %s::%s", file_name, class_name, method_name)
    txt = hio.from_file(file_name)
    if as_python:
        # Package the code snippet.
        if not fuzzy_match:
            # Align the output at the same level as 'exp = r...'.
            num_spaces = 8
            txt = hprint.indent(txt, num_spaces=num_spaces)
        output = f"""
        act =
        exp = r\"\"\"
{txt}
        \"\"\".lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match={fuzzy_match})
        """
    else:
        output = txt
    # Print or copy to clipboard.
    hlitauti._to_pbcopy(output, pbcopy)
    return output


# #############################################################################
# Find module dependencies.
# #############################################################################


standard_libs = [
    "abc",
    "argparse",
    "datetime",
    "importlib",
    "logging",
    "os",
    "pandas",
    "pytest",
    "re",
    "unittest",
]


@task
def find_dependency(  # type: ignore
    ctx,
    module_name,
    mode="print_deps",
    only_module="",
    ignore_standard_libs=True,
    ignore_helpers=True,
    remove_dups=True,
):
    """
    E.g., ```

    # Find all the dependency of a module from itself
    > i find_dependency --module-name "amp.dataflow.model" --mode "find_lev2_deps" --ignore-helpers --only-module dataflow
    amp/dataflow/model/stats_computer.py:16 dataflow.core
    amp/dataflow/model/model_plotter.py:4   dataflow.model
    ```

    :param module_name: the module path to analyze (e.g., `amp.dataflow.model`)
    :param mode:
        - `print_deps`: print the result of grepping for imports
        - `find_deps`: find all the dependencies
        - `find_lev1_deps`, `find_lev2_deps`: find all the dependencies
    :param only_module: keep only imports containing a certain module (e.g., `dataflow`)
    :param ignore_standard_libs: ignore the Python standard libs (e.g., `os`, `...`)
    :param ignore_helpers: ignore the `helper` lib
    :param remove_dups: remove the duplicated imports
    """
    _ = ctx
    # (cd amp/dataflow/model/; jackpy "import ") | grep -v notebooks | grep -v test | grep -v __init__ | grep "import dataflow"
    src_dir = module_name.replace(".", "/")
    hdbg.dassert_dir_exists(src_dir)
    # Find all the imports.
    cmd = f'find {src_dir} -name "*.py" | xargs grep -n -r "^import "'
    _, txt = hsystem.system_to_string(cmd)
    #
    if mode == "print_deps":
        print(txt)
        return
    # Parse the output.
    _LOG.debug("\n" + hprint.frame("Parse"))
    lines = txt.split("\n")
    lines_out = []
    for line in lines:
        # ./forecast_evaluator_from_prices.py:16:import helpers.hpandas as hpandas
        # import helpers.hunit_test as hunitest  # pylint: disable=no-name-in-module'
        data = line.split(":")
        hdbg.dassert_lte(3, len(data), "Invalid line='%s'", line)
        file, line_num, import_code = data[:3]
        _LOG.debug(hprint.to_str("file line_num import_code"))
        lines_out.append((file, line_num, import_code))
    lines = lines_out
    _LOG.debug("Found %d imports", len(lines))
    # Remove irrelevant files and imports.
    _LOG.debug("\n" + hprint.frame("Remove irrelevant entries"))
    lines_out = []
    for line in lines:
        file, line_num, import_code = line
        _LOG.debug("# " + hprint.to_str("file line_num import_code"))
        if "__init__.py" in file:
            _LOG.debug("Remove because init")
            continue
        if "/test/" in file:
            _LOG.debug("Remove because test")
            continue
        if "notebooks/" in file:
            _LOG.debug("Remove because notebook")
            continue
        if "from typing import" in import_code:
            _LOG.debug("Remove because typing")
            continue
        lines_out.append(line)
    lines = lines_out
    _LOG.debug("After removal %d imports", len(lines))
    # Process.
    _LOG.debug("\n" + hprint.frame("Process entries"))
    lines_out = []
    for line in lines:
        # ./forecast_evaluator_from_prices.py:16:import helpers.hpandas as hpandas
        file, line_num, import_code = line
        _LOG.debug("# " + hprint.to_str("file line_num import_code"))
        # Parse import code.
        m = re.match("^import\s+(\S+)(\s+as)?", import_code)
        hdbg.dassert(m, "Can't parse line='%s'", import_code)
        #
        import_name = m.group(1)
        _LOG.debug("import_name='%s'", import_name)
        lev1_import = import_name.split(".")[0]
        if ignore_standard_libs:
            if lev1_import in standard_libs:
                _LOG.debug("Ignoring standard lib '%s'", lev1_import)
                continue
        if ignore_helpers:
            if lev1_import.startswith("helpers"):
                _LOG.debug("Ignoring helpers '%s'", lev1_import)
                continue
        if only_module:
            if only_module not in import_name:
                _LOG.debug(
                    "Ignoring '%s' since it doesn't contain %s",
                    import_name,
                    only_module,
                )
                continue
        #
        if mode == "find_deps":
            dep = import_name
        elif mode == "find_lev1_deps":
            deps = import_name.split(".")
            if len(deps) > 1:
                dep = deps[0]
            else:
                dep = import_name
        elif mode == "find_lev2_deps":
            deps = import_name.split(".")
            if len(deps) > 1:
                dep = ".".join(deps[:2])
            else:
                dep = import_name
        else:
            raise ValueError(f"Invalid mode='{mode}'")
        lines_out.append((file, line_num, dep))
    lines = lines_out
    # Remove repeated tuples.
    if remove_dups:
        _LOG.debug("\n" + hprint.frame("Remove repeated tuples"))
        import_names = set()
        lines_out = []
        for line in lines:
            if line[2] in import_names:
                continue
            lines_out.append(line)
            import_names.add(line[2])
        lines = lines_out
    else:
        _LOG.warning("Remove dups skipped")
    # Sort.
    _LOG.debug("\n" + hprint.frame("Sort tuples"))
    lines = sorted(lines, key=lambda x: x[2])
    # Print and save.
    print(hprint.frame("Results"))
    _LOG.debug("\n" + hprint.frame("Print"))
    txt = "\n".join([":".join(line) for line in lines])
    file_name = "cfile"
    hio.to_file(file_name, txt)
    _LOG.info("%s saved", file_name)
    #
    txt = "\n".join(["%s:%s\t\t\t%s" % line for line in lines])
    print(txt)
