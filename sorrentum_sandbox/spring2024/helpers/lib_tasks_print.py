"""
Import as:

import helpers.lib_tasks_print as hlitapri
"""

import logging
import os
import re

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hsystem as hsystem
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access

# #############################################################################
# Set-up.
# #############################################################################


@task
def print_setup(ctx):  # type: ignore
    """
    Print some configuration variables.
    """
    hlitauti.report_task()
    _ = ctx
    var_names = "CK_ECR_BASE_PATH BASE_IMAGE".split()
    for v in var_names:
        print(f"{v}={hlitauti.get_default_param(v)}")


@task
def print_tasks(ctx, as_code=False):  # type: ignore
    """
    Print all the available tasks in `lib_tasks.py`.

    These tasks might be exposed or not by different.

    :param as_code: print as python code so that it can be embed in a
        `from helpers.lib_tasks import ...`
    """
    hlitauti.report_task()
    _ = ctx
    func_names = []
    lib_tasks_file_name = os.path.join(
        hgit.get_amp_abs_path(), "helpers/lib_tasks.py"
    )
    hdbg.dassert_file_exists(lib_tasks_file_name)
    # TODO(gp): Use __file__ instead of hardwiring the file.
    cmd = rf'\grep "^@task" -A 1 {lib_tasks_file_name} | grep def'
    # def print_setup(ctx):  # type: ignore
    # def git_pull(ctx):  # type: ignore
    # def git_fetch_master(ctx):  # type: ignore
    _, txt = hsystem.system_to_string(cmd)
    for line in txt.split("\n"):
        _LOG.debug("line=%s", line)
        m = re.match(r"^def\s+(\S+)\(", line)
        if m:
            func_name = m.group(1)
            _LOG.debug("  -> %s", func_name)
            func_names.append(func_name)
    func_names = sorted(func_names)
    if as_code:
        print("\n".join([f"{fn}," for fn in func_names]))
    else:
        print("\n".join(func_names))


@task
def print_env(ctx):  # type: ignore
    """
    Print the repo configuration.
    """
    _ = ctx
    print(henv.env_to_str())


# TODO(gp):
# Print a CSV
# cat /share/data/cf_production/20221005/system_log_dir/process_forecasts/target_positions/20221005_153006.csv | column -t -s,
