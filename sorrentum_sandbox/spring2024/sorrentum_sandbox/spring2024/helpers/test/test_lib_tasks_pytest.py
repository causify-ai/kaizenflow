import logging
import os
import re
import unittest.mock as umock
from typing import List

import pytest

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import helpers.lib_tasks_pytest as hlitapyt
import helpers.test.test_lib_tasks as httestlib

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


class Test_build_run_command_line1(hunitest.TestCase):
    def run_fast_tests1_helper(
        self,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Basic run fast tests.

        :param is_dev_ck_return_value: mocking the return_value of `hserver.is_dev_ck()`
        :param is_inside_ci_return_value: mocking the return_value of `hserver.is_inside_ci()`
        :param exp: expected output string
        """
        custom_marker = ""
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = False
        n_threads = "1"
        #
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_run_fast_tests1_inside_ck_infra(self) -> None:
        """
        Mock test for running fast tests inside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests1_inside_ci(self) -> None:
        """
        Mock test for running fast tests inside CI flow only.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests1_outside_ck_infra(self) -> None:
        """
        Mock test for running fast tests outside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 50 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_inside_ci_return_value = False
        is_dev_ck_return_value = False
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def run_fast_tests2_helper(
        self,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Coverage and collect-only.

        See `run_fast_tests1_helper()` for params description.
        """
        custom_marker = ""
        pytest_opts = ""
        skip_submodules = False
        coverage = True
        collect_only = True
        tee_to_file = False
        n_threads = "1"
        #
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_run_fast_tests2_inside_ck_infra(self) -> None:
        """
        Mock test for running fast tests inside the CK infra.
        """

        exp = (
            r'pytest -m "not slow and not superslow" . '
            r"-o timeout_func_only=true --timeout 5 --reruns 2 "
            r'--only-rerun "Failed: Timeout" --cov=.'
            r" --cov-branch --cov-report term-missing --cov-report html "
            r"--collect-only -n 1"
        )
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        self.run_fast_tests2_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests2_inside_ci(self) -> None:
        """
        Mock test for running fast tests inside CI flow only.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests2_outside_ck_infra(self) -> None:
        """
        Mock test for running fast tests outside the CK infra.
        """
        exp = (
            r'pytest -m "not slow and not superslow" . '
            r"-o timeout_func_only=true --timeout 50 --reruns 2 "
            r'--only-rerun "Failed: Timeout" --cov=.'
            r" --cov-branch --cov-report term-missing --cov-report html "
            r"--collect-only -n 1"
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = False
        self.run_fast_tests2_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

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
        test_list_name = "fast_tests"
        custom_marker = ""
        pytest_opts = ""
        skip_submodules = True
        coverage = False
        collect_only = False
        tee_to_file = False
        n_threads = "1"
        #
        act = hlitapyt._build_run_command_line(
            test_list_name,
            custom_marker,
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
            n_threads,
        )
        exp = (
            "pytest Test_build_run_command_line1.test_run_fast_tests4/tmp.scratch/"
            "test/test_that.py"
        )
        self.assert_equal(act, exp)

    def run_fast_tests5_helper(
        self,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Basic run fast tests tee-ing to a file. Mock depending on
        `is_dev_ck_return_value`.

        See `run_fast_tests1_helper()` for params description.
        """
        custom_marker = ""
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = True
        n_threads = "1"
        #
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_run_fast_tests5_inside_ck_infra(self) -> None:
        """
        Mock test for running fast tests inside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1 2>&1'
            " | tee tmp.pytest.fast_tests.log"
        )
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        self.run_fast_tests5_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests5_inside_ci(self) -> None:
        """
        Mock test for running fast tests inside CI flow only.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests5_outside_ck_infra(self) -> None:
        """
        Mock test for running fast tests outside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 50 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1 2>&1'
            " | tee tmp.pytest.fast_tests.log"
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = False
        self.run_fast_tests5_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def run_fast_tests6_helper(
        self,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Run fast tests with a custom test marker.

        See `run_fast_tests1_helper()` for params description.
        """
        custom_marker = "optimizer"
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = False
        n_threads = "1"
        #
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_run_fast_tests6_inside_ck_infra(self) -> None:
        """
        Mock test for running fast tests inside the CK infra.
        """
        exp = (
            'pytest -m "optimizer and not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        self.run_fast_tests6_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests6_inside_ci(self) -> None:
        """
        Mock test for running fast tests inside CI flow only.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests6_outside_ck_infra(self) -> None:
        """
        Mock test for running fast tests outside the CK infra.
        """
        exp = (
            'pytest -m "optimizer and not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 50 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = False
        self.run_fast_tests6_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def run_fast_tests7_helper(
        self,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Run fast tests with parallelization.

        See `run_fast_tests1_helper()` for params description.
        """
        custom_marker = ""
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = False
        n_threads = "auto"
        #
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_run_fast_tests7_inside_ck_infra(self) -> None:
        """
        Mock test for running fast tests inside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n auto'
        )
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        self.run_fast_tests7_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests7_inside_ci(self) -> None:
        """
        Mock test for running fast tests inside CI flow only.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = True
        self.run_fast_tests1_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def test_run_fast_tests7_outside_ck_infra(self) -> None:
        """
        Mock test for running fast tests outside the CK infra.
        """
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 50 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n auto'
        )
        is_dev_ck_return_value = False
        is_inside_ci_return_value = False
        self.run_fast_tests7_helper(
            is_dev_ck_return_value, is_inside_ci_return_value, exp
        )

    def get_custom_marker_helper(
        self,
        run_only_test_list: str,
        skip_test_list: str,
        is_dev_ck_return_value: bool,
        is_inside_ci_return_value: bool,
        exp: str,
    ) -> None:
        """
        Check that a correct cmd line is generated with custom marker string.

        :param run_only_test_list: a string of comma-separated markers to run
        :param skip_test_list: a string of comma-separated markers to skip
        :param is_dev_ck_return_value: see `run_fast_tests1_helper()`
        :param is_inside_ci_return_value: see `run_fast_tests1_helper()`
        :param exp: expected output string
        """
        # Mock settings.
        pytest_opts = ""
        skip_submodules = False
        coverage = False
        collect_only = False
        tee_to_file = False
        n_threads = "1"
        # Mock test.
        with umock.patch.object(
            hserver, "is_dev_ck", return_value=is_dev_ck_return_value
        ), umock.patch.object(
            hserver, "is_inside_ci", return_value=is_inside_ci_return_value
        ):
            custom_marker = hlitapyt._get_custom_marker(
                run_only_test_list=run_only_test_list,
                skip_test_list=skip_test_list,
            )
            act = hlitapyt._build_run_command_line(
                "fast_tests",
                custom_marker,
                pytest_opts,
                skip_submodules,
                coverage,
                collect_only,
                tee_to_file,
                n_threads,
            )
            self.assert_equal(act, exp)

    def test_get_custom_marker1_full(self) -> None:
        # Input params.
        run_only_test_list = "run_marker_1,run_marker_2"
        skip_test_list = "skip_marker_1,skip_marker_2"
        is_dev_ck_return_value = False
        is_inside_ci_return_value = False
        # Expected output.
        exp = (
            'pytest -m "'
            "run_marker_1 and run_marker_2 "
            "and not requires_ck_infra "
            "and not skip_marker_1 and not skip_marker_2 "
            'and not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 50 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        # Mock check.
        self.get_custom_marker_helper(
            run_only_test_list,
            skip_test_list,
            is_dev_ck_return_value,
            is_inside_ci_return_value,
            exp,
        )

    def get_custom_marker2_empty(self) -> None:
        # Input params.
        run_only_test_list = ""
        skip_test_list = ""
        is_dev_ck_return_value = True
        is_inside_ci_return_value = True
        # Expected output.
        exp = (
            'pytest -m "not slow and not superslow" . '
            "-o timeout_func_only=true --timeout 5 --reruns 2 "
            '--only-rerun "Failed: Timeout" -n 1'
        )
        # Mock check.
        self.get_custom_marker_helper(
            run_only_test_list,
            skip_test_list,
            is_dev_ck_return_value,
            is_inside_ci_return_value,
            exp,
        )


class Test_pytest_repro1(hunitest.TestCase):
    def helper(self, file_name: str, mode: str, exp: List[str]) -> None:
        script_name = os.path.join(
            self.get_scratch_space(), "tmp.pytest_repro.sh"
        )
        ctx = httestlib._build_mock_context_returning_ok()
        act = hlitapyt.pytest_repro(
            ctx, mode=mode, file_name=file_name, script_name=script_name
        )
        hdbg.dassert_isinstance(act, str)
        exp = "\n".join(["pytest " + x for x in exp])
        self.assert_equal(act, exp)

    def test_tests1(self) -> None:
        file_name = self._build_pytest_file1()
        mode = "tests"
        exp = [
            "dev_scripts/testing/test/test_run_tests.py",
            "dev_scripts/testing/test/test_run_tests2.py",
            "documentation/scripts/test/test_all.py",
            "documentation/scripts/test/test_render_md.py",
            "helpers/test/helpers/test/test_list.py::Test_list_1",
            "helpers/test/test_cache.py::TestAmpTask1407",
            "helpers/test/test_printing.py::Test_dedent1::test2",
        ]
        self.helper(file_name, mode, exp)

    def test_files1(self) -> None:
        file_name = self._build_pytest_file1()
        mode = "files"
        exp = [
            "dev_scripts/testing/test/test_run_tests.py",
            "dev_scripts/testing/test/test_run_tests2.py",
            "documentation/scripts/test/test_all.py",
            "documentation/scripts/test/test_render_md.py",
            "helpers/test/helpers/test/test_list.py",
            "helpers/test/test_cache.py",
            "helpers/test/test_printing.py",
        ]
        self.helper(file_name, mode, exp)

    def test_classes1(self) -> None:
        file_name = self._build_pytest_file1()
        mode = "classes"
        exp = [
            "helpers/test/helpers/test/test_list.py::Test_list_1",
            "helpers/test/test_cache.py::TestAmpTask1407",
            "helpers/test/test_printing.py::Test_dedent1",
        ]
        self.helper(file_name, mode, exp)

    def test_tests2(self) -> None:
        file_name = self._build_pytest_file2()
        mode = "tests"
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
        self.helper(file_name, mode, exp)

    def test_files2(self) -> None:
        file_name = self._build_pytest_file2()
        mode = "files"
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
        self.helper(file_name, mode, exp)

    def test_classes2(self) -> None:
        file_name = self._build_pytest_file2()
        mode = "classes"
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
        self.helper(file_name, mode, exp)

    # ////////////////////////////////////////////////////////////////////////////

    def _build_pytest_filehelper(self, txt: str) -> str:
        txt = hprint.dedent(txt)
        file_name = os.path.join(self.get_scratch_space(), "cache/lastfailed")
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
        return self._build_pytest_filehelper(txt)

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
        return self._build_pytest_filehelper(txt)


@pytest.mark.slow("~6 sec.")
class Test_pytest_repro_end_to_end(hunitest.TestCase):
    """
    - Run the `pytest_repro` invoke from command line
      - A fixed file imitating the pytest output file is used
    - Compare the output to the golden outcome
    """

    def helper(self, cmd: str) -> None:
        # Save output in tmp dir.
        script_name = os.path.join(
            self.get_scratch_space(), "tmp.pytest_repro.sh"
        )
        cmd += f" --script-name {script_name}"
        # Run the command.
        _, act = hsystem.system_to_string(cmd)
        # Filter out the "No module named ..." warnings.
        # TODO(Grisha): add the "no module warning" filtering to
        # `purify_text()` in `check_string()`.
        regex = "WARN.*No module"
        act = hunitest.filter_text(regex, act)
        # Remove "Encountered unexpected exception importing solver GLPK"
        # generated on Mac.
        regex = "Encountered unexpected exception importing solver GLPK"
        act = hunitest.filter_text(regex, act)
        # ImportError("cannot import name 'glpk' from 'cvxopt' (/venv/lib/python3.9/site-packages/cvxopt/__init__.py)")
        regex = r"""ImportError\("cannot import name"""
        act = hunitest.filter_text(regex, act)
        # Modify the outcome for reproducibility.
        act = hprint.remove_non_printable_chars(act)
        act = re.sub(r"[0-9]{2}:[0-9]{2}:[0-9]{2} - ", r"HH:MM:SS - ", act)
        act = act.replace("/app/amp/", "/app/")
        act = re.sub(
            r"lib_tasks_pytest.py pytest_repro:[0-9]+",
            r"lib_tasks_pytest.py pytest_repro:{LINE_NUM}",
            act,
        )
        # Remove unstable content.
        lines = act.split("\n")
        line_cmd = lines[0]
        test_output_start = lines.index("## pytest_repro: ")
        lines_test_output = lines[test_output_start:]
        act = "\n".join([line_cmd] + lines_test_output)
        regex = "(WARN|INFO)\s+hcache.py"
        act = hunitest.filter_text(regex, act)
        # Check the outcome.
        self.check_string(act, purify_text=True, fuzzy_match=True)

    def test1(self) -> None:
        file_name = f"{self.get_input_dir()}/cache/lastfailed"
        cmd = f"invoke pytest_repro --file-name='{file_name}'"
        self.helper(cmd)

    def test2(self) -> None:
        """
        The tests are different since the input depends on the test and it's
        different for different tests.
        """
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}'"
        self.helper(cmd)

    def test3(self) -> None:
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}'"
        self.helper(cmd)

    def test4(self) -> None:
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}' --show-stacktrace"
        self.helper(cmd)

    def test5(self) -> None:
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}' --show-stacktrace"
        self.helper(cmd)

    def test6(self) -> None:
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}' --show-stacktrace"
        self.helper(cmd)

    def test7(self) -> None:
        file_name = f"{self.get_input_dir()}/log.txt"
        cmd = f"invoke pytest_repro --file-name='{file_name}' --show-stacktrace"
        self.helper(cmd)
