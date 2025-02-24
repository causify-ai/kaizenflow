"""
Import as:

import helpers.lib_tasks_pytest as hlitapyt
"""

import json
import logging
import os
import re
import sys
from typing import Any, List, Optional

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hlist as hlist
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.htraceback as htraceb
import helpers.lib_tasks_docker as hlitadoc
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


# #############################################################################
# Run tests.
# #############################################################################


_COV_PYTEST_OPTS = [
    # Only compute coverage for current project and not venv libraries.
    "--cov=.",
    "--cov-branch",
    # Report the missing lines.
    # Name                 Stmts   Miss  Cover   Missing
    # -------------------------------------------------------------------------
    # myproj/__init__          2      0   100%
    # myproj/myproj          257     13    94%   24-26, 99, 149, 233-236, 297-298
    "--cov-report term-missing",
    # Report data in the directory `htmlcov`.
    "--cov-report html",
    # "--cov-report annotate",
]


_TEST_TIMEOUTS_IN_SECS = {
    "fast_tests": 5,
    "slow_tests": 30,
    "superslow_tests": 60 * 60,
}


_NUM_TIMEOUT_TEST_RERUNS = {
    "fast_tests": 2,
    "slow_tests": 1,
    "superslow_tests": 1,
}


@task
def run_blank_tests(ctx, stage="dev", version=""):  # type: ignore
    """
    (ONLY CI/CD) Test that pytest in the container works.
    """
    hlitauti.report_task()
    _ = ctx
    base_image = ""
    cmd = '"pytest -h >/dev/null"'
    docker_cmd_ = hlitadoc._get_docker_compose_cmd(
        base_image, stage, version, cmd
    )
    hsystem.system(docker_cmd_, abort_on_error=False, suppress_output=False)


def _select_tests_to_skip(test_list_name: str) -> str:
    """
    Generate text for pytest specifying which tests to deselect.
    """
    if test_list_name == "fast_tests":
        skipped_tests = "not slow and not superslow"
    elif test_list_name == "slow_tests":
        skipped_tests = "slow and not superslow"
    elif test_list_name == "superslow_tests":
        skipped_tests = "not slow and superslow"
    else:
        raise ValueError(f"Invalid `test_list_name`={test_list_name}")
    return skipped_tests


def _build_run_command_line(
    test_list_name: str,
    custom_marker: str,
    pytest_opts: str,
    skip_submodules: bool,
    coverage: bool,
    collect_only: bool,
    tee_to_file: bool,
    n_threads: str,
    *,
    allure_dir: Optional[str] = None,
) -> str:
    """
    Build the pytest run command.

    E.g.,

    ```
    pytest -m "optimizer and not slow and not superslow" \
                . \
                -o timeout_func_only=true \
                --timeout 5 \
                --reruns 2 \
                --only-rerun "Failed: Timeout"
    ```

    The rest of params are the same as in `run_fast_tests()`.

    The invariant is that we don't want to duplicate pytest options that can be
    passed by the user through `-p` (unless really necessary).

    :param test_list_name: "fast_tests", "slow_tests" or
        "superslow_tests"
    :param custom_marker: specify a space separated list of
        `pytest` markers to skip (e.g., `optimizer` for the optimizer
        tests, see `pytest.ini`). Empty means no marker to skip
    :param allure_dir: directory to save allure results to. If specified, allure
        plugin will be installed on-the-fly and results will be generated
        and saved to the specified directory
    """
    hdbg.dassert_in(
        test_list_name, _TEST_TIMEOUTS_IN_SECS, "Invalid test_list_name"
    )
    pytest_opts = pytest_opts or "."
    pytest_opts_tmp = []
    # Select tests to skip based on the `test_list_name` (e.g., fast tests)
    # and on the custom marker, if present.
    skipped_tests = _select_tests_to_skip(test_list_name)
    timeout_in_sec = _TEST_TIMEOUTS_IN_SECS[test_list_name]
    # Detect if we are running on a CK dev server / inside CI
    # or a laptop outside the CK infra.
    is_outside_ck_infra = not hserver.is_dev_ck() and not hserver.is_inside_ci()
    if is_outside_ck_infra:
        timeout_multiplier = 10
        _LOG.warning(
            f"Tests are running outside the CK server and CI, timeout increased {timeout_multiplier} times."
        )
        # Since we are running outside the CK server we increase the duration
        # of the timeout, since the thresholds are set for the CK server.
        timeout_in_sec *= timeout_multiplier
    if custom_marker != "":
        pytest_opts_tmp.append(f'-m "{custom_marker} and {skipped_tests}"')
    else:
        pytest_opts_tmp.append(f'-m "{skipped_tests}"')
    if pytest_opts:
        pytest_opts_tmp.append(pytest_opts)
    # Adding `timeout_func_only` is a workaround for
    # https://github.com/pytest-dev/pytest-rerunfailures/issues/99. Because of
    # it, we limit only run time, without setup and teardown time.
    pytest_opts_tmp.append("-o timeout_func_only=true")
    pytest_opts_tmp.append(f"--timeout {timeout_in_sec}")
    num_reruns = _NUM_TIMEOUT_TEST_RERUNS[test_list_name]
    pytest_opts_tmp.append(
        f'--reruns {num_reruns} --only-rerun "Failed: Timeout"'
    )
    if henv.execute_repo_config_code("skip_submodules_test()"):
        # For some repos (e.g. `dev_tools`) submodules should be skipped
        # regardless of the passed value.
        skip_submodules = True
    if skip_submodules:
        submodule_paths = hgit.get_submodule_paths()
        _LOG.warning(
            "Skipping %d submodules: %s", len(submodule_paths), submodule_paths
        )
        pytest_opts_tmp.append(
            " ".join([f"--ignore {path}" for path in submodule_paths])
        )
    if coverage:
        pytest_opts_tmp.append(" ".join(_COV_PYTEST_OPTS))
    if collect_only:
        _LOG.warning("Only collecting tests as per user request")
        pytest_opts_tmp.append("--collect-only")
    # Indicate the number of threads for parallelization.
    if n_threads != "serial":
        pytest_opts_tmp.append(f"-n {str(n_threads)}")
    if allure_dir is not None:
        pytest_opts_tmp.append(f"--alluredir={allure_dir}")
    # Concatenate the options.
    _LOG.debug("pytest_opts_tmp=\n%s", str(pytest_opts_tmp))
    pytest_opts_tmp = [po for po in pytest_opts_tmp if po != ""]
    # TODO(gp): Use to_multi_line_cmd()
    pytest_opts = " ".join([po.rstrip().lstrip() for po in pytest_opts_tmp])
    cmd = f"pytest {pytest_opts}"
    if allure_dir is not None:
        # Install the `allure-pytest` before running the tests. This is needed
        # to generate Allure results which serve as an input for generating
        # Allure HTML reports.
        # Excluding the command `"source /venv/bin/activate"` because post-activation,
        # the `PATH` variable lacks necessary values, causing a failure in a test
        # associated with `publish_notebook.py`.
        cmd = f"sudo /venv/bin/pip install allure-pytest && {cmd}"
    if tee_to_file:
        cmd += f" 2>&1 | tee tmp.pytest.{test_list_name}.log"
    return cmd


def _run_test_cmd(
    ctx: Any,
    stage: str,
    version: str,
    cmd: str,
    coverage: bool,
    collect_only: bool,
    start_coverage_script: bool,
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    """
    See params in `run_fast_tests()`.
    """
    if collect_only:
        # Clean files.
        hlitauti.run(ctx, "rm -rf ./.coverage*")
    # Run.
    base_image = ""
    # We need to add some " to pass the string as it is to the container.
    cmd = f"'{cmd}'"
    # We use "host" for the app container to allow access to the database
    # exposing port 5432 on localhost (of the server), when running dind we
    # need to switch back to bridge. See CmTask988.
    extra_env_vars = ["NETWORK_MODE=bridge"]
    docker_cmd_ = hlitadoc._get_docker_compose_cmd(
        base_image, stage, version, cmd, extra_env_vars=extra_env_vars
    )
    _LOG.info("cmd=%s", docker_cmd_)
    # We can't use `hsystem.system()` because of buffering of the output,
    # losing formatting and so on, so we stick to executing through `ctx`.
    rc: Optional[int] = hlitadoc._docker_cmd(ctx, docker_cmd_, **ctx_run_kwargs)
    # Print message about coverage.
    if coverage:
        msg = """
- The coverage results in textual form are above

- To browse the files annotate with coverage, start a server (not from the
  container):
  > (cd ./htmlcov; python -m http.server 33333)
- Then go with your browser to `localhost:33333` to see which code is
  covered
"""
        print(msg)
        if start_coverage_script:
            # Create and run a script to show the coverage in the browser.
            script_txt = """(sleep 2; open http://localhost:33333) &
(cd ./htmlcov; python -m http.server 33333)"""
            script_name = "./tmp.coverage.sh"
            hio.create_executable_script(script_name, script_txt)
            coverage_rc = hsystem.system(script_name)
            if coverage_rc != 0:
                _LOG.warning(
                    "Setting `rc` to `0` even though the coverage script fails."
                )
                rc = 0
    return rc


def _run_tests(
    ctx: Any,
    test_list_name: str,
    stage: str,
    version: str,
    custom_marker: str,
    pytest_opts: str,
    skip_submodules: bool,
    coverage: bool,
    collect_only: bool,
    tee_to_file: bool,
    n_threads: str,
    git_clean_: bool,
    *,
    start_coverage_script: bool = False,
    allure_dir: Optional[str] = None,
    # TODO(Grisha): do we need to expose ctx kwargs to the invoke targets?
    # E.g., to `run_fast_tests`. See CmTask3602 "All tests fail".
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    """
    See params in `run_fast_tests()`.
    """
    if git_clean_:
        cmd = "invoke git_clean --fix-perms"
        hlitauti.run(ctx, cmd)
    # Build the command line.
    cmd = _build_run_command_line(
        test_list_name,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        allure_dir=allure_dir,
    )
    # Execute the command line.
    rc = _run_test_cmd(
        ctx,
        stage,
        version,
        cmd,
        coverage,
        collect_only,
        start_coverage_script,
        **ctx_run_kwargs,
    )
    return rc


# TODO(Grisha): "Unit tests run_*_tests invokes" CmTask #1652.
@task
def run_tests(  # type: ignore
    ctx,
    test_lists,
    abort_on_first_error=False,
    stage="dev",
    version="",
    custom_marker="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
    **kwargs,
):
    """
    :param test_lists: comma separated list with test lists to run (e.g., `fast_test,slow_tests`)
    :param abort_on_first_error: stop after the first test list failing
    """
    results = []
    for test_list_name in test_lists.split(","):
        rc = _run_tests(
            ctx,
            test_list_name,
            stage,
            version,
            custom_marker,
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
            n_threads,
            git_clean_,
            warn=True,
            allure_dir=allure_dir,
            **kwargs,
        )
        if rc != 0:
            _LOG.error("'%s' tests failed", test_list_name)
            if abort_on_first_error:
                sys.exit(-1)
        results.append((test_list_name, rc))
    #
    rc = any(result[1] for result in results)
    # Summarize the results.
    _LOG.info("# Tests run summary:")
    for test_list_name, rc in results:
        if rc != 0:
            _LOG.error("'%s' tests failed", test_list_name)
        else:
            _LOG.info("'%s' tests succeeded", test_list_name)
    return rc


def _get_custom_marker(
    *,
    run_only_test_list: str = "",
    skip_test_list: str = "",
) -> str:
    """
    Get a custom pytest marker from comma-separated string representations of
    test lists to run or skip.

    :param run_only_test_list: a string of comma-separated markers to
        run, e.g. `run_only_test_list =
        "requires_ck_infra,requires_aws"`
    :param skip_test_list: a string of comma-separated markers to skip
    :return: custom pytest marker
    """
    # If we are running outside the CK server / CI, tests requiring CK infra
    # should be automatically skipped.
    is_outside_ck_infra = not hserver.is_dev_ck() and not hserver.is_inside_ci()
    # Skip tests that requires CK infra.
    if is_outside_ck_infra:
        _LOG.warning(
            "Skipping the tests that require CK "
            "infra when running outside the CK server / CI."
        )
        if skip_test_list:
            skip_test_list = "requires_ck_infra," + skip_test_list
        else:
            skip_test_list = "requires_ck_infra"
    # Convert string representations of lists to actual lists.
    if run_only_test_list:
        # This works as expected when there is a single test in the list.
        run_only_test_list_items = run_only_test_list.split(",")
        _LOG.warning("Running only tests inside %s.", run_only_test_list_items)
    else:
        run_only_test_list_items = []
    if skip_test_list:
        # This works as expected when there is a single test in the list.
        skip_test_list_items = skip_test_list.split(",")
        _LOG.warning("Skipping the tests inside %s.", skip_test_list_items)
    else:
        # The list can be empty when running inside CK infra.
        skip_test_list_items = []
    # Convert marker strings for `pytest -m` using `and` and `not`.
    run_only_marker_string = " and ".join(run_only_test_list_items)
    skip_marker_string = " and ".join(
        [("not " + item) for item in skip_test_list_items]
    )
    if run_only_marker_string:
        if skip_marker_string:
            custom_marker = run_only_marker_string + " and " + skip_marker_string
        else:
            custom_marker = run_only_marker_string
    else:
        custom_marker = skip_marker_string
    return custom_marker


# TODO(gp): Pass a test_list in fast, slow, ... instead of duplicating all the code CmTask #1571.
@task
def run_fast_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    run_only_test_list="",
    skip_test_list="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
):
    """
    Run fast tests. check `gh auth status` before invoking to avoid auth
    errors.

    :param stage: select a specific stage for the Docker image
    :param pytest_opts: additional options for `pytest` invocation. It can be empty
    :param run_only_test_list: select markers to run. Takes comma-separated tokens,
           e.g. `--run_only_test_list = requires_ck_infra,requires_aws`
    :param skip_test_list: select markers to skip. Takes comma-separated tokens.
    :param skip_submodules: ignore all the dir inside a submodule
    :param coverage: enable coverage computation
    :param collect_only: do not run tests but show what will be executed
    :param tee_to_file: save output of pytest in `tmp.pytest.log`
    :param n_threads: the number of threads to run the tests with
        - "auto": distribute the tests across all the available CPUs
    :param git_clean_: run `invoke git_clean --fix-perms` before running the tests
    :param allure_dir: directory to save allure results to. If specified, allure
        plugin will be installed on-the-fly and results will be generated
        and saved to the specified directory
    :param kwargs: kwargs for `ctx.run`
    """
    hlitauti.report_task()
    hdbg.dassert(
        not (run_only_test_list and skip_test_list),
        "You can't specify both --run_only_test_list and --skip_test_list",
    )
    test_list_name = "fast_tests"
    # Convert cmd line marker lists to a pytest marker list.
    custom_marker = _get_custom_marker(
        run_only_test_list=run_only_test_list, skip_test_list=skip_test_list
    )
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        allure_dir=allure_dir,
    )
    return rc


@task
def run_slow_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    run_only_test_list="",
    skip_test_list="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
):
    """
    Run slow tests.

    Same params as `invoke run_fast_tests`.
    """
    hlitauti.report_task()
    test_list_name = "slow_tests"
    # Convert cmd line marker lists to a pytest marker list.
    custom_marker = _get_custom_marker(
        run_only_test_list=run_only_test_list, skip_test_list=skip_test_list
    )
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        allure_dir=allure_dir,
    )
    return rc


@task
def run_superslow_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    run_only_test_list="",
    skip_test_list="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
):
    """
    Run superslow tests.

    Same params as `invoke run_fast_tests`.
    """
    hlitauti.report_task()
    test_list_name = "superslow_tests"
    # Convert cmd line marker lists to a pytest marker list.
    custom_marker = _get_custom_marker(
        run_only_test_list=run_only_test_list, skip_test_list=skip_test_list
    )
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        allure_dir=allure_dir,
    )
    return rc


@task
def run_fast_slow_tests(  # type: ignore
    ctx,
    abort_on_first_error=False,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
):
    """
    Run fast and slow tests back-to-back.

    Same params as `invoke run_fast_tests`.
    """
    hlitauti.report_task()
    # Run fast tests but do not fail on error.
    test_lists = "fast_tests,slow_tests"
    custom_marker = ""
    rc = run_tests(
        ctx,
        test_lists,
        abort_on_first_error,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        allure_dir,
    )
    return rc


@task
def run_fast_slow_superslow_tests(  # type: ignore
    ctx,
    abort_on_first_error=False,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="serial",
    git_clean_=False,
    allure_dir=None,
):
    """
    Run fast, slow, superslow tests back-to-back.

    Same params as `invoke run_fast_tests`.
    """
    hlitauti.report_task()
    # Run fast tests but do not fail on error.
    test_lists = "fast_tests,slow_tests,superslow_tests"
    custom_marker = ""
    rc = run_tests(
        ctx,
        test_lists,
        abort_on_first_error,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        allure_dir,
    )
    return rc


@task
def run_qa_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
):
    """
    Run QA tests independently.

    :param version: version to tag the image and code with
    :param stage: select a specific stage for the Docker image
    """
    hlitauti.report_task()
    #
    qa_test_fn = hlitauti.get_default_param("QA_TEST_FUNCTION")
    # Run the call back function.
    rc = qa_test_fn(ctx, stage, version)
    if not rc:
        msg = "QA tests failed"
        _LOG.error(msg)
        raise RuntimeError(msg)


# #############################################################################
# Coverage report
# #############################################################################


def _publish_html_coverage_report_on_s3(aws_profile: str) -> None:
    """
    Publish HTML coverage report on S3 so that it can be accessed via browser.

    Target S3 dir is constructed from linux user and Git branch name, e.g.
    `s3://...-html/html_coverage/grisha_CmTask1047_fix_tests`.
    """
    # Build the dir name from user and branch name.
    user = hsystem.get_user_name()
    branch_name = hgit.get_branch_name()
    _LOG.debug("User='%s', branch_name='%s'", user, branch_name)
    s3_html_coverage_dir = f"{user}_{branch_name}"
    # Get the full path to the dir.
    s3_html_base_dir = "html_coverage"
    s3_html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    s3_html_coverage_path = os.path.join(
        s3_html_bucket_path, s3_html_base_dir, s3_html_coverage_dir
    )
    # Copy HTML coverage data from the local dir to S3.
    local_coverage_path = "./htmlcov"
    # TODO(Nikola): Revert to `s3fs_.put` after `s3fs` is updated to latest
    # version.
    #   See CmTask #2400.
    use_aws_copy = True
    if use_aws_copy:
        sudo_prefix = ""
        if hserver.is_inside_ci():
            # There is no AWS config in GH action, thus create default one from
            # chosen profile. To bypass permission errors, `sudo` is used.
            sudo_prefix = "sudo "
            aws_set_param_cmd = "sudo aws configure set"
            aws_set_profile_cmd = f"--profile {aws_profile}"
            aws_set_value_pairs = [
                f"aws_access_key_id ${aws_profile.upper()}_AWS_ACCESS_KEY_ID",
                f"aws_secret_access_key ${aws_profile.upper()}_AWS_SECRET_ACCESS_KEY",
                f"region ${aws_profile.upper()}_AWS_DEFAULT_REGION",
            ]
            aws_config_cmds = [
                f"{aws_set_param_cmd} {aws_set_value_pair} {aws_set_profile_cmd}"
                for aws_set_value_pair in aws_set_value_pairs
            ]
            aws_config_pipe_cmd = " && ".join(aws_config_cmds)
            hsystem.system(aws_config_pipe_cmd)
        cp_cmd = (
            f"{sudo_prefix}aws s3 cp {local_coverage_path} {s3_html_coverage_path} "
            f"--recursive --profile {aws_profile}"
        )
        hsystem.system(cp_cmd)
    else:
        # Use `s3fs` to copy data to AWS S3.
        s3fs_ = hs3.get_s3fs(aws_profile)
        s3fs_.put(local_coverage_path, s3_html_coverage_path, recursive=True)
    _LOG.info(
        "HTML coverage report is published on S3: path=`%s`",
        s3_html_coverage_path,
    )


@task
def run_coverage_report(  # type: ignore
    ctx,
    target_dir,
    generate_html_report=True,
    publish_html_on_s3=True,
    aws_profile="ck",
):
    """
    Compute test coverage stats.

    The flow is:
       - Run tests and compute coverage stats for each test type
       - Combine coverage stats in a single file
       - Generate a text report
       - Generate a HTML report (optional)
          - Post it on S3 (optional)

    :param target_dir: directory to compute coverage stats for
        - "." for all the dirs in the current working directory
    :param generate_html_report: whether to generate HTML coverage report or not
    :param publish_html_on_s3: whether to publish HTML coverage report or not
    :param aws_profile: the AWS profile to use for publishing HTML report
    """
    # TODO(Grisha): allow user to specify which tests to run.
    # Run fast tests for the target dir and collect coverage results.
    fast_tests_cmd = f"invoke run_fast_tests --coverage -p {target_dir}"
    hlitauti.run(ctx, fast_tests_cmd, use_system=False)
    fast_tests_coverage_file = ".coverage_fast_tests"
    create_fast_tests_file_cmd = f"mv .coverage {fast_tests_coverage_file}"
    hsystem.system(create_fast_tests_file_cmd)
    # Run slow tests for the target dir and collect coverage results.
    slow_tests_cmd = f"invoke run_slow_tests --coverage -p {target_dir}"
    hlitauti.run(ctx, slow_tests_cmd, use_system=False)
    slow_tests_coverage_file = ".coverage_slow_tests"
    create_slow_tests_file_cmd = f"mv .coverage {slow_tests_coverage_file}"
    hsystem.system(create_slow_tests_file_cmd)
    # Check that coverage files are present for both fast and slow tests.
    hdbg.dassert_file_exists(fast_tests_coverage_file)
    hdbg.dassert_file_exists(slow_tests_coverage_file)
    #
    report_cmd: List[str] = []
    # Clean the previous coverage results. For some docker-specific reasons
    # command which combines stats does not work when being run first in
    # the chain `bash -c "cmd1 && cmd2 && cmd3"`. So `erase` command which
    # does not affect the coverage results was added as a workaround.
    report_cmd.append("coverage erase")
    # Merge stats for fast and slow tests into single dir.
    report_cmd.append(
        f"coverage combine --keep {fast_tests_coverage_file} {slow_tests_coverage_file}"
    )
    # Specify the dirs to include and exclude in the report.
    exclude_from_report = None
    if target_dir == ".":
        # Include all dirs.
        include_in_report = "*"
        if henv.execute_repo_config_code("skip_submodules_test()"):
            # Exclude submodules.
            submodule_paths = hgit.get_submodule_paths()
            exclude_from_report = ",".join(
                path + "/*" for path in submodule_paths
            )
    else:
        # Include only the target dir.
        include_in_report = f"*/{target_dir}/*"
    # Generate text report with the coverage stats.
    report_stats_cmd = (
        f"coverage report --include={include_in_report} --sort=Cover"
    )
    if exclude_from_report is not None:
        report_stats_cmd += f" --omit={exclude_from_report}"
    report_cmd.append(report_stats_cmd)
    if generate_html_report:
        # Generate HTML report with the coverage stats.
        report_html_cmd = f"coverage html --include={include_in_report}"
        if exclude_from_report is not None:
            report_html_cmd += f" --omit={exclude_from_report}"
        report_cmd.append(report_html_cmd)
    # Execute commands above one-by-one inside docker. Coverage tool is not
    # installed outside docker.
    full_report_cmd = " && ".join(report_cmd)
    docker_cmd_ = f"invoke docker_cmd --use-bash --cmd '{full_report_cmd}'"
    hlitauti.run(ctx, docker_cmd_)
    if publish_html_on_s3:
        # Publish HTML report on S3.
        _publish_html_coverage_report_on_s3(aws_profile)


# #############################################################################
# Traceback.
# #############################################################################


# TODO(gp): Consolidate the code from dev_scripts/testing here.


@task
def traceback(ctx, log_name="tmp.pytest_script.txt", purify=True):  # type: ignore
    """
    Parse the traceback from Pytest and navigate it with vim.

    ```
    # Run a unit test.
    > pytest helpers/test/test_traceback.py 2>&1 | tee tmp.pytest.log
    > pytest.sh helpers/test/test_traceback.py
    # Parse the traceback
    > invoke traceback -i tmp.pytest.log
    ```

    :param log_name: the file with the traceback
    :param purify: purify the filenames from client (e.g., from running inside Docker)
    """
    hlitauti.report_task()
    #
    dst_cfile = "cfile"
    hio.delete_file(dst_cfile)
    # Convert the traceback into a cfile.
    cmd = []
    cmd.append("traceback_to_cfile.py")
    if log_name:
        cmd.append(f"-i {log_name}")
    cmd.append(f"-o {dst_cfile}")
    # Purify the file names.
    if purify:
        cmd.append("--purify_from_client")
    else:
        cmd.append("--no_purify_from_client")
    cmd = " ".join(cmd)
    hlitauti.run(ctx, cmd)
    # Read and navigate the cfile with vim.
    if os.path.exists(dst_cfile):
        cmd = 'vim -c "cfile cfile"'
        hlitauti.run(ctx, cmd, pty=True)
    else:
        _LOG.warning("Can't find %s", dst_cfile)


# #############################################################################
# pytest_clean
# #############################################################################


@task
def pytest_clean(ctx):  # type: ignore
    """
    Clean pytest artifacts.
    """
    hlitauti.report_task()
    _ = ctx
    import helpers.hpytest as hpytest

    hpytest.pytest_clean(".")


# #############################################################################
# pytest_repro
# #############################################################################


def _get_failed_tests_from_file(file_name: str) -> List[str]:
    hdbg.dassert_file_exists(file_name)
    txt = hio.from_file(file_name)
    if file_name.endswith("/cache/lastfailed"):
        # Decode the json-style string.
        # {
        # "vendors/test/test_vendors.py::Test_gp::test1": true,
        # "vendors/test/test_vendors.py::Test_kibot_utils1::...": true,
        # }
        vals = json.loads(txt)
        hdbg.dassert_isinstance(vals, dict)
        tests = [k for k, v in vals.items() if v]
    else:
        # Extract failed tests from the regular text output.
        tests = re.findall(r"FAILED (\S+\.py::\S+::\S+)\b", txt)
    return tests


@task
def pytest_repro(  # type: ignore
    ctx,
    mode="tests",
    file_name="./.pytest_cache/v/cache/lastfailed",
    show_stacktrace=False,
    create_script=True,
    script_name="./tmp.pytest_repro.sh",
):
    """
    Generate commands to reproduce the failed tests after a `pytest` run.

    The workflow is:
    ```
    # Run a lot of tests, e.g., the entire regression suite.
    server> i run_fast_slow_tests 2>&1 | log pytest.txt
    docker> pytest ... 2>&1 | log pytest.txt

    # Run the `pytest_repro` to summarize test failures and to generate
    # commands to reproduce them.
    server> i pytest_repro
    ```

    :param mode: the granularity level for generating the commands
        - "tests" (default): failed test methods, e.g.,
            ```
            pytest helpers/test/test_cache.py::TestCachingOnS3::test_with_caching1
            pytest helpers/test/test_cache.py::TestCachingOnS3::test_with_caching2
            ```
        - "classes": classes of the failed tests, e.g.,
            ```
            pytest helpers/test/test_cache.py::TestCachingOnS3
            pytest helpers/test/test_cache.py::TestCachingOnS3_2
            ```
        - "files": files with the failed tests, e.g.,
            ```
            pytest helpers/test/test_cache.py
            pytest helpers/test/test_lib_tasks.py
            ```
    :param file_name: the name of the file containing the pytest output file to parse
    :param show_stacktrace: whether to show the stacktrace of the failed tests
      - only if it is available in the pytest output file
    :param create_script: create a script to run the tests
    :return: commands to reproduce pytest failures at the requested granularity level
    """
    hlitauti.report_task()
    _ = ctx
    # Read file.
    _LOG.info("Reading file_name='%s'", file_name)
    hdbg.dassert_file_exists(file_name)
    _LOG.info("Reading failed tests from file '%s'", file_name)
    # E.g., vendors/test/test_vendors.py::Test_gp::test1
    tests = _get_failed_tests_from_file(file_name)
    if len(tests) == 0:
        _LOG.info("Found 0 failed tests")
        return ""
    _LOG.debug("tests=%s", str(tests))
    # Process the tests.
    targets = []
    for test in tests:
        data = test.split("::")
        hdbg.dassert_lte(len(data), 3, "Can't parse '%s'", test)
        # E.g., dev_scripts/testing/test/test_run_tests.py
        # E.g., helpers/test/helpers/test/test_list.py::Test_list_1
        # E.g., core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5
        test_file_name = test_class = test_method = ""
        if len(data) >= 1:
            test_file_name = data[0]
        if len(data) >= 2:
            test_class = data[1]
        if len(data) >= 3:
            test_method = data[2]
        _LOG.debug(
            "test=%s -> (%s, %s, %s)",
            test,
            test_file_name,
            test_class,
            test_method,
        )
        if mode == "tests":
            targets.append(test)
        elif mode == "files":
            if test_file_name != "":
                targets.append(test_file_name)
            else:
                _LOG.warning(
                    "Skipping test='%s' since test_file_name='%s'",
                    test,
                    test_file_name,
                )
        elif mode == "classes":
            if test_file_name != "" and test_class != "":
                targets.append(f"{test_file_name}::{test_class}")
            else:
                _LOG.warning(
                    "Skipping test='%s' since test_file_name='%s', test_class='%s'",
                    test,
                    test_file_name,
                    test_class,
                )
        else:
            hdbg.dfatal(f"Invalid mode='{mode}'")
    # Package the output.
    # targets is a list of tests in the format
    # `helpers/test/test_env.py::Test_env1::test_get_system_signature1`.
    hdbg.dassert_isinstance(targets, list)
    targets = hlist.remove_duplicates(targets)
    targets = sorted(targets)
    failed_test_output_str = (
        f"Found {len(targets)} failed pytest '{mode}' target(s); "
        "to reproduce run:\n"
    )
    res = [f"pytest {t}" for t in targets]
    res = "\n".join(res)
    failed_test_output_str += res
    #
    if show_stacktrace:
        # Get the stacktrace block from the pytest output.
        txt = hio.from_file(file_name)
        if (
            "====== FAILURES ======" in txt
            and "====== slowest 3 durations ======" in txt
        ):
            failures_blocks = txt.split("====== FAILURES ======")[1:]
            failures_blocks = [
                x.split("====== slowest 3 durations ======")[0]
                for x in failures_blocks
            ]
            txt = "\n".join([x.rstrip("=").lstrip("=") for x in failures_blocks])
            # Get the classes and names of the failed tests, e.g.
            # "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5" ->
            # -> "TestSmaModel.test5".
            failed_test_names = [
                test.split("::")[1] + "." + test.split("::")[2] for test in tests
            ]
            tracebacks = []
            for name in failed_test_names:
                # Get the stacktrace for the individual test failure.
                # Its start is marked with the name of the test, e.g.
                # "___________________ TestSmaModel.test5 ___________________".
                start_block = "__ " + name + " __"
                traceback_block = txt.rsplit(start_block, maxsplit=1)[-1]
                end_block_options = [
                    "__ " + n + " __" for n in failed_test_names if n != name
                ]
                for end_block in end_block_options:
                    # The end of the traceback for the current failed test is the
                    # start of the traceback for the next failed test.
                    if end_block in traceback_block:
                        traceback_block = traceback_block.split(end_block)[0]
                _, traceback_ = htraceb.parse_traceback(
                    traceback_block, purify_from_client=False
                )
                tracebacks.append(
                    "\n".join(["# " + name, traceback_.strip(), ""])
                )
            # Combine the stacktraces for all the failures.
            full_traceback = "\n\n" + "\n".join(tracebacks)
            failed_test_output_str += full_traceback
            res += full_traceback
    _LOG.info("%s", failed_test_output_str)
    if create_script:
        # pytest \
        #   amp/oms/test/test_portfolio.py::TestDatabasePortfolio2::test1 \
        #   ...
        #   $*
        script_txt = []
        # pytest or pytest_log
        script_txt.append("pytest_log \\")
        script_txt.extend([f"  {t} \\" for t in targets])
        script_txt.append("  $*")
        script_txt = "\n".join(script_txt)
        msg = "To run the tests"
        hio.create_executable_script(script_name, script_txt, msg=msg)
    return res


# #############################################################################
# pytest_rename_test
# #############################################################################


@task
def pytest_rename_test(ctx, old_test_class_name, new_test_class_name):  # type: ignore
    """
    Rename the test and move its golden outcome.

    E.g., to rename a test class and all the test methods:
    ```
    > i pytest_rename_test TestCacheUpdateFunction1 \
            TestCacheUpdateFunction_new
    ```

    :param old_test_class_name: old class name
    :param new_test_class_name: new class name
    """
    hlitauti.report_task()
    _ = ctx
    root_dir = os.getcwd()
    # `lib_tasks` is used from outside the Docker container in the thin dev
    # environment and we want to avoid pulling in too many dependencies, unless
    # necessary, so we import dynamically.
    import helpers.hunit_test_utils as hunteuti

    renamer = hunteuti.UnitTestRenamer(
        old_test_class_name, new_test_class_name, root_dir
    )
    renamer.run()


# #############################################################################
# pytest_find_ununsed_goldens
# #############################################################################


@task
def pytest_find_unused_goldens(  # type: ignore
    ctx,
    dir_name=".",
    stage="prod",
    version="",
    out_file_name="pytest_find_unused_goldens.output.txt",
):
    """
    Detect mismatches between tests and their golden outcome files.

    - When goldens are required by the tests but the corresponding files
      do not exist
    - When the existing golden files are not actually required by the
      corresponding tests

    :param dir_name: the head dir to start the check from
    """
    hlitauti.report_task()
    # Remove the log file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        hlitauti.run(ctx, cmd)
    # Prepare the command line.
    amp_abs_path = hgit.get_amp_abs_path()
    amp_path = amp_abs_path.replace(
        os.path.commonpath([os.getcwd(), amp_abs_path]), ""
    )
    script_path = os.path.join(
        amp_path, "dev_scripts/find_unused_golden_files.py"
    ).lstrip("/")
    docker_cmd_opts = [f"--dir_name {dir_name}"]
    docker_cmd_ = f"{script_path} " + hlitauti._to_single_line_cmd(
        docker_cmd_opts
    )
    # Execute command line.
    cmd = hlitadoc._get_lint_docker_cmd(docker_cmd_, stage, version)
    cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
    # Run.
    hlitauti.run(ctx, cmd)


# #############################################################################
# pytest_compare_logs
# #############################################################################


def _purify_log_file(
    file_name: str, remove_line_numbers: bool, grep_regex: str
) -> str:
    txt = hio.from_file(file_name)
    # Remove leading `16:34:27`.
    txt = re.sub(r"^\d\d:\d\d:\d\d ", "", txt, flags=re.MULTILINE)
    # Remove references like `at 0x7f43493442e0`.
    txt = re.sub(r"at 0x\S{12}", "at 0x", txt, flags=re.MULTILINE)
    # Remove `done (0.014 s)`.
    txt = re.sub(r"(done) \(\d+\.\d+ s\)", "\\1", txt, flags=re.MULTILINE)
    # Remove wall_clock_time='2022-06-17 04:36:56.062645-04:00'.
    txt = re.sub(r"(wall_clock_time=)'.*'", "\\1", txt, flags=re.MULTILINE)
    # Remove `real_wall_clock_time = '2022-06-17 04:33:19.946025-04:00'`.
    txt = re.sub(r"(real_wall_clock_time=)'.*'", "\\1", txt, flags=re.MULTILINE)
    # Remove `tqdm [00:00<00:00,  4.05it/s]`.
    txt = re.sub(r"(htqdm.py.*)\[.*\]", "\\1", txt, flags=re.MULTILINE)
    # Remove `Task-3`.
    txt = re.sub(r"(Task-)\d+", "\\1", txt, flags=re.MULTILINE)
    # Remove line number, e.g.,
    # `htqdm.py abstract_market_data.py get_data_for_interval:259`
    if remove_line_numbers:
        txt = re.sub(
            r"(\.py [a-zA-Z_][a-zA-Z0-9_]*):\d+ ",
            "\\1:0 ",
            txt,
            flags=re.MULTILINE,
        )
    #
    if grep_regex:
        lines = []
        for line in txt.split("\n"):
            if re.search(grep_regex, line):
                lines.append(line)
        txt = "\n".join(lines)
    return txt


@task
def pytest_compare_logs(  # type: ignore
    ctx, file1, file2, remove_line_numbers=False, grep_regex="", dry_run=False
):
    """
    Diff two log files removing the irrelevant parts (e.g., timestamps, object
    pointers).

    :param remove_line_numbers: remove line numbers from function calls
        (e.g., `abstract_market_data.py get_data_for_interval:259`
    :param grep_regex: select lines based on a regex
    """
    suffix = "tmp"
    #
    txt = _purify_log_file(file1, remove_line_numbers, grep_regex)
    file1_tmp = hio.add_suffix_to_filename(file1, suffix)
    hio.to_file(file1_tmp, txt)
    #
    txt = _purify_log_file(file2, remove_line_numbers, grep_regex)
    file2_tmp = hio.add_suffix_to_filename(file2, suffix)
    hio.to_file(file2_tmp, txt)
    # Save the script to compare.
    script_file_name = "./tmp.vimdiff_log.sh"
    script_txt = f"vimdiff {file1_tmp} {file2_tmp}"
    msg = "To diff run:"
    hio.create_executable_script(script_file_name, script_txt, msg=msg)
    hlitauti.run(ctx, script_file_name, dry_run=dry_run, pty=True)


# #############################################################################
# pytest_buildmeister
# #############################################################################


def _run(
    cmd: str,
    *,
    abort_on_error: bool = False,
    output_file: Optional[str] = None,
    tee: bool = False,
) -> int:
    rc = hsystem.system(
        cmd,
        abort_on_error=abort_on_error,
        suppress_output=False,
        log_level="echo_frame",
        output_file=output_file,
        tee=tee,
    )
    return rc


def _get_invoke_cmd_line(target: str, opts: str, pytest_opts: str) -> str:
    """

    :param opts: options to pass to invoke
    """
    cmd = ["invoke"]
    cmd.append(target)
    if opts:
        cmd.append(opts)
    if pytest_opts:
        cmd.append("--pytest-opts %s" % pytest_opts)
    cmd.append("2>&1")
    return " ".join(cmd)


def _run_cmd_and_tg(cmd: str, *args: Any, **kwargs: Any) -> None:
    rc = _run(cmd, *args, **kwargs)
    if rc != 0:
        # pytest returns 5, if there are no tests to run.
        # On error, send Telegram message.
        cmd = "tg.py"
        _run(cmd, abort_on_error=False)


@task
def pytest_buildmeister_check(ctx, print_output=False):  # type: ignore
    """

    :param print_output: print content of the file with the output of the
        buildmeister run
    """
    _ = ctx
    # Concat the files generated by `invoke pytest_...`
    log_file = "bm.log.txt"
    if os.path.exists(log_file):
        cmd = f"rm -rf {log_file}"
        _run(cmd)
    log_file = "bm.log.txt"
    cmd = 'cat $(find . -name "bm.log*.txt" | sort) >%s' % log_file
    _run(cmd)
    #
    if print_output:
        print(hprint.frame("Print output"))
        cmd = f"cat {log_file}"
        _run(cmd)
    # Report failures using `invoke pytest_repro`.
    print(hprint.frame("Failures"))
    # "> sudo -u sasm rm ./tmp.pytest_repro.sh; i pytest_repro -f {log_file}"
    if os.path.exists("./tmp.pytest_repro.sh"):
        cmd = "sudo -u sasm rm ./tmp.pytest_repro.sh"
        _run(cmd)
    #
    cmd = f"invoke pytest_repro -f {log_file}"
    _run(cmd)
    # Report failures using `grep`.
    print(hprint.frame("grep Failures"))
    cmd = f"grep '^FAILED' {log_file} | sort"
    _run(cmd)


@task
def pytest_buildmeister(  # type: ignore
    ctx, opts="", pytest_opts="", docker_clean=False, test=False
):
    """
    Run the regression tests.

    - Run updating all the tests
    ```
    > pytest_buildmeister --pytest-opts "--update_outcomes"
    ```

    :param docker_clean: remove all dead Docker instances
    :param opts: options to pass to the invoke (e.g., `--version 1.2.0` to test
        a specific version of the Docker container)
    :param pytest_opts: options to pass to pytest
    :param test: just run a single quick test to verify functionality of this
        script
    """
    _ = ctx
    if test:
        # For testing.
        pytest_opts = "amp/dataflow/backtest/test/test_dataflow_backtest_utils.py::Test_get_configs_from_command_line_Amp1::test1"
    if docker_clean:
        cmd = "dev_scripts_lime/docker_clean.sh"
        _run(cmd)
    # Clean and sync.
    cmd = "invoke git_clean -f"
    _run(cmd)
    #
    cmd = "invoke git_pull"
    _run(cmd)
    #
    log_file = "bm.log*txt"
    if os.path.exists(log_file):
        cmd = f"rm -rf {log_file}"
        _run(cmd)
    #
    files_to_merge = []
    #
    target = "run_fast_tests"
    cmd = _get_invoke_cmd_line(target, opts, pytest_opts)
    log_file = f"bm.log.{target}.txt"
    files_to_merge.append(log_file)
    cmd = f"({cmd} | tee {log_file};" + " exit ${PIPESTATUS[0]})"
    cmd = f"bash -c '{cmd}'"
    _run_cmd_and_tg(cmd)
    #
    cmd = "invoke fix_perms"
    hsystem.system(cmd)
    #
    target = "run_slow_tests"
    cmd = _get_invoke_cmd_line(target, opts, pytest_opts)
    log_file = f"bm.log.{target}.txt"
    files_to_merge.append(log_file)
    cmd = f"({cmd} | tee {log_file};" + " exit ${PIPESTATUS[0]})"
    cmd = f"bash -c '{cmd}'"
    _run_cmd_and_tg(cmd)
    #
    cmd = "invoke fix_perms"
    _run(cmd)
    #
    target = "run_superslow_tests"
    log_file = f"bm.log.{target}.txt"
    files_to_merge.append(log_file)
    cmd = _get_invoke_cmd_line(target, opts, pytest_opts)
    cmd = f"({cmd} | tee {log_file};" + " exit ${PIPESTATUS[0]})"
    cmd = f"bash -c '{cmd}'"
    _run_cmd_and_tg(cmd)
    #
    pytest_buildmeister_check(ctx)


# #############################################################################
# pytest_collect_only
# #############################################################################


@task
def pytest_collect_only(ctx):  # type: ignore
    _ = ctx
    cmd = 'invoke docker_cmd --cmd "pytest --collect-only 2>&1"'
    hsystem.system(cmd, suppress_output=False)


# #############################################################################
# pytest_add_untracked_golden_outcomes
# #############################################################################


@task
def pytest_add_untracked_golden_outcomes(ctx):  # type: ignore
    """
    Add the golden outcomes files that are not tracked under git.
    """
    _ = ctx
    cmd = 'git add $(git ls-files . --exclude-standard --others | \grep "output" | grep -v tmp)'
    hsystem.system(cmd, suppress_output=False)


# #############################################################################
# TO_ADD
# #############################################################################
