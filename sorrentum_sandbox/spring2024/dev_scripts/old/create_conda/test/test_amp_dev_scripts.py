import logging
import os
from typing import List

import pytest

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import helpers.old.conda as holdcond

_LOG = logging.getLogger(__name__)


# #############################################################################
# _setenv.py
# #############################################################################

# TODO(gp): Call _setenv.py as a library to increase converage and get
#  annotations from pyannotate.


@pytest.mark.skip("Deprecated after switch to Docker dev env")
class Test_set_env_amp(hunitest.TestCase):
    def test_setenv_py1(self) -> None:
        """
        Find _setenv_amp.py executable and run it.
        """
        executable = hgit.find_file_in_git_tree(
            "_setenv_amp.py", super_module=False
        )
        executable = os.path.abspath(executable)
        _LOG.debug("executable=%s", executable)
        hdbg.dassert_path_exists(executable)
        hsystem.system(executable)

    # Since there are dependency from the user environment, we freeze a
    # particular run of _setenv_amp.py.
    @pytest.mark.skipif('hsystem.get_user_name() != "saggese"')
    def test_setenv_py2(self) -> None:
        """
        Find _setenv_amp.py executable, run it, and freeze the output.
        """
        executable = hgit.find_file_in_git_tree(
            "_setenv_amp.py", super_module=False
        )
        executable = os.path.abspath(executable)
        _LOG.debug("executable=%s", executable)
        hdbg.dassert_path_exists(executable)
        # Run _setup.py and get its output.
        _, txt = hsystem.system_to_string(executable)
        # There is a difference between running the same test from different
        # repos, so we remove this line.
        txt = hunitest.filter_text("curr_path=", txt)
        txt = hunitest.filter_text("server_name=", txt)
        self.check_string(txt)

    def test_setenv_sh1(self) -> None:
        """
        Execute setenv_amp.sh.
        """
        executable = hgit.find_file_in_git_tree(
            "setenv_amp.sh", super_module=False
        )
        executable = os.path.abspath(executable)
        _LOG.debug("executable=%s", executable)
        hdbg.dassert_path_exists(executable)
        cmd = f"source {executable} amp_develop"
        hsystem.system(cmd)


# #############################################################################
# create_conda.py
# #############################################################################


@pytest.mark.skip("Deprecated after switch to Docker dev env")
class Test_install_create_conda_py1(hunitest.TestCase):
    @pytest.mark.slow
    def test_create_conda_test_install1(self) -> None:
        """
        Run create_conda with --test_install to exercise the script.
        """
        cmd_opts = [""]
        env_name = "test_install"
        cmd_opts.append(f"--env_name {env_name}")
        cmd_opts.append("--req_file dummy")
        cmd_opts.append("--test_install")
        self._helper(env_name, cmd_opts)

    @pytest.mark.slow
    def test_create_conda_yaml1(self) -> None:
        """
        Run create_conda.py with a single YAML file.
        """
        yaml = """
channels:
  - conda-forge
  - quantopian
dependencies:
  - pandas
  - pandas-datareader=0.8.0     # PTask344.
  - pip
  - pip:
    #- ta                   # Technical analysis package.
    - trading-calendars
    """
        yaml_file = os.path.join(self.get_scratch_space(), "reqs.yaml")
        hio.to_file(yaml_file, yaml)
        #
        cmd_opts = []
        env_name = "test_create_conda_yaml1"
        cmd_opts.append(f"--env_name {env_name}")
        cmd_opts.append(f"--req_file {yaml_file}")
        self._helper(env_name, cmd_opts)

    @pytest.mark.slow
    def test_create_conda_yaml2(self) -> None:
        """
        Run create_conda.py with two YAML files.
        """
        yaml1 = """
channels:
  - conda-forge
  - quantopian
dependencies:
  - pandas
  - pandas-datareader=0.8.0     # PTask344.
  - pip:
    #- ta                   # Technical analysis package.
    - trading-calendars """
        yaml_file1 = os.path.join(self.get_scratch_space(), "reqs1.yaml")
        hio.to_file(yaml_file1, yaml1)
        #
        yaml2 = """
channels:
  - conda-forge
  - quantopian
dependencies:
  - numpy"""
        yaml_file2 = os.path.join(self.get_scratch_space(), "reqs2.yaml")
        hio.to_file(yaml_file2, yaml2)
        #
        cmd_opts = []
        env_name = "test_create_conda_yaml2"
        cmd_opts.append(f"--env_name {env_name}")
        cmd_opts.append(f"--req_file {yaml_file1}")
        cmd_opts.append(f"--req_file {yaml_file2}")
        self._helper(env_name, cmd_opts)

    def _run_create_conda(self, cmd_opts: List[str], cleanup: bool) -> None:
        """
        Run a create_conda command using custom options `cmd_opts`.

        :param cleanup: True if we want to cleanup the conda env instead of
            creating it.
        """
        exec_file = hgit.find_file_in_git_tree("create_conda.py")
        cmd = []
        cmd.append(exec_file)
        cmd.extend(cmd_opts)
        cmd.append("--delete_env_if_exists")
        cmd.append("-v DEBUG")
        # TODO(gp): Find a way to check the output looking at the packages.
        if cleanup:
            if hunitest.get_incremental_tests():
                # No clean up for manual inspection with:
                _LOG.warning("No clean up as per incremental test mode")
                return
            # Remove env.
            cmd.append("--skip_install_env")
            cmd.append("--skip_pip_install")
            cmd.append("--skip_test_env")
        cmd_tmp = " ".join(cmd)
        hsystem.system(cmd_tmp)

    def _helper(self, env_name: str, cmd_opts: List[str]) -> None:
        """
        Run create_conda with custom options `cmd_opts` and then remove the
        env.
        """
        self._run_create_conda(cmd_opts, cleanup=False)
        #
        cmd = f"conda activate {env_name} && conda info --envs"
        holdcond.conda_system(cmd, suppress_output=False)
        # Clean up the env.
        self._run_create_conda(cmd_opts, cleanup=True)


# pylint: disable=line-too-long
## #############################################################################
## linter.py
## #############################################################################
#
#
## pylint: disable=too-many-public-methods
# @pytest.mark.amp
# @pytest.mark.skip(reason="Disabled because of AmpTask508")
# class Test_linter_py1(hunitest.TestCase):
#    def _write_input_file(self, txt: str, file_name: str) -> Tuple[str, str]:
#        dir_name = self.get_scratch_space()
#        hdbg.dassert_is_not(file_name, None)
#        file_name = os.path.join(dir_name, file_name)
#        file_name = os.path.abspath(file_name)
#        hio.to_file(file_name, txt)
#        return dir_name, file_name
#
#    def _run_linter(
#        self, file_name: str, linter_log: str, as_system_call: bool,
#    ) -> str:
#        if as_system_call:
#            cmd = []
#            cmd.append(f"linter.py -f {file_name} --linter_log {linter_log}")
#            cmd_as_str = " ".join(cmd)
#            # We need to ignore the errors reported by the script, since it
#            # represents how many lints were found.
#            suppress_output = _LOG.getEffectiveLevel() > logging.DEBUG
#            hsystem.system(
#                cmd_as_str, abort_on_error=False, suppress_output=suppress_output
#            )
#        else:
#            logger_verbosity = hdbg.get_logger_verbosity()
#            parser = lntr._parse()
#            args = parser.parse_args(
#                [
#                    "-f",
#                    file_name,
#                    "--linter_log",
#                    linter_log,
#                    # TODO(gp): Avoid to call the logger.
#                    "-v",
#                    "ERROR",
#                    # No output from the print.
#                    "--no_print",
#                ]
#            )
#            lntr._main(args)
#            hdbg.init_logger(logger_verbosity)
#
#        # Read log.
#        _LOG.debug("linter_log=%s", linter_log)
#        txt = hio.from_file(linter_log)
#        # Process log.
#        output = []
#        output.append("# linter log")
#        for l in txt.split("\n"):
#            # Remove the line:
#            #   cmd line='.../linter.py -f input.py --linter_log ./linter.log'
#            if "cmd line=" in l:
#                continue
#            # Filter out code rate because of #2241
#            if "Your code has been rated at" in l:
#                continue
#            output.append(l)
#        # Read output.
#        _LOG.debug("file_name=%s", file_name)
#        output.append("# linter file")
#        txt = hio.from_file(file_name)
#        output.extend(txt.split("\n"))
#        #
#        output_as_str = "\n".join(output)
#        return output_as_str
#
#    def _helper(self, txt: str, file_name: str, as_system_call: bool) -> str:
#        # Create file to lint.
#        dir_name, file_name = self._write_input_file(txt, file_name)
#        # Run.
#        dir_name = self.get_scratch_space()
#        linter_log = "linter.log"
#        linter_log = os.path.abspath(os.path.join(dir_name, linter_log))
#        output = self._run_linter(file_name, linter_log, as_system_call)
#        return output
#
#    # #########################################################################
#
#    @staticmethod
#    def _get_horrible_python_code1() -> str:
#        txt = r"""
# import python
#
#
# if __name__ == "main":
#    txt = "hello"
#    m = re.search("\s", txt)
#        """
#        return txt
#
#    @pytest.mark.skip(reason="Disable because of PTask3409")
#    @pytest.mark.skipif(
#        'hsystem.get_server_name() == "docker-instance"', reason="Issue #1522, #1831"
#    )
#    def test_linter1(self) -> None:
#        """Run linter.py as executable on some text."""
#        txt = self._get_horrible_python_code1()
#        # Run.
#        file_name = "input.py"
#        as_system_call = True
#        output = self._helper(txt, file_name, as_system_call)
#        # Check.
#        self.check_string(output, purify_text=True)
#
#    @pytest.mark.skip(reason="Disable because of PTask3409")
#    @pytest.mark.skipif(
#        'hsystem.get_server_name() == "docker-instance"', reason="Issue #1522, #1831"
#    )
#    def test_linter2(self) -> None:
#        """Run linter.py as library on some text."""
#        txt = self._get_horrible_python_code1()
#        # Run.
#        file_name = "input.py"
#        as_system_call = False
#        output = self._helper(txt, file_name, as_system_call)
#        # Check.
#        self.check_string(output, purify_text=True)
#
#    @pytest.mark.skip(reason="Disabled until #2430 is solved")
#    def test_linter_md1(self) -> None:
#        """Run linter.py as executable on some text."""
#        txt = r"""
## Good
# - Good time management
#  1. choose the right tasks
#    - Avoid non-essential tasks
#
### Bad
# -  Hello
#    - World
#        """
#        # Run.
#        file_name = "hello.md"
#        as_system_call = True
#        output = self._helper(txt, file_name, as_system_call)
#        # Remove the line:
#        # '12-16_14:59 ^[[33mWARNING^[[0m: _refresh_toc   :138 : No tags for table'
#        output = hunitest.filter_text("No tags for table", output)
#        # Check.
#        self.check_string(output)
#
#    # #########################################################################
#
#    def _helper_check_shebang(
#        self, file_name: str, txt: str, is_executable: bool, exp: str,
#    ) -> None:
#        txt_array = txt.split("\n")
#        msg = lntr._CustomPythonChecks._check_shebang(
#            file_name, txt_array, is_executable
#        )
#        self.assert_equal(msg, exp)
#
#    def test_check_shebang1(self) -> None:
#        """Executable with wrong shebang: error."""
#        file_name = "exec.py"
#        txt = """#!/bin/bash
# hello
# world
# """
#        is_executable = True
#        exp = "exec.py:1: any executable needs to start with a shebang '#!/usr/bin/env python'"
#        self._helper_check_shebang(file_name, txt, is_executable, exp)
#
#    def test_check_shebang2(self) -> None:
#        """Executable with the correct shebang: correct."""
#        file_name = "exec.py"
#        txt = """#!/usr/bin/env python
# hello
# world
# """
#        is_executable = True
#        exp = ""
#        self._helper_check_shebang(file_name, txt, is_executable, exp)
#
#    def test_check_shebang3(self) -> None:
#        """Non executable with a shebang: error."""
#        file_name = "exec.py"
#        txt = """#!/usr/bin/env python
# hello
# world
# """
#        is_executable = False
#        exp = "exec.py:1: any executable needs to start with a shebang '#!/usr/bin/env python'"
#        self._helper_check_shebang(file_name, txt, is_executable, exp)
#
#    def test_check_shebang4(self) -> None:
#        """Library without a shebang: correct."""
#        file_name = "lib.py"
#        txt = '''"""
# Import as:
#
# import _setenv_lib as selib
#'''
#        is_executable = False
#        exp = ""
#        self._helper_check_shebang(file_name, txt, is_executable, exp)
#
#    # #########################################################################
#
#    def _helper_was_baptized(self, file_name: str, txt: str, exp: str) -> None:
#        txt_array = txt.split("\n")
#        msg = lntr._CustomPythonChecks._was_baptized(file_name, txt_array)
#        self.assert_equal(msg, exp)
#
#    def test_was_baptized1(self) -> None:
#        """Correct import."""
#        file_name = "lib.py"
#        txt = '''"""
# Import as:
#
# import _setenv_lib as selib
#'''
#        exp = ""
#        self._helper_was_baptized(file_name, txt, exp)
#
#    def test_was_baptized2(self) -> None:
#        """Invalid."""
#        file_name = "lib.py"
#        txt = """
# Import as:
#
# """
#        exp = '''lib.py:1: every library needs to describe how to be imported:
# """
# Import as:
#
# import foo.bar as fba
# """'''
#        self._helper_was_baptized(file_name, txt, exp)
#
#    # #########################################################################
#
#    def _helper_check_line_by_line(
#        self, file_name: str, txt: str, exp: str
#    ) -> None:
#        txt_array = txt.split("\n")
#        output, txt_new = lntr._CustomPythonChecks._check_line_by_line(
#            file_name, txt_array
#        )
#        actual: List[str] = []
#        actual.append("# output")
#        actual.extend(output)
#        actual.append("# txt_new")
#        actual.extend(txt_new)
#        actual_as_str = "\n".join(actual)
#        self.assert_equal(actual_as_str, exp)
#
#    def test_check_line_by_line1(self) -> None:
#        """Valid import."""
#        file_name = "lib.py"
#        txt = "from typing import List"
#        exp = """# output
## txt_new
# from typing import List"""
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    def test_check_line_by_line2(self) -> None:
#        """Invalid import."""
#        file_name = "lib.py"
#        txt = "from pandas import DataFrame"
#        exp = """# output
# lib.py:1: do not use 'from pandas import DataFrame' use 'import foo.bar as fba'
## txt_new
# f-r-o-m pandas import DataFrame"""
#        # To avoid the linter to complain.
#        exp = exp.replace("-", "")
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    def test_check_line_by_line3(self) -> None:
#        """Invalid import."""
#        file_name = "lib.py"
#        txt = "import pandas as a_very_long_name"
#        exp = """# output
# lib.py:1: the import shortcut 'a_very_long_name' in 'import pandas as a_very_long_name' is longer than 8 characters
## txt_new
# i-m-p-o-r-t pandas as a_very_long_name"""
#        # To avoid the linter to complain.
#        exp = exp.replace("-", "")
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    def test_check_line_by_line4(self) -> None:
#        """Conflict markers."""
#        file_name = "lib.py"
#        txt = """import pandas as pd
# <-<-<-<-<-<-< HEAD
# hello
# =============================================================================
# world
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# """
#        txt = txt.replace("-", "")
#        exp = """# output
# lib.py:2: there are conflict markers
# lib.py:4: there are conflict markers
# lib.py:6: there are conflict markers
## txt_new
# import pandas as pd
# <-<-<-<-<-<-< HEAD
# hello
# =============================================================================
# world
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# """
#        exp = exp.replace("-", "")
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    def test_check_line_by_line5(self) -> None:
#        file_name = "lib.py"
#        # We use some _ to avoid getting a replacement from the linter here.
#        txt = """
# from typing import List
#
## _#_#_#_#_#_#_#_##
## hello
## =_=_=_=_=_=
# """
#        txt = txt.replace("_", "")
#        exp = """# output
## txt_new
#
# from typing import List
#
## #############################################################################
## hello
## =============================================================================
# """
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    def test_check_line_by_line6(self) -> None:
#        """Check that it doesn't replace if the bar is not until the end of the
#        line."""
#        file_name = "lib.py"
#        # We use some _ to avoid getting a replacement from the linter here.
#        txt = """
# from typing import List
#
## _#_#_#_#_#_#_#_##
## hello
## =_=_=_=_=_='''
# """
#        txt = txt.replace("_", "")
#        exp = """# output
## txt_new
#
# from typing import List
#
## #############################################################################
## hello
## ======'''
# """
#        self._helper_check_line_by_line(file_name, txt, exp)
#
#    # #########################################################################
#
#    def _helper_check_notebook_dir(self, file_name: str, exp: str) -> None:
#        msg = lntr._CheckFileProperty._check_notebook_dir(file_name)
#        self.assert_equal(msg, exp)
#
#    def test_check_notebook_dir1(self) -> None:
#        """The notebook is not under 'notebooks': invalid."""
#        file_name = "hello/world/notebook.ipynb"
#        # pylint: disable=line-too-long
#        exp = "hello/world/notebook.ipynb:1: each notebook should be under a 'notebooks' directory to not confuse pytest"
#        # pylint: enable=line-too-long
#        self._helper_check_notebook_dir(file_name, exp)
#
#    def test_check_notebook_dir2(self) -> None:
#        """The notebook is under 'notebooks': valid."""
#        file_name = "hello/world/notebooks/notebook.ipynb"
#        exp = ""
#        self._helper_check_notebook_dir(file_name, exp)
#
#    def test_check_notebook_dir3(self) -> None:
#        """It's not a notebook: valid."""
#        file_name = "hello/world/notebook.py"
#        exp = ""
#        self._helper_check_notebook_dir(file_name, exp)
#
#    # #########################################################################
#
#    def _helper_check_test_file_dir(self, file_name: str, exp: str) -> None:
#        msg = lntr._CheckFileProperty._check_test_file_dir(file_name)
#        self.assert_equal(msg, exp)
#
#    def test_check_test_file_dir1(self) -> None:
#        """Test is under `test`: valid."""
#        file_name = "hello/world/test/test_all.py"
#        exp = ""
#        self._helper_check_test_file_dir(file_name, exp)
#
#    def test_check_test_file_dir2(self) -> None:
#        """Test is not under `test`: invalid."""
#        file_name = "hello/world/test_all.py"
#        # pylint: disable=line-too-long
#        exp = "hello/world/test_all.py:1: test files should be under 'test' directory to be discovered by pytest"
#        # pylint: enable=line-too-long
#        self._helper_check_test_file_dir(file_name, exp)
#
#    def test_check_test_file_dir3(self) -> None:
#        """Test is not under `test`: invalid."""
#        file_name = "hello/world/tests/test_all.py"
#        # pylint: disable=line-too-long
#        exp = "hello/world/tests/test_all.py:1: test files should be under 'test' directory to be discovered by pytest"
#        # pylint: enable=line-too-long
#        self._helper_check_test_file_dir(file_name, exp)
#
#    def test_check_test_file_dir4(self) -> None:
#        """It's a notebook: valid."""
#        file_name = "hello/world/tests/test_all.ipynb"
#        exp = ""
#        self._helper_check_test_file_dir(file_name, exp)
#
#
# @pytest.mark.amp
# class Test_process_jupytext(hunitest.TestCase):
#    @pytest.mark.skip(
#        "Latest version of jupytext fixed this problem (PTask1240)"
#    )
#    def test1_end_to_end(self) -> None:
#        file_name = "test_notebook.py"
#        file_path = os.path.join(self.get_input_dir(), file_name)
#        cmd = f"process_jupytext.py -f {file_path} --action test 2>&1"
#        _, txt = hsystem.system_to_string(cmd, abort_on_error=False)
#        _LOG.debug("txt=\n%s", txt)
#        # There is a date in output, so we remove date using split.
#        # Output example:
#        # \x1B[0m02-19_20:56 \x1B[33mWARNING\x1B[0m: _is_jupytext_version_different:108 :
#        #    There is a mismatch of jupytext version:
#        #    'jupytext_version: 1.1.2' vs 'jupytext_version: 1.3.2': skipping
#        txts = txt.split("WARNING")
#        hdbg.dassert_eq(2, len(txts), "txt='%s'", txt)
#        txts = txts[1]
#        #
#        txts = txts.split("[")
#        hdbg.dassert_eq(2, len(txts), "txt='%s'", txt)
#        txt_no_date = txts[1]
#        self.check_string(txt_no_date)
#
#    def test2_is_jupytext_version_different_true(self) -> None:
#        txt = """
# --- expected
# +++ actual
# @@ -5,7 +5,7 @@
# #       extension: .py
# #       format_name: percent
# #       format_version: '1.3'
# -#       jupytext_version: 1.3.3
# +#       jupytext_version: 1.3.0
# #   kernelspec:
# #     display_name: Python [conda env:.conda-develop] *
# #     language: python
# """
#        self.assertTrue(proc_jup._is_jupytext_version_different(txt))
#
#    def test3_is_jupytext_version_different_false(self) -> None:
#        txt = """
# --- expected
# +++ actual
# @@ -5,7 +5,7 @@
# #       extension: .py
# -#       format_name: percent
# +#       format_name: plus
# #       format_version: '1.3'
# #       jupytext_version: 1.3.3
# #   kernelspec:
# #     display_name: Python [conda env:.conda-develop] *
# #     language: python
# """
#        self.assertFalse(proc_jup._is_jupytext_version_different(txt))
