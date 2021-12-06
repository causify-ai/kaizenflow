# This should only test helper functions from `lib_tasks.py`.
# `test_tasks.py` associated to `tasks.py` should test specific task targets.

import logging
import os
import re
from typing import Dict, List

import invoke
import pytest

import helpers.git as hgit
import helpers.io_ as hio
import helpers.lib_tasks as hlibtask
import helpers.printing as hprint
import helpers.system_interaction as hsysinte
import helpers.unit_test as hunitest

_LOG = logging.getLogger(__name__)


def _get_default_params() -> Dict[str, str]:
    """
    Get fake params pointing to a different image so we can test the code
    without affecting the official images.
    """
    ecr_base_path = os.environ["AM_ECR_BASE_PATH"]
    default_params = {
        "ECR_BASE_PATH": ecr_base_path,
        "BASE_IMAGE": "amp_test",
        "DEV_TOOLS_IMAGE_PROD": f"{ecr_base_path}/dev_tools:prod",
    }
    return default_params


class _LibTasksTestCase(hunitest.TestCase):
    """
    Test class injecting default parameters in the `lib_tasks` singleton on
    `setUp()` and cleaning up the singleton on `tearDown()`.
    """

    def setUp(self) -> None:
        super().setUp()
        params = _get_default_params()
        hlibtask.set_default_params(params)

    def tearDown(self) -> None:
        hlibtask.reset_default_params()
        super().tearDown()


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


def _gh_login() -> None:
    """
    Log in inside GitHub.

    This is needed by GitHub actions.
    """
    env_var = "GH_ACTION_ACCESS_TOKEN"
    if os.environ.get(env_var, None):
        # If the env var exists and it's not None.
        _LOG.warning("Using env var '%s' to log in GitHub", env_var)
        # For debugging only (see AmpTask1864).
        if False:

            def _cmd(cmd):
                hsysinte.system(
                    cmd,
                    suppress_output=False,
                    log_level="echo",
                    abort_on_error=False,
                )

            for cmd in [
                "ls -l $HOME/.config",
                "ls -l $HOME/.config/gh",
                "ls -l $HOME/.config/gh/config.yml",
                "touch $HOME/.config/gh/config.yml",
                "ls -l $HOME/.config/gh/config.yml",
            ]:
                _cmd(cmd)
        cmd = "echo $GH_ACTION_ACCESS_TOKEN | gh auth login --with-token"
        hsysinte.system(cmd)
    # Check that we are logged in.
    cmd = "gh auth status"
    hsysinte.system(cmd)


class TestGhLogin1(hunitest.TestCase):
    def test_gh_login(self) -> None:
        _gh_login()


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

    # TODO(gp): We can't test this since amp and cmamp have now different base image.
    # def test_print_setup(self) -> None:
    #     target = "print_setup"
    #     self._dry_run(target)

    def test_git_pull(self) -> None:
        target = "git_pull"
        self._dry_run(target)

    def test_git_pull_master(self) -> None:
        target = "git_pull_master"
        self._dry_run(target)

    def test_git_clean(self) -> None:
        target = "git_clean"
        self._dry_run(target)

    # ################################################################################
    # TODO(gp): -> TestDockerCommands1

    @pytest.mark.skipif(
        hsysinte.is_inside_ci(), reason="In CI the output is different"
    )
    def test_docker_images_ls_repo(self) -> None:
        target = "docker_images_ls_repo"
        self._dry_run(target)

    def test_docker_ps(self) -> None:
        target = "docker_ps"
        self._dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_stats(self) -> None:
        target = "docker_stats"
        self._dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_last(self) -> None:
        target = "docker_kill"
        self._dry_run(target)

    @pytest.mark.skip(
        reason="AmpTask1347: Add support for mocking `system*()` "
        "functions to unit test"
    )
    def test_docker_kill_all(self) -> None:
        target = "docker_kill --all"
        self._dry_run(target)

    # ################################################################################

    def _dry_run(self, target: str, dry_run: bool = True) -> None:
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
        _, act = hsysinte.system_to_string(cmd)
        act = hprint.remove_non_printable_chars(act)
        self.check_string(act)


# #############################################################################


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

    def test_git_pull_master(self) -> None:
        target = "git_pull_master(ctx)"
        self._check_output(target)

    def test_git_clean(self) -> None:
        target = "git_clean(ctx)"
        self._check_output(target)

    def test_git_clean2(self) -> None:
        target = "git_clean(ctx, dry_run=False)"
        self._check_output(target)

    # ################################################################################

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

    # ################################################################################
    # TODO(gp): -> TestGhCommands1

    def test_gh_create_pr1(self) -> None:
        _gh_login()
        target = "gh_create_pr(ctx, repo_short_name='amp', title='test')"
        self._check_output(target)

    def test_gh_create_pr2(self) -> None:
        _gh_login()
        target = "gh_create_pr(ctx, body='hello_world', repo_short_name='amp', title='test')"
        self._check_output(target)

    def test_gh_create_pr3(self) -> None:
        _gh_login()
        target = (
            "gh_create_pr(ctx, draft=False, repo_short_name='amp', title='test')"
        )
        self._check_output(target)

    def test_gh_issue_title(self) -> None:
        _gh_login()
        target = "gh_issue_title(ctx, 1)"
        self._check_output(target)

    @pytest.mark.skipif(not hgit.is_amp(), reason="Only run in amp")
    def test_gh_workflow_list(self) -> None:
        _gh_login()
        target = "gh_workflow_list(ctx, branch='master')"
        self._check_output(target)

    # This is an action with side effects so we can't test it.
    # def test_gh_workflow_run(self) -> None:
    #     target = "gh_workflow_run(ctx)"
    #     self._check_output(target)

    # ################################################################################
    # TODO(gp): -> TestGitCommands1
    @pytest.mark.slow("7 seconds.")
    def test_git_branch_files(self) -> None:
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        target = "git_branch_files(ctx)"
        self._check_output(target)

    def test_git_create_branch1(self) -> None:
        target = (
            "git_create_branch(ctx, branch_name='test', "
            "only_branch_from_master=False)"
        )
        self._check_output(target)

    def test_git_create_branch2(self) -> None:
        target = (
            "git_create_branch(ctx, issue_id=1, repo_short_name='amp', "
            "only_branch_from_master=False)"
        )
        self._check_output(target)

    def test_git_create_branch3(self) -> None:
        with self.assertRaises(AssertionError):
            target = (
                "git_create_branch(ctx, branch_name='test', issue_id=1, "
                "only_branch_from_master=False)"
            )
            self._check_output(target, check=False)

    # This is an action with side effects so we can't test it.
    # def test_git_delete_merged_branches(self) -> None:
    #     target = "git_delete_merged_branches(ctx)"
    #     self._check_output(target)

    def test_git_merge_master(self) -> None:
        target = "git_merge_master(ctx)"
        self._check_output(target)

    # ################################################################################
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
        hsysinte.is_inside_ci(), reason="In CI the output is different"
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
        self._check_calls(ctx)


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
# - pytest_failed (with checked in file)
# - lint

# #############################################################################


class TestLibTasks1(hunitest.TestCase):
    """
    Test some auxiliary functions, e.g., `_get_gh_issue_title()`.
    """

    def test_get_gh_issue_title1(self) -> None:
        _gh_login()
        issue_id = 1
        repo = "amp"
        act = hlibtask._get_gh_issue_title(issue_id, repo)
        exp = (
            "AmpTask1_Bridge_Python_and_R",
            "https://github.com/alphamatic/amp/issues/1",
        )
        self.assert_equal(str(act), str(exp))

    @pytest.mark.skipif(
        not hgit.is_cmamp(),
        reason="CmampTask #683.",
    )
    def test_get_gh_issue_title3(self) -> None:
        _gh_login()
        issue_id = 1
        repo = "dev_tools"
        act = hlibtask._get_gh_issue_title(issue_id, repo)
        exp = (
            "DevToolsTask1_Migration_from_amp",
            "https://github.com/alphamatic/dev_tools/issues/1",
        )
        self.assert_equal(str(act), str(exp))

    def test_get_gh_issue_title4(self) -> None:
        _gh_login()
        issue_id = 1
        repo = "current"
        _ = hlibtask._get_gh_issue_title(issue_id, repo)


# #############################################################################


class TestLibTasksRemoveSpaces1(hunitest.TestCase):
    def test1(self) -> None:
        txt = r"""
            IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp_test:dev \
                docker-compose \
                --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
                run \
                --rm \
                -l user=$USER_NAME \
                --entrypoint bash \
                user_space
            """
        act = hlibtask._to_single_line_cmd(txt)
        exp = (
            "IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp_test:dev"
            " docker-compose --file"
            " $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml"
            " run --rm -l user=$USER_NAME --entrypoint bash user_space"
        )
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class TestLibTasksGetDockerCmd1(_LibTasksTestCase):
    """
    Test `_get_docker_cmd()`.
    """

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Only run in amp as submodule"
    )
    def test_docker_bash1(self) -> None:
        """
        Command for docker_bash target.
        """
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        cmd = "bash"
        service_name = "app"
        entrypoint = False
        print_docker_config = False
        act = hlibtask._get_docker_cmd(
            base_image,
            stage,
            version,
            cmd,
            service_name=service_name,
            entrypoint=entrypoint,
            print_docker_config=print_docker_config,
        )
        exp = r"""
        IMAGE=*****/amp_test:dev-1.0.0 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env \
            run \
            --rm \
            --entrypoint bash \
            app
        """
        self._check(act, exp)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Only run in amp as submodule"
    )
    def test_docker_bash2(self) -> None:
        """
        Command for docker_bash with entrypoint.
        """
        base_image = ""
        stage = "local"
        version = "1.0.0"
        cmd = "bash"
        print_docker_config = False
        act = hlibtask._get_docker_cmd(
            base_image, stage, version, cmd, print_docker_config=print_docker_config
        )
        exp = r"""
        IMAGE=*****/amp_test:local \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env \
            run \
            --rm \
            app \
            bash
        """
        self._check(act, exp)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Only run in amp as submodule"
    )
    def test_docker_bash3(self) -> None:
        """
        Command for docker_bash with some env vars.
        """
        base_image = ""
        stage = "local"
        version = "1.0.0"
        cmd = "bash"
        extra_env_vars = ["PORT=9999", "SKIP_RUN=1"]
        print_docker_config = False
        act = hlibtask._get_docker_cmd(
            base_image,
            stage,
            version,
            cmd,
            extra_env_vars=extra_env_vars,
            print_docker_config=print_docker_config,
        )
        exp = r"""
        IMAGE=*****/amp_test:local-1.0.0 \
        PORT=9999 \
        SKIP_RUN=1 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env \
            run \
            --rm \
            app \
            bash
        """
        self._check(act, exp)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Only run in amp as supermodule",
    )
    def test_docker_bash4(self) -> None:
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        cmd = "bash"
        entrypoint = False
        print_docker_config = False
        act = hlibtask._get_docker_cmd(
            base_image,
            stage,
            version,
            cmd,
            entrypoint=entrypoint,
            print_docker_config=print_docker_config,
        )
        exp = r"""
        IMAGE=*****/amp_test:dev-1.0.0 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml \
            --env-file devops/env/default.env \
            run \
            --rm \
            --entrypoint bash \
            app
        """
        self._check(act, exp)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Only run in amp as submodule"
    )
    def test_docker_jupyter1(self) -> None:
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        port = 9999
        self_test = True
        print_docker_config = False
        act = hlibtask._get_docker_jupyter_cmd(
            stage,
            base_image,
            version,
            port,
            self_test,
            print_docker_config=print_docker_config,
        )
        exp = r"""
        IMAGE=*****/amp_test:dev \
        PORT=9999 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env \
            run \
            --rm \
            --service-ports \
            jupyter_server_test
        """
        self._check(act, exp)

    def _check(self, act: str, exp: str) -> None:
        act = hunitest.purify_txt_from_client(act)
        # This is required when different repos run Docker with user vs root / remap.
        act = hunitest.filter_text("--user", act)
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_build_run_command_line1(hunitest.TestCase):
    def test_run_fast_tests1(self) -> None:
        """
        Basic run fast tests.
        """
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = False
        #
        act = hlibtask._build_run_command_line(
            "fast_tests",
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
        )
        exp = 'pytest -m "not slow and not superslow" . --timeout 5'
        self.assert_equal(act, exp)

    def test_run_fast_tests2(self) -> None:
        """
        Coverage and collect-only.
        """
        pytest_opts = ""
        skip_submodules = False
        coverage = True
        collect_only = True
        tee_to_file = False
        #
        act = hlibtask._build_run_command_line(
            "fast_tests",
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
        )
        exp = (
            r'pytest -m "not slow and not superslow" . --timeout 5 --cov=. --cov-branch'
            r" --cov-report term-missing --cov-report html --collect-only"
        )
        self.assert_equal(act, exp)

    @pytest.mark.skip(reason="Fix support for pytest_mark")
    @pytest.mark.skipif(not hgit.is_amp(), reason="Only run in amp")
    def test_run_fast_tests4(self) -> None:
        """
        Select pytest_mark.
        """
        scratch_space = self.get_scratch_space(use_absolute_path=False)
        dir_name = os.path.join(scratch_space, "test")
        file_dict = {
            "test_this.py": hprint.dedent(
                """
                    foo

                    class TestHelloWorld(hunitest.TestCase):
                        bar
                    """
            ),
            "test_that.py": hprint.dedent(
                """
                    foo
                    baz

                    @pytest.mark.no_container
                    class TestHello_World(hunitest.):
                        bar
                    """
            ),
        }
        incremental = True
        hunitest.create_test_dir(dir_name, incremental, file_dict)
        #
        pytest_opts = ""
        dir_name = scratch_space
        skip_submodules = True
        coverage = False
        collect_only = False
        tee_to_file = False
        #
        act = hlibtask._build_run_command_line(
            "fast_tests",
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
        )
        exp = (
            "pytest Test_build_run_command_line1.test_run_fast_tests4/tmp.scratch/"
            "test/test_that.py"
        )
        self.assert_equal(act, exp)

    def test_run_fast_tests5(self) -> None:
        """
        Basic run fast tests tee-ing to a file.
        """
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = True
        #
        act = hlibtask._build_run_command_line(
            "fast_tests",
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
        )
        exp = 'pytest -m "not slow and not superslow" . --timeout 5 2>&1 | tee tmp.pytest.fast_tests.log'
        self.assert_equal(act, exp)


# #############################################################################


class TestLibTasksRunTests1(hunitest.TestCase):
    """
    Test `_find_test_files()`, `_find_test_decorator()`.
    """

    def test_find_test_files1(self) -> None:
        """
        Find all the test files in the current dir.
        """
        files = hlibtask._find_test_files()
        # For sure there are more than 1 test files: at least this one.
        self.assertGreater(len(files), 1)

    def test_find_test_files2(self) -> None:
        """
        Find all the test files from the top of the super module root.
        """
        git_root = hgit.get_client_root(super_module=True)
        files = hlibtask._find_test_files(git_root)
        # For sure there are more than 1 test files: at least this one.
        self.assertGreater(len(files), 1)

    def test_find_test_class1(self) -> None:
        """
        Find the current test class.
        """
        git_root = hgit.get_client_root(super_module=True)
        file_names = hlibtask._find_test_files(git_root)
        #
        file_names = hlibtask._find_test_class(
            "TestLibTasksRunTests1", file_names
        )
        act = hunitest.purify_file_names(file_names)
        exp = ["helpers/test/test_lib_tasks.py::TestLibTasksRunTests1"]
        self.assert_equal(str(act), str(exp))

    def test_find_test_class2(self) -> None:
        """
        Find the current test class.
        """
        file_names = [__file__]
        #
        file_names = hlibtask._find_test_class(
            "TestLibTasksRunTests1", file_names
        )
        act = hunitest.purify_file_names(file_names)
        exp = ["helpers/test/test_lib_tasks.py::TestLibTasksRunTests1"]
        self.assert_equal(str(act), str(exp))

    def test_find_test_class3(self) -> None:
        """
        Create synthetic code and look for a class.
        """
        scratch_space = self.get_scratch_space()
        dir_name = os.path.join(scratch_space, "test")
        file_dict = {
            "test_this.py": hprint.dedent(
                """
                    foo

                    class TestHelloWorld(hunitest.TestCase):
                        bar
                    """
            ),
            "test_that.py": hprint.dedent(
                """
                    foo
                    baz

                    class TestHello_World(hunitest.):
                        bar
                    """
            ),
        }
        incremental = True
        hunitest.create_test_dir(dir_name, incremental, file_dict)
        #
        file_names = hlibtask._find_test_files(dir_name)
        act_file_names = [os.path.relpath(d, scratch_space) for d in file_names]
        exp_file_names = ["test/test_that.py", "test/test_this.py"]
        self.assert_equal(str(act_file_names), str(exp_file_names))
        #
        act = hlibtask._find_test_class("TestHelloWorld", file_names)
        act = hunitest.purify_file_names(act)
        exp = [
            "helpers/test/TestLibTasksRunTests1.test_find_test_class3/tmp.scratch/"
            "test/test_this.py::TestHelloWorld"
        ]
        self.assert_equal(str(act), str(exp))

    def test_find_test_decorator1(self) -> None:
        """
        Find test functions in the "no_container" in synthetic code.
        """
        scratch_space = self.get_scratch_space()
        dir_name = os.path.join(scratch_space, "test")
        file_dict = {
            "test_this.py": hprint.dedent(
                """
                    foo

                    class TestHelloWorld(hunitest.TestCase):
                        bar
                    """
            ),
            "test_that.py": hprint.dedent(
                """
                    foo
                    baz

                    @pytest.mark.no_container
                    class TestHello_World(hunitest.):
                        bar
                    """
            ),
        }
        incremental = True
        hunitest.create_test_dir(dir_name, incremental, file_dict)
        #
        file_names = hlibtask._find_test_files(dir_name)
        act = hlibtask._find_test_decorator("no_container", file_names)
        act = hunitest.purify_file_names(act)
        exp = [
            "helpers/test/TestLibTasksRunTests1.test_find_test_decorator1/"
            "tmp.scratch/test/test_that.py"
        ]
        self.assert_equal(str(act), str(exp))

    @pytest.mark.skipif(not hgit.is_amp(), reason="Only run in amp")
    def test_find_test_decorator2(self) -> None:
        """
        Find test functions in the "no_container" test list.
        """
        file_names = ["test/test_tasks.py"]
        act = hlibtask._find_test_decorator("no_container", file_names)
        act = hunitest.purify_file_names(act)
        exp = ["test/test_tasks.py"]
        self.assert_equal(str(act), str(exp))


# #############################################################################

@pytest.mark.slow(reason="slow via gh actions #687.")
class TestLibTasksGitCreatePatch1(hunitest.TestCase):
    """
    Test `git_create_patch()`.
    """

    def test_tar_modified1(self) -> None:
        """
        Exercise the code for:

        > invoke git_create_patch ... --branch
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = True
        branch = False
        last_commit = False
        files = ""
        self._helper(modified, branch, last_commit, files)

    def test_tar_branch1(self) -> None:
        """
        Exercise the code for:

        > invoke git_create_patch ... --modified
        """
        modified = False
        branch = True
        last_commit = False
        files = ""
        self._helper(modified, branch, last_commit, files)

    def test_tar_last_commit1(self) -> None:
        """
        Exercise the code for:

        > invoke git_create_patch ... --last-commit
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = False
        branch = False
        last_commit = True
        files = ""
        self._helper(modified, branch, last_commit, files)

    def test_tar_files1(self) -> None:
        """
        Exercise the code for:

        > invoke git_create_patch \
                --mode="tar" \
                --files "this file" \
                --modified
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        ctx = _build_mock_context_returning_ok()
        mode = "tar"
        modified = True
        branch = False
        last_commit = False
        files = __file__
        hlibtask.git_create_patch(ctx, mode, modified, branch, last_commit, files)

    def test_diff_files_abort1(self) -> None:
        """
        Exercise the code for:

        > invoke git_create_patch --mode="diff" --files "this file"

        In this case one needs to specify at least one --branch, --modified,
        --last-commit option.
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        ctx = _build_mock_context_returning_ok()
        mode = "diff"
        modified = False
        branch = False
        last_commit = False
        files = __file__
        with self.assertRaises(AssertionError) as cm:
            hlibtask.git_create_patch(
                ctx, mode, modified, branch, last_commit, files
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '0'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    @staticmethod
    def _helper(
        modified: bool, branch: bool, last_commit: bool, files: str
    ) -> None:
        ctx = _build_mock_context_returning_ok()
        #
        mode = "tar"
        hlibtask.git_create_patch(ctx, mode, modified, branch, last_commit, files)
        #
        mode = "diff"
        hlibtask.git_create_patch(ctx, mode, modified, branch, last_commit, files)


# #############################################################################


class Test_parse_linter_output1(hunitest.TestCase):
    """
    Test `_parse_linter_output()`.
    """

    def test1(self) -> None:
        # pylint: disable=line-too-long
        txt = r"""
Tabs remover.............................................................Passed
autoflake................................................................Passed
isort....................................................................Failed
- hook id: isort
- files were modified by this hook

INFO: > cmd='/app/linters/amp_isort.py core/dataflow/builders.py core/test/test_core.py core/dataflow/nodes.py helpers/printing.py helpers/lib_tasks.py core/data_adapters.py helpers/test/test_dbg.py helpers/unit_test.py core/dataflow/core.py core/finance.py core/dataflow/models.py core/dataflow/visualization.py helpers/dbg.py helpers/test/test_git.py core/dataflow/runners.py core/dataflow/test/test_visualization.py helpers/test/test_lib_tasks.py'
Fixing /src/amp/core/dataflow/builders.py
Fixing /src/amp/core/data_adapters.py
Fixing /src/amp/core/dataflow/models.py

black....................................................................Passed
flake8...................................................................Failed
- hook id: flake8
- exit code: 6

INFO: > cmd='/app/linters/amp_flake8.py core/dataflow/builders.py core/test/test_core.py core/dataflow/nodes.py helpers/printing.py'
core/dataflow/nodes.py:601:9: F821 undefined name '_check_col_names'
core/dataflow/nodes.py:608:9: F821 undefined name '_check_col_names'
INFO: > cmd='/app/linters/amp_flake8.py helpers/lib_tasks.py core/data_adapters.py helpers/test/test_dbg.py helpers/unit_test.py'
helpers/lib_tasks.py:302:12: W605 invalid escape sequence '\g'
helpers/lib_tasks.py:309:27: W605 invalid escape sequence '\s'
helpers/lib_tasks.py:309:31: W605 invalid escape sequence '\S'
helpers/lib_tasks.py:309:35: W605 invalid escape sequence '\('
helpers/lib_tasks.py:2184:9: F541 f-string is missing placeholders
helpers/test/test_dbg.py:71:25: F821 undefined name 'y'
INFO: > cmd='/app/linters/amp_flake8.py core/dataflow/core.py core/finance.py core/dataflow/models.py core/dataflow/visualization.py'
core/finance.py:250:5: E301 expected 1 blank line, found 0
INFO: > cmd='/app/linters/amp_flake8.py helpers/dbg.py helpers/test/test_git.py core/dataflow/runners.py core/dataflow/test/test_visualization.py'

INFO: > cmd='/app/linters/amp_flake8.py helpers/test/test_lib_tasks.py'
helpers/test/test_lib_tasks.py:225:5: F811 redefinition of unused 'test_git_clean' from line 158

doc_formatter............................................................Passed
pylint...................................................................
"""
        # pylint: enable=line-too-long
        act = hlibtask._parse_linter_output(txt)
        # pylint: disable=line-too-long
        exp = r"""
core/dataflow/nodes.py:601:9:[flake8] F821 undefined name '_check_col_names'
core/dataflow/nodes.py:608:9:[flake8] F821 undefined name '_check_col_names'
core/finance.py:250:5:[flake8] E301 expected 1 blank line, found 0
helpers/lib_tasks.py:2184:9:[flake8] F541 f-string is missing placeholders
helpers/lib_tasks.py:302:12:[flake8] W605 invalid escape sequence '\g'
helpers/lib_tasks.py:309:27:[flake8] W605 invalid escape sequence '\s'
helpers/lib_tasks.py:309:31:[flake8] W605 invalid escape sequence '\S'
helpers/lib_tasks.py:309:35:[flake8] W605 invalid escape sequence '\('
helpers/test/test_dbg.py:71:25:[flake8] F821 undefined name 'y'
helpers/test/test_lib_tasks.py:225:5:[flake8] F811 redefinition of unused 'test_git_clean' from line 158
"""
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        # pylint: disable=line-too-long
        txt = """
BUILD_TAG='dev_tools-1.0.0-20210513-DevTools196_Switch_from_makefile_to_invoke-e9ee441a1144883d2e8835740cba4dc09e7d4f2a'
PRE_COMMIT_HOME=/root/.cache/pre-commit
total 44
-rw-r--r-- 1 root root   109 May 13 12:54 README
-rw------- 1 root root 20480 May 13 12:54 db.db
drwx------ 4 root root  4096 May 13 12:54 repo0a8anbxn
drwx------ 8 root root  4096 May 13 12:54 repodla_5o4g
drwx------ 9 root root  4096 May 13 12:54 repoeydyv2ho
drwx------ 7 root root  4096 May 13 12:54 repokrr14v6z
drwx------ 4 root root  4096 May 13 12:54 repozqvepk0i
5
which python: /venv/bin/python
check pandas package: <module 'pandas' from '/venv/lib/python3.8/site-packages/pandas/__init__.py'>
PATH=/app/linters:/app/dev_scripts/eotebooks:/app/documentation/scripts:/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PYTHONPATH=/app:
cmd: 'pre-commit run -c /app/.pre-commit-config.yaml --files ./core/dataflow/builders.py'
Don't commit to branch...................................................^[[42mPassed^[[m
Check for merge conflicts................................................^[[42mPassed^[[m
Trim Trailing Whitespace.................................................^[[42mPassed^[[m
Fix End of Files.........................................................^[[42mPassed^[[m
Check for added large files..............................................^[[42mPassed^[[m
CRLF end-lines remover...................................................^[[42mPassed^[[m
Tabs remover.............................................................^[[42mPassed^[[m
autoflake................................................................^[[42mPassed^[[m
isort....................................................................^[[42mPassed^[[m
black....................................................................^[[42mPassed^[[m
flake8...................................................................^[[42mPassed^[[m
doc_formatter............................................................^[[42mPassed^[[m
pylint...................................................................^[[41mFailed^[[m
^[[2m- hook id: pylint^[[m
^[[2m- exit code: 3^[[m

^[[33mWARNING^[[0m: No module named 'pandas'
^[[33mWARNING^[[0m: No module named 'matplotlib'
^[[0m^[[36mINFO^[[0m: > cmd='/app/linters/amp_pylint.py core/dataflow/builders.py'
************* Module core.dataflow.builders
core/dataflow/builders.py:104: [R1711(useless-return), DagBuilder.get_column_to_tags_mapping] Useless return at end of function or method
core/dataflow/builders.py:195: [W0221(arguments-differ), ArmaReturnsBuilder.get_dag] Parameters differ from overridden 'get_dag' method

mypy.....................................................................^[[41mFailed^[[m
^[[2m- hook id: mypy^[[m
^[[2m- exit code: 3^[[m

^[[0m^[[36mINFO^[[0m: > cmd='/app/linters/amp_mypy.py core/dataflow/builders.py'
core/dataflow/builders.py:125: error: Returning Any from function declared to return "str"  [no-any-return]
core/dataflow/builders.py:195: error: Argument 2 of "get_dag" is incompatible with supertype "DagBuilder"; supertype defines the argument type as "Optional[Any]"  [override]
core/dataflow/builders.py:195: note: This violates the Liskov substitution principle
        """
        # pylint: enable=line-too-long
        act = hlibtask._parse_linter_output(txt)
        # pylint: disable=line-too-long
        exp = r"""
core/dataflow/builders.py:104:[pylint] [R1711(useless-return), DagBuilder.get_column_to_tags_mapping] Useless return at end of function or method
core/dataflow/builders.py:125:[mypy] error: Returning Any from function declared to return "str"  [no-any-return]
core/dataflow/builders.py:195:[mypy] error: Argument 2 of "get_dag" is incompatible with supertype "DagBuilder"; supertype defines the argument type as "Optional[Any]"  [override]
core/dataflow/builders.py:195:[mypy] note: This violates the Liskov substitution principle
core/dataflow/builders.py:195:[pylint] [W0221(arguments-differ), ArmaReturnsBuilder.get_dag] Parameters differ from overridden 'get_dag' method
"""
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_find_check_string_output1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `find_check_string_output()` by searching the `check_string` of
        this test.
        """
        # Force to generate a `check_string` file so we can search for it.
        act = "A fake check_string output to use for test1"
        self.check_string(act)
        # Check.
        exp = '''
        act =
        exp = r"""
        A fake check_string output to use for test1
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=False)
        '''
        self._helper(exp, fuzzy_match=False)

    def test2(self) -> None:
        """
        Like test1 but using `fuzzy_match=True`.
        """
        # Force to generate a `check_string` file so we can search for it.
        act = "A fake check_string output to use for test2"
        self.check_string(act)
        # Check.
        exp = '''
        act =
        exp = r"""
A fake check_string output to use for test2
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)
        '''
        self._helper(exp, fuzzy_match=True)

    def _helper(self, exp: str, fuzzy_match: bool) -> None:
        # Look for the `check_string()` corresponding to this test.
        ctx = _build_mock_context_returning_ok()
        class_name = self.__class__.__name__
        method_name = self._testMethodName
        as_python = True
        # We don't want to copy but just print.
        pbcopy = False
        act = hlibtask.find_check_string_output(
            ctx, class_name, method_name, as_python, fuzzy_match, pbcopy
        )
        # Check that it matches exactly.
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class Test_get_files_to_process1(hunitest.TestCase):
    """
    We can't check the outcome so we just execute the code.
    """

    def test_modified1(self) -> None:
        """
        Retrieve files modified in this client.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlibtask._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    @pytest.mark.skipif(
        hgit.get_branch_name() != "master",
        reason="This test makes sense for a branch",
    )
    def test_branch1(self) -> None:
        """
        Retrieved files modified in this client.
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = False
        branch = True
        last_commit = False
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlibtask._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    def test_last_commit1(self) -> None:
        """
        Retrieved files modified in the last commit.
        """
        modified = False
        branch = False
        last_commit = True
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlibtask._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    def test_files1(self) -> None:
        """
        Pass through files from user.
        """
        modified = False
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = True
        remove_dirs = True
        files = hlibtask._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        self.assertEqual(files, [__file__])

    def test_assert1(self) -> None:
        """
        Test that --modified and --branch together cause an assertion.
        """
        modified = True
        branch = True
        last_commit = False
        all_ = True
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        with self.assertRaises(AssertionError) as cm:
            hlibtask._get_files_to_process(
                modified,
                branch,
                last_commit,
                all_,
                files_from_user,
                mutually_exclusive,
                remove_dirs,
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '3'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit, --all_files, and --files
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert2(self) -> None:
        """
        Test that --modified and --files together cause an assertion if
        `mutually_exclusive=True`.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = True
        remove_dirs = True
        with self.assertRaises(AssertionError) as cm:
            hlibtask._get_files_to_process(
                modified,
                branch,
                last_commit,
                all_,
                files_from_user,
                mutually_exclusive,
                remove_dirs,
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '2'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit, --all_files, and --files
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert3(self) -> None:
        """
        Test that --modified and --files together don't cause an assertion if
        `mutually_exclusive=False`.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = False
        remove_dirs = True
        files = hlibtask._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        self.assertEqual(files, [__file__])


# #############################################################################


class Test_pytest_failed1(hunitest.TestCase):
    def test_tests1(self) -> None:
        file_name = self._build_pytest_file1()
        target_type = "tests"
        exp = [
            "dev_scripts/testing/test/test_run_tests.py",
            "dev_scripts/testing/test/test_run_tests2.py",
            "helpers/test/test_printing.py::Test_dedent1::test2",
            "documentation/scripts/test/test_all.py",
            "documentation/scripts/test/test_render_md.py",
            "helpers/test/helpers/test/test_list.py::Test_list_1",
            "helpers/test/test_cache.py::TestAmpTask1407",
        ]
        self._helper(file_name, target_type, exp)

    def test_files1(self) -> None:
        file_name = self._build_pytest_file1()
        target_type = "files"
        exp = [
            "dev_scripts/testing/test/test_run_tests.py",
            "dev_scripts/testing/test/test_run_tests2.py",
            "helpers/test/test_printing.py",
            "documentation/scripts/test/test_all.py",
            "documentation/scripts/test/test_render_md.py",
            "helpers/test/helpers/test/test_list.py",
            "helpers/test/test_cache.py",
        ]
        self._helper(file_name, target_type, exp)

    def test_classes1(self) -> None:
        file_name = self._build_pytest_file1()
        target_type = "classes"
        exp = [
            "helpers/test/test_printing.py::Test_dedent1",
            "helpers/test/helpers/test/test_list.py::Test_list_1",
            "helpers/test/test_cache.py::TestAmpTask1407",
        ]
        self._helper(file_name, target_type, exp)

    def test_tests2(self) -> None:
        file_name = self._build_pytest_file2()
        target_type = "tests"
        # pylint: disable=line-too-long
        exp = [
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_compare_to_linear_regression1",
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_compare_to_linear_regression2",
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_fit1",
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_fit_no_x1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test2",
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test3",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test2",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test3",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test2",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test3",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test4",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test01",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test02",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test03",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test04",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test05",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test06",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test07",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test09",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test10",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test11",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test12",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test13",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_col_mode1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_col_mode2",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_demodulate1",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_modulate1",
            "core/dataflow/test/test_builders.py::TestArmaReturnsBuilder::test1",
            "core/dataflow/test/test_runners.py::TestIncrementalDagRunner::test1",
            "core/dataflow_model/test/test_model_evaluator.py::TestModelEvaluator::test_dump_json1",
            "core/dataflow_model/test/test_model_evaluator.py::TestModelEvaluator::test_load_json1",
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test1",
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test2",
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test3",
            "core/test/test_config.py::Test_subtract_config1::test_test1",
            "core/test/test_config.py::Test_subtract_config1::test_test2",
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_dump_json1",
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_load_json1",
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_load_json2",
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test1",
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test2",
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test3",
            "helpers/test/test_lib_tasks.py::Test_find_check_string_output1::test2",
            "helpers/test/test_printing.py::Test_dedent1::test2",
        ]
        # pylint: enable=line-too-long
        self._helper(file_name, target_type, exp)

    def test_files2(self) -> None:
        file_name = self._build_pytest_file2()
        target_type = "files"
        # pylint: disable=line-too-long
        exp = [
            "core/dataflow/nodes/test/test_sarimax_models.py",
            "core/dataflow/nodes/test/test_volatility_models.py",
            "core/dataflow/test/test_builders.py",
            "core/dataflow/test/test_runners.py",
            "core/dataflow_model/test/test_model_evaluator.py",
            "core/dataflow_model/test/test_run_experiment.py",
            "core/test/test_config.py",
            "core/test/test_dataframe_modeler.py",
            "dev_scripts/test/test_run_notebook.py",
            "helpers/test/test_lib_tasks.py",
            "helpers/test/test_printing.py",
        ]
        # pylint: enable=line-too-long
        self._helper(file_name, target_type, exp)

    def test_classes2(self) -> None:
        file_name = self._build_pytest_file2()
        target_type = "classes"
        # pylint: disable=line-too-long
        exp = [
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel",
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel",
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel",
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator",
            "core/dataflow/test/test_builders.py::TestArmaReturnsBuilder",
            "core/dataflow/test/test_runners.py::TestIncrementalDagRunner",
            "core/dataflow_model/test/test_model_evaluator.py::TestModelEvaluator",
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1",
            "core/test/test_config.py::Test_subtract_config1",
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler",
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1",
            "helpers/test/test_lib_tasks.py::Test_find_check_string_output1",
            "helpers/test/test_printing.py::Test_dedent1",
        ]
        # pylint: enable=line-too-long
        self._helper(file_name, target_type, exp)

    # #########################################################################

    def _build_pytest_file_helper(self, txt: str) -> str:
        txt = hprint.dedent(txt)
        file_name = os.path.join(self.get_scratch_space(), "input.txt")
        hio.to_file(file_name, txt)
        return file_name

    def _build_pytest_file1(self) -> str:
        txt = """
        {
            "dev_scripts/testing/test/test_run_tests.py": true,
            "dev_scripts/testing/test/test_run_tests2.py": true,
            "helpers/test/test_printing.py::Test_dedent1::test2": true,
            "documentation/scripts/test/test_all.py": true,
            "documentation/scripts/test/test_render_md.py": true,
            "helpers/test/helpers/test/test_list.py::Test_list_1": true,
            "helpers/test/test_cache.py::TestAmpTask1407": true
        }
        """
        return self._build_pytest_file_helper(txt)

    def _build_pytest_file2(self) -> str:
        # pylint: disable=line-too-long
        txt = """
        {
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_compare_to_linear_regression1": true,
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_compare_to_linear_regression2": true,
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_fit1": true,
            "core/dataflow/nodes/test/test_sarimax_models.py::TestContinuousSarimaxModel::test_fit_no_x1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test2": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestMultiindexVolatilityModel::test3": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test2": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSingleColumnVolatilityModel::test3": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test2": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test3": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test4": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test01": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test02": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test03": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test04": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test05": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test06": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test07": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test09": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test10": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test11": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test12": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModel::test13": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_col_mode1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_col_mode2": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_demodulate1": true,
            "core/dataflow/nodes/test/test_volatility_models.py::TestVolatilityModulator::test_modulate1": true,
            "core/dataflow/test/test_builders.py::TestArmaReturnsBuilder::test1": true,
            "core/dataflow/test/test_runners.py::TestIncrementalDagRunner::test1": true,
            "core/dataflow_model/test/test_model_evaluator.py::TestModelEvaluator::test_dump_json1": true,
            "core/dataflow_model/test/test_model_evaluator.py::TestModelEvaluator::test_load_json1": true,
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test1": true,
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test2": true,
            "core/dataflow_model/test/test_run_experiment.py::TestRunExperiment1::test3": true,
            "core/test/test_config.py::Test_subtract_config1::test_test1": true,
            "core/test/test_config.py::Test_subtract_config1::test_test2": true,
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_dump_json1": true,
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_load_json1": true,
            "core/test/test_dataframe_modeler.py::TestDataFrameModeler::test_load_json2": true,
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test1": true,
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test2": true,
            "dev_scripts/test/test_run_notebook.py::TestRunNotebook1::test3": true,
            "helpers/test/test_lib_tasks.py::Test_find_check_string_output1::test2": true,
            "helpers/test/test_printing.py::Test_dedent1::test2": true
        }
        """
        # pylint: enable=line-too-long
        return self._build_pytest_file_helper(txt)

    def _helper(self, file_name: str, target_type: str, exp: List[str]) -> None:
        ctx = _build_mock_context_returning_ok()
        # It is a dummy parameter when `file_name` is specified.
        use_frozen_list = True
        act = hlibtask.pytest_failed(
            ctx,
            use_frozen_list=use_frozen_list,
            target_type=target_type,
            file_name=file_name,
            pbcopy=False,
        )
        exp = " ".join(exp)
        self.assert_equal(act, exp)
