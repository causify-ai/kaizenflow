"""
Import as:

import helpers.lib_tasks_gh as hlitagh
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.htable as htable
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access

# #############################################################################
# GitHub CLI.
# #############################################################################


@task
def gh_login(  # type: ignore
    ctx,
    account="",
    print_status=False,
):
    hlitauti.report_task()
    #
    if not account:
        # Retrieve the name of the repo, e.g., "alphamatic/amp".
        full_repo_name = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=False
        )
        _LOG.debug(hprint.to_str("full_repo_name"))
        account = full_repo_name.split("/")[0]
    _LOG.info(hprint.to_str("account"))
    #
    ssh_filename = os.path.expanduser(f"~/.ssh/id_rsa.{account}.github")
    _LOG.debug(hprint.to_str("ssh_filename"))
    if os.path.exists(ssh_filename):
        cmd = f"export GIT_SSH_COMMAND='ssh -i {ssh_filename}'"
        print(cmd)
    else:
        _LOG.warning("Can't find file '%s'", ssh_filename)
    #
    if print_status:
        cmd = "gh auth status"
        hlitauti.run(ctx, cmd)
    #
    github_pat_filename = os.path.expanduser(f"~/.ssh/github_pat.{account}.txt")
    if os.path.exists(github_pat_filename):
        cmd = f"gh auth login --with-token <{github_pat_filename}"
        hlitauti.run(ctx, cmd)
    else:
        _LOG.warning("Can't find file '%s'", github_pat_filename)
    #
    if print_status:
        cmd = "gh auth status"
        hlitauti.run(ctx, cmd)


def _get_branch_name(branch_mode: str) -> Optional[str]:
    if branch_mode == "current_branch":
        branch_name: Optional[str] = hgit.get_branch_name()
    elif branch_mode == "master":
        branch_name = "master"
    elif branch_mode == "all":
        branch_name = None
    else:
        raise ValueError(f"Invalid branch='{branch_mode}'")
    return branch_name


def _get_workflow_table() -> htable.TableType:
    """
    Get a table with the status of the GH workflow for the current repo.
    """
    # Get the workflow status from GH.
    cmd = "export NO_COLOR=1; gh run list"
    _, txt = hsystem.system_to_string(cmd)
    _LOG.debug(hprint.to_str("txt"))
    # pylint: disable=line-too-long
    # > gh run list
    # STATUS  TITLE                                                          WORKFLOW    BRANCH                                                         EVENT         ID          ELAPSED  AGE
    # *       AmpTask1786_Integrate_20230518_2                               Fast tests  AmpTask1786_Integrate_20230518_2                               pull_request  5027911519  4m49s    4m
    # > gh run list | more
    # completed       success AmpTask1786_Integrate_20230518_2        Fast tests      AmpTask1786_Integrate_20230518_2        pull_request    5027911519      7m17s   10m
    # in_progress             AmpTask1786_Integrate_20230518_2        Slow tests      AmpTask1786_Integrate_20230518_2        pull_request    5027911518      10m9s   10m

    # pylint: enable=line-too-long
    # The output is tab separated, so convert it into CSV.
    first_line = txt.split("\n")[0]
    _LOG.debug("first_line=%s", first_line.replace("\t", ","))
    num_cols = len(first_line.split("\t"))
    _LOG.debug(hprint.to_str("first_line num_cols"))
    cols = [
        "completed",  # E.g., completed, in_progress
        "status",  # E.g., success, failure
        "name",  # Aka title
        "workflow",
        "branch",
        "event",
        "id",
        "elapsed",
        "age",
    ]
    hdbg.dassert_eq(num_cols, len(cols))
    # Build the table.
    table = htable.Table.from_text(cols, txt, delimiter="\t")
    _LOG.debug(hprint.to_str("table"))
    return table


# TODO(Grisha): seems like GH changed the output format, we should update accordingly,
# see CmTask #4672 "Slow tests fail (9835540316)" for details.
@task
def gh_workflow_list(  # type: ignore
    ctx,
    filter_by_branch="current_branch",
    filter_by_completed="all",
    report_only_status=True,
    show_stack_trace=False,
):
    """
    Report the status of the GH workflows.

    :param filter_by_branch: name of the branch to check
        - `current_branch` for the current Git branch
        - `master` for master branch
        - `all` for all branches
    :param filter_by_completed: filter table by the status of the workflow
        - E.g., "failure", "success"
    :param show_stack_trace: in case of error run `pytest_repro` reporting also
        the stack trace
    """
    hlitauti.report_task(
        txt=hprint.to_str("filter_by_branch filter_by_completed")
    )
    # Login.
    gh_login(ctx)
    # Get the table.
    table = _get_workflow_table()
    # Filter table based on the branch.
    if filter_by_branch != "all":
        field = "branch"
        value = _get_branch_name(filter_by_branch)
        print(f"Filtering table by {field}={value}")
        table = table.filter_rows(field, value)
    # Filter table by the workflow status.
    if filter_by_completed != "all":
        field = "completed"
        value = filter_by_completed
        print(f"Filtering table by {field}={value}")
        table = table.filter_rows(field, value)
    if (
        filter_by_branch not in ("current_branch", "master")
        or not report_only_status
    ):
        print(str(table))
        return
    # For each workflow find the last success.
    branch_name = hgit.get_branch_name()
    workflows = table.unique("workflow")
    print(f"workflows={workflows}")
    for workflow in workflows:
        print(hprint.frame(workflow))
        table_tmp = table.filter_rows("workflow", workflow)
        # Report the full status.
        print(table_tmp)
        # Find the first success.
        num_rows = table.size()[0]
        _LOG.debug("num_rows=%s", num_rows)
        for i in range(num_rows):
            status_column = table_tmp.get_column("status")
            _LOG.debug("status_column=%s", str(status_column))
            hdbg.dassert_lt(
                i, len(status_column), msg="status_column=%s" % status_column
            )
            status = status_column[i]
            if status == "success":
                print(f"Workflow '{workflow}' for '{branch_name}' is ok")
                break
            if status in ("failure", "startup_failure", "cancelled"):
                _LOG.error(
                    "Workflow '%s' for '%s' is broken", workflow, branch_name
                )
                # Get the output of the broken run.
                # > gh run view 1477484584 --log-failed
                workload_id = table_tmp.get_column("id")[i]
                log_file_name = f"tmp.failure.{workflow}.{branch_name}.txt"
                log_file_name = log_file_name.replace(" ", "_").lower()
                cmd = f"gh run view {workload_id} --log-failed >{log_file_name}"
                hsystem.system(cmd)
                print(f"# Log is in '{log_file_name}'")
                # Run_fast_tests  Run fast tests  2021-12-19T00:19:38.3394316Z FAILED data
                # cmd = rf"grep 'Z FAILED ' {log_file_name}"
                workflow_as_str = workflow.lower().replace(" ", "_")
                script_name = f"./tmp.pytest_repro.{workflow_as_str}.sh"
                cmd = f"invoke pytest_repro --file-name {log_file_name} --script-name {script_name}"
                if show_stack_trace:
                    cmd += " -s"
                hsystem.system(cmd, suppress_output=False, abort_on_error=False)
                break
            if status == "":
                if i == (len(status_column) - 1):
                    # If all the runs in the table are in progress, i.e. there is no
                    # failed or succesful run, issue a warning and exit. E.g.,
                    # #########################################################
                    # Superslow tests
                    # #########################################################
                    # completed   | status | name            | workflow        | branch | event             | id         | elapsed | age |
                    # ----------- | ------ | --------------- | --------------- | ------ | ----------------- | ---------- | ------- | --- |
                    # in_progress |        | Superslow tests | Superslow tests | master | workflow_dispatch | 5421740561 | 13m25s  | 13m |
                    _LOG.warning(
                        "No failed/successful run found for workflow=%s for branch=%s, all runs are in progress, exiting.",
                        workflow,
                        branch_name,
                    )
                    break
                _LOG.debug(
                    "Workflow=%s for branch %s is in progress, continue looking for a failed/successful run",
                    workflow,
                    branch_name,
                )
                # It's in progress.
            else:
                raise ValueError(f"Invalid status='{status}'")


@task
def gh_workflow_run(ctx, branch="current_branch", workflows="all"):  # type: ignore
    """
    Run GH workflows in a branch.
    """
    hlitauti.report_task(txt=hprint.to_str("branch workflows"))
    # Login.
    gh_login(ctx)
    # Get the branch name.
    if branch == "current_branch":
        branch_name = hgit.get_branch_name()
    elif branch == "master":
        branch_name = "master"
    else:
        raise ValueError(f"Invalid branch='{branch}'")
    _LOG.debug(hprint.to_str("branch_name"))
    # Get the workflows.
    if workflows == "all":
        gh_tests = ["fast_tests", "slow_tests"]
    else:
        gh_tests = [workflows]
    _LOG.debug(hprint.to_str("workflows"))
    # Run.
    for gh_test in gh_tests:
        gh_test += ".yml"
        # gh workflow run fast_tests.yml --ref AmpTask1251_Update_GH_actions_for_amp
        cmd = f"gh workflow run {gh_test} --ref {branch_name}"
        hlitauti.run(ctx, cmd)


def _get_repo_full_name_from_cmd(repo_short_name: str) -> Tuple[str, str]:
    """
    Convert the `repo_short_name` from command line (e.g., "current", "amp",
    "lm") to the repo_short_name full name without host name.
    """
    repo_full_name_with_host: str
    if repo_short_name == "current":
        # Get the repo name from the current repo.
        repo_full_name_with_host = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=True
        )
        # Compute the short repo name corresponding to "current".
        repo_full_name = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=False
        )
        ret_repo_short_name = hgit.get_repo_name(
            repo_full_name, in_mode="full_name", include_host_name=False
        )
    else:
        # Get the repo name using the short -> full name mapping.
        repo_full_name_with_host = hgit.get_repo_name(
            repo_short_name, in_mode="short_name", include_host_name=True
        )
        ret_repo_short_name = repo_short_name
    _LOG.debug(
        "repo_short_name=%s -> repo_full_name_with_host=%s ret_repo_short_name=%s",
        repo_short_name,
        repo_full_name_with_host,
        ret_repo_short_name,
    )
    return repo_full_name_with_host, ret_repo_short_name


# #############################################################################


def _get_gh_issue_title(issue_id: int, repo_short_name: str) -> Tuple[str, str]:
    """
    Get the title of a GitHub issue.

    :param repo_short_name: `current` refer to the repo_short_name where we are,
        otherwise a repo_short_name short name (e.g., "amp")
    """
    repo_full_name_with_host, repo_short_name = _get_repo_full_name_from_cmd(
        repo_short_name
    )
    # > (export NO_COLOR=1; gh issue view 1251 --json title)
    # {"title":"Update GH actions for amp"}
    hdbg.dassert_lte(1, issue_id)
    cmd = f"gh issue view {issue_id} --repo {repo_full_name_with_host} --json title,url"
    _, txt = hsystem.system_to_string(cmd)
    _LOG.debug("txt=\n%s", txt)
    # Parse json.
    dict_ = json.loads(txt)
    _LOG.debug("dict_=\n%s", dict_)
    title = dict_["title"]
    _LOG.debug("title=%s", title)
    url = dict_["url"]
    _LOG.debug("url=%s", url)
    # Remove some annoying chars.
    for char in ": + ( ) / ` *".split():
        title = title.replace(char, "")
    # Replace multiple spaces with one.
    title = re.sub(r"\s+", " ", title)
    #
    title = title.replace(" ", "_")
    title = title.replace("-", "_")
    title = title.replace("'", "_")
    title = title.replace("`", "_")
    title = title.replace('"', "_")
    # Add the prefix `AmpTaskXYZ_...`
    task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)
    _LOG.debug("task_prefix=%s", task_prefix)
    title = f"{task_prefix}{issue_id}_{title}"
    return title, url


@task
def gh_issue_title(ctx, issue_id, repo_short_name="current", pbcopy=True):  # type: ignore
    """
    Print the title that corresponds to the given issue and repo_short_name.
    E.g., AmpTask1251_Update_GH_actions_for_amp.

    Before running the invoke, one must check their login status on GH
    by running `gh auth status`.

    :param issue_id: id number of the issue to create the branch for
    :param repo_short_name: short name of the repo to use for the branch
        name building. "current" refers to the repo where the call is
        implemented
    :param pbcopy: save the result into the system clipboard (only on
        macOS)
    """
    hlitauti.report_task(txt=hprint.to_str("issue_id repo_short_name"))
    # Login.
    gh_login(ctx)
    #
    issue_id = int(issue_id)
    hdbg.dassert_lte(1, issue_id)
    title, url = _get_gh_issue_title(issue_id, repo_short_name)
    # Print or copy to clipboard.
    msg = f"{title}: {url}"
    hlitauti._to_pbcopy(msg, pbcopy)


def _check_if_pr_exists(title: str) -> bool:
    """
    Return whether a PR exists or not.
    """
    # > gh pr diff AmpTask1955_Lint_20211219
    # no pull requests found for branch "AmpTask1955_Lint_20211219"
    cmd = f"gh pr diff {title}"
    rc = hsystem.system(cmd, abort_on_error=False)
    pr_exists: bool = rc == 0
    return pr_exists


@task
def gh_create_pr(  # type: ignore
    ctx,
    body="",
    draft=True,
    auto_merge=False,
    repo_short_name="current",
    title="",
):
    """
    Create a draft PR for the current branch in the corresponding
    repo_short_name.

    ```
    # To open a PR in the web browser
    > gh pr view --web

    # To see the status of the checks
    > gh pr checks
    ```

    :param body: the body of the PR
    :param draft: draft or ready-to-review PR
    :param auto_merge: enable auto merging PR
    :param title: title of the PR or the branch name, if title is empty
    """
    hlitauti.report_task()
    # Login.
    gh_login(ctx)
    #
    branch_name = hgit.get_branch_name()
    if not title:
        # Use the branch name as title.
        title = branch_name
    repo_full_name_with_host, repo_short_name = _get_repo_full_name_from_cmd(
        repo_short_name
    )
    _LOG.info(
        "Creating PR with title '%s' for '%s' in %s",
        title,
        branch_name,
        repo_full_name_with_host,
    )
    if auto_merge:
        hdbg.dassert(
            not draft, "The PR can't be a draft in order to auto merge it"
        )
    pr_exists = _check_if_pr_exists(title)
    _LOG.debug(hprint.to_str("pr_exists"))
    if pr_exists:
        _LOG.warning("PR '%s' already exists: skipping creation", title)
    else:
        cmd = (
            "gh pr create"
            + f" --repo {repo_full_name_with_host}"
            + (" --draft" if draft else "")
            + f' --title "{title}"'
            + f' --body "{body}"'
        )
        # TODO(gp): Use _to_single_line_cmd
        hlitauti.run(ctx, cmd)
    if auto_merge:
        cmd = f"gh pr ready {title}"
        hlitauti.run(ctx, cmd)
        cmd = f"gh pr merge {title} --auto --delete-branch --squash"
        hlitauti.run(ctx, cmd)


# TODO(gp): Add gh_open_pr to jump to the PR from this branch.

# TODO(Grisha): probably the section deserves a separate lib.
# #############################################################################
# Buildmeister dashboard
# #############################################################################


@task
def gh_publish_buildmeister_dashboard_to_s3(ctx, mark_as_latest=True):  # type: ignore
    """
    Run the buildmeister dashboard notebook and publish it to S3.

    :param mark_as_latest: if True, mark the dashboard as `latest`, otherwise
        just publish a timestamped copy
    """
    hlitauti.report_task()
    # Login to GH CLI.
    if hserver.is_inside_ci():
        _LOG.info("Skipping login since running inside CI")
    else:
        gh_login(ctx)
    # Run and publish the Buildmeister dashboard Jupyter notebook locally.
    amp_abs_path = hgit.get_amp_abs_path()
    run_notebook_script_path = os.path.join(
        amp_abs_path, "dev_scripts/notebooks/run_notebook.py"
    )
    notebook_path = os.path.join(
        amp_abs_path, "devops/notebooks/Master_buildmeister_dashboard.ipynb"
    )
    dst_local_dir = os.path.join(amp_abs_path, "tmp.notebooks")
    cmd_run_txt = [
        run_notebook_script_path,
        f"--notebook {notebook_path}",
        # The notebook does not require a config, so using a random dummy config.
        # TODO(Grisha): consider creating a separate config builder for the notebook.
        "--config_builder 'im_v2.common.data.qa.qa_check.build_dummy_data_reconciliation_config()'",
        f"--dst_dir '{dst_local_dir}'",
        "--publish",
        "--num_threads serial",
    ]
    cmd_run_txt = " ".join(cmd_run_txt)
    hsystem.system(cmd_run_txt)
    # To avoid the dependency on `helpers.hs3`.
    import helpers.hs3 as hs3

    # Get HTML file name.
    tmp_local_dir_name = os.path.join(amp_abs_path, "tmp.notebooks")
    pattern = "Master_buildmeister_dashboard.0*.html"
    only_files = True
    use_relative_paths = False
    local_html_files = hio.listdir(
        tmp_local_dir_name,
        pattern,
        only_files=only_files,
        use_relative_paths=use_relative_paths,
    )
    # Assert if more than 1 file is returned.
    hdbg.dassert_eq(
        len(local_html_files),
        1,
        f"Found more than one file in {tmp_local_dir_name} - {local_html_files}",
    )
    local_html_file = local_html_files[0]
    s3_build_path = os.path.join(
        henv.execute_repo_config_code("get_html_bucket_path()"),
        "build/buildmeister_dashboard",
    )
    aws_profile = "ck"
    if mark_as_latest:
        # Copy the dashboard notebook to S3 as latest build.
        s3_latest_build_path = os.path.join(
            s3_build_path, "Master_buildmeister_dashboard.latest.html"
        )
        hs3.copy_file_to_s3(local_html_file, s3_latest_build_path, aws_profile)
    # Copy the timestamped version of the dashboard notebook to S3.
    # Need to add a trailing slash to the path to copy the file into the folder.
    # https://docs.python.org/3/library/os.path.html#os.path.join
    s3_build_path_folder = os.path.join(s3_build_path, "")
    hs3.copy_file_to_s3(local_html_file, s3_build_path_folder, aws_profile)


def gh_get_open_prs(repo: str) -> List[Dict[str, Any]]:
    """
    Return a list of open PRs.

    :param repo: repo name in the format "organization/repo", e.g.,
        "cryptokaizen/cmamp"
    """
    cmd = f"gh pr list --state 'open' --json id --repo {repo}"
    pull_requests = _gh_run_and_get_json(cmd)
    return pull_requests


def _get_failed_or_successful_workflow_run(
    workflow_runs: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent successful or failed workflow run.

    :param workflow_runs: list of workflow runs
    :return: the most recent successful or failed workflow run or None if not
        found, e.g.,
        ```
        {
            'conclusion': 'success',
            'status': 'completed',
            'url': 'https://github.com/cryptokaizen/cmamp/actions/runs/8714881296',
            'workflowName': 'Allure fast tests'
        }    
        ```
    """
    # We assume that the workflow runs are sorted by time in descending order. 
    # Therefore, we can iterate over the list and return the last successful 
    # or failed run.
    workflow_run_dict = None
    for curr_workflow_run in workflow_runs:
        if curr_workflow_run["conclusion"] in ["success", "failure"]:
            # The last complete run found, exiting the loop. A run is considered
            # complete if the "conclusion" field meets the current condition. 
            workflow_run_dict = curr_workflow_run 
            break
    return workflow_run_dict 


def gh_get_details_for_all_workflows(repo_list: List[str]) -> "pd.DataFrame":
    """
    Get status for all the workflows.

    :param repo_list: list of repos to get the status for e.g.,
        ["cryptokaizen/cmamp", "cryptokaizen/orange"]
    :return: a table with the status of all the workflows, e.g.,
    ```
                    Repo            workflowName                                                url     status
    0    cryptokaizen/cmamp       Allure fast tests  https://github.com/cryptokaizen/cmamp/actions/...  completed
    1    cryptokaizen/cmamp       Allure slow tests  https://github.com/cryptokaizen/cmamp/actions/...  completed
    ```
    """
    # TODO(Grisha): expose cols to the interface, i.e. a caller decides what to do.
    gh_cols = ["workflowName", "url", "status", "conclusion"]
    # Import locally in order not to introduce external dependencies to the lib.
    import pandas as pd

    repo_dfs = []
    for repo_name in repo_list:
        # Get all workflow names for the given repo.
        workflow_names = gh_get_workflow_type_names(repo_name)
        # For each workflow find the last run.
        for workflow_name in workflow_names:
            # Get at least a few runs to compute the status; this is useful when
            # the latest run is not completed, in this case the run before the
            # latest one tells the status for a workflow.
            limit = 5
            workflow_statuses = gh_get_workflow_details(
                repo_name, workflow_name, gh_cols, limit
            )
            if len(workflow_statuses) < limit:
                # TODO(Grisha): should we just insert empty rows as placeholders so that
                # we know that such workflows exist?
                _LOG.warning(
                    "Not enough runs to compute status for '%s', repo '%s', skipping the workflow",
                    workflow_name,
                    repo_name,
                )
                continue
            # Get the latest successful or failed workflow run.
            workflow_status = _get_failed_or_successful_workflow_run(workflow_statuses)
            if workflow_status is None:
                _LOG.warning(
                    "No successful or failed runs found for '%s', repo '%s', skipping the workflow",
                    workflow_name,
                    repo_name,
                )
                continue
            # Access the info of latest workflow run.
            workflow_status = pd.DataFrame([workflow_status])
            workflow_status["repo_name"] = repo_name
            repo_dfs.append(workflow_status)
    # Collect per-repo tables into a single DataFrame.
    df = pd.concat(repo_dfs, ignore_index=True)
    # Rename the columns.
    df = df.drop(columns=["status"])
    df = df.rename(columns={"workflowName": "workflow_name"})
    return df


def gh_get_overall_build_status_for_repo(
    repo_df: "pd.Dataframe",
    *,
    use_colors: bool = True,
) -> str:
    """
    Return the overall status of the workflows for a repo.

    :param repo_df: table with the status of the workflows for a repo
    :param use_colors: if True, return the status with colors
    :return: overall status of the build for a repo
    """
    if use_colors:
        hdbg.dassert(
            hsystem.is_running_in_ipynb(),
            msg="The use_colors option is applicable only when running inside a Jupyter notebook",
        )
        # See: https://stackoverflow.com/questions/19746350/how-to-change-color-in-markdown-cells-ipython-jupyter-notebook
        failed_status = '<span style="color:red">Failed</span>'
        success_status = '<span style="color:green">Success</span>'
    else:
        failed_status = "Failed"
        success_status = "Success"
    if "failure" in repo_df["conclusion"].values:
        # The build is failed if at least one workflow is failed.
        overall_status = failed_status
    else:
        overall_status = success_status
    return overall_status


def gh_get_workflow_type_names(repo_name: str, *, sort: bool = True) -> List[str]:
    """
    Get a list of workflow names for a given repo.

    :param repo_name: git repo name in the format "organization/repo",
        e.g., "cryptokaizen/cmamp"
    :param sort: if True, sort the list of workflow names
    :return: list of workflow names, e.g., ["Fast tests", "Slow tests"]
    """
    hdbg.dassert_isinstance(repo_name, str)
    _LOG.debug(hprint.to_str("repo_name"))
    # Get the workflow list.
    cmd = f"gh workflow list --json name --repo {repo_name}"
    workflow_types = _gh_run_and_get_json(cmd)
    workflow_names = [workflow["name"] for workflow in workflow_types]
    if sort:
        workflow_names = sorted(workflow_names)
    return workflow_names


def gh_get_workflow_details(
    repo_name: str, workflow_name: str, fields: List[str], limit: int
) -> List[Dict[str, Any]]:
    """
    Return the stats for a given workflow.

    :param repo_name: git repo name in the format "organization/repo",
        e.g., "cryptokaizen/cmamp"
    :param workflow_name: workflow name, e.g., "Fast tests"
    :param fields: list of fields to return, e.g., ["workflowName", "status"]
    :param limit: number of runs to return
    :return: workflow stats
        Example output:
        ```
        [
            {
                "conclusion": "success",
                "status": "completed",
                "url": "https://github.com/cryptokaizen/cmamp/actions/runs/7757345960",
                "workflowName": "Slow tests"
            }
        ]
        ```
    """
    hdbg.dassert_isinstance(repo_name, str)
    hdbg.dassert_isinstance(workflow_name, str)
    hdbg.dassert_container_type(fields, List, str)
    _LOG.debug(hprint.to_str("repo_name workflow_name fields"))
    # Fetch the latest `limit` runs for status calculation.
    cmd = f"""
    gh run list \
        --json {",".join(fields)} \
        --repo {repo_name} \
        --branch master \
        --limit {limit} \
        --workflow "{workflow_name}"
    """
    workflow_statuses = _gh_run_and_get_json(cmd)
    # We still want to return the statuses even there are less runs than requested. E.g., there is a new workflow with a few runs or there is a workflow that was never run.
    hdbg.dassert_eq(len(workflow_statuses), limit, only_warning=True)
    _LOG.debug("workflow_statuses=\n%s", workflow_statuses)
    return workflow_statuses


def _gh_run_and_get_json(cmd: str) -> List[Dict[str, Any]]:
    """
    Run a `gh` command and remove colors when running inside a notebook.

    :param cmd: `gh` command to run
    :return: parsed JSON output of a command
    """
    _, _txt = hsystem.system_to_string(cmd)
    if hsystem.is_running_in_ipynb():
        # Remove the colors from the text.
        _txt = re.sub(r"\x1b\[((1;)*[0-9]{2})*m", "", _txt)
    _LOG.debug(hprint.to_str("_txt"))
    return json.loads(_txt)
