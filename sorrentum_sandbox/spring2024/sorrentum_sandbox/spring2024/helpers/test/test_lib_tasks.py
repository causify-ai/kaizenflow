# This should only test helper functions from `lib_tasks.py`.
# `test_tasks.py` associated to `tasks.py` should test specific task targets.

import logging
import os
import re
from typing import Dict

import invoke
import pytest

import helpers.hgit as hgit
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import helpers.lib_tasks as hlibtask
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)


def _get_default_params() -> Dict[str, str]:
    """
    Get fake params pointing to a different image so we can test the code
    without affecting the official images.
    """
    ecr_base_path = os.environ["AM_ECR_BASE_PATH"]
    default_params = {
        "AM_ECR_BASE_PATH": ecr_base_path,
        "CK_ECR_BASE_PATH": os.environ["CK_ECR_BASE_PATH"],
        "BASE_IMAGE": "amp_test",
        "DEV_TOOLS_IMAGE_PROD": f"{ecr_base_path}/dev_tools:prod",
    }
    return default_params


class _LibTasksTestCase(hunitest.TestCase):
    """
    Test class injecting default parameters in the `lib_tasks` singleton in
    `set_up_test()` and cleaning up the singleton in `tear_down_test()`.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        params = _get_default_params()
        hlitauti.set_default_params(params)

    def tear_down_test(self) -> None:
        hlitauti.reset_default_params()


# #############################################################################


def _build_mock_context_returning_ok() -> invoke.MockContext:
    """
    Build a MockContext catching any command and returning rc=0.
    """
    ctx = invoke.MockContext(
        repeat=True, run={re.compile(".*"): invoke.Result(exited=0)}
    )
    return ctx


class _CheckDryRunTestCase(hunitest.TestCase):
    """
    Test class running an invoke target with/without dry-run and checking that
    the issued commands are what is expected.
    """

    def _check_calls(self, ctx: invoke.MockContext) -> None:
        """
        `check_string()` the sequence of commands issued in the context.
        """
        act = "\n".join(map(str, ctx.run.mock_calls))
        act = hprint.remove_non_printable_chars(act)
        self.check_string(act)

    def _check_output(self, target: str, check: bool = True) -> None:
        """
        Dry run target checking that the sequence of commands issued is the
        expected one.
        """
        ctx = _build_mock_context_returning_ok()
        # pylint: disable=exec-used
        exec(f"hlibtask.{target}")
        # pylint: enable=exec-used
        # Check the outcome.
        if check:
            self._check_calls(ctx)


# #############################################################################


# TODO(gp): We should group the tests by what is tested and not how it's
# tested. E.g. TestDryRunTasks1::test_print_setup and
# TestDryRunTasks2::test_print_setup should go together in a class.


class TestDryRunTasks1(hunitest.TestCase):
    """
    - Run invoke in dry-run mode from command line
    - Compare the output to the golden outcomes
    """

    # TODO(gp): -> TestGitCommands1

    def dry_run(
        self, target: str, dry_run: bool = True, check_string: bool = True
    ) -> None:
        """
        Invoke the given target with dry run.

        This is used to test the commands that we can't actually
        execute.
        """
        opts = "--dry" if dry_run else ""
        # TODO(vitalii): While deploying the container versioning
        # we disable the check in the unit tests. Remove `SKIP_VERSION_CHECK=1`
        # after CmampTask570 is fixed.
        cmd = f"SKIP_VERSION_CHECK=1 invoke {opts} {target} | grep -v INFO | grep -v '>>ENV<<:'"
        _, act = hsystem.system_to_string(cmd)
        act = hprint.remove_non_printable_chars(act)
        regex = "(WARN|INFO)\s+hcache.py"
        act = hunitest.filter_text(regex, act)
        # Filter out `no module` warnings.
        # TODO(Grisha): add the "no module warning" filtering
        # to `purify_text()` in `check_string()`.
        regex = "WARN.*No module"
        act = hunitest.filter_text(regex, act)
        if check_string:
            self.check_string(act)

    # #########################################################################

    # TODO(gp): We can't test this since amp and cmamp have now different base image.
    # def test_print_setup(self) -> None:
    #     target = "print_setup"
    #     self.dry_run(target)

    # The problem is that we use system and not ctx to execute the command, so that
    # --dry-run doesn't work.
    @pytest.mark.skip(reason="This is actually run")
    def test_git_pull(self) -> None:
        target = "git_pull"
        self.dry_run(target)

    @pytest.mark.skip(reason="This is actually run")
    def test_git_fetch_master(self) -> None:
        target = "git_fetch_master"
        self.dry_run(target)

    @pytest.mark.skip(reason="This is actually run deleting files")
    def test_git_clean(self) -> None:
        target = "git_clean"
        self.dry_run(target)

    # #########################################################################
    # TODO(gp): -> TestDockerCommands1

    @pytest.mark.slow("~6 sec.")
    @pytest.mark.skipif(
        hserver.is_inside_ci(), reason="In CI the output is different"
    )
    def test_docker_images_ls_repo(self) -> None:
        target = "docker_images_ls_repo"
        # TODO(gp): amp and cmamp have different version of aws cli and so the
        # output is different.
        check_string = False
        self.dry_run(target, check_string=check_string)

    @pytest.mark.slow("~6 sec.")
    def test_docker_ps(self) -> None:
        target = "docker_ps"
        self.dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_stats(self) -> None:
        target = "docker_stats"
        self.dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_last(self) -> None:
        target = "docker_kill"
        self.dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_all(self) -> None:
        target = "docker_kill --all"
        self.dry_run(target)


# #############################################################################


# Outside CK infra, the class hangs, so we skip it.
@pytest.mark.requires_ck_infra
@pytest.mark.slow(reason="Around 7s")
@pytest.mark.skipif(
    not hgit.is_in_amp_as_supermodule(),
    reason="Run only in amp as super-module",
)
class TestDryRunTasks2(_LibTasksTestCase, _CheckDryRunTestCase):
    """
    - Call the invoke task directly from Python
    - `check_string()` that the sequence of commands issued by the target is the
      expected one using mocks to return ok for every system call.
    """

    def test_print_setup(self) -> None:
        target = "print_setup(ctx)"
        self._check_output(target)

    def test_git_pull(self) -> None:
        target = "git_pull(ctx)"
        self._check_output(target)

    def test_git_fetch_master(self) -> None:
        target = "git_fetch_master(ctx)"
        self._check_output(target)

    def test_git_clean(self) -> None:
        target = "git_clean(ctx)"
        self._check_output(target)

    # TODO(Grisha): is not it the same as `test_git_clean()`?
    def test_git_clean2(self) -> None:
        target = "git_clean(ctx, dry_run=False)"
        self._check_output(target)

    # #########################################################################

    def test_docker_images_ls_repo(self) -> None:
        target = "docker_images_ls_repo(ctx)"
        self._check_output(target, check=False)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_all(self) -> None:
        target = "docker_kill(ctx, all=True)"
        self._check_output(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_last(self) -> None:
        target = "docker_kill(ctx)"
        self._check_output(target)

    def test_docker_ps(self) -> None:
        target = "docker_ps(ctx)"
        self._check_output(target)

    def test_docker_pull(self) -> None:
        target = "docker_pull(ctx)"
        self._check_output(target, check=False)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_stats(self) -> None:
        target = "docker_stats(ctx)"
        self._check_output(target)

    # #########################################################################
    # TODO(gp): -> TestGhCommands1

    # TODO(ShaopengZ): Outside CK infra, the test hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Only run in amp as supermodule",
    )
    def test_gh_create_pr1(self) -> None:
        target = "gh_create_pr(ctx, repo_short_name='amp', title='test')"
        self._check_output(target)

    # TODO(ShaopengZ): Outside CK infra, the test hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Only run in amp as supermodule",
    )
    def test_gh_create_pr2(self) -> None:
        target = "gh_create_pr(ctx, body='hello_world', repo_short_name='amp', title='test')"
        self._check_output(target)

    # TODO(ShaopengZ): Outside CK infra, the test hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Only run in amp as supermodule",
    )
    def test_gh_create_pr3(self) -> None:
        target = (
            "gh_create_pr(ctx, draft=False, repo_short_name='amp', title='test')"
        )
        self._check_output(target)

    def test_gh_issue_title(self) -> None:
        target = "gh_issue_title(ctx, 1)"
        self._check_output(target)

    # TODO(Shaopengz):Outside CK infra, the test hangs, so skip.
    @pytest.mark.requires_ck_infra
    @pytest.mark.skipif(not hgit.is_amp(), reason="Only run in amp")
    def test_gh_workflow_list(self) -> None:
        target = "gh_workflow_list(ctx, filter_by_branch='master')"
        self._check_output(target)

    # This is an action with side effects so we can't test it.
    # def test_gh_workflow_run(self) -> None:
    #     target = "gh_workflow_run(ctx)"
    #     self._check_output(target)

    # #########################################################################
    # TODO(gp): -> TestGitCommands1
    def test_git_branch_files(self) -> None:
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        target = "git_branch_files(ctx)"
        self._check_output(target)

    def test_git_branch_create1(self) -> None:
        target = (
            "git_branch_create(ctx, branch_name='AmpTask123_test', "
            "only_branch_from_master=False)"
        )
        self._check_output(target)

    def test_git_branch_create2(self) -> None:
        # Difference between `cmamp` and `kaizenflow`.
        target = (
            "git_branch_create(ctx, issue_id=1, repo_short_name='kaizen', "
            "only_branch_from_master=False)"
        )
        self._check_output(target)

    def test_git_branch_create3(self) -> None:
        with self.assertRaises(AssertionError):
            target = (
                "git_branch_create(ctx, branch_name='test', issue_id=1, "
                "only_branch_from_master=False)"
            )
            self._check_output(target, check=False)

    # This is an action with side effects so we can't test it.
    # def test_git_branch_delete_merged(self) -> None:
    #     target = "git_branch_delete_merged(ctx)"
    #     self._check_output(target)

    def test_git_merge_master(self) -> None:
        target = "git_merge_master(ctx, abort_if_not_clean=False)"
        self._check_output(target)

    # #########################################################################
    # TODO(gp): -> TestLintCommands1

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_lint1(self) -> None:
        target = "lint(ctx, modified=True)"
        # The output depends on the client, so don't check it.
        self._check_output(target, check=False)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_lint2(self) -> None:
        target = "lint(ctx, branch=True)"
        # The output depends on the client, so don't check it.
        self._check_output(target, check=False)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_lint3(self) -> None:
        file = __file__
        target = f"lint(ctx, files='{file}')"
        # The output depends on the client, so don't check it.
        self._check_output(target, check=False)

    def test_find_test_class1(self) -> None:
        class_name = self.__class__.__name__
        target = f"find_test_class(ctx, class_name='{class_name}')"
        self._check_output(target)

    # #########################################################################

    @pytest.mark.skipif(
        hserver.is_inside_ci(), reason="In CI the output is different"
    )
    def test_docker_login(self) -> None:
        """
        Instead of using _build_mock_context_returning_ok(), set the return
        values more explicitly.
        """
        stdout = "aws-cli/1.19.49 Python/3.7.6 Darwin/19.6.0 botocore/1.20.49\n"
        ctx = invoke.MockContext(
            run={
                "aws --version": invoke.Result(stdout),
                re.compile("^docker login"): invoke.Result(exited=0),
                re.compile("^eval"): invoke.Result(exited=0),
            }
        )
        hlibtask.docker_login(ctx)
        # Check the outcome.
        # self._check_calls(ctx)


# #############################################################################

# TODO(gp): Run test coverage with
# > i run_fast_slow_tests \
#       --pytest-opts="helpers/test/test_lib_tasks.py test/test_tasks.py" \
#       --coverage

# TODO(gp): Add tests for:
# - print_tasks
# - git_files
# - git_last_commit_files
# - check_python_files
# - docker_stats
# - traceback (with checked in file)
# - lint


# #############################################################################


class TestFailing(hunitest.TestCase):
    """
    Run a test that fails based on AM_FORCE_TEST_FAIL environment variable.
    """

    def test_failing(self) -> None:
        if os.environ.get("AM_FORCE_TEST_FAIL", "") == "1":
            self.fail("test failed succesfully")
