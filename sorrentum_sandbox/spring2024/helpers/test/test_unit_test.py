"""
Import as:

import helpers.test.test_unit_test as ttutes
"""

import logging
import os
import tempfile
import unittest.mock as umock
from typing import Optional, Tuple

import pandas as pd
import pytest

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _git_add(file_name: str) -> None:
    # pylint: disable=unreachable
    cmd = f"git add -u {file_name}"
    _LOG.debug("> %s", cmd)
    rc = hsystem.system(cmd, abort_on_error=False)
    if rc:
        _LOG.warning(
            "Can't run '%s': you need to add the file manually",
            cmd,
        )


def _to_skip_on_update_outcomes() -> bool:
    """
    Determine whether to skip on `--update_outcomes`.

    Some tests can't pass with `--update_outcomes`, since they exercise
    the logic in `--update_outcomes` itself.

    We can't always use `@pytest.mark.skipif(hunitest.get_update_tests)`
    since pytest decides which tests need to be run before the variable
    is actually set.
    """
    to_skip = False
    if hunitest.get_update_tests():
        _LOG.warning(
            "Skip this test since it exercises the logic for --update_outcomes"
        )
        to_skip = True
    return to_skip


# #############################################################################


class TestTestCase1(hunitest.TestCase):
    """
    Test free-standing functions in unit_test.py.
    """

    def test_get_input_dir1(self) -> None:
        """
        Test hunitest.get_input_dir().
        """
        act = self.get_input_dir()
        act = hunitest.purify_txt_from_client(act)
        exp = "$GIT_ROOT/helpers/test/outcomes/TestTestCase1.test_get_input_dir1/input"
        self.assertEqual(act, exp)

    def test_get_input_dir2(self) -> None:
        use_only_test_class = False
        test_class_name = "test_class"
        test_method_name = "test_method"
        act = self.get_input_dir(
            use_only_test_class, test_class_name, test_method_name
        )
        act = hunitest.purify_txt_from_client(act)
        #
        exp = "$GIT_ROOT/helpers/test/outcomes/test_class.test_method/input"
        self.assertEqual(act, exp)

    def test_get_input_dir3(self) -> None:
        use_only_test_class = False
        test_class_name = None
        test_method_name = None
        act = self.get_input_dir(
            use_only_test_class, test_class_name, test_method_name
        )
        act = hunitest.purify_txt_from_client(act)
        #
        exp = "$GIT_ROOT/helpers/test/outcomes/TestTestCase1.test_get_input_dir3/input"
        self.assertEqual(act, exp)

    def test_get_input_dir4(self) -> None:
        use_only_test_class = True
        test_class_name = None
        test_method_name = None
        act = self.get_input_dir(
            use_only_test_class, test_class_name, test_method_name
        )
        act = hunitest.purify_txt_from_client(act)
        #
        exp = "$GIT_ROOT/helpers/test/outcomes/TestTestCase1/input"
        self.assertEqual(act, exp)

    def test_get_output_dir1(self) -> None:
        """
        Test hunitest.get_output_dir().
        """
        act = self.get_output_dir()
        act = hunitest.purify_txt_from_client(act)
        exp = "$GIT_ROOT/helpers/test/outcomes/TestTestCase1.test_get_output_dir1/output"
        self.assertEqual(act, exp)

    def test_get_scratch_space1(self) -> None:
        """
        Test hunitest.get_scratch_space().
        """
        act = self.get_scratch_space()
        act = hunitest.purify_txt_from_client(act)
        exp = (
            "$GIT_ROOT/helpers/test/outcomes/TestTestCase1.test_get_scratch_space1"
            "/tmp.scratch"
        )
        self.assertEqual(act, exp)

    def test_get_scratch_space2(self) -> None:
        test_class_name = "test_class"
        test_method_name = "test_method"
        act = self.get_scratch_space(test_class_name, test_method_name)
        act = hunitest.purify_txt_from_client(act)
        exp = "$GIT_ROOT/helpers/test/outcomes/test_class.test_method/tmp.scratch"
        self.assertEqual(act, exp)

    def test_get_scratch_space3(self) -> None:
        test_class_name = "test_class"
        test_method_name = "test_method"
        use_absolute_path = False
        act = self.get_scratch_space(
            test_class_name, test_method_name, use_absolute_path
        )
        act = hunitest.purify_txt_from_client(act)
        exp = "outcomes/test_class.test_method/tmp.scratch"
        self.assertEqual(act, exp)

    def test_get_s3_scratch_dir1(self) -> None:
        act = self.get_s3_scratch_dir()
        _LOG.debug("act=%s", act)
        # It is difficult to test, so we just execute.

    def test_get_s3_scratch_dir2(self) -> None:
        test_class_name = "test_class"
        test_method_name = "test_method"
        act = self.get_s3_scratch_dir(test_class_name, test_method_name)
        _LOG.debug("act=%s", act)
        # It is difficult to test, so we just execute.

    def test_assert_equal1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test_assert_not_equal1(self) -> None:
        actual = "hello world"
        expected = "hello world w"
        tmp_dir = tempfile.mkdtemp()
        with self.assertRaises(RuntimeError):
            self.assert_equal(actual, expected, dst_dir=tmp_dir)

    def test_assert_not_equal2(self) -> None:
        actual = "hello world"
        expected = "hello world w"
        # Create a dir like `/var/tmp/tmph_kun9xq`.
        tmp_dir = tempfile.mkdtemp()
        self.assert_equal(actual, expected, abort_on_error=False, dst_dir=tmp_dir)
        # Compute the signature from the dir.
        act = hunitest.get_dir_signature(
            tmp_dir, include_file_content=True, num_lines=None
        )
        act = hunitest.purify_txt_from_client(act)
        act = act.replace(tmp_dir, "$TMP_DIR")
        # pylint: disable=line-too-long
        exp = """
        # Dir structure
        $TMP_DIR
        $TMP_DIR/tmp_diff.sh
        # File signatures
        len(file_names)=1
        file_names=$TMP_DIR/tmp_diff.sh
        # $TMP_DIR/tmp_diff.sh
        num_lines=9
        '''
        #!/bin/bash
        if [[ $1 == "wrap" ]]; then
            cmd='vimdiff -c "windo set wrap"'
        else
            cmd='vimdiff'
        fi;
        cmd="$cmd helpers/test/outcomes/TestTestCase1.test_assert_not_equal2/tmp.final.actual.txt helpers/test/outcomes/TestTestCase1.test_assert_not_equal2/tmp.final.expected.txt"
        eval $cmd

        '''
        """
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert_equal_fuzzy_match1(self) -> None:
        actual = "hello world"
        expected = "hello world "
        is_equal = self.assert_equal(actual, expected, fuzzy_match=True)
        self.assertTrue(is_equal)

    def test_assert_equal5(self) -> None:
        actual = "hello world"
        expected = "hello world2"
        with self.assertRaises(RuntimeError):
            self.assert_equal(actual, expected, fuzzy_match=True)

    def _remove_lines1(self) -> None:
        txt = r"""
        # #####################################################################
        * Failed assertion *
        'in1' not in '{'in1': 'out1'}'
        ##
        `in1` already receiving input from node n1
        # #####################################################################
        # #####################################################################
        """
        act = hunitest._remove_spaces(txt)
        exp = r"""
        * Failed assertion *
        'in1' not in '{'in1': 'out1'}'
        ##
        `in1` already receiving input from node n1
        # #####################################################################
        """
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class Test_AssertEqual1(hunitest.TestCase):
    def test_equal1(self) -> None:
        """
        Matching act and exp without fuzzy matching.
        """
        act = r"""
completed       failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""
        exp = r"""
completed       failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""
        test_name = self._get_test_name()
        test_dir = self.get_scratch_space()
        is_equal = hunitest.assert_equal(act, exp, test_name, test_dir)
        _LOG.debug(hprint.to_str("is_equal"))
        self.assertTrue(is_equal)

    def test_equal2(self) -> None:
        """
        Matching act and exp with fuzzy matching.
        """
        act = r"""
completed failure Lint Run_linter
completed success Lint Fast_tests
completed success Lint Slow_tests
"""
        exp = r"""
completed       failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""
        test_name = self._get_test_name()
        test_dir = self.get_scratch_space()
        fuzzy_match = True
        is_equal = hunitest.assert_equal(
            act, exp, test_name, test_dir, fuzzy_match=fuzzy_match
        )
        _LOG.debug(hprint.to_str("is_equal"))
        self.assertTrue(is_equal)

    def test_not_equal1(self) -> None:
        """
        Mismatching act and exp.
        """
        act = r"""
completed failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""
        exp = r"""
completed       failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""
        test_name = self._get_test_name()
        test_dir = self.get_scratch_space()
        fuzzy_match = False
        with self.assertRaises(RuntimeError) as cm:
            hunitest.assert_equal(
                act, exp, test_name, test_dir, fuzzy_match=fuzzy_match
            )
        # Check that the assertion is what expected.
        act = str(cm.exception)
        act = hunitest.purify_txt_from_client(act)
        exp = '''
--------------------------------------------------------------------------------
ACTUAL vs EXPECTED: Test_AssertEqual1.test_not_equal1
--------------------------------------------------------------------------------

                                                                          (
completed failure Lint    Run_linter                                      |  completed       failure Lint    Run_linter
completed       success Lint    Fast_tests                                (
completed       success Lint    Slow_tests                                (
Diff with:
> ./tmp_diff.sh
--------------------------------------------------------------------------------
ACTUAL VARIABLE: Test_AssertEqual1.test_not_equal1
--------------------------------------------------------------------------------
exp = r"""
completed failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests
"""'''
        if act != exp:
            hio.to_file("act.txt", act)
            hio.to_file("exp.txt", exp)
            self.assert_equal(act, exp, fuzzy_match=False)
        # We don't use self.assert_equal() since this is exactly we are testing,
        # so we use a trusted function.
        self.assertEqual(act, exp)

    # For debugging: don't commit code with this test enabled.
    @pytest.mark.skip(
        reason="This is only used to debug the debugging the infrastructure"
    )
    def test_not_equal_debug(self) -> None:
        """
        Create a mismatch on purpose to see how the suggested updated to
        expected variable looks like.
        """
        act = r"""empty
start

completed failure Lint    Run_linter
completed       success Lint    Fast_tests
completed       success Lint    Slow_tests

end

"""
        exp = "hello"
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class TestCheckString1(hunitest.TestCase):
    def test_check_string1(self) -> None:
        """
        Compare the actual value to a matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        golden_outcome = "hello world"
        #
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Overwrite the golden file, so that --update_golden doesn't matter.
        hio.to_file(file_name, golden_outcome)
        try:
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(act)
            # Actual match the golden outcome and it wasn't updated.
        finally:
            # Clean up.
            hio.to_file(file_name, golden_outcome)
            _git_add(file_name)
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertTrue(is_equal)

    def test_check_string_not_equal1(self) -> None:
        """
        Compare the actual value to a mismatching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        golden_outcome = "hello world2"
        #
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Modify the golden.
        hio.to_file(file_name, golden_outcome)
        try:
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(
                act, abort_on_error=False
            )
        finally:
            # Clean up.
            hio.to_file(file_name, golden_outcome)
            _git_add(file_name)
        # Actual doesn't match the golden outcome.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertFalse(is_equal)

    def test_check_string_not_equal2(self) -> None:
        """
        Compare the actual value to a mismatching golden outcome and udpate it.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        golden_outcome = "hello world2"
        # Force updating the golden outcomes.
        self.mock_update_tests()
        #
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Modify the golden.
        hio.to_file(file_name, golden_outcome)
        try:
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(
                act, abort_on_error=False
            )
            new_golden = hio.from_file(file_name)
            _git_add(file_name)
        finally:
            # Clean up.
            hio.to_file(file_name, golden_outcome)
            _git_add(file_name)
        # Actual doesn't match the golden outcome and it was updated.
        self.assertTrue(outcome_updated)
        self.assertTrue(file_exists)
        self.assertFalse(is_equal)
        # The golden outcome was updated.
        self.assertEqual(new_golden, "hello world")

    def test_check_string_not_equal3(self) -> None:
        """
        Like test_check_string_not_equal1() but raising the exception.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        golden_outcome = "hello world2"
        #
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Modify the golden.
        hio.to_file(file_name, golden_outcome)
        try:
            # Check.
            with self.assertRaises(RuntimeError):
                self.check_string(act)
        finally:
            # Clean up.
            hio.to_file(file_name, golden_outcome)
            _git_add(file_name)

    def test_check_string_missing1(self) -> None:
        """
        When running with --update_outcomes, the golden outcome was missing and
        so it was added.

        This tests the code path when action_on_missing_golden="update".
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        # Force updating the golden outcomes.
        self.mock_update_tests()
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(
                act, abort_on_error=False
            )
            hdbg.dassert_file_exists(file_name)
            new_golden = hio.from_file(file_name)
        finally:
            # Clean up.
            hio.delete_file(file_name)
            _git_add(file_name)
        # Actual doesn't match the golden outcome and it was updated.
        self.assertTrue(outcome_updated)
        self.assertFalse(file_exists)
        self.assertFalse(is_equal)
        #
        self.assertEqual(new_golden, "hello world")

    def test_check_string_missing2(self) -> None:
        """
        Without running with --update_outcomes, the golden outcome was missing,
        action_on_missing_golden="assert", and the unit test framework
        asserted.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(
                act, abort_on_error=False, action_on_missing_golden="assert"
            )
            hdbg.dassert_file_exists(file_name + ".tmp")
            new_golden = hio.from_file(file_name + ".tmp")
        finally:
            # Clean up.
            hio.delete_file(file_name)
        # Actual doesn't match the golden outcome and it was updated.
        self.assertFalse(outcome_updated)
        self.assertFalse(file_exists)
        self.assertFalse(is_equal)
        #
        self.assertEqual(new_golden, "hello world")

    def test_check_string_missing3(self) -> None:
        """
        Without running with --update_outcomes, the golden outcome was missing,
        action_on_missing_golden="update", and the unit test framework updates
        the golden.
        """
        if _to_skip_on_update_outcomes():
            return
        act = "hello world"
        tag = "test"
        _, file_name = self._get_golden_outcome_file_name(tag)
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_string(
                act, abort_on_error=False, action_on_missing_golden="update"
            )
            hdbg.dassert_file_exists(file_name)
            new_golden = hio.from_file(file_name)
        finally:
            # Clean up.
            hio.delete_file(file_name)
        # Actual doesn't match the golden outcome and it was updated.
        self.assertTrue(outcome_updated)
        self.assertFalse(file_exists)
        self.assertFalse(is_equal)
        #
        self.assertEqual(new_golden, "hello world")


# #############################################################################


class TestCheckDataFrame1(hunitest.TestCase):
    """
    Some of these tests can't pass with `--update_outcomes`, since they
    exercise the logic in `--update_outcomes` itself.
    """

    def test_check_df_equal1(self) -> None:
        """
        Compare the actual value of a df to a matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        abort_on_error = True
        err_threshold = 0.0001
        outcome_updated, file_exists, is_equal = self._check_df_helper(
            act, abort_on_error, err_threshold
        )
        # Actual outcome matches the golden outcome and it wasn't updated.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertTrue(is_equal)

    def test_check_df_equal2(self) -> None:
        """
        Compare the actual value of a df to a matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1.01, 2], [3, 4, 5]], columns="a b c".split())
        abort_on_error = True
        err_threshold = 0.05
        outcome_updated, file_exists, is_equal = self._check_df_helper(
            act, abort_on_error, err_threshold
        )
        # Actual outcome matches the golden outcome and it wasn't updated.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertTrue(is_equal)

    def test_check_df_equal3(self) -> None:
        """
        Compare the actual value of a df to a matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1.05, 2], [3, 4, 5]], columns="a b c".split())
        abort_on_error = True
        err_threshold = 0.05
        outcome_updated, file_exists, is_equal = self._check_df_helper(
            act, abort_on_error, err_threshold
        )
        # Actual outcome matches the golden outcome and it wasn't updated.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertTrue(is_equal)

    def test_check_df_not_equal1(self) -> None:
        """
        Compare the actual value of a df to a non-matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1.06, 2], [3, 4, 5]], columns="a b c".split())
        abort_on_error = False
        err_threshold = 0.05
        outcome_updated, file_exists, is_equal = self._check_df_helper(
            act, abort_on_error, err_threshold
        )
        # Actual outcome doesn't match the golden outcome and it wasn't updated.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertFalse(is_equal)
        exp_error_msg = """
            actual=
            a b c
            0 0 1.06 2
            1 3 4.00 5
            expected=
            a b c
            0 0 1 2
            1 3 4 5
            actual_masked=
            [[ nan 1.06 nan]
            [ nan nan nan]]
            expected_masked=
            [[nan 1. nan]
            [nan nan nan]]
            err=
            [[ nan 0.06 nan]
            [ nan nan nan]]
            max_err=0.060
        """
        self.assert_equal(self._error_msg, exp_error_msg, fuzzy_match=True)

    def test_check_df_not_equal2(self) -> None:
        """
        Compare the actual value of a df to a not matching golden outcome.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a d c".split())
        abort_on_error = False
        err_threshold = 0.05
        outcome_updated, file_exists, is_equal = self._check_df_helper(
            act, abort_on_error, err_threshold
        )
        # Actual outcome doesn't match the golden outcome and it wasn't updated.
        self.assertFalse(outcome_updated)
        self.assertTrue(file_exists)
        self.assertFalse(is_equal)

    def test_check_df_not_equal3(self) -> None:
        """
        Compare the actual value to a mismatching golden outcome and update it.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        golden_outcome = pd.DataFrame(
            [[0, 2, 2], [3, 4, 5]], columns="a b c".split()
        )
        # Force updating the golden outcomes.
        self.mock_update_tests()
        tag = "test_df"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Modify the golden.
        hio.create_enclosing_dir(file_name, incremental=True)
        golden_outcome.to_csv(file_name)
        try:
            # Check.
            outcome_updated, file_exists, is_equal = self.check_dataframe(
                act, abort_on_error=False
            )
            #
            new_golden = pd.read_csv(file_name, index_col=0)
        finally:
            # Clean up.
            hio.to_file(file_name, golden_outcome)
            _git_add(file_name)
        # Actual doesn't match the golden outcome and it was updated.
        self.assertTrue(outcome_updated)
        self.assertTrue(file_exists)
        self.assertFalse(is_equal)
        # Check golden.
        self.assert_equal(str(new_golden), str(act))

    def test_check_df_not_equal4(self) -> None:
        """
        Like `test_check_df_not_equal1()` but raising the exception.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1.06, 2], [3, 4, 5]], columns="a b c".split())
        abort_on_error = True
        err_threshold = 0.05
        with self.assertRaises(RuntimeError):
            self._check_df_helper(act, abort_on_error, err_threshold)

    def test_check_df_missing1(self) -> None:
        """
        When running with --update_outcomes, the golden outcome was missing and
        so it was added.

        This tests the code path when action_on_missing_golden="update".
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        # Force updating the golden outcomes.
        self.mock_update_tests()
        tag = "test_df"
        _, file_name = self._get_golden_outcome_file_name(tag)
        _LOG.debug(hprint.to_str("file_name"))
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_dataframe(
                act, abort_on_error=False
            )
            hdbg.dassert_file_exists(file_name)
            new_golden = pd.read_csv(file_name, index_col=0)
        finally:
            # Clean up.
            hio.delete_file(file_name)
            _git_add(file_name)
        # Expected outcome doesn't exists and it was updated.
        self.assertTrue(outcome_updated)
        self.assertFalse(file_exists)
        self.assertFalse(is_equal)
        # Check golden.
        self.assert_equal(str(new_golden), str(act))

    def test_check_df_missing2(self) -> None:
        """
        Without running with --update_outcomes, the golden outcome was missing,
        action_on_missing_golden="assert", and the unit test framework
        asserted.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        tag = "test_df"
        _, file_name = self._get_golden_outcome_file_name(tag)
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_dataframe(
                act, abort_on_error=False, action_on_missing_golden="assert"
            )
            hdbg.dassert_file_exists(file_name + ".tmp")
            new_golden = pd.read_csv(file_name + ".tmp", index_col=0)
            hdbg.dassert_path_not_exists(file_name)
        finally:
            # Clean up.
            hio.delete_file(file_name)
        # Expected outcome doesn't exists and it was not updated.
        self.assertFalse(outcome_updated)
        self.assertFalse(file_exists)
        self.assertIs(is_equal, None)
        # Check golden.
        self.assert_equal(str(new_golden), str(act))

    def test_check_df_missing3(self) -> None:
        """
        Without running with --update_outcomes, the golden outcome was missing,
        action_on_missing_golden="update", and the unit test framework updates
        the golden.
        """
        if _to_skip_on_update_outcomes():
            return
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        tag = "test_df"
        _, file_name = self._get_golden_outcome_file_name(tag)
        try:
            # Remove the golden.
            hio.delete_file(file_name)
            # Check.
            outcome_updated, file_exists, is_equal = self.check_dataframe(
                act, abort_on_error=False, action_on_missing_golden="update"
            )
            hdbg.dassert_file_exists(file_name)
            new_golden = pd.read_csv(file_name, index_col=0)
        finally:
            # Clean up.
            hio.delete_file(file_name)
        # Expected outcome doesn't exists and it was not updated.
        self.assertTrue(outcome_updated)
        self.assertFalse(file_exists)
        self.assertIs(is_equal, None)
        # Check golden.
        self.assert_equal(str(new_golden), str(act))

    def _check_df_helper(
        self, act: pd.DataFrame, abort_on_error: bool, err_threshold: float
    ) -> Tuple[bool, bool, Optional[bool]]:
        golden_outcomes = pd.DataFrame(
            [[0, 1, 2], [3, 4, 5]], columns="a b c".split()
        )
        #
        tag = "test_df"
        _, file_name = self._get_golden_outcome_file_name(tag)
        # Overwrite the golden file, so that --update_golden doesn't matter.
        hio.create_enclosing_dir(file_name, incremental=True)
        golden_outcomes.to_csv(file_name)
        try:
            outcome_updated, file_exists, is_equal = self.check_dataframe(
                act, abort_on_error=abort_on_error, err_threshold=err_threshold
            )
        finally:
            # Clean up.
            golden_outcomes.to_csv(file_name)
            _git_add(file_name)
        return outcome_updated, file_exists, is_equal


# #############################################################################


class Test_check_string_debug1(hunitest.TestCase):
    def test1(self) -> None:
        act = "hello"
        # action_on_missing_golden = "assert"
        action_on_missing_golden = "update"
        self.check_string(act, action_on_missing_golden=action_on_missing_golden)

    def test2(self) -> None:
        act = pd.DataFrame([[0, 1, 2], [3, 4, 5]], columns="a b c".split())
        # action_on_missing_golden = "assert"
        action_on_missing_golden = "update"
        self.check_dataframe(
            act, action_on_missing_golden=action_on_missing_golden
        )


# #############################################################################


class Test_unit_test1(hunitest.TestCase):
    def test_purify_txt_from_client1(self) -> None:
        super_module_path = hgit.get_client_root(super_module=True)
        # TODO(gp): We should remove the current path.
        # pylint: disable=line-too-long
        txt = r"""
************* Module input [pylint]
$SUPER_MODULE/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py: Your code has been rated at -10.00/10 (previous run: -10.00/10, +0.00) [pylint]
$SUPER_MODULE/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3:20: W605 invalid escape sequence '\s' [flake8]
$SUPER_MODULE/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3:9: F821 undefined name 're' [flake8]
cmd line='$SUPER_MODULE/dev_scripts/linter.py -f $SUPER_MODULE/amp/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py --linter_log $SUPER_MODULE/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/linter.log'
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: [E0602(undefined-variable), ] Undefined variable 're' [pylint]
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: [W1401(anomalous-backslash-in-string), ] Anomalous backslash in string: '\s'. String constant might be missing an r prefix. [pylint]
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: error: Name 're' is not defined [mypy]
"""
        txt = txt.replace("$SUPER_MODULE", super_module_path)
        exp = r"""
************* Module input [pylint]
$GIT_ROOT/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py: Your code has been rated at -10.00/10 (previous run: -10.00/10, +0.00) [pylint]
$GIT_ROOT/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3:20: W605 invalid escape sequence '\s' [flake8]
$GIT_ROOT/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3:9: F821 undefined name 're' [flake8]
cmd line='$GIT_ROOT/dev_scripts/linter.py -f $GIT_ROOT/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py --linter_log $GIT_ROOT/dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/linter.log'
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: [E0602(undefined-variable), ] Undefined variable 're' [pylint]
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: [W1401(anomalous-backslash-in-string), ] Anomalous backslash in string: '\s'. String constant might be missing an r prefix. [pylint]
dev_scripts/test/Test_linter_py1.test_linter1/tmp.scratch/input.py:3: error: Name 're' is not defined [mypy]
"""
        # pylint: enable=line-too-long
        act = hunitest.purify_txt_from_client(txt)
        self.assert_equal(act, exp)

    def test_purify_txt_from_client2(self) -> None:
        """
        Test case when client root path is equal to `/`
        """
        # pylint: disable=redefined-outer-name
        hgit = umock.Mock()
        hgit.get_client_root.return_value = "/"
        txt = "/tmp/subdir1"
        exp = txt
        act = hunitest.purify_txt_from_client(txt)
        self.assertEqual(act, exp)


# #############################################################################


class Test_unit_test2(hunitest.TestCase):
    def test_purify_parquet_file_names1(self) -> None:
        """
        Test purification of Parquet file names with the path.

        The Parquet file names with the
        GUID have to be replaced with the `data.parquet` string.
        """
        txt = """
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=1/ea5e3faed73941a2901a2128abeac4ca-0.parquet
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=2/f7a39fefb69b40e0987cec39569df8ed-0.parquet
        """
        exp = """
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=1/data.parquet
        s3://some_bucket/root/currency_pair=BTC_USDT/year=2024/month=2/data.parquet
        """
        act = hunitest.purify_parquet_file_names(txt)
        hdbg.dassert_eq(act, exp)

    def test_purify_parquet_file_names2(self) -> None:
        """
        Test purification of Parquet file name without the path.
        """
        txt = """
        ffa39fffb69b40e0987cec39569df8ed-0.parquet
        """
        exp = """
        data.parquet
        """
        act = hunitest.purify_parquet_file_names(txt)
        hdbg.dassert_eq(act, exp)


# #############################################################################


class Test_get_dir_signature1(hunitest.TestCase):
    def helper(self, include_file_content: bool) -> str:
        in_dir = self.get_input_dir()
        act = hunitest.get_dir_signature(
            in_dir, include_file_content, num_lines=None
        )
        act = hunitest.purify_txt_from_client(act)
        return act  # type: ignore[no-any-return]

    def test1(self) -> None:
        """
        Test dir signature excluding the file content.
        """
        include_file_content = False
        act = self.helper(include_file_content)
        # pylint: disable=line-too-long
        exp = r"""
        # Dir structure
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_0
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_0/config.pkl
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_0/config.txt
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_0/run_notebook.0.log
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_1
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_1/config.pkl
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_1/config.txt
        $GIT_ROOT/helpers/test/outcomes/Test_get_dir_signature1.test1/input/result_1/run_notebook.1.log
        """
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test dir signature including the file content.
        """
        include_file_content = True
        act = self.helper(include_file_content)
        # The golden outcome is long and uninteresting so we use check_string.
        self.check_string(act, fuzzy_match=True)


# #############################################################################


class Test_purify_txt_from_client1(hunitest.TestCase):
    def helper(self, txt: str, exp: str) -> None:
        act = hunitest.purify_txt_from_client(txt)
        self.assert_equal(act, exp)

    def test1(self) -> None:
        txt = "amp/helpers/test/test_system_interaction.py"
        exp = "helpers/test/test_system_interaction.py"
        self.helper(txt, exp)

    def test2(self) -> None:
        txt = "amp/helpers/test/test_system_interaction.py"
        exp = "helpers/test/test_system_interaction.py"
        self.helper(txt, exp)

    def test3(self) -> None:
        txt = "['amp/helpers/test/test_system_interaction.py']"
        exp = "['helpers/test/test_system_interaction.py']"
        self.helper(txt, exp)


# TODO(ShaopengZ): numerical issue. (arm vs x86)
@pytest.mark.requires_ck_infra
class Test_purify_from_env_vars(hunitest.TestCase):
    """
    Test purification from env vars.
    """

    def helper(self, env_var: str) -> None:
        env_var_value = os.environ[env_var]
        input_ = f"s3://{env_var_value}/"
        act = hunitest.purify_from_env_vars(input_)
        exp = f"s3://${env_var}/"
        self.assert_equal(act, exp, fuzzy_match=True)

    @pytest.mark.skipif(
        not henv.execute_repo_config_code("get_name()") == "//cmamp",
        reason="Run only in //cmamp",
    )
    def test1(self) -> None:
        """
        - $CK_AWS_S3_BUCKET
        """
        env_var = "CK_AWS_S3_BUCKET"
        self.helper(env_var)

    @pytest.mark.requires_ck_infra
    def test2(self) -> None:
        """
        - $AM_TELEGRAM_TOKEN
        """
        env_var = "AM_TELEGRAM_TOKEN"
        self.helper(env_var)

    def test3(self) -> None:
        """
        - $AM_AWS_S3_BUCKET
        """
        env_var = "AM_AWS_S3_BUCKET"
        self.helper(env_var)

    def test4(self) -> None:
        """
        - $AM_ECR_BASE_PATH
        """
        env_var = "AM_ECR_BASE_PATH"
        self.helper(env_var)

    @pytest.mark.skipif(
        not henv.execute_repo_config_code("get_name()") == "//cmamp",
        reason="Run only in //cmamp",
    )
    def test_end_to_end(self) -> None:
        """
        - Multiple env vars.
        """
        am_aws_s3_bucket = os.environ["AM_AWS_S3_BUCKET"]
        ck_aws_s3_bucket = os.environ["CK_AWS_S3_BUCKET"]
        am_telegram_token = os.environ["AM_TELEGRAM_TOKEN"]
        am_ecr_base_path = os.environ["AM_ECR_BASE_PATH"]
        #
        text = f"""
        $AM_AWS_S3_BUCKET = {am_aws_s3_bucket}
        $CK_AWS_S3_BUCKET = {ck_aws_s3_bucket}
        $AM_TELEGRAM_TOKEN = {am_telegram_token}
        $AM_ECR_BASE_PATH = {am_ecr_base_path}
        """
        #
        actual = hunitest.purify_from_env_vars(text)
        self.check_string(actual, fuzzy_match=True)


# #############################################################################
# Test_purify_object_representation1
# #############################################################################


class Test_purify_object_representation1(hunitest.TestCase):
    def helper(self, txt: str, exp: str) -> None:
        txt = hprint.dedent(txt)
        act = hunitest.purify_object_representation(txt)
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp)

    def test1(self) -> None:
        txt = """
        load_prices: {'source_node_name': 'RealTimeDataSource object
        at 0x7f571c329b50
        """
        exp = r"""
        load_prices: {'source_node_name': 'RealTimeDataSource object
        at 0x"""
        self.helper(txt, exp)

    def test2(self) -> None:
        txt = """
        load_prices: {'source_node_name at 0x7f571c329b51':
        'RealTimeDataSource object at 0x7f571c329b50
        """
        exp = r"""
        load_prices: {'source_node_name at 0x':
        'RealTimeDataSource object at 0x"""
        self.helper(txt, exp)

    def test3(self) -> None:
        txt = """
        load_prices: {'source_node_name': 'RealTimeDataSource',
        'source_node_kwargs': {'market_data':
        <market_data.market_data.ReplayedMarketData
        object>, 'period': 'last_5mins', 'asset_id_col': 'asset_id',
        'multiindex_output': True}} process_forecasts: {'prediction_col': 'close',
        'execution_mode': 'real_time', 'process_forecasts_config':
        {'market_data':
        <market_data.market_data.ReplayedMarketData
        object at 0x7faff4c3faf0>,'portfolio  ': <oms.portfolio.SimulatedPortfolio
        object>, 'order_type': 'price@twap', 'ath_start_time':
        datetime.time(9, 30), 'trading_start_time': datetime.time(9, 30),
        'ath_end_time': datetime.time(16, 40), 'trading_end_time':
        datetime.time(16, 4  0)}}
        """
        exp = r"""
        load_prices: {'source_node_name': 'RealTimeDataSource',
        'source_node_kwargs': {'market_data':
        <market_data.market_data.ReplayedMarketData
        object>, 'period': 'last_5mins', 'asset_id_col': 'asset_id',
        'multiindex_output': True}} process_forecasts: {'prediction_col': 'close',
        'execution_mode': 'real_time', 'process_forecasts_config':
        {'market_data':
        <market_data.market_data.ReplayedMarketData
        object at 0x>,'portfolio  ': <oms.portfolio.SimulatedPortfolio
        object>, 'order_type': 'price@twap', 'ath_start_time':
        datetime.time(9, 30), 'trading_start_time': datetime.time(9, 30),
        'ath_end_time': datetime.time(16, 40), 'trading_end_time':
        datetime.time(16, 4  0)}}"""
        self.helper(txt, exp)

    def test4(self) -> None:
        """
        Test replacing wall_clock_time=Timestamp('..., tz='America/New_York'))
        """
        txt = """
        _knowledge_datetime_col_name='timestamp_db' <str> _delay_in_secs='0'
        <int>>, 'bar_duration_in_secs': 300, 'rt_timeout_in_secs_or_time': 900} <dict>,
        _dst_dir=None <NoneType>, _fit_at_beginning=False <bool>,
        _wake_up_timestamp=None <NoneType>, _bar_duration_in_secs=300 <int>,
        _events=[Event(num_it=1, current_time=Timestamp('2000-01-01
        10:05:00-0500', tz='America/New_York'),
        wall_clock_time=Timestamp('2022-08-04 09:29:13.441715-0400',
        tz='America/New_York')), Event(num_it=2,
        current_time=Timestamp('2000-01-01 10:10:00-0500',
        tz='America/New_York'), wall_clock_time=Timestamp('2022-08-04
        09:29:13.892793-0400', tz='America/New_York')), Event(num_it=3,
        current_time=Timestamp('2000-01-01 10:15:00-0500',
        tz='America/New_York'), wall_clock_time=Timestamp('2022-08-04
        09:29:14.131619-0400', tz='America/New_York'))] <list>)
        """
        exp = """
        _knowledge_datetime_col_name='timestamp_db' <str> _delay_in_secs='0'
        <int>>, 'bar_duration_in_secs': 300, 'rt_timeout_in_secs_or_time': 900} <dict>,
        _dst_dir=None <NoneType>, _fit_at_beginning=False <bool>,
        _wake_up_timestamp=None <NoneType>, _bar_duration_in_secs=300 <int>,
        _events=[Event(num_it=1, current_time=Timestamp('2000-01-01
        10:05:00-0500', tz='America/New_York'),
        wall_clock_time=Timestamp('xxx', tz='America/New_York')),
        Event(num_it=2, current_time=Timestamp('2000-01-01 10:10:00-0500',
        tz='America/New_York'), wall_clock_time=Timestamp('xxx',
        tz='America/New_York')), Event(num_it=3,
        current_time=Timestamp('2000-01-01 10:15:00-0500',
        tz='America/New_York'), wall_clock_time=Timestamp('xxx',
        tz='America/New_York'))] <list>)
        """
        txt = " ".join(hprint.dedent(txt).split("\n"))
        exp = " ".join(hprint.dedent(exp).split("\n"))
        self.helper(txt, exp)


# #############################################################################


class Test_purify_amp_reference1(hunitest.TestCase):
    def helper(self, txt: str, exp: str) -> None:
        txt = hprint.dedent(txt)
        act = hunitest.purify_amp_references(txt)
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp)

    def test1(self) -> None:
        """
        Remove the reference to `amp.`.
        """
        txt = """
        * Failed assertion *
        Instance '<amp.helpers.test.test_dbg._Man object at 0x123456>'
            of class '_Man' is not a subclass of '<class 'int'>'
        """
        exp = r"""
        * Failed assertion *
        Instance '<helpers.test.test_dbg._Man object at 0x123456>'
            of class '_Man' is not a subclass of '<class 'int'>'
        """
        self.helper(txt, exp)


# #############################################################################


class Test_purify_from_environment1(hunitest.TestCase):
    def check_helper(self, input_: str, exp: str) -> None:
        """
        Check that the text is purified from environment variables correctly.
        """
        try:
            # Manually set a user name to test the behaviour.
            hsystem.set_user_name("root")
            # Run.
            act = hunitest.purify_from_environment(input_)
            self.assert_equal(act, exp, fuzzy_match=True)
        finally:
            # Reset the global user name variable regardless of a test results.
            hsystem.set_user_name(None)

    def test1(self) -> None:
        input_ = "IMAGE=$CK_ECR_BASE_PATH/amp_test:local-root-1.0.0"
        exp = "IMAGE=$CK_ECR_BASE_PATH/amp_test:local-$USER_NAME-1.0.0"
        self.check_helper(input_, exp)

    def test2(self) -> None:
        input_ = "--name root.amp_test.app.app"
        exp = "--name $USER_NAME.amp_test.app.app"
        self.check_helper(input_, exp)

    def test3(self) -> None:
        input_ = "run --rm -l user=root"
        exp = "run --rm -l user=$USER_NAME"
        self.check_helper(input_, exp)

    def test4(self) -> None:
        input_ = "run_docker_as_root='True'"
        exp = "run_docker_as_root='True'"
        self.check_helper(input_, exp)

    def test5(self) -> None:
        input_ = "out_col_groups: [('root_q_mv',), ('root_q_mv_adj',), ('root_q_mv_os',)]"
        exp = "out_col_groups: [('root_q_mv',), ('root_q_mv_adj',), ('root_q_mv_os',)]"
        self.check_helper(input_, exp)

    def test6(self) -> None:
        input_ = "/app/jupyter_core/application.py"
        exp = "$GIT_ROOT/jupyter_core/application.py"
        self.check_helper(input_, exp)

    def test7(self) -> None:
        input_ = "/app"
        exp = "$GIT_ROOT"
        self.check_helper(input_, exp)


# #############################################################################


class Test_purify_line_number(hunitest.TestCase):
    """
    Check that `purify_line_number` is working as expected.
    """

    def test1(self) -> None:
        """
        Check that the text is purified from line numbers correctly.
        """
        txt = """
        dag_config (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        in_col_groups (marked_as_used=True, writer=$GIT_ROOT/dataflow/system/system_builder_utils.py::286::apply_history_lookback, val_type=list): [('close',), ('volume',)]
        out_col_group (marked_as_used=True, writer=$GIT_ROOT/dataflow/system/system_builder_utils.py::286::apply_history_lookback, val_type=tuple): ()
        """
        expected = r"""
        dag_config (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        in_col_groups (marked_as_used=True, writer=$GIT_ROOT/dataflow/system/system_builder_utils.py::$LINE_NUMBER::apply_history_lookback, val_type=list): [('close',), ('volume',)]
        out_col_group (marked_as_used=True, writer=$GIT_ROOT/dataflow/system/system_builder_utils.py::$LINE_NUMBER::apply_history_lookback, val_type=tuple): ()
        """
        actual = hunitest.purify_line_number(txt)
        self.assert_equal(actual, expected, fuzzy_match=True)
