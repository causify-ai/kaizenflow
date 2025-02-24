import logging

import numpy as np
import pandas as pd

import core.signal_processing.fir_utils as csprfiut
import core.signal_processing.swt as csiprswt
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_extract_fir_filter_weights(hunitest.TestCase):
    def swt_helper(
        self,
        level: int,
        wavelet: str,
        timing_mode: str,
        output_mode: str,
        warmup_length,
    ) -> str:
        input = pd.Series(0, range(0, warmup_length))
        func = csiprswt.get_swt_level
        func_kwargs = {
            "level": level,
            "wavelet": wavelet,
            "timing_mode": timing_mode,
            "output_mode": output_mode,
        }
        weights = csprfiut.extract_fir_filter_weights(
            input, func, func_kwargs, warmup_length
        )
        result = hpandas.df_to_str(weights, num_rows=None)
        return result

    def test1(self) -> None:
        actual = self.swt_helper(
            1,
            "haar",
            "knowledge_time",
            "detail",
            4,
        )
        expected = r"""
   weight  normalized_weight  relative_weight
0     0.0                0.0              0.0
1     0.0                0.0              0.0
2     0.5                0.5              1.0
3    -0.5               -0.5             -1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        actual = self.swt_helper(
            1,
            "haar",
            "knowledge_time",
            "smooth",
            4,
        )
        expected = r"""
   weight  normalized_weight  relative_weight
0     0.0                0.0              0.0
1     0.0                0.0              0.0
2     0.5                0.5              1.0
3     0.5                0.5              1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test3(self) -> None:
        actual = self.swt_helper(
            2,
            "haar",
            "knowledge_time",
            "detail",
            8,
        )
        expected = r"""
   weight  normalized_weight  relative_weight
0    0.00               0.00              0.0
1    0.00               0.00              0.0
2    0.00               0.00              0.0
3    0.00               0.00              0.0
4    0.25               0.25              1.0
5    0.25               0.25              1.0
6   -0.25              -0.25             -1.0
7   -0.25              -0.25             -1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test4(self) -> None:
        actual = self.swt_helper(
            2,
            "haar",
            "knowledge_time",
            "smooth",
            8,
        )
        expected = r"""
   weight  normalized_weight  relative_weight
0    0.00               0.00              0.0
1    0.00               0.00              0.0
2    0.00               0.00              0.0
3    0.00               0.00              0.0
4    0.25               0.25              1.0
5    0.25               0.25              1.0
6    0.25               0.25              1.0
7    0.25               0.25              1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test5(self) -> None:
        actual = self.swt_helper(
            1,
            "db2",
            "knowledge_time",
            "detail",
            8,
        )
        expected = r"""
     weight  normalized_weight  relative_weight
0  0.000000           0.000000         0.000000
1  0.000000           0.000000         0.000000
2  0.000000           0.000000         0.000000
3  0.000000           0.000000         0.000000
4 -0.091506          -0.077350        -0.267949
5 -0.158494          -0.133975        -0.464102
6  0.591506           0.500000         1.732051
7 -0.341506          -0.288675        -1.000000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test6(self) -> None:
        actual = self.swt_helper(
            1,
            "db2",
            "knowledge_time",
            "smooth",
            8,
        )
        expected = r"""
     weight  normalized_weight  relative_weight
0  0.000000           0.000000         0.000000
1  0.000000           0.000000         0.000000
2  0.000000           0.000000         0.000000
3  0.000000           0.000000         0.000000
4  0.341506           0.288675         3.732051
5  0.591506           0.500000         6.464102
6  0.158494           0.133975         1.732051
7 -0.091506          -0.077350        -1.000000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_fit_ema_to_fir_filter(hunitest.TestCase):
    def test1(self) -> None:
        lag_weights = pd.Series([1, 0.5, 0.25, 0.125])
        actual = csprfiut.fit_ema_to_fir_filter(lag_weights)
        actual_0 = hpandas.df_to_str(actual[0], num_rows=None)
        actual_1 = actual[1]
        expected_0 = r"""
   com=1.022
0   0.978454
1   0.367793
2   0.138250
3   0.051967
"""
        self.assert_equal(actual_0, expected_0, fuzzy_match=True)
        expected_1 = 1.0220205693130382
        np.testing.assert_almost_equal(actual_1, expected_1)
