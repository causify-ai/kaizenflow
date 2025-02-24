import logging
from typing import Union

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing.misc_transformations as csprmitr
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_sign_normalize(hunitest.TestCase):
    """
    Check that signal values are normalized according to sign correctly.
    """

    def test1(self) -> None:
        """
        - input signal is `pd.Series`
        - atol = 0
        """
        signal = pd.Series([-5, -1, 0, 1, 5])
        res = csprmitr.sign_normalize(signal)
        actual_signature = hpandas.df_to_str(res)
        expected_signature = r"""
           0
        0 -1
        1 -1
        2  0
        3  1
        4  1
        """
        self.assert_equal(actual_signature, expected_signature, fuzzy_match=True)

    def test2(self) -> None:
        """
        - input signal is `pd.Series`
        - atol = 2
        """
        signal = pd.Series([-3, -2, 0, 2, 3])
        atol = 2
        res = csprmitr.sign_normalize(signal, atol)
        actual_signature = hpandas.df_to_str(res)
        expected_signature = r"""
           0
        0 -1
        1 -1
        2  0
        3  1
        4  1
        """
        self.assert_equal(actual_signature, expected_signature, fuzzy_match=True)

    def test3(self) -> None:
        """
        - input signal is `pd.DataFrame`
        - atol = 0
        """
        signal = pd.DataFrame([-5, -1, 0, 1, 5])
        actual = csprmitr.sign_normalize(signal)
        expected = pd.DataFrame([-1, -1, 0, 1, 1])
        self.assertTrue(actual.equals(expected))

    def test4(self) -> None:
        """
        - input signal is `pd.DataFrame`
        - atol = 2
        """
        signal = pd.DataFrame([-3, -2, 0, 2, 3])
        atol = 2
        actual = csprmitr.sign_normalize(signal, atol)
        expected = pd.DataFrame([-1, -1, 0, 1, 1])
        self.assertTrue(actual.equals(expected))


class Test_compress_tails(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check that an input is processed correctly with default param values.
        """
        signal = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        actual = csprmitr.compress_tails(signal)
        actual = hpandas.df_to_str(actual)
        expected = r"""          A         B
        0  0.761594  0.999329
        1  0.964028  0.999909
        2  0.995055  0.999988
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Check that an input is processed correctly with specified param values.
        """
        signal = pd.DataFrame({"A": [1, 0, -3], "B": [-4, 5, 6]})
        rescale = 4
        scale = 0.5
        actual = csprmitr.compress_tails(signal, scale=scale, rescale=rescale)
        actual = hpandas.df_to_str(actual)
        expected = r"""     A    B
        0  0.5 -0.5
        1  0.0  0.5
        2 -0.5  0.5
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test3(self) -> None:
        """
        Check that an empty input is processed correctly.
        """
        signal = pd.DataFrame({"A": [], "B": []})
        actual = csprmitr.compress_tails(signal)
        actual = hpandas.df_to_str(actual)
        expected = r"""Empty DataFrame
        Columns: [A, B]
        Index: []"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test4(self) -> None:
        """
        Check that an error is raised if scale is lower than 0.
        """
        signal = pd.Series([1, 2, 3, 4, 5])
        scale = -1
        with self.assertRaises(AssertionError) as cm:
            csprmitr.compress_tails(signal, scale=scale)
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        0 < -1
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test5(self) -> None:
        """
        Check that an error is raised if rescale is lower than 0.
        """
        signal = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [1, 2, 3, 4, 5]})
        rescale = -1
        with self.assertRaises(AssertionError) as cm:
            csprmitr.compress_tails(signal, rescale=rescale)
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        0 < -1
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test6(self) -> None:
        """
        Check that an error is raised if input contains non-numeric values.
        """
        signal = pd.DataFrame({"A": ["x", "y", "z"], "B": [1, 2, 3]})
        with self.assertRaises(TypeError) as cm:
            csprmitr.compress_tails(signal)
        actual = str(cm.exception)
        expected = "unsupported operand type(s) for /: 'str' and 'int'"
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_get_symmetric_equisized_bins(hunitest.TestCase):
    def test_zero_in_bin_interior_false(self) -> None:
        input_ = pd.Series([-1, 3])
        expected = np.array([-3, -2, -1, 0, 1, 2, 3])
        actual = csprmitr.get_symmetric_equisized_bins(input_, 1)
        np.testing.assert_array_equal(actual, expected)

    def test_zero_in_bin_interior_true(self) -> None:
        input_ = pd.Series([-1, 3])
        expected = np.array([-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5])
        actual = csprmitr.get_symmetric_equisized_bins(input_, 1, True)
        np.testing.assert_array_equal(actual, expected)

    def test_infs(self) -> None:
        data = pd.Series([-1, np.inf, -np.inf, 3])
        expected = np.array([-4, -2, 0, 2, 4])
        actual = csprmitr.get_symmetric_equisized_bins(data, 2)
        np.testing.assert_array_equal(actual, expected)


class Test_digitize1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        bins = [0, 0.2, 0.4]
        right = False
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csprmitr.digitize(signal, bins, right)
        self.check_string(actual.to_string())

    def test_heaviside1(self) -> None:
        heaviside = carsigen.get_heaviside(-10, 20, 1, 1)
        bins = [0, 0.2, 0.4]
        right = False
        actual = csprmitr.digitize(heaviside, bins, right)
        self.check_string(actual.to_string())


class Test_compute_weighted_sum1(hunitest.TestCase):
    @staticmethod
    def get_test_df() -> pd.DataFrame:
        df = pd.DataFrame(
            [[1, -1, np.nan], [0, 1, 1], [-1, -1, -1]],
            [0, 1, 2],
            ["col1", "col2", 3],
        )
        return df

    def test1(self) -> None:
        df = Test_compute_weighted_sum1.get_test_df()
        weights = pd.Series([1, 1, 0], ["col1", "col2", 3], name="test_weights")
        actual = csprmitr.compute_weighted_sum(df, weights)
        actual_str = hpandas.df_to_str(actual)
        expected_str = r"""
        test_weights
0           0.0
1           1.0
2          -2.0"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)


class Test_split_positive_and_negative_parts(hunitest.TestCase):
    @staticmethod
    def get_test_data() -> pd.Series:
        """
        Create artificial signal for unit test.
        """
        data = [100, -50, 0, 75, -25]
        index = pd.date_range(start="2023-04-01", periods=5)
        test_data = pd.Series(data, index=index, name="position_intent_1")
        return test_data

    def test1(self) -> None:
        """
        Check that a Series input is processed correctly.
        """
        series_input = self.get_test_data()
        self.helper(series_input)

    def test2(self) -> None:
        """
        Check that a DataFrame input is processed correctly.
        """
        df_input = pd.DataFrame({"position_intent_1": self.get_test_data()})
        self.helper(df_input)

    def helper(self, input: Union[pd.Series, pd.DataFrame]) -> None:
        actual_df = csprmitr.split_positive_and_negative_parts(input)
        expected_length = 5
        expected_column_names = ["positive", "negative"]
        expected_column_unique_values = None
        expected_signature = r"""
        # df=
        index=[2023-04-01 00:00:00, 2023-04-05 00:00:00]
        columns=positive,negative
        shape=(5, 2)
                    positive  negative
        2023-04-01     100.0       0.0
        2023-04-02       0.0      50.0
        2023-04-03       0.0       0.0
        2023-04-04      75.0       0.0
        2023-04-05       0.0      25.0
        """
        self.check_df_output(
            actual_df,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )


# #############################################################################


class TestNormalize(hunitest.TestCase):
    def test1(self):
        """
        Check that a simple signal input is normalized correctly.
        """
        # Create input data for testing.
        signal = pd.Series([-7, -6, -5, -1, 0, 2, 3, 4, 8], name="Signals")
        actual_result = csprmitr.normalize(signal)
        # Define expected values.
        expected_length = len(signal)
        expected_unique_values = None
        expected_result_signature = r"""
            Signals
        0    -0.490098
        1    -0.420084
        2    -0.350070
        3    -0.070014
        4    0.000000
        5    0.140028
        6    0.210042
        7    0.280056
        8    0.560112
        """
        # Check result.
        self.check_srs_output(
            actual_result,
            expected_length,
            expected_unique_values,
            expected_result_signature,
        )

    def test2(self):
        """
        Check that a signal input with NaN values is processed correctly.
        """
        # Create input data for testing.
        signal = pd.Series([-7, -6, -5, -1, np.NaN, 2, 3, 4, 8], name="Signals")
        with self.assertRaises(AssertionError) as result:
            csprmitr.normalize(signal)
        actual_result = str(result.exception)
        # Define expected values.
        expected_result_signature = r"""
        ################################################################################
        * Failed assertion *
        cond=False
        NaNs detected at Index([4], dtype='int64')
        ################################################################################
        """
        # Check result.
        self.assert_equal(
            actual_result, expected_result_signature, fuzzy_match=True
        )
