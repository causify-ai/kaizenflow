"""
Contain all the code needed to interact with the outside world, e.g., through
system commands, env vars, ...

Import as:

import helpers.hsystem as hsystem
"""

import contextlib
import getpass
import logging
import os
import re
import signal
import subprocess
import sys
import time
from typing import Any, Callable, List, Match, Optional, Tuple, Union, cast

import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hlogging as hloggin
import helpers.hprint as hprint

# This module can depend only on:
# - Python standard modules
# - a few helpers as described in `helpers/dependencies.txt`


_LOG = logging.getLogger(__name__)

# Set logging level of this file.
_LOG.setLevel(logging.INFO)

# #############################################################################


# TODO(gp): Maybe move to hserver.py
def is_running_in_ipynb() -> bool:
    # From https://stackoverflow.com/questions/15411967
    try:
        _ = get_ipython().config  # type: ignore
        res = True
    except NameError:
        res = False
    return res


# TODO(gp): Use is_mac()
def is_running_on_macos() -> bool:
    return get_os_name() == "Darwin"


# #############################################################################

_USER_NAME = None


def set_user_name(user_name: str) -> None:
    """
    To impersonate a user.

    To use only in rare cases for testing or back-door.
    """
    _LOG.warning("Setting user to '%s'", user_name)
    global _USER_NAME
    _USER_NAME = user_name


def get_user_name() -> str:
    if _USER_NAME is None:
        res = getpass.getuser()
    else:
        res = _USER_NAME
    hdbg.dassert_ne(res, "")
    return res


def get_server_name() -> str:
    res = os.uname()
    # posix.uname_result(
    #   sysname='Darwin',
    #   nodename='gpmac.lan',
    #   release='18.2.0',
    #   version='Darwin Kernel Version 18.2.0: Mon Nov 12 20:24:46 PST 2018;
    #       root:xnu-4903.231.4~2/RELEASE_X86_64',
    #   machine='x86_64')
    # This is not compatible with python2.7
    # return res.nodename
    return res[1]


def get_os_name() -> str:
    res = os.uname()
    # This is not compatible with python2.7
    # return res.sysname
    return res[0]


def get_env_var(env_var_name: str) -> str:
    if env_var_name not in os.environ:
        msg = f"Can't find '{env_var_name}': re-run dev_scripts/setenv.sh?"
        _LOG.error(msg)
        raise RuntimeError(msg)
    return os.environ[env_var_name]


# #############################################################################
# system(), system_to_string()
# #############################################################################


# pylint: disable=too-many-branches,too-many-statements,too-many-arguments,too-many-locals
def _system(
    cmd: str,
    abort_on_error: bool,
    suppress_error: Optional[Any],
    suppress_output: Union[bool, str],
    blocking: bool,
    wrapper: Optional[Any],
    output_file: Optional[Any],
    num_error_lines: Optional[int],
    tee: bool,
    dry_run: bool,
    log_level: Union[int, str],
) -> Tuple[int, str]:
    """
    Execute a shell command.

    To print the command and see the output call this as:
    ```
    _system(cmd, suppress_output=False, log_level="echo")
    ```

    :param cmd: string with command to execute
    :param abort_on_error: whether we should assert in case of error or not
    :param suppress_error: set of error codes to suppress
    :param suppress_output: whether to print the output or not
        - If "ON_DEBUG_LEVEL" then print the output if the log level is DEBUG
    :param blocking: blocking system call or not
    :param wrapper: another command to prepend the execution of cmd
    :param output_file: redirect stdout and stderr to this file
    :param num_error_lines: number of lines of the output to display when
        raising `RuntimeError`
    :param tee: if True, tee append (i.e., `tee -a`) stdout and stderr to
        `output_file`
    :param dry_run: print the final command but not execute it
    :param log_level: print the command to execute at level "log_level".
        - If `echo` then print the command line to screen as `print()` and not
          logging
    :return:
        - return code as int
        - output of the command as str
    """
    _LOG.debug("##> %s", cmd)
    _LOG.debug(
        hprint.to_str(
            "abort_on_error suppress_error suppress_output "
            "blocking wrapper output_file num_error_lines tee dry_run log_level"
        )
    )
    orig_cmd = cmd[:]
    _LOG.debug("orig_cmd=%s", orig_cmd)
    # Handle `suppress_output`.
    hdbg.dassert_in(suppress_output, ("ON_DEBUG_LEVEL", True, False))
    if suppress_output == "ON_DEBUG_LEVEL":
        # print("eff_lev=%s" % eff_level)
        # print("lev=%s" % logging.DEBUG)
        _LOG.getEffectiveLevel()
        # Suppress the output if the verbosity level is higher than DEBUG,
        # otherwise print.
        suppress_output = _LOG.getEffectiveLevel() > logging.DEBUG
    _LOG.debug(hprint.to_str("suppress_output"))
    # Prepare the command line.
    cmd = f"({cmd})"
    hdbg.dassert_imply(tee, output_file is not None)
    if output_file is not None:
        # Redirect to a file.
        dir_name = os.path.dirname(output_file)
        if not dir_name:
            dir_name = "."
        if not os.path.exists(dir_name):
            _LOG.debug("Dir '%s' doesn't exist: creating", dir_name)
            hdbg.dassert(bool(dir_name), "dir_name='%s'", dir_name)
            os.makedirs(dir_name)
        if tee:
            cmd += f" 2>&1 | tee -a {output_file};"
            cmd += " exit ${PIPESTATUS[0]}"
        else:
            cmd += f" 2>&1 >{output_file}"
    else:
        # Do not redirect to a file.
        cmd += " 2>&1"
    # Handle `wrapper`.
    if wrapper:
        cmd = wrapper + " && " + cmd
    # Handle `log_level`.
    # TODO(gp): Make it "ECHO" or "PRINT".
    if isinstance(log_level, str):
        hdbg.dassert_in(log_level, ("echo", "echo_frame"))
        if log_level == "echo_frame":
            print(hprint.frame(f"> {cmd}"))
        elif log_level == "echo":
            print(f"> {cmd}")
        else:
            raise ValueError(f"Invalid log_level='{log_level}'")
        _LOG.debug("> %s", cmd)
    else:
        _LOG.log(log_level, "> %s", cmd)
    output = ""
    # Handle `dry_run`.
    if dry_run:
        _LOG.warning("As per user request, not executing command:\n%s", cmd)
        rc = 0
        return rc, output
    # Execute the command.
    try:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT
        # We want to print the command line even if this module logging is disabled.
        # print("  ==> cmd=%s" % cmd)
        with hloggin.set_level(_LOG, logging.DEBUG):
            _LOG.debug("> %s", cmd)
        with subprocess.Popen(
            cmd, shell=True, executable="/bin/bash", stdout=stdout, stderr=stderr
        ) as p:
            output = ""
            if blocking:
                # Blocking call: get the output.
                while True:
                    line = p.stdout.readline().decode("utf-8")  # type: ignore
                    if not line:
                        break
                    if not suppress_output:
                        # print("  ==> %s" % line.rstrip("\n"))
                        print("  ... %s" % line.rstrip("\n"))
                    output += line
                p.stdout.close()  # type: ignore
                rc = p.wait()
            else:
                # Not blocking.
                # Wait until process terminates (without using p.wait()).
                max_cnt = 20
                cnt = 0
                while p.poll() is None:
                    # Process hasn't exited yet, let's wait some time.
                    time.sleep(0.1)
                    cnt += 1
                    _LOG.debug("cnt=%s, rc=%s", cnt, p.returncode)
                    if cnt > max_cnt:
                        break
                if cnt > max_cnt:
                    # Timeout: we assume it worked.
                    rc = 0
                else:
                    rc = p.returncode
        if suppress_error is not None:
            hdbg.dassert_isinstance(suppress_error, set)
            if rc in suppress_error:
                rc = 0
    except OSError as e:
        rc = -1
        _LOG.error("error=%s", str(e))
    _LOG.debug("  ==> rc=%s", rc)
    if abort_on_error and rc != 0:
        msg = (
            "\n"
            + hprint.frame(f"cmd='{cmd}' failed with rc='{rc}'")
            + f"\nOutput of the failing command is:\n{hprint.line('>')}"
            + f"\n{output}\n{hprint.line('<')}"
        )
        _LOG.error("%s", msg)
        # Report the first `num_error_lines` of the output.
        num_error_lines = num_error_lines or 30
        output_error = "\n".join(output.split("\n")[:num_error_lines])
        raise RuntimeError(
            f"cmd='{cmd}' failed with rc='{rc}'\ntruncated output=\n{output_error}"
        )
    # hdbg.dassert_type_in(output, (str, ))
    return rc, output


# pylint: disable=too-many-arguments
def system(
    cmd: str,
    abort_on_error: bool = True,
    suppress_error: Optional[Any] = None,
    suppress_output: Union[str, bool] = "ON_DEBUG_LEVEL",
    blocking: bool = True,
    wrapper: Optional[Any] = None,
    output_file: Optional[Any] = None,
    num_error_lines: Optional[int] = None,
    tee: bool = False,
    dry_run: bool = False,
    log_level: Union[int, str] = logging.DEBUG,
) -> int:
    """
    Execute a shell command, without capturing its output.

    See _system() for options.
    """
    rc, _ = _system(
        cmd,
        abort_on_error=abort_on_error,
        suppress_error=suppress_error,
        suppress_output=suppress_output,
        blocking=blocking,
        wrapper=wrapper,
        output_file=output_file,
        num_error_lines=num_error_lines,
        tee=tee,
        dry_run=dry_run,
        log_level=log_level,
    )
    return rc


# def _system_to_string(cmd):
#     py_ver = sys.version_info[0]
#     if py_ver == 2:
#         txt = subprocess.check_output(cmd)
#     elif py_ver == 3:
#         txt = subprocess.getoutput(cmd)
#     else:
#         raise RuntimeError("Invalid py_ver=%s" % py_ver)
#     txt = [f for f in txt.split("\n") if f]
#     hdbg.dassert_eq(len(txt), 1)
#     return txt[0]


def system_to_string(
    cmd: str,
    abort_on_error: bool = True,
    wrapper: Optional[Any] = None,
    dry_run: bool = False,
    log_level: Union[int, str] = logging.DEBUG,
) -> Tuple[int, str]:
    """
    Execute a shell command and capture its output.

    See _system() for options.
    """
    rc, output = _system(
        cmd,
        abort_on_error=abort_on_error,
        suppress_error=None,
        suppress_output="ON_DEBUG_LEVEL",
        # If we want to see the output the system call must be blocking.
        blocking=True,
        wrapper=wrapper,
        output_file=None,
        num_error_lines=None,
        tee=False,
        dry_run=dry_run,
        log_level=log_level,
    )
    output = output.rstrip("\n")
    return rc, output


# #############################################################################
# system_to_one_line()
# #############################################################################


def get_first_line(output: str) -> str:
    """
    Return the first (and only) line from a string.

    This is used when calling system_to_string() and expecting a single
    line output.
    """
    output = hprint.remove_empty_lines(output)
    output_as_arr: List[str] = output.split("\n")
    # Remove the annoying spurious matches under `tmp.base`.
    output_as_arr = [line for line in output_as_arr if "/tmp.base/" not in line]
    hdbg.dassert_eq(len(output_as_arr), 1, "output='%s'", output)
    output = output_as_arr[0]
    output = output.rstrip().lstrip()
    return output


# TODO(gp): Move it to a more general file, e.g., `helpers/printing.py`?
def text_to_list(txt: str) -> List[str]:
    """
    Convert a string (e.g., from system_to_string) into a list of lines.
    """
    res = [line.rstrip().lstrip() for line in txt.split("\n")]
    res = [line for line in res if line != ""]
    return res


def system_to_one_line(cmd: str, *args: Any, **kwargs: Any) -> Tuple[int, str]:
    """
    Execute a shell command, capturing its output (expected to be a single
    line).

    This is a thin wrapper around system_to_string().
    """
    rc, output = system_to_string(cmd, *args, **kwargs)
    output = get_first_line(output)
    return rc, output


# #############################################################################
# system_to_files()
# #############################################################################


def to_normal_paths(files: List[str]) -> List[str]:
    files: List[str] = list(map(os.path.normpath, files))  # type: ignore
    return files


def to_absolute_paths(files: List[str]) -> List[str]:
    files: List[str] = list(map(os.path.abspath, files))  # type: ignore
    return files


def _remove_files_non_present(files: List[str]) -> List[str]:
    """
    Return list of files from `files` excluding the files that don't exist.
    """
    files_tmp = []
    for f in files:
        if os.path.exists(f):
            files_tmp.append(f)
        else:
            _LOG.warning("File '%s' doesn't exist: skipping", f)
    return files_tmp


def remove_dirs(files: List[str]) -> List[str]:
    """
    Return list of files from `files` excluding the files that are directories.
    """
    files_tmp: List[str] = []
    dirs_tmp: List[str] = []
    for file in files:
        if os.path.isdir(file):
            _LOG.debug("file='%s' is a dir: skipping", file)
            dirs_tmp.append(file)
        else:
            files_tmp.append(file)
    if dirs_tmp:
        _LOG.warning("Removed dirs: %s", ", ".join(dirs_tmp))
    return files_tmp


def select_result_file_from_list(files: List[str], mode: str) -> List[str]:
    """
    Select a file from a list according to various approaches encoded in
    `mode`.

    :param mode:
        - "return_all_results": return the list of files, whatever it is
        - "assert_unless_one_result": assert unless there is a single file and return
          the only file. Note that we still return a list to keep the interface
          simple.
    """
    res: List[str] = []
    if mode == "assert_unless_one_result":
        # Expect to have a single result and return that.
        if len(files) == 0:
            hdbg.dfatal(f"mode={mode}: didn't find file")
        elif len(files) > 1:
            hdbg.dfatal(
                "mode=%s: found multiple files:\n%s" % (mode, "\n".join(files))
            )
        res = [files[0]]
    elif mode == "return_all_results":
        # Return all files.
        res = files
    else:
        hdbg.dfatal(f"Invalid mode='{mode}'")
    return res


def system_to_files(
    cmd: str,
    dir_name: Optional[str] = None,
    remove_files_non_present: bool = False,
    mode: str = "return_all_results",
) -> List[str]:
    """
    Execute command `cmd` in `dir_name` and return the output as a list of
    strings.

    :param remove_files_non_present: remove files that don't exist on the filesystem
    :param mode: like in `select_result_file_from_list()`
    """
    if dir_name is None:
        dir_name = "."
    hdbg.dassert_dir_exists(dir_name)
    cmd = f"cd {dir_name} && {cmd}"
    _, output = system_to_string(cmd)
    # Remove empty lines.
    _LOG.debug("output=\n%s", output)
    files = output.split("\n")
    files = [line.rstrip().rstrip() for line in files]
    files = [line for line in files if line != ""]
    _LOG.debug("files=%s", " ".join(files))
    # Convert to normalized paths.
    files = [os.path.join(dir_name, f) for f in files]
    files: List[str] = list(map(os.path.normpath, files))  # type: ignore
    # Remove non-existent files, if needed.
    if remove_files_non_present:
        files = _remove_files_non_present(files)
    # Process output.
    files = select_result_file_from_list(files, mode)
    return files


# #############################################################################
# Functions handling processes
# #############################################################################


def get_process_pids(
    keep_line: Callable[[str], bool]
) -> Tuple[List[int], List[str]]:
    """
    Find all the processes corresponding to `ps ax` filtered line by line with
    `keep_line()`.

    :return: list of pids and filtered output of `ps ax`
    """
    cmd = "ps ax"
    rc, txt = system_to_string(cmd, abort_on_error=False)
    _LOG.debug("txt=\n%s", txt)
    pids: List[int] = []
    txt_out: List[str] = []
    if rc == 0:
        for line in txt.split("\n"):
            _LOG.debug("line=%s", line)
            # PID   TT  STAT      TIME COMMAND
            if "PID" in line and "TT" in line and "STAT" in line:
                txt_out.append(line)
                continue
            keep = keep_line(line)
            _LOG.debug("  keep=%s", keep)
            if not keep:
                continue
            # > ps ax | grep 'ssh -i' | grep localhost
            # 19417   ??  Ss     0:00.39 ssh -i /Users/gp/.ssh/id_rsa -f -nNT \
            #           -L 19999:localhost:19999 gp@54.172.40.4
            fields = line.split()
            try:
                pid = int(fields[0])
            except ValueError as e:
                _LOG.error("Can't parse fields '%s' from line '%s'", fields, line)
                raise e
            _LOG.debug("pid=%s", pid)
            pids.append(pid)
            txt_out.append(line)
    return pids, txt_out


def kill_process(
    get_pids: Callable[[], Tuple[List[int], str]],
    timeout_in_secs: int = 5,
    polltime_in_secs: float = 0.1,
) -> None:
    """
    Kill all the processes returned by the function `get_pids()`.

    :param timeout_in_secs: how many seconds to wait at most before giving up
    :param polltime_in_secs: how often to check for dead processes
    """
    import tqdm

    pids, txt = get_pids()
    _LOG.info("Killing %d pids (%s)\n%s", len(pids), pids, "\n".join(txt))
    if not pids:
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError as e:
            _LOG.warning(str(e))
    #
    _LOG.info("Waiting %d processes (%s) to die", len(pids), pids)
    for _ in tqdm.tqdm(
        range(int(timeout_in_secs / polltime_in_secs)), desc="Polling process"
    ):
        time.sleep(polltime_in_secs)
        pids, _ = get_pids()
        if not pids:
            break
    pids, txt = get_pids()
    hdbg.dassert_eq(len(pids), 0, "Processes are still alive:%s", "\n".join(txt))
    _LOG.info("Processes dead")


# #############################################################################
# User interaction
# #############################################################################


def query_yes_no(question: str, abort_on_no: bool = True) -> bool:
    """
    Ask a yes/no question via `raw_input()` and return their answer.

    :param question: string with the question presented to the user
    :param abort_on_no: exit if the user answers "no"
    :return: True for "yes" or False for "no"
    """
    hdbg.dassert_isinstance(question, str)
    hdbg.dassert_isinstance(abort_on_no, bool)
    valid = {
        "yes": True,
        "y": True,
        #
        "no": False,
        "n": False,
    }
    prompt = " [y/n] "
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice in valid:
            ret = valid[choice]
            break
    _LOG.debug("ret=%s", ret)
    if abort_on_no:
        if not ret:
            print("You answer no: exiting")
            sys.exit(-1)
    return ret


def press_enter_to_continue(prompt: str = "") -> None:
    hdbg.dassert_isinstance(prompt, str)
    if not prompt:
        prompt = "Press Enter to continue..."
    sys.stdout.write(prompt)
    _ = input()


# #############################################################################
# Functions similar to Linux commands.
# #############################################################################


def check_exec(tool: str) -> bool:
    """
    Check if an executable can be executed.

    :return: True if the executables "tool" can be executed.
    """
    suppress_output = _LOG.getEffectiveLevel() > logging.DEBUG
    cmd = f"which {tool}"
    abort_on_error = False
    rc = system(
        cmd,
        abort_on_error=abort_on_error,
        suppress_output=suppress_output,
        log_level=logging.DEBUG,
    )
    return rc == 0


# TODO(Nikola): Use filesystem's `du` and move to `hio` instead?
def du(path: str, human_format: bool = False) -> Union[int, str]:
    """
    Return the size in bytes of a file or a directory (recursively).

    :param human_format: represent the size in KB, MB, ... instead of bytes
        using `hintrospection.format_size()`
    """
    hdbg.dassert_path_exists(path)
    cmd = f"du -d 0 {path}" + " | awk '{print $1}'"
    # > du -d 0 core
    # 20    core
    _, txt = system_to_one_line(cmd)
    _LOG.debug("txt=%s", txt)
    # `du` returns size in KB.
    size_in_bytes = int(txt) * 1024
    size: Union[int, str]
    if human_format:
        size = hintros.format_size(size_in_bytes)
    else:
        size = size_in_bytes
    return size


def _compute_file_signature(file_name: str, dir_depth: int) -> Optional[List]:
    """
    Compute a signature for files using basename and `dir_depth` enclosing
    dirs.

    :return: tuple of extracted enclosing dirs
        - E.g., `("core", "dataflow_model", "utils.py")`
    """
    # Split a file like:
    # /app/amp/core/test/TestCheckSameConfigs.test_check_same_configs_error/output/test.txt
    # into
    # ['', 'app', 'amp', 'core', 'test',
    #   'TestCheckSameConfigs.test_check_same_configs_error', 'output', 'test.txt']
    path = os.path.normpath(file_name)
    paths = path.split(os.sep)
    hdbg.dassert_lte(1, dir_depth)
    if dir_depth > len(paths):
        _LOG.warning(
            "Can't compute signature of file_name='%s' with"
            " dir_depth=%s, len(paths)=%s",
            file_name,
            dir_depth,
            len(paths),
        )
        signature = None
    else:
        signature = paths[-(dir_depth + 1) :]
    return signature


# TODO(gp): -> io_.py
def find_file_with_dir(
    file_name: str,
    *,
    root_dir: str = ".",
    dir_depth: int = -1,
    mode: str = "return_all_results",
    candidate_files: Optional[List[str]] = None,
) -> List[str]:
    """
    Find a file matching basename and several enclosing dir name starting from
    `root_dir`.

    E.g., find a file matching `amp/core/dataflow_model/utils.py` with `dir_depth=1`
    means looking for a file with basename 'utils.py' under a dir 'dataflow_model'.

    :param dir_depth: how many enclosing dirs in order to declare a match.
        - `-1` to use as many enclosing dirs as possible. E.g.,
          `/app/amp/core/dataflow/utils.py` will use 3 levels, since `/app` is
          removed
    :param mode: control the returned list of files, like in
        `select_result_file_from_list()`
    :param candidate_files: list of results from the `find` command for unit test
        mocking
    :return: list of files found
    """
    _LOG.debug(hprint.to_str("file_name root_dir dir_depth mode"))
    # Find all the files in the dir with the same basename.
    if candidate_files is None:
        base_name = os.path.basename(file_name)
        cmd = rf"find . -name '{base_name}' -not -path '*/\.git/*'"
        # > find . -name "utils.py"
        # ./amp/core/dataflow/utils.py
        # ./amp/core/dataflow_model/utils.py
        # ./amp/im/common/test/utils.py
        mode_ = "return_all_results"
        candidate_files = system_to_files(cmd, dir_name=root_dir, mode=mode_)
    _LOG.debug("candidate files=\n%s", "\n".join(candidate_files))
    #
    if dir_depth == -1:
        # Remove "/app" if present.
        prefix = "/app/"
        if file_name.startswith(prefix):
            file_name = file_name[len(prefix) :]
        # Remove "amp" if present.
        prefix = "amp/"
        if file_name.startswith(prefix):
            file_name = file_name[len(prefix) :]
        # Count how many dirs levels there are.
        dir_depth = len(os.path.normpath(file_name).split("/")) - 1
        _LOG.debug("inferred dir_depth=%s for file_name=%s", dir_depth, file_name)
    # Check the matching files.
    matching_files = []
    for candidate_file_name in sorted(candidate_files):
        signature1 = _compute_file_signature(candidate_file_name, dir_depth)
        signature2 = _compute_file_signature(file_name, dir_depth)
        is_equal = signature1 == signature2
        _LOG.debug("found_file=%s -> is_equal=%s", candidate_file_name, is_equal)
        if is_equal:
            matching_files.append(candidate_file_name)
    _LOG.debug(
        "Found %d files:\n%s", len(matching_files), "\n".join(matching_files)
    )
    # Select the result based on mode.
    res = select_result_file_from_list(matching_files, mode)
    _LOG.debug("-> res=%s", str(res))
    return res


# https://stackoverflow.com/questions/169070
@contextlib.contextmanager
def cd(dir_name: str) -> None:
    """
    Context manager managing changing directory.
    """
    hdbg.dassert_dir_exists(dir_name)
    current_dir = os.getcwd()
    _LOG.debug("Entering ctx manager: " + hprint.to_str("current_dir"))
    try:
        os.chdir(dir_name)
        _LOG.debug("Switched to dir '%s'", os.getcwd())
        yield
    finally:
        _LOG.debug("Switching back to dir '%s'", current_dir)
        os.chdir(current_dir)
    _LOG.debug("Exiting ctx manager")


# #############################################################################
# File timestamping.
# #############################################################################


def has_timestamp(file_name: str) -> bool:
    """
    Check whether `file_name` contains a timestamp.

    The timestamp is in the format `%Y%m%d-%H_%M_%S` (e.g.,
    20210724-12_45_51). E.g., this function for
    `experiment.RH1E.5T.20210724-12_45_51` returns True.
    """
    file_name = os.path.basename(file_name)
    # E.g., %Y%m%d-%H_%M_%S
    # The separator is _, -, or nothing.
    sep = "[-_]?"
    regex = sep.join([r"\d{4}", r"\d{2}", r"\d{2}", r"\d{2}", r"\d{2}", r"\d{2}"])
    _LOG.debug("regex=%s", regex)
    occurrences = re.findall(regex, file_name)
    hdbg.dassert_lte(
        len(occurrences), 1, "Found more than one timestamp", str(occurrences)
    )
    m = re.search("(" + regex + ")", file_name)
    has_timestamp_ = m is not None
    if has_timestamp_:
        m = cast(Match[str], m)
        _LOG.debug("Found a timestamp '%s' in '%s'", m.group(1), file_name)
    return has_timestamp_


def append_timestamp_tag(file_name: str, tag: str) -> str:
    """
    Add a tag and the current timestamp to a filename, before the extension.

    :return: new filename
    """
    dir_name = os.path.dirname(file_name)
    base_name = os.path.basename(file_name)
    name, extension = os.path.splitext(base_name)
    tag_ = ""
    # E.g., 20210723-20_52_00
    if not has_timestamp(file_name):
        import helpers.hdatetime as hdateti

        tag_ += "." + hdateti.get_current_timestamp_as_string(tz="ET")
    # Add tag, if specified.
    if tag:
        # If the tag is specified prepend a `.` in the filename.
        tag_ += "." + tag
    new_file_name = os.path.join(dir_name, "".join([name, tag_, extension]))
    _LOG.debug(hprint.to_str("file_name new_file_name"))
    return new_file_name
