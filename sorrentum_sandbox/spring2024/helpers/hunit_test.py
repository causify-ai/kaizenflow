"""
Import as:

import helpers.hunit_test as hunitest
"""

import abc
import collections
import datetime
import inspect
import logging
import os
import pprint
import random
import re
import sys
import traceback
import unittest
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.htimer as htimer
import helpers.hwall_clock_time as hwacltim

# We use strings as type hints (e.g., 'pd.DataFrame') since we are not sure
# we have the corresponding libraries installed.


# Minimize dependencies from installed packages.

# TODO(gp): Use `hprint.color_highlight`.
_WARNING = "\033[33mWARNING\033[0m"

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError as e:
    print(_WARNING + ": " + str(e))
    _HAS_NUMPY = False
try:
    import pandas as pd

    _HAS_PANDAS = True
except ImportError as e:
    print(_WARNING + ": " + str(e))
    _HAS_PANDAS = False

try:
    import matplotlib.pyplot as plt

    _HAS_MATPLOTLIB = True
except ImportError as e:
    print(_WARNING + ": " + str(e))
    _HAS_MATPLOTLIB = False


_LOG = logging.getLogger(__name__)
# Mute this module unless we want to debug it.
_LOG.setLevel(logging.INFO)

# #############################################################################

# Global setter / getter for updating test.

# This controls whether the output of a test is updated or not.
# Set by `conftest.py`.
_UPDATE_TESTS = False


# TODO(gp): -> ..._update_outcomes.
def set_update_tests(val: bool) -> None:
    global _UPDATE_TESTS
    _UPDATE_TESTS = val


def get_update_tests() -> bool:
    return _UPDATE_TESTS


# #############################################################################

# Global setter / getter for incremental mode.

# This is useful when a long test wants to reuse some data already generated.
# Set by conftest.py.
_INCREMENTAL_TESTS = False


def set_incremental_tests(val: bool) -> None:
    global _INCREMENTAL_TESTS
    _INCREMENTAL_TESTS = val


def get_incremental_tests() -> bool:
    return _INCREMENTAL_TESTS


# #############################################################################

_CONFTEST_IN_PYTEST = False


# TODO(gp): Use https://stackoverflow.com/questions/25188119
# TODO(gp): -> is_in_unit_test()
def in_unit_test_mode() -> bool:
    """
    Return True if we are inside a pytest run.

    This is set by `conftest.py`.
    """
    return _CONFTEST_IN_PYTEST


# #############################################################################


# Set by `conftest.py`.
_GLOBAL_CAPSYS = None


def pytest_print(txt: str) -> None:
    """
    Print bypassing `pytest` output capture.
    """
    with _GLOBAL_CAPSYS.disabled():  # type: ignore
        sys.stdout.write(txt)


def pytest_warning(txt: str, prefix: str = "") -> None:
    """
    Print a warning bypassing `pytest` output capture.

    :param prefix: prepend the message with a string
    """
    txt_tmp = ""
    if prefix:
        txt_tmp += prefix
    txt_tmp += hprint.color_highlight("WARNING", "yellow") + f": {txt}"
    pytest_print(txt_tmp)


# #############################################################################
# Generation and conversion functions.
# #############################################################################


# TODO(gp): Is this dataflow Info? If so it should go somewhere else.
def convert_info_to_string(info: Mapping) -> str:
    """
    Convert info to string for verifying test results.

    Info often contains `pd.Series`, so pandas context is provided to print all rows
    and all contents.

    :param info: info to convert to string
    :return: string representation of info
    """
    output = []
    # Provide context for full representation of `pd.Series` in info.
    with pd.option_context(
        "display.max_colwidth",
        int(1e6),
        "display.max_columns",
        None,
        "display.max_rows",
        None,
    ):
        output.append(hprint.frame("info"))
        output.append(pprint.pformat(info))
        output_str = "\n".join(output)
    return output_str


# TODO(gp): This seems the python3.9 version of `to_str`. Remove if possible.
def to_string(var: str) -> str:
    return """f"%s={%s}""" % (var, var)


# TODO(gp): @all move to hpandas
def compare_df(df1: "pd.DataFrame", df2: "pd.DataFrame") -> None:
    """
    Compare two dfs including their metadata.
    """
    if not df1.equals(df2):
        print(df1.compare(df2))
        raise ValueError("Dfs are different")

    def _compute_df_signature(df: "pd.DataFrame") -> str:
        txt = []
        txt.append(f"df1=\n{str(df)}")
        txt.append(f"df1.dtypes=\n{str(df.dtypes)}")
        if hasattr(df.index, "freq"):
            txt.append(f"df1.index.freq=\n{str(df.index.freq)}")
        return "\n".join(txt)

    full_test_name = "dummy"
    test_dir = "."
    assert_equal(
        _compute_df_signature(df1),
        _compute_df_signature(df2),
        full_test_name,
        test_dir,
    )


# #############################################################################


def create_test_dir(
    dir_name: str, incremental: bool, file_dict: Dict[str, str]
) -> None:
    """
    Create a directory `dir_name` with the files from `file_dict`.

    `file_dict` is interpreted as pair of files relative to `dir_name`
    and content.
    """
    hdbg.dassert_no_duplicates(file_dict.keys())
    hio.create_dir(dir_name, incremental=incremental)
    for file_name in file_dict:
        dst_file_name = os.path.join(dir_name, file_name)
        _LOG.debug("file_name=%s -> %s", file_name, dst_file_name)
        hio.create_enclosing_dir(dst_file_name, incremental=incremental)
        file_content = file_dict[file_name]
        hio.to_file(dst_file_name, file_content)


# TODO(gp): Make remove_dir_name=True default.
def get_dir_signature(
    dir_name: str,
    include_file_content: bool,
    *,
    remove_dir_name: bool = False,
    num_lines: Optional[int] = None,
) -> str:
    """
    Compute a string with the content of the files in `dir_name`.

    :param include_file_content: include the content of the files, besides the
        name of files and directories
    :param remove_dir_name: use paths relative to `dir_name`
    :param num_lines: number of lines to include for each file

    The output looks like:
    ```
    # Dir structure
    $GIT_ROOT/.../tmp.scratch
    $GIT_ROOT/.../tmp.scratch/dummy_value_1=1
    $GIT_ROOT/.../tmp.scratch/dummy_value_1=1/dummy_value_2=A
    $GIT_ROOT/.../tmp.scratch/dummy_value_1=1/dummy_value_2=A/data.parquet
    ...

    # File signatures
    len(file_names)=3
    file_names=$GIT_ROOT/.../tmp.scratch/dummy_value_1=1/dummy_value_2=A/data.parquet,
    $GIT_ROOT/.../tmp.scratch/dummy_value_1=2/dummy_value_2=B/data.parquet, ...
    # $GIT_ROOT/.../tmp.scratch/dummy_value_1=1/dummy_value_2=A/data.parquet
    num_lines=13
    '''
    original shape=(1, 1)
    Head:
    {
        "0":{
            "dummy_value_3":0
        }
    }
    Tail:
    {
        "0":{
            "dummy_value_3":0
        }
    }
    '''
    # $GIT_ROOT/.../tmp.scratch/dummy_value_1=2/dummy_value_2=B/data.parquet
    ```
    """

    def _remove_dir_name(file_name: str) -> str:
        if remove_dir_name:
            res = os.path.relpath(file_name, dir_name)
        else:
            res = file_name
        return res

    txt: List[str] = []
    # Find all the files under `dir_name`.
    _LOG.debug("dir_name=%s", dir_name)
    hdbg.dassert_path_exists(dir_name)
    cmd = f'find {dir_name} -name "*"'
    remove_files_non_present = False
    dir_name_tmp = None
    file_names = hsystem.system_to_files(
        cmd, dir_name_tmp, remove_files_non_present
    )
    file_names = sorted(file_names)
    # Save the directory / file structure.
    txt.append("# Dir structure")
    txt.append("\n".join(map(_remove_dir_name, file_names)))
    #
    if include_file_content:
        txt.append("# File signatures")
        # Remove the directories.
        file_names = hsystem.remove_dirs(file_names)
        # Scan the files.
        txt.append(f"len(file_names)={len(file_names)}")
        txt.append(f"file_names={', '.join(map(_remove_dir_name, file_names))}")
        for file_name in file_names:
            _LOG.debug("file_name=%s", file_name)
            txt.append("# " + _remove_dir_name(file_name))
            # Read file.
            txt_tmp = hio.from_file(file_name)
            # This seems unstable on different systems.
            # txt.append("num_chars=%s" % len(txt_tmp))
            txt_tmp = txt_tmp.split("\n")
            # Filter lines, if needed.
            txt.append(f"num_lines={len(txt_tmp)}")
            if num_lines is not None:
                hdbg.dassert_lte(1, num_lines)
                txt_tmp = txt_tmp[:num_lines]
            txt.append("'''\n" + "\n".join(txt_tmp) + "\n'''")
    else:
        hdbg.dassert_is(num_lines, None)
    # Concat everything in a single string.
    txt = "\n".join(txt)
    return txt


# TODO(gp): @all Use the copy in helpers/print.py.
def filter_text(regex: str, txt: str) -> str:
    """
    Remove lines in `txt` that match the regex `regex`.
    """
    _LOG.debug("Filtering with '%s'", regex)
    if regex is None:
        return txt
    txt_out = []
    txt_as_arr = txt.split("\n")
    for line in txt_as_arr:
        if re.search(regex, line):
            _LOG.debug("Skipping line='%s'", line)
            continue
        txt_out.append(line)
    # We can only remove lines.
    hdbg.dassert_lte(
        len(txt_out),
        len(txt_as_arr),
        "txt_out=\n'''%s'''\ntxt=\n'''%s'''",
        "\n".join(txt_out),
        "\n".join(txt_as_arr),
    )
    txt = "\n".join(txt_out)
    return txt


# #############################################################################
# Outcome purification functions.
# #############################################################################


# TODO(gp): -> private functions?


def purify_from_environment(txt: str) -> str:
    """
    Replace environment variables with placeholders.

    The performed transformations are:
    1. Replace the Git path with `$GIT_ROOT`
    2. Replace the path of current working dir with `$PWD`
    3. Replace the current user name with `$USER_NAME`
    """
    # 1) Remove references to Git modules starting from the innermost one.
    # Make sure that the path is not followed by a word character.
    # E.g., `/app/test.txt` is the correct path, while `/application.py`
    # is not a root path even though `/app` is the part of the text.
    dir_pattern = r"(?![\w])"
    for super_module in [False, True]:
        # Replace the git path with `$GIT_ROOT`.
        super_module_path = hgit.get_client_root(super_module=super_module)
        if super_module_path != "/":
            pattern = re.compile(f"{super_module_path}{dir_pattern}")
            txt = pattern.sub("$GIT_ROOT", txt)
        else:
            # If the git path is `/` then we don't need to do anything.
            pass
    # 2) Replace the path of current working dir with `$PWD`
    pwd = os.getcwd()
    pattern = re.compile(f"{pwd}{dir_pattern}")
    txt = pattern.sub("$PWD", txt)
    # 3) Replace the current user name with `$USER_NAME`.
    user_name = hsystem.get_user_name()
    # Set a regex pattern that finds a user name surrounded by dot, dash or space.
    # E.g., `IMAGE=$CK_ECR_BASE_PATH/amp_test:local-$USER_NAME-1.0.0`,
    # `--name $USER_NAME.amp_test.app.app`, `run --rm -l user=$USER_NAME`.
    pattern = rf"([\s\n\-\.\=]|^)+{user_name}+([.\s/-]|$)"
    # Use `\1` and `\2` to preserve specific characters around `$USER_NAME`.
    target = r"\1$USER_NAME\2"
    txt = re.sub(pattern, target, txt)
    _LOG.debug("After %s: txt='\n%s'", hintros.get_function_name(), txt)
    return txt


def purify_amp_references(txt: str) -> str:
    """
    Remove references to amp.
    """
    # E.g., `amp/helpers/test/...`
    txt = re.sub(r"^\s*amp\/", "", txt, flags=re.MULTILINE)
    # E.g., `<amp.helpers.test.test_dbg._Man object at 0x`
    # in GH actions the packages end up being called `app.` for some reason
    # (see AmpTask1627), so we clean up also that.
    txt = re.sub(r"<a[mp]p\.", "<", txt, flags=re.MULTILINE)
    # E.g., class 'amp.
    txt = re.sub(r"class 'a[mp]p\.", "class '", txt, flags=re.MULTILINE)
    # E.g., from helpers/test/test_playback.py::TestPlaybackInputOutput1
    # ```
    # Test created for amp.helpers.test.test_playback.get_result_ae
    # ```
    txt = re.sub(
        r"# Test created for a[mp]p\.helpers",
        "# Test created for helpers",
        txt,
        flags=re.MULTILINE,
    )
    # E.g., `['amp/helpers/test/...`
    txt = re.sub(r"'amp\/", "'", txt, flags=re.MULTILINE)
    txt = re.sub(r"\/amp\/", "/", txt, flags=re.MULTILINE)
    # E.g., `vimdiff helpers/test/...`
    txt = re.sub(r"\s+amp\/", " ", txt, flags=re.MULTILINE)
    txt = re.sub(r"\/amp:", ":", txt, flags=re.MULTILINE)
    txt = re.sub(r"^\./", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"amp\.helpers", "helpers", txt, flags=re.MULTILINE)
    _LOG.debug("After %s: txt='\n%s'", hintros.get_function_name(), txt)
    return txt


def purify_app_references(txt: str) -> str:
    """
    Remove references to `/app`.
    """
    txt = re.sub(r"/app/", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"app\.helpers", "helpers", txt, flags=re.MULTILINE)
    txt = re.sub(r"app\.amp\.helpers", "amp.helpers", txt, flags=re.MULTILINE)
    _LOG.debug("After %s: txt='\n%s'", hintros.get_function_name(), txt)
    return txt


def purify_file_names(file_names: List[str]) -> List[str]:
    """
    Express file names in terms of the root of git repo, removing reference to
    `amp`.
    """
    git_root = hgit.get_client_root(super_module=True)
    file_names = [os.path.relpath(f, git_root) for f in file_names]
    # TODO(gp): Add also `purify_app_references`.
    file_names = list(map(purify_amp_references, file_names))
    return file_names


def purify_from_env_vars(txt: str) -> str:
    # TODO(gp): Diff between amp and cmamp.
    for env_var in [
        "AM_ECR_BASE_PATH",
        "AM_AWS_S3_BUCKET",
        "AM_TELEGRAM_TOKEN",
        "CK_AWS_S3_BUCKET",
        "CK_ECR_BASE_PATH",
    ]:
        if env_var in os.environ:
            val = os.environ[env_var]
            if val == "":
                _LOG.debug("Env var '%s' is empty", env_var)
            else:
                txt = txt.replace(val, f"${env_var}")
    _LOG.debug("After %s: txt='\n%s'", hintros.get_function_name(), txt)
    return txt


def purify_object_representation(txt: str) -> str:
    """
    Remove references like `at 0x7f43493442e0`.
    """
    txt = re.sub(r"at 0x[0-9A-Fa-f]+", "at 0x", txt, flags=re.MULTILINE)
    txt = re.sub(r" id='\d+'>", " id='xxx'>", txt, flags=re.MULTILINE)
    txt = re.sub(r"port=\d+", "port=xxx", txt, flags=re.MULTILINE)
    txt = re.sub(r"host=\S+ ", "host=xxx ", txt, flags=re.MULTILINE)
    # wall_clock_time=Timestamp('2022-08-04 09:25:04.830746-0400'
    txt = re.sub(
        r"wall_clock_time=Timestamp\('.*?',",
        r"wall_clock_time=Timestamp('xxx',",
        txt,
        flags=re.MULTILINE,
    )
    _LOG.debug("After %s: txt='\n%s'", hintros.get_function_name(), txt)
    return txt


def purify_today_date(txt: str) -> str:
    """
    Remove today's date like `20220810`.
    """
    today_date = datetime.date.today()
    today_date_as_str = today_date.strftime("%Y%m%d")
    # Replace predict.3.compress_tails.df_out.20220627_094500.YYYYMMDD_171106.csv.gz.
    txt = re.sub(
        today_date_as_str + "_\d{6}", "YYYYMMDD_HHMMSS", txt, flags=re.MULTILINE
    )
    txt = re.sub(today_date_as_str, "YYYYMMDD", txt, flags=re.MULTILINE)
    return txt


# TODO(gp): -> purify_trailing_white_spaces
def purify_white_spaces(txt: str) -> str:
    """
    Remove trailing white spaces.
    """
    txt_new = []
    for line in txt.split("\n"):
        line = line.rstrip()
        txt_new.append(line)
    txt = "\n".join(txt_new)
    return txt


# TODO(Grisha): move to `purify_txt_from_client`.
def purify_line_number(txt: str) -> str:
    """
    Replace line number with `$LINE_NUMBER`.
    """
    txt = re.sub(r"\.py::\d+", ".py::$LINE_NUMBER", txt, flags=re.MULTILINE)
    return txt


def purify_parquet_file_names(txt: str) -> str:
    """
    Replace UUIDs file names to `data.parquet` in the goldens.

    Some tests are expecting in the goldens the Parquet files with the names
    `data.parquet`.
    Example:
        Initial text:
        ```
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=1/ea5e3faed73941a2901a2128abeac4ca-0.parquet
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=2/f7a39fefb69b40e0987cec39569df8ed-0.parquet
        ```
        Purified text:
        ```
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=1/data.parquet
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=2/data.parquet
        ```
    """
    pattern = r"""
        [0-9a-f]{32}-[0-9].* # GUID pattern.
        (?=\.parquet) # positive lookahead assertion that matches a position followed by ".parquet" without consuming it.
    """
    # TODO(Vlad): Need to change the replacement to `$FILE_NAME` as in the
    # `purify_from_environment()` function. For now, some tests are expecting
    # `data.parquet` files.
    replacement = "data"
    # flags=re.VERBOSE allows us to use whitespace and comments in the pattern.
    txt = re.sub(pattern, replacement, txt, flags=re.VERBOSE)
    return txt


def purify_txt_from_client(txt: str) -> str:
    """
    Remove from a string all the information of a specific run.
    """
    txt = purify_from_environment(txt)
    txt = purify_app_references(txt)
    txt = purify_amp_references(txt)
    txt = purify_from_env_vars(txt)
    txt = purify_object_representation(txt)
    txt = purify_today_date(txt)
    txt = purify_white_spaces(txt)
    txt = purify_parquet_file_names(txt)
    return txt


# #############################################################################


def diff_files(
    file_name1: str,
    file_name2: str,
    tag: Optional[str] = None,
    abort_on_exit: bool = True,
    dst_dir: str = ".",
    error_msg: str = "",
) -> None:
    """
    Compare the passed filenames and create script to compare them with
    vimdiff.

    :param tag: add a banner the tag
    :param abort_on_exit: whether to assert or not
    :param dst_dir: dir where to save the comparing script
    """
    _LOG.debug(hprint.to_str("tag abort_on_exit dst_dir"))
    file_name1 = os.path.relpath(file_name1, os.getcwd())
    file_name2 = os.path.relpath(file_name2, os.getcwd())
    msg = []
    # Add tag.
    if tag is not None:
        msg.append("\n" + hprint.frame(tag, char1="-"))
    # Diff to screen.
    _, res = hsystem.system_to_string(
        f"echo; sdiff --expand-tabs -l -w 150 {file_name1} {file_name2}",
        abort_on_error=False,
        log_level=logging.DEBUG,
    )
    msg.append(res)
    # Save a script to diff.
    diff_script = os.path.join(dst_dir, "tmp_diff.sh")
    vimdiff_cmd = f"""#!/bin/bash
if [[ $1 == "wrap" ]]; then
    cmd='vimdiff -c "windo set wrap"'
else
    cmd='vimdiff'
fi;
cmd="$cmd {file_name1} {file_name2}"
eval $cmd
"""
    # TODO(gp): Use hio.create_executable_script().
    hio.to_file(diff_script, vimdiff_cmd)
    cmd = "chmod +x " + diff_script
    hsystem.system(cmd)
    # Report how to diff.
    msg.append("Diff with:")
    msg.append("> " + diff_script)
    msg_as_str = "\n".join(msg)
    # Append also error_msg to the current message.
    if error_msg:
        msg_as_str += "\n" + error_msg
    # Add also the stack trace to the logging error.
    if False:
        log_msg_as_str = (
            msg_as_str
            + "\n"
            + hprint.frame("Traceback", char1="-")
            + "\n"
            + "".join(traceback.format_stack())
        )
        _LOG.error(log_msg_as_str)
    # Assert.
    if abort_on_exit:
        raise RuntimeError(msg_as_str)


def diff_strings(
    string1: str,
    string2: str,
    tag: Optional[str] = None,
    abort_on_exit: bool = True,
    dst_dir: str = ".",
) -> None:
    """
    Compare two strings using the diff_files() flow by creating a script to
    compare with vimdiff.

    :param dst_dir: where to save the intermediatary files
    """
    _LOG.debug(hprint.to_str("tag abort_on_exit dst_dir"))
    # Save the actual and expected strings to files.
    file_name1 = f"{dst_dir}/tmp.string1.txt"
    hio.to_file(file_name1, string1)
    #
    file_name2 = f"{dst_dir}/tmp.string2.txt"
    hio.to_file(file_name2, string2)
    # Compare with diff_files.
    if tag is None:
        tag = "string1 vs string2"
    diff_files(
        file_name1,
        file_name2,
        tag=tag,
        abort_on_exit=abort_on_exit,
        dst_dir=dst_dir,
    )


def diff_df_monotonic(
    df: "pd.DataFrame",
    tag: Optional[str] = None,
    abort_on_exit: bool = True,
    dst_dir: str = ".",
) -> None:
    """
    Check for a dataframe to be monotonic using the vimdiff flow from
    diff_files().
    """
    _LOG.debug(hprint.to_str("abort_on_exit dst_dir"))
    if not df.index.is_monotonic_increasing:
        df2 = df.copy()
        df2.sort_index(inplace=True)
        diff_strings(
            df.to_csv(),
            df2.to_csv(),
            tag=tag,
            abort_on_exit=abort_on_exit,
            dst_dir=dst_dir,
        )


# #############################################################################


# pylint: disable=protected-access
def get_pd_default_values() -> "pd._config.config.DictWrapper":
    import copy

    vals = copy.deepcopy(pd.options)
    return vals


def set_pd_default_values() -> None:
    # 'display':
    default_pd_values = {
        "chop_threshold": None,
        "colheader_justify": "right",
        "date_dayfirst": False,
        "date_yearfirst": False,
        "encoding": "UTF-8",
        "expand_frame_repr": True,
        "float_format": None,
        "html": {"border": 1, "table_schema": False, "use_mathjax": True},
        "large_repr": "truncate",
        "latex": {
            "escape": True,
            "longtable": False,
            "multicolumn": True,
            "multicolumn_format": "l",
            "multirow": False,
            "repr": False,
        },
        "max_categories": 8,
        "max_columns": 20,
        "max_colwidth": 50,
        "max_info_columns": 100,
        "max_info_rows": 1690785,
        "max_rows": 60,
        "max_seq_items": 100,
        "memory_usage": True,
        "min_rows": 10,
        "multi_sparse": True,
        "notebook_repr_html": True,
        "pprint_nest_depth": 3,
        "precision": 6,
        "show_dimensions": "truncate",
        "unicode": {"ambiguous_as_wide": False, "east_asian_width": False},
        "width": 80,
    }
    section = "display"
    for key, new_val in default_pd_values.items():
        if isinstance(new_val, dict):
            continue
        full_key = f"{section}.{key}"
        old_val = pd.get_option(full_key)
        if old_val != new_val:
            _LOG.debug(
                "-> Assigning a different value: full_key=%s, "
                "old_val=%s, new_val=%s",
                full_key,
                old_val,
                new_val,
            )
        pd.set_option(full_key, new_val)


# #############################################################################


def _remove_spaces(txt: str) -> str:
    """
    Remove leading / trailing spaces and empty lines.

    This is used to implement fuzzy matching.
    """
    txt = txt.replace("\\n", "\n").replace("\\t", "\t")
    # Convert multiple empty spaces (but not newlines) into a single one.
    txt = re.sub(r"[^\S\n]+", " ", txt)
    # Remove insignificant crap.
    lines = []
    for line in txt.split("\n"):
        # Remove leading and trailing spaces.
        line = re.sub(r"^\s+", "", line)
        line = re.sub(r"\s+$", "", line)
        # Skip empty lines.
        if line != "":
            lines.append(line)
    txt = "\n".join(lines)
    return txt


def _remove_banner_lines(txt: str) -> str:
    """
    Remove lines of separating characters long at least 20 characters.
    """
    txt_tmp: List[str] = []
    for line in txt.split("\n"):
        if re.match(r"^\s*[\#\-><=]{20,}\s*$", line):
            continue
        txt_tmp.append(line)
    txt = "\n".join(txt_tmp)
    return txt


def _fuzzy_clean(txt: str) -> str:
    """
    Remove irrelevant artifacts to make string comparison less strict.
    """
    hdbg.dassert_isinstance(txt, str)
    # Ignore spaces.
    txt = _remove_spaces(txt)
    # Ignore separation lines.
    txt = _remove_banner_lines(txt)
    return txt


def _ignore_line_breaks(txt: str) -> str:
    # Ignore line breaks.
    txt = txt.replace("\n", " ")
    return txt


def _sort_lines(txt: str) -> str:
    """
    Sort the lines in alphabetical order.

    This is used when we want to perform a comparison of equality but
    without order. Of course there are false negatives, since the
    relative order of lines might matter.
    """
    lines = txt.split("\n")
    lines.sort()
    lines = "\n".join(lines)
    return lines


def _save_diff(
    actual: str,
    expected: str,
    tag: str,
    test_dir: str,
) -> None:
    if tag != "":
        tag += "."
    # Save expected strings to dir.
    for dst_dir in (".", test_dir):
        act_file_name = f"{dst_dir}/tmp.{tag}actual.txt"
        hio.to_file(act_file_name, actual)
        exp_file_name = f"{dst_dir}/tmp.{tag}expected.txt"
        hio.to_file(exp_file_name, expected)


def assert_equal(
    actual: str,
    expected: str,
    full_test_name: str,
    test_dir: str,
    *,
    check_string: bool = False,
    dedent: bool = False,
    purify_text: bool = False,
    purify_expected_text: bool = False,
    fuzzy_match: bool = False,
    ignore_line_breaks: bool = False,
    sort: bool = False,
    abort_on_error: bool = True,
    dst_dir: str = ".",
    error_msg: str = "",
) -> bool:
    """
    See interface in `TestCase.assert_equal()`.

    :param full_test_name: e.g., `TestRunNotebook1.test2`
    :param check_string: if it was invoked by `check_string()` or directly
    """
    _LOG.debug(
        hprint.to_str(
            "full_test_name test_dir "
            "dedent purify_text fuzzy_match ignore_line_breaks "
            "abort_on_error dst_dir"
        )
    )
    # Store a mapping tag after each transformation (e.g., original, sort, ...) to
    # (actual, expected).
    values: Dict[str, str] = collections.OrderedDict()

    def _append(tag: str, actual: str, expected: str) -> None:
        _LOG.debug("tag=%s\n  act='\n%s'\n  exp='\n%s'", actual, expected)
        hdbg.dassert_not_in(tag, values)
        values[tag] = (actual, expected)

    #
    _LOG.debug("Before any transformation:")
    tag = "original"
    _append(tag, actual, expected)
    # 1) Remove white spaces.
    actual = purify_white_spaces(actual)
    expected = purify_white_spaces(expected)
    tag = "purify_white_spaces"
    _append(tag, actual, expected)
    # Dedent only expected since we often align it to make it look more readable
    # in the Python code, if needed.
    if dedent:
        expected = hprint.dedent(expected)
        tag = "dedent"
        _append(tag, actual, expected)
    # Purify text, if needed.
    if purify_text:
        actual = purify_txt_from_client(actual)
        if purify_expected_text:
            expected = purify_txt_from_client(expected)
        tag = "purify"
        _append(tag, actual, expected)
    # Ensure that there is a single `\n` at the end of the strings.
    actual = actual.rstrip("\n") + "\n"
    expected = expected.rstrip("\n") + "\n"
    # Sort the lines.
    if sort:
        actual = _sort_lines(actual)
        expected = _sort_lines(expected)
        tag = "sort"
        _append(tag, actual, expected)
    # Fuzzy match, if needed.
    if fuzzy_match:
        actual = _fuzzy_clean(actual)
        expected = _fuzzy_clean(expected)
        tag = "fuzzy_clean"
        _append(tag, actual, expected)
    # Ignore line breaks, if needed.
    if ignore_line_breaks:
        actual = _ignore_line_breaks(actual)
        expected = _ignore_line_breaks(expected)
        tag = "ignore_line_breaks"
        _append(tag, actual, expected)
    # Check.
    tag = "final"
    _append(tag, actual, expected)
    #
    is_equal = expected == actual
    _LOG.debug(hprint.to_str("is_equal"))
    if is_equal:
        return is_equal
    _LOG.error(
        "%s",
        "\n"
        + hprint.frame(
            f"Test '{full_test_name}' failed", char1="=", num_chars=80
        ),
    )
    if not check_string:
        # If this is a `self.assert_equal()` and not a `self.check_string()`,
        # then print the correct output, like:
        #   exp = r'"""
        #   2021-02-17 09:30:00-05:00
        #   2021-02-17 10:00:00-05:00
        #   2021-02-17 11:00:00-05:00
        #   """
        txt = []
        txt.append(hprint.frame(f"ACTUAL VARIABLE: {full_test_name}", char1="-"))
        # TODO(gp): Switch to expected or expected_result.
        exp_var = "exp = r"
        # We always return the variable exactly as this should be, even if we
        # could make it look better through indentation in case of fuzzy match.
        actual_orig = values["original"][0]
        if actual_orig.startswith('"'):
            sep = "'''"
        else:
            sep = '"""'
        exp_var += sep
        if fuzzy_match:
            # We can print in a more readable way since spaces don't matter.
            exp_var += "\n"
        exp_var += actual_orig
        if fuzzy_match:
            # We can print in a more readable way since spaces don't matter.
            exp_var += "\n"
        exp_var += sep
        # Save the expected variable to files.
        exp_var_file_name = f"{test_dir}/tmp.exp_var.txt"
        hio.to_file(exp_var_file_name, exp_var)
        #
        exp_var_file_name = "tmp.exp_var.txt"
        hio.to_file(exp_var_file_name, exp_var)
        _LOG.info("Saved exp_var in %s", exp_var_file_name)
        #
        txt.append(exp_var)
        txt = "\n".join(txt)
        error_msg += txt
    # Save all the values after the transformations.
    debug = False
    if debug:
        for idx, key in enumerate(values.keys()):
            actual_tmp, expected_tmp = values[key]
            tag = "%s.%s" % (idx, key)
            _save_diff(actual_tmp, expected_tmp, tag, test_dir)
    else:
        key = "final"
        actual_tmp, expected_tmp = values[key]
        _save_diff(actual_tmp, expected_tmp, key, test_dir)
    # Compare the last values.
    act_file_name = f"{test_dir}/tmp.final.actual.txt"
    exp_file_name = f"{test_dir}/tmp.final.expected.txt"
    if fuzzy_match:
        msg = "FUZZY ACTUAL vs FUZZY EXPECTED"
    else:
        msg = "ACTUAL vs EXPECTED"
    msg += f": {full_test_name}"
    diff_files(
        act_file_name,
        exp_file_name,
        tag=msg,
        abort_on_exit=abort_on_error,
        dst_dir=dst_dir,
        error_msg=error_msg,
    )
    return is_equal


# #############################################################################

# If a golden outcome is missing asserts (instead of updating golden and adding
# it to Git repo, corresponding to "update").
_ACTION_ON_MISSING_GOLDEN = "assert"


# TODO(gp): Remove all the calls to `dedent()` and use the `dedent` switch.
class TestCase(unittest.TestCase):
    """
    Add some functions to compare actual results to a golden outcome.
    """

    def setUp(self) -> None:
        """
        Execute before any test method.
        """
        # Set up the base class in case it does something, current
        # implementation does nothing, see
        # https://docs.python.org/3/library/unittest.html#unittest.TestCase.setUp.
        super().setUp()
        # Print banner to signal the start of a new test.
        func_name = f"{self.__class__.__name__}.{self._testMethodName}"
        _LOG.info("\n%s", hprint.frame(func_name))
        # Set the random seed.
        random_seed = 20000101
        _LOG.debug("Resetting random.seed to %s", random_seed)
        random.seed(random_seed)
        if _HAS_NUMPY:
            _LOG.debug("Resetting np.random.seed to %s", random_seed)
            np.random.seed(random_seed)
        # Disable matplotlib plotting by overwriting the `show` function.
        if _HAS_MATPLOTLIB:
            plt.show = lambda: 0
        # Name of the dir with artifacts for this test.
        self._scratch_dir: Optional[str] = None
        # The base directory is the one including the class under test.
        self._base_dir_name = os.path.dirname(inspect.getfile(self.__class__))
        _LOG.debug("base_dir_name=%s", self._base_dir_name)
        # Store whether a test needs to be updated or not.
        self._update_tests = get_update_tests()
        self._overriden_update_tests = False
        # Store whether the golden outcome of this test was updated.
        self._test_was_updated = False
        # Store whether the output files need to be added to hgit.
        self._git_add = True
        # Error message printed when comparing actual and expected outcome.
        self._error_msg = ""
        # Set the default pandas options (see AmpTask1140).
        if _HAS_PANDAS:
            self._old_pd_options = get_pd_default_values()
            set_pd_default_values()
        # Reset the timestamp of the current bar.
        hwacltim.reset_current_bar_timestamp()
        # Start the timer to measure the execution time of the test.
        self._timer = htimer.Timer()

    def tearDown(self) -> None:
        # Stop the timer to measure the execution time of the test.
        self._timer.stop()
        pytest_print("(%.2f s) " % self._timer.get_total_elapsed())
        # Report if the test was updated
        if self._test_was_updated:
            if not self._overriden_update_tests:
                pytest_warning("Test was updated) ", prefix="(")
            else:
                # We forced an update from the unit test itself, so no need
                # to report an update.
                pass
        # Recover the original default pandas options.
        if _HAS_PANDAS:
            pd.options = self._old_pd_options
        # Force matplotlib to close plots to decouple tests.
        if _HAS_MATPLOTLIB:
            plt.close()
            plt.clf()
        # Delete the scratch dir, if needed.
        # TODO(gp): We would like to keep this if the test failed.
        #  I can't find an easy way to detect this situation.
        #  For now just re-run with --incremental.
        if self._scratch_dir and os.path.exists(self._scratch_dir):
            if get_incremental_tests():
                _LOG.warning("Skipping deleting %s", self._scratch_dir)
            else:
                _LOG.debug("Deleting %s", self._scratch_dir)
                hio.delete_dir(self._scratch_dir)
        # Tear down the base class in case it does something, current
        # implementation does nothing, see
        # https://docs.python.org/3/library/unittest.html#unittest.TestCase.tearDown.
        super().tearDown()

    def set_base_dir_name(self, base_dir_name: str) -> None:
        """
        Set the base directory for the input, output, and scratch directories.

        This is used to override the standard location of the base
        directory which is close to the class under test.
        """
        self._base_dir_name = base_dir_name
        _LOG.debug("Setting base_dir_name to '%s'", self._base_dir_name)
        hio.create_dir(self._base_dir_name, incremental=True)

    def mock_update_tests(self) -> None:
        """
        When unit testing the unit test framework we want to test updating the
        golden outcome.
        """
        self._update_tests = True
        self._overriden_update_tests = True
        self._git_add = False

    def get_input_dir(
        self,
        use_only_test_class: bool = False,
        test_class_name: Optional[str] = None,
        test_method_name: Optional[str] = None,
        use_absolute_path: bool = True,
    ) -> str:
        """
        Return the path of the directory storing input data for this test
        class.

        E.g., `TestLinearRegression1.test1`.

        :param use_only_test_class: use only the name on the test class and not of
            the method. E.g., when one wants all the test methods to use a single
            file for testing
        :param test_class_name: `None` uses the current test class name
        :param test_method_name: `None` uses the current test method name
        :param use_absolute_path: use the path from the file containing the test
        :return: dir name
        """
        # Get the dir of the test.
        dir_name = self._get_current_path(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        # Add `input` to the dir.
        dir_name = os.path.join(dir_name, "input")
        return dir_name

    def get_output_dir(self, *, test_class_name: Optional[str] = None) -> str:
        """
        Return the path of the directory storing output data for this test
        class.

        :return: dir name
        """
        # The output dir is specific of this dir.
        use_only_test_class = False
        test_method_name = None
        use_absolute_path = True
        dir_name = self._get_current_path(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        # Add `output` to the dir.
        dir_name = os.path.join(dir_name, "output")
        return dir_name

    # TODO(gp): -> get_scratch_dir().
    def get_scratch_space(
        self,
        test_class_name: Optional[str] = None,
        test_method_name: Optional[str] = None,
        use_absolute_path: bool = True,
    ) -> str:
        """
        Return the path of the directory storing scratch data for this test.

        The directory is also created and cleaned up based on whether
        the incremental behavior is enabled or not.
        """
        if self._scratch_dir is None:
            # Create the dir on the first invocation on a given test.
            use_only_test_class = False
            dir_name = self._get_current_path(
                use_only_test_class,
                test_class_name,
                test_method_name,
                use_absolute_path,
            )
            # Add `tmp.scratch` to the dir.
            dir_name = os.path.join(dir_name, "tmp.scratch")
            # On the first invocation create the dir.
            hio.create_dir(dir_name, incremental=get_incremental_tests())
            # Store the value.
            self._scratch_dir = dir_name
        return self._scratch_dir

    def get_s3_scratch_dir(
        self,
        test_class_name: Optional[str] = None,
        test_method_name: Optional[str] = None,
    ) -> str:
        """
        Return the path of a directory storing scratch data on S3 for this
        test.

        E.g.,
            s3://alphamatic-data/tmp/cache.unit_test/
                root.98e1cf5b88c3.amp.TestTestCase1.test_get_s3_scratch_dir1
        """
        # Make the path unique for the test.
        use_only_test_class = False
        use_absolute_path = False
        test_path = self._get_current_path(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        # Make the path unique for the current user.
        user_name = hsystem.get_user_name()
        server_name = hsystem.get_server_name()
        project_dirname = hgit.get_project_dirname()
        dir_name = f"{user_name}.{server_name}.{project_dirname}"
        # Assemble everything in a single path.
        import helpers.hs3 as hs3

        aws_profile = "ck"
        s3_bucket = hs3.get_s3_bucket_path_unit_test(aws_profile)
        scratch_dir = f"{s3_bucket}/tmp/cache.unit_test/{dir_name}.{test_path}"
        return scratch_dir

    def get_s3_input_dir(
        self,
        *,
        use_only_test_class: bool = False,
        test_class_name: Optional[str] = None,
        test_method_name: Optional[str] = None,
        use_absolute_path: bool = False,
    ) -> str:
        import helpers.henv as henv

        s3_bucket = henv.execute_repo_config_code("get_unit_test_bucket_path()")
        hdbg.dassert_isinstance(s3_bucket, str)
        # Make the path unique for the test.
        test_path = self.get_input_dir(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        hdbg.dassert_isinstance(test_path, str)
        # Assemble everything in a single path.
        input_dir = os.path.join(s3_bucket, test_path)
        return input_dir

    # ///////////////////////////////////////////////////////////////////////

    def assert_equal(
        self,
        actual: str,
        expected: str,
        *,
        dedent: bool = False,
        purify_text: bool = False,
        purify_expected_text: bool = False,
        fuzzy_match: bool = False,
        ignore_line_breaks: bool = False,
        sort: bool = False,
        abort_on_error: bool = True,
        dst_dir: str = ".",
    ) -> bool:
        """
        Return if `actual` and `expected` are different and report the
        difference.

        Implement a better version of `self.assertEqual()` that reports
        mismatching strings with sdiff and save them to files for
        further analysis with vimdiff.

        The interface is similar to `check_string()`.
        """
        _LOG.debug(hprint.to_str("fuzzy_match abort_on_error dst_dir"))
        hdbg.dassert_in(type(actual), (bytes, str), "actual=%s", str(actual))
        hdbg.dassert_in(
            type(expected), (bytes, str), "expected=%s", str(expected)
        )
        # Get the current dir name.
        use_only_test_class = False
        test_class_name = None
        test_method_name = None
        use_absolute_path = True
        dir_name = self._get_current_path(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        _LOG.debug("dir_name=%s", dir_name)
        hio.create_dir(dir_name, incremental=True)
        hdbg.dassert_path_exists(dir_name)
        #
        test_name = self._get_test_name()
        is_equal = assert_equal(
            actual,
            expected,
            test_name,
            dir_name,
            check_string=False,
            dedent=dedent,
            purify_text=purify_text,
            purify_expected_text=purify_expected_text,
            fuzzy_match=fuzzy_match,
            ignore_line_breaks=ignore_line_breaks,
            sort=sort,
            abort_on_error=abort_on_error,
            dst_dir=dst_dir,
        )
        return is_equal

    def assert_dfs_close(
        self,
        actual: "pd.DataFrame",
        expected: "pd.DataFrame",
        **kwargs: Any,
    ) -> None:
        """
        Assert dfs have same indexes and columns and that all values are close.

        This is a more robust alternative to `compare_df()`. In
        particular, it is less sensitive to floating point round-off
        errors.
        """
        self.assertEqual(actual.index.to_list(), expected.index.to_list())
        self.assertEqual(actual.columns.to_list(), expected.columns.to_list())
        # Often the output of a failing assertion is difficult to parse
        # so we resort to our special `assert_equal()`.
        if not np.allclose(actual, expected, **kwargs):
            import helpers.hpandas as hpandas

            self.assert_equal(
                hpandas.df_to_str(actual), hpandas.df_to_str(expected)
            )
        np.testing.assert_allclose(actual, expected, **kwargs)

    # TODO(gp): There is a lot of similarity between `check_string()` and
    #  `check_df_string()` that can be factored out if we extract the code that
    #  reads and saves the golden file.
    def check_string(
        self,
        actual: str,
        *,
        dedent: bool = False,
        purify_text: bool = False,
        fuzzy_match: bool = False,
        ignore_line_breaks: bool = False,
        sort: bool = False,
        use_gzip: bool = False,
        tag: str = "test",
        abort_on_error: bool = True,
        action_on_missing_golden: str = _ACTION_ON_MISSING_GOLDEN,
        test_class_name=None,
    ) -> Tuple[bool, bool, Optional[bool]]:
        """
        Check the actual outcome of a test against the expected outcome
        contained in the file. If `--update_outcomes` is used, updates the
        golden reference file with the actual outcome.

        :param dedent: call `dedent` on the expected string to align it to the
            beginning of the row
        :param purify_text: remove some artifacts (e.g., user names,
            directories, reference to Git client)
        :param fuzzy_match: ignore differences in spaces
        :param ignore_line_breaks: ignore difference due to line breaks
        :param sort: sort the text and then compare it. In other terms we check
            whether the lines are the same although in different order
        :param action_on_missing_golden: what to do (e.g., "assert" or "update" when
            the golden outcome is missing)
        :return: outcome_updated, file_exists, is_equal
        :raises: `RuntimeError` if there is a mismatch. If `abort_on_error` is False
            (which should be used only for unit testing) return the result but do not
            assert
        """
        _LOG.debug(
            hprint.to_str(
                "dedent purify_text fuzzy_match ignore_line_breaks sort "
                "tag abort_on_error"
            )
        )
        hdbg.dassert_in(type(actual), (bytes, str), "actual='%s'", actual)
        #
        dir_name, file_name = self._get_golden_outcome_file_name(
            tag, test_class_name=test_class_name
        )
        if use_gzip:
            file_name += ".gz"
        _LOG.debug("file_name=%s", file_name)
        # Remove reference from the current environment.
        # TODO(gp): Not sure why we purify here and not delegate to `assert_equal`.
        if purify_text:
            _LOG.debug("Purifying actual outcome")
            actual = purify_txt_from_client(actual)
        _LOG.debug("actual=\n%s", actual)
        outcome_updated = False
        file_exists = os.path.exists(file_name)
        _LOG.debug("file_exists=%s", file_exists)
        is_equal: Optional[bool] = None
        if self._update_tests:
            _LOG.debug("# Update golden outcomes")
            # Determine whether outcome needs to be updated.
            if file_exists:
                expected = hio.from_file(file_name)
                is_equal = expected == actual
                if not is_equal:
                    outcome_updated = True
            else:
                # The golden outcome doesn't exist.
                outcome_updated = True
            _LOG.debug("outcome_updated=%s", outcome_updated)
            if outcome_updated:
                # Update the golden outcome.
                self._check_string_update_outcome(file_name, actual, use_gzip)
        else:
            # Check the test result.
            _LOG.debug("# Check golden outcomes")
            if file_exists:
                # Golden outcome is available: check the actual outcome against
                # the golden outcome.
                expected = hio.from_file(file_name)
                test_name = self._get_test_name()
                is_equal = assert_equal(
                    actual,
                    expected,
                    test_name,
                    dir_name,
                    check_string=True,
                    dedent=dedent,
                    # We have handled the purification of the output earlier.
                    purify_text=False,
                    fuzzy_match=fuzzy_match,
                    ignore_line_breaks=ignore_line_breaks,
                    sort=sort,
                    abort_on_error=abort_on_error,
                )
            else:
                # No golden outcome available.
                _LOG.warning("Can't find golden outcome file '%s'", file_name)
                if action_on_missing_golden == "assert":
                    # Save the result to a temporary file and assert.
                    file_name += ".tmp"
                    hio.to_file(file_name, actual, use_gzip=use_gzip)
                    msg = (
                        "The golden outcome doesn't exist: saved the actual "
                        f"output in '{file_name}'"
                    )
                    _LOG.error(msg)
                    if abort_on_error:
                        hdbg.dfatal(msg)
                elif action_on_missing_golden == "update":
                    # Create golden file and add it to the repo.
                    _LOG.warning("Creating the golden outcome")
                    outcome_updated = True
                    self._check_string_update_outcome(file_name, actual, use_gzip)
                    is_equal = None
                else:
                    hdbg.dfatal(
                        "Invalid action_on_missing_golden="
                        + f"'{action_on_missing_golden}'"
                    )
        self._test_was_updated = outcome_updated
        _LOG.debug(hprint.to_str("outcome_updated file_exists is_equal"))
        return outcome_updated, file_exists, is_equal

    def check_dataframe(
        self,
        actual: "pd.DataFrame",
        *,
        err_threshold: float = 0.05,
        dedent: bool = False,
        tag: str = "test_df",
        abort_on_error: bool = True,
        action_on_missing_golden: str = _ACTION_ON_MISSING_GOLDEN,
    ) -> Tuple[bool, bool, Optional[bool]]:
        """
        Like `check_string()` but for pandas dataframes, instead of strings.
        """
        _LOG.debug(hprint.to_str("err_threshold tag abort_on_error"))
        hdbg.dassert_isinstance(actual, pd.DataFrame)
        #
        dir_name, file_name = self._get_golden_outcome_file_name(tag)
        _LOG.debug("file_name=%s", file_name)
        outcome_updated = False
        file_exists = os.path.exists(file_name)
        _LOG.debug(hprint.to_str("file_exists"))
        is_equal: Optional[bool] = None
        if self._update_tests:
            _LOG.debug("# Update golden outcomes")
            # Determine whether outcome needs to be updated.
            if file_exists:
                is_equal, _ = self._check_df_compare_outcome(
                    file_name, actual, err_threshold
                )
                _LOG.debug(hprint.to_str("is_equal"))
                if not is_equal:
                    outcome_updated = True
            else:
                # The golden outcome doesn't exist.
                outcome_updated = True
            _LOG.debug("outcome_updated=%s", outcome_updated)
            if outcome_updated:
                # Update the golden outcome.
                self._check_df_update_outcome(file_name, actual)
        else:
            # Check the test result.
            _LOG.debug("# Check golden outcomes")
            if file_exists:
                # Golden outcome is available: check the actual outcome against
                # the golden outcome.
                is_equal, expected = self._check_df_compare_outcome(
                    file_name, actual, err_threshold
                )
                # If not equal, report debug information.
                if not is_equal:
                    test_name = self._get_test_name()
                    assert_equal(
                        str(actual),
                        str(expected),
                        test_name,
                        dir_name,
                        check_string=True,
                        dedent=dedent,
                        purify_text=False,
                        fuzzy_match=False,
                        ignore_line_breaks=False,
                        abort_on_error=abort_on_error,
                        error_msg=self._error_msg,
                    )
            else:
                # No golden outcome available.
                _LOG.warning("Can't find golden outcome file '%s'", file_name)
                if action_on_missing_golden == "assert":
                    # Save the result to a temporary file and assert.
                    file_name += ".tmp"
                    hio.create_enclosing_dir(file_name)
                    actual.to_csv(file_name)
                    msg = (
                        "The golden outcome doesn't exist: saved the actual "
                        f"output in '{file_name}'"
                    )
                    _LOG.error(msg)
                    if abort_on_error:
                        hdbg.dfatal(msg)
                elif action_on_missing_golden == "update":
                    # Create golden file and add it to the repo.
                    _LOG.warning("Creating the golden outcome")
                    outcome_updated = True
                    self._check_df_update_outcome(file_name, actual)
                    is_equal = None
                else:
                    hdbg.dfatal(
                        "Invalid action_on_missing_golden="
                        + f"'{action_on_missing_golden}'"
                    )
        self._test_was_updated = outcome_updated
        # TODO(gp): Print the file with the updated test.
        _LOG.debug(hprint.to_str("outcome_updated file_exists is_equal"))
        return outcome_updated, file_exists, is_equal

    def check_df_output(
        self,
        actual_df: "pd.DataFrame",
        expected_length: Optional[int],
        expected_column_names: Optional[List[str]],
        expected_column_unique_values: Optional[Dict[str, List[Any]]],
        expected_signature: str,
    ) -> None:
        """
        Verify that actual outcome dataframe matches the expected one.

        :param actual_df: actual outcome dataframe
        :param expected_length: expected outcome dataframe length
            - If `None`, skip the check
        :param expected_column_names: expected outcome dataframe column names
            - If `None`, skip the check
        :param expected_column_unique_values: dict of column names and unique values
            that they should contain
            - If `None`, skip the check
        :param expected_signature: expected outcome dataframe as string
            - If `__CHECK_STRING__` use the value in `self.check_string()`
        """
        # TODO(Grisha): get rid of `hpandas` dependency.
        import helpers.hpandas as hpandas

        hdbg.dassert_isinstance(actual_df, pd.DataFrame)
        if expected_length:
            # Verify that the output length is correct.
            actual_length = actual_df.shape[0]
            self.assert_equal(str(actual_length), str(expected_length))
        if expected_column_names:
            # Verify that the column names are correct.
            self.assert_equal(
                str(sorted(actual_df.columns)), str(sorted(expected_column_names))
            )
        if expected_column_unique_values:
            hdbg.dassert_is_subset(
                list(expected_column_unique_values.keys()), actual_df.columns
            )
            # Verify that the unique values in specified columns are correct.
            for column in expected_column_unique_values:
                actual_one_column_unique_values = sorted(
                    list(actual_df[column].unique())
                )
                self.assert_equal(
                    str(actual_one_column_unique_values),
                    str(sorted(expected_column_unique_values[column])),
                )
        # Build signature.
        actual_signature = hpandas.df_to_str(
            actual_df,
            print_shape_info=True,
            tag="df",
        )
        _LOG.debug("\n%s", actual_signature)
        # Check signature.
        if expected_signature == "__CHECK_STRING__":
            self.check_string(actual_signature, dedent=True, fuzzy_match=True)
        else:
            hdbg.dassert_isinstance(expected_signature, str)
            self.assert_equal(
                actual_signature,
                expected_signature,
                dedent=True,
                fuzzy_match=True,
            )

    def check_srs_output(
        self,
        actual_srs: "pd.Series",
        expected_length: Optional[int],
        expected_unique_values: Optional[List[Any]],
        expected_signature: str,
    ) -> None:
        """
        Verify that actual outcome series matches the expected one.

        :param actual_srs: actual outcome series
        :param expected_length: expected outcome series length
            - If `None`, skip the check
        :param expected_unique_values: list of expected unique values in series
            - If `None`, skip the check
        :param expected_signature: expected outcome series as string
        """
        # Import `hpandas` dynamically to exclude `pandas` from the thin client
        # requirements. See CmTask6613 for details.
        import helpers.hpandas as hpandas

        hdbg.dassert_isinstance(actual_srs, pd.Series)
        if expected_length:
            # Verify that output length is correct.
            self.assert_equal(str(actual_srs.shape[0]), str(expected_length))
        if expected_unique_values:
            # Verify that unique values in series are correct.
            self.assert_equal(
                str(sorted(list(actual_srs.unique()))),
                str(sorted(expected_unique_values)),
            )
        # Build signature.
        actual_signature = hpandas.df_to_str(actual_srs, num_rows=None)
        _LOG.debug("\n%s", actual_signature)
        # Check signature.
        if expected_signature == "__CHECK_STRING__":
            self.check_string(actual_signature, dedent=True, fuzzy_match=True)
        else:
            hdbg.dassert_isinstance(expected_signature, str)
            self.assert_equal(
                actual_signature,
                expected_signature,
                dedent=True,
                fuzzy_match=True,
            )

    # ///////////////////////////////////////////////////////////////////////

    # TODO(gp): This needs to be moved to `helper.git` and generalized.
    def _git_add_file(self, file_name: str) -> None:
        """
        Add to git repo `file_name`, if needed.
        """
        _LOG.debug(hprint.to_str("file_name"))
        if self._git_add:
            # Find the file relative to here.
            mode = "assert_unless_one_result"
            file_names_tmp = hgit.find_docker_file(file_name, mode=mode)
            file_name_tmp = file_names_tmp[0]
            _LOG.debug(hprint.to_str("file_name file_name_tmp"))
            if file_name_tmp.startswith("amp"):
                # To add a file like
                # amp/core/test/TestCheckSameConfigs.test_check_same_configs_error/output/test.txt
                # we need to descend into `amp`.
                # TODO(gp): This needs to be generalized to `lm`. We should `cd`
                # in the dir of the repo that includes the file.
                file_name_in_amp = os.path.relpath(file_name_tmp, "amp")
                cmd = f"cd amp; git add -u {file_name_in_amp}"
            else:
                cmd = f"git add -u {file_name_tmp}"
            rc = hsystem.system(cmd, abort_on_error=False)
            if rc:
                pytest_warning(
                    f"Can't git add file\n'{file_name}' -> '{file_name_tmp}'\n"
                    "You need to git add the file manually\n",
                    prefix="\n",
                )
                pytest_print(f"> {cmd}\n")

    def _check_string_update_outcome(
        self, file_name: str, actual: str, use_gzip: bool
    ) -> None:
        _LOG.debug(hprint.to_str("file_name"))
        hio.to_file(file_name, actual, use_gzip=use_gzip)
        # Add to git repo.
        self._git_add_file(file_name)

    # ///////////////////////////////////////////////////////////////////////

    def _check_df_update_outcome(
        self,
        file_name: str,
        actual: "pd.DataFrame",
    ) -> None:
        _LOG.debug(hprint.to_str("file_name"))
        hio.create_enclosing_dir(file_name)
        actual.to_csv(file_name)
        pytest_warning(f"Update golden outcome file '{file_name}'", prefix="\n")
        # Add to git repo.
        self._git_add_file(file_name)

    def _check_df_compare_outcome(
        self, file_name: str, actual: "pd.DataFrame", err_threshold: float
    ) -> Tuple[bool, "pd.DataFrame"]:
        _LOG.debug(hprint.to_str("file_name"))
        _LOG.debug("actual_=\n%s", actual)
        hdbg.dassert_lte(0, err_threshold)
        hdbg.dassert_lte(err_threshold, 1.0)
        # Load the expected df from file.
        expected = pd.read_csv(file_name, index_col=0)
        _LOG.debug("expected=\n%s", expected)
        hdbg.dassert_isinstance(expected, pd.DataFrame)
        ret = True
        # Compare columns.
        if actual.columns.tolist() != expected.columns.tolist():
            msg = f"Columns are different:\n{str(actual.columns)}\n{str(expected.columns)}"
            self._to_error(msg)
            ret = False
        # Compare the values.
        _LOG.debug("actual.shape=%s", str(actual.shape))
        _LOG.debug("expected.shape=%s", str(expected.shape))
        # From https://numpy.org/doc/stable/reference/generated/numpy.allclose.html
        # absolute(a - b) <= (atol + rtol * absolute(b))
        # absolute(a - b) / absolute(b)) <= rtol
        is_close = np.allclose(
            actual, expected, rtol=err_threshold, equal_nan=True
        )
        if not is_close:
            _LOG.error("Dataframe values are not close")
            if actual.shape == expected.shape:
                close_mask = np.isclose(actual, expected, equal_nan=True)
                #
                msg = f"actual=\n{actual}"
                self._to_error(msg)
                #
                msg = f"expected=\n{expected}"
                self._to_error(msg)
                #
                actual_masked = np.where(close_mask, np.nan, actual)
                msg = f"actual_masked=\n{actual_masked}"
                self._to_error(msg)
                #
                expected_masked = np.where(close_mask, np.nan, expected)
                msg = f"expected_masked=\n{expected_masked}"
                self._to_error(msg)
                #
                err = np.abs((actual_masked - expected_masked) / expected_masked)
                msg = f"err=\n{err}"
                self._to_error(msg)
                max_err = np.nanmax(np.nanmax(err))
                msg = "max_err=%.3f" % max_err
                self._to_error(msg)
            else:
                msg = (
                    "Shapes are different:\n"
                    f"actual.shape={str(actual.shape)}\nexpected.shape={str(expected.shape)}"
                )
                self._to_error(msg)
            ret = False
        _LOG.debug("ret=%s", ret)
        return ret, expected

    # ///////////////////////////////////////////////////////////////////////

    def _get_golden_outcome_file_name(
        self, tag: str, *, test_class_name: Optional[str] = None
    ) -> Tuple[str, str]:
        # Get the current dir name.
        use_only_test_class = False
        test_method_name = None
        use_absolute_path = True
        dir_name = self._get_current_path(
            use_only_test_class,
            test_class_name,
            test_method_name,
            use_absolute_path,
        )
        _LOG.debug("dir_name=%s", dir_name)
        hio.create_dir(dir_name, incremental=True)
        hdbg.dassert_path_exists(dir_name)
        # Get the expected outcome.
        file_name = (
            self.get_output_dir(test_class_name=test_class_name) + f"/{tag}.txt"
        )
        return dir_name, file_name

    def _get_test_name(self) -> str:
        """
        Return the full test name as `class.method`.
        """
        return f"{self.__class__.__name__}.{self._testMethodName}"

    def _get_current_path(
        self,
        use_only_class_name: bool,
        test_class_name: Optional[str],
        test_method_name: Optional[str],
        use_absolute_path: bool,
    ) -> str:
        """
        Return the name of the directory containing the input / output data.

        E.g.,
        ```
        ./core/dataflow/test/outcomes/TestContinuousSarimaxModel.test_compare
        ```

        The parameters have the same meaning as in `get_input_dir()`.
        """
        if test_class_name is None:
            test_class_name = self.__class__.__name__
        if use_only_class_name:
            # Use only class name.
            dir_name = test_class_name
        else:
            # Use both class and test method.
            if test_method_name is None:
                test_method_name = self._testMethodName
            dir_name = f"{test_class_name}.{test_method_name}"
        if use_absolute_path:
            # E.g., `.../dataflow/test/outcomes/TestContinuousSarimaxModel.test_compare`.
            dir_name = os.path.join(self._base_dir_name, "outcomes", dir_name)
        else:
            # E.g., `outcomes/TestContinuousSarimaxModel.test_compare`.
            dir_name = os.path.join("outcomes", dir_name)
        return dir_name

    def _to_error(self, msg: str) -> None:
        self._error_msg += msg + "\n"
        _LOG.error(msg)


# #############################################################################


@pytest.mark.qa
@pytest.mark.skipif(
    hserver.is_inside_docker(), reason="Test needs to be run outside Docker"
)
class QaTestCase(TestCase, abc.ABC):
    """
    Use for QA to test functionalities (e.g., invoke tasks) that run the dev /
    prod container.
    """

    # TODO(Grisha): Linter should not remove `pass` statement from an empty class
    # DevToolsTask #476.
