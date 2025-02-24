"""
Import as:

import helpers.lib_tasks_lint as hlitalin
"""

import datetime
import logging
import os
import re
from typing import List, Optional

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.lib_tasks_docker as hlitadoc
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


# #############################################################################
# Linter.
# #############################################################################


@task
def lint_check_python_files_in_docker(  # type: ignore
    ctx,
    python_compile=True,
    python_execute=True,
    modified=False,
    branch=False,
    last_commit=False,
    all_=False,
    files="",
):
    """
    Compile and execute Python files checking for errors.

    This is supposed to be run inside Docker.

    The params have the same meaning as in `_get_files_to_process()`.
    """
    hlitauti.report_task()
    _ = ctx
    # We allow to filter through the user specified `files`.
    mutually_exclusive = False
    remove_dirs = True
    file_list = hlitauti._get_files_to_process(
        modified,
        branch,
        last_commit,
        all_,
        files,
        mutually_exclusive,
        remove_dirs,
    )
    _LOG.debug("Found %d files:\n%s", len(file_list), "\n".join(file_list))
    # Filter keeping only Python files.
    _LOG.debug("Filtering for Python files")
    exclude_paired_jupytext = True
    file_list = hio.keep_python_files(file_list, exclude_paired_jupytext)
    _LOG.debug("file_list=%s", "\n".join(file_list))
    _LOG.info("Need to process %d files", len(file_list))
    if not file_list:
        _LOG.warning("No files were selected")
    # Scan all the files.
    failed_filenames = []
    for file_name in file_list:
        _LOG.info("Processing '%s'", file_name)
        if python_compile:
            import compileall

            success = compileall.compile_file(file_name, force=True, quiet=1)
            _LOG.debug("file_name='%s' -> python_compile=%s", file_name, success)
            if not success:
                msg = f"'{file_name}' doesn't compile correctly"
                _LOG.error(msg)
                failed_filenames.append(file_name)
        # TODO(gp): Add also `python -c "import ..."`, if not equivalent to `compileall`.
        if python_execute:
            cmd = f"python {file_name}"
            rc = hsystem.system(cmd, abort_on_error=False, suppress_output=False)
            _LOG.debug("file_name='%s' -> python_compile=%s", file_name, rc)
            if rc != 0:
                msg = f"'{file_name}' doesn't execute correctly"
                _LOG.error(msg)
                failed_filenames.append(file_name)
    hprint.log_frame(
        _LOG,
        f"failed_filenames={len(failed_filenames)}",
        verbosity=logging.INFO,
    )
    _LOG.info("\n".join(failed_filenames))
    error = len(failed_filenames) > 0
    return error


@task
def lint_check_python_files(  # type: ignore
    ctx,
    python_compile=True,
    python_execute=True,
    modified=False,
    branch=False,
    last_commit=False,
    all_=False,
    files="",
):
    """
    Compile and execute Python files checking for errors.

    The params have the same meaning as in `_get_files_to_process()`.
    """
    _ = python_compile, python_execute, modified, branch, last_commit, all_, files
    # Execute the same command line but inside the container. E.g.,
    # /Users/saggese/src/venv/amp.client_venv/bin/invoke lint_docker_check_python_files --branch
    cmd_line = hdbg.get_command_line()
    # Replace the full path of invoke with just `invoke`.
    cmd_line = cmd_line.split()
    cmd_line = ["/venv/bin/invoke lint_check_python_files_in_docker"] + cmd_line[
        2:
    ]
    docker_cmd_ = " ".join(cmd_line)
    cmd = f'invoke docker_cmd --cmd="{docker_cmd_}"'
    hlitauti.run(ctx, cmd)


def _parse_linter_output(txt: str) -> str:
    """
    Parse the output of the linter and return a file suitable for vim quickfix.
    """
    stage: Optional[str] = None
    output: List[str] = []
    for i, line in enumerate(txt.split("\n")):
        _LOG.debug("%d:line='%s'", i + 1, line)
        # Tabs remover...............................................Passed
        # isort......................................................Failed
        # Don't commit to branch...............................^[[42mPassed^[[m
        m = re.search(r"^(\S.*?)\.{10,}\S+?(Passed|Failed)\S*?$", line)
        if m:
            stage = m.group(1)
            result = m.group(2)
            _LOG.debug("  -> stage='%s' (%s)", stage, result)
            continue
        # The regex only fires when the line starts with an alphabetic character.
        # In our target case the line starts with the name of the file.
        # If the line starts with a number (e.g. a timestamp in debug messages,
        # warnings, etc), there will be no match.
        # E.g.,
        # "core/dataflow/nodes.py:601:9: F821 undefined name 'a'" will be matched;
        # "17:24:53 lib_tasks.py _parse_linter_output:5244" will not be matched.
        m = re.search(r"^([a-zA-Z]\S+):(\d+)[:\d+:]\s+(.*)$", line)
        if m:
            _LOG.debug("  -> Found a lint to parse: '%s'", line)
            hdbg.dassert_is_not(stage, None)
            file_name = m.group(1)
            line_num = int(m.group(2))
            msg = m.group(3)
            _LOG.debug(
                "  -> file_name='%s' line_num=%d msg='%s'",
                file_name,
                line_num,
                msg,
            )
            output.append(f"{file_name}:{line_num}:[{stage}] {msg}")
    # Sort to keep the lints in order of files.
    output = sorted(output)
    output_as_str = "\n".join(output)
    return output_as_str


@task
def lint_detect_cycles(  # type: ignore
    ctx,
    dir_name=".",
    stage="prod",
    version="",
    out_file_name="lint_detect_cycles.output.txt",
    debug_tool=False,
):
    """
    Detect cyclic imports in the directory files.

    For param descriptions, see `lint()`.

    :param dir_name: the name of the dir to detect cyclic imports in
        - By default, the check will be carried out in the dir from where
          the task is run
    :param debug_tool: print the output of the cycle detector
    """
    hlitauti.report_task()
    # Remove the log file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        hlitauti.run(ctx, cmd)
    # Prepare the command line.
    docker_cmd_opts = [dir_name]
    if debug_tool:
        docker_cmd_opts.append("-v DEBUG")
    docker_cmd_ = (
        "/app/import_check/detect_import_cycles.py "
        + hlitauti._to_single_line_cmd(docker_cmd_opts)
    )
    # Execute command line.
    cmd = hlitadoc._get_lint_docker_cmd(docker_cmd_, stage, version)
    # Use `PIPESTATUS` otherwise the exit status of the pipe is always 0
    # because writing to a file succeeds.
    cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}; exit $PIPESTATUS"
    # Run.
    hlitauti.run(ctx, cmd)


# pylint: disable=line-too-long
@task
def lint(  # type: ignore
    ctx,
    modified=False,
    branch=False,
    last_commit=False,
    files="",
    dir_name="",
    phases="",
    only_format=False,
    only_check=False,
    fast=False,
    run_linter_step=True,
    parse_linter_output=True,
    run_entrypoint_and_bash=False,
    run_bash_without_entrypoint=False,
    # TODO(gp): These params should go earlier, since are more important.
    stage="prod",
    version="",
    out_file_name="linter_output.txt",
):
    """
    Lint files.

    ```
    # To lint all the files:
    > i lint --dir-name . --only-format

    # To lint only a repo (e.g., lime, lemonade) including `amp` but not `amp` itself:
    > i lint --files="$(find . -name '*.py' -not -path './compute/*' -not -path './amp/*')"

    # To lint dev_tools:
    > i lint --files="$(find . -name '*.py' -not -path './amp/*' -not -path './import_check/example/*' -not -path './import_check/test/outcomes/*')"
    ```

    :param modified: select the files modified in the client
    :param branch: select the files modified in the current branch
    :param last_commit: select the files modified in the previous commit
    :param files: specify a space-separated list of files
    :param dir_name: process all the files in a dir
    :param phases: specify the lint phases to execute
    :param only_format: run only the formatting phases (e.g., black)
    :param only_check: run only the checking phases (e.g., pylint, mypy) that
        don't change the code
    :param fast: run everything but skip `pylint`, since it is often very picky
        and slow
    :param run_linter_step: run linter step
    :param parse_linter_output: parse linter output and generate vim cfile
    :param run_entrypoint_and_bash: run the entrypoint of the container (which
        configures the environment) and then `bash`, instead of running the
        lint command
    :param run_bash_without_entrypoint: run bash, skipping the entrypoint
        TODO(gp): This seems to work but have some problems with tty
    :param stage: the image stage to use
    :param out_file_name: name of the file to save the log output in
    """
    hlitauti.report_task()
    # Remove the file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        hlitauti.run(ctx, cmd)
    # The available phases are:
    # ```
    # > i lint -f "foobar.py"
    # Don't commit to branch...............................................Passed
    # Check for merge conflicts........................(no files to check)Skipped
    # Trim Trailing Whitespace.........................(no files to check)Skipped
    # Fix End of Files.................................(no files to check)Skipped
    # Check for added large files......................(no files to check)Skipped
    # CRLF end-lines remover...........................(no files to check)Skipped
    # Tabs remover.....................................(no files to check)Skipped
    # autoflake........................................(no files to check)Skipped
    # add_python_init_files............................(no files to check)Skipped
    # amp_lint_md......................................(no files to check)Skipped
    # amp_doc_formatter................................(no files to check)Skipped
    # amp_isort........................................(no files to check)Skipped
    # amp_class_method_order...........................(no files to check)Skipped
    # amp_normalize_import.............................(no files to check)Skipped
    # amp_format_separating_line.......................(no files to check)Skipped
    # amp_black........................................(no files to check)Skipped
    # amp_processjupytext..............................(no files to check)Skipped
    # amp_check_filename...............................(no files to check)Skipped
    # amp_warn_incorrectly_formatted_todo..............(no files to check)Skipped
    # amp_flake8.......................................(no files to check)Skipped
    # amp_pylint.......................................(no files to check)Skipped
    # amp_mypy.........................................(no files to check)Skipped
    # ```
    if run_bash_without_entrypoint:
        # Run bash, without the Docker entrypoint.
        docker_cmd_ = "bash"
        cmd = hlitadoc._get_lint_docker_cmd(
            docker_cmd_, stage, version, entrypoint=False
        )
        cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
        # Run.
        hlitauti.run(ctx, cmd)
        return
    if run_entrypoint_and_bash:
        # Run the Docker entrypoint (which configures the environment) and then bash.
        docker_cmd_ = "bash"
        cmd = hlitadoc._get_lint_docker_cmd(docker_cmd_, stage, version)
        cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
        # Run.
        hlitauti.run(ctx, cmd)
        return
    if only_format:
        hdbg.dassert_eq(phases, "")
        phases = " ".join(
            [
                "add_python_init_files",
                "amp_isort",
                "amp_class_method_order",
                "amp_normalize_import",
                "amp_format_separating_line",
                "amp_black",
                "amp_processjupytext",
                "amp_remove_eof_newlines",
            ]
        )
    if only_check:
        hdbg.dassert_eq(phases, "")
        phases = " ".join(
            [
                "amp_pylint",
                "amp_mypy",
            ]
        )
    if run_linter_step:
        # We don't want to run this all the times.
        # docker_pull(ctx, stage=stage, images="dev_tools")
        # Get the files to lint.
        # TODO(gp): For now we don't support linting the entire tree.
        all_ = False
        if dir_name != "":
            hdbg.dassert_eq(files, "")
            pattern = "*.py"
            only_files = True
            use_relative_paths = False
            files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
            files = " ".join(files)
        # For linting we can use only files modified in the client, in the branch, or
        # specified.
        mutually_exclusive = True
        # pre-commit doesn't handle directories, but only files.
        remove_dirs = True
        files_as_list = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files,
            mutually_exclusive,
            remove_dirs,
        )
        _LOG.info("Files to lint:\n%s", "\n".join(files_as_list))
        if not files_as_list:
            _LOG.warning("Nothing to lint: exiting")
            return
        files_as_str = " ".join(files_as_list)
        phases = phases.split(" ")
        for phase in phases:
            # Prepare the command line.
            precommit_opts = []
            precommit_opts.extend(
                [
                    f"run {phase}",
                    "-c /app/.pre-commit-config.yaml",
                    f"--files {files_as_str}",
                ]
            )
            docker_cmd_ = "pre-commit " + hlitauti._to_single_line_cmd(
                precommit_opts
            )
            if fast:
                docker_cmd_ = "SKIP=amp_pylint " + docker_cmd_
            cmd = hlitadoc._get_lint_docker_cmd(docker_cmd_, stage, version)
            cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
            # Run.
            hlitauti.run(ctx, cmd)
    else:
        _LOG.warning("Skipping linter step, as per user request")
    #
    if parse_linter_output:
        # Parse the linter output into a cfile.
        _LOG.info("Parsing '%s'", out_file_name)
        txt = hio.from_file(out_file_name)
        cfile = _parse_linter_output(txt)
        cfile_name = "./linter_warnings.txt"
        hio.to_file(cfile_name, cfile)
        _LOG.info("Saved cfile in '%s'", cfile_name)
        print(cfile)
    else:
        _LOG.warning("Skipping lint parsing, as per user request")


@task
def lint_check_if_it_was_run(ctx):
    """
    Check if the linter was run in the current branch.

    - abort the task with error if the files were modified
    """
    hlitauti.report_task()
    # Check if the files were modified.
    hgit.is_client_clean(abort_if_not_clean=True)


@task
def lint_create_branch(ctx, dry_run=False):  # type: ignore
    """
    Create the branch for linting in the current dir.

    The dir needs to be specified to ensure the set-up is correct.
    """
    hlitauti.report_task()
    #
    date = datetime.datetime.now().date()
    date_as_str = date.strftime("%Y%m%d")
    branch_name = f"AmpTask1955_Lint_{date_as_str}"
    # query_yes_no("Are you sure you want to create the branch '{branch_name}'")
    _LOG.info("Creating branch '%s'", branch_name)
    cmd = f"invoke git_branch_create -b '{branch_name}'"
    hlitauti.run(ctx, cmd, dry_run=dry_run)
