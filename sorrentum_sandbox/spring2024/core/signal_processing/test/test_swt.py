import logging
from typing import Optional

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing.swt as csiprswt
import core.statistics.random_samples as cstrasam
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_swt(hunitest.TestCase):
    def helper(
        self,
        *,
        timing_mode: Optional[str] = None,
        output_mode: Optional[str] = None,
    ) -> str:
        series = self._get_series(seed=1)
        actual = csiprswt.get_swt(
            series,
            timing_mode=timing_mode,
            output_mode=output_mode,
        )
        if isinstance(actual, tuple):
            smooth_df_string = hpandas.df_to_str(
                actual[0],
                num_rows=None,
            )
            detail_df_string = hpandas.df_to_str(
                actual[1],
                num_rows=None,
            )
            output_str = (
                f"smooth_df:\n{smooth_df_string}\n"
                f"\ndetail_df\n{detail_df_string}\n"
            )
        else:
            output_str = hpandas.df_to_str(actual, num_rows=None)
        return output_str

    def test_clean1(self) -> None:
        """
        Test for default values.
        """
        output_str = self.helper()
        self.check_string(output_str)

    def test_timing_mode1(self) -> None:
        """
        Test for timing_mode="knowledge_time".
        """
        timing_mode = "knowledge_time"
        output_str = self.helper(timing_mode=timing_mode)
        self.check_string(output_str)

    def test_timing_mode2(self) -> None:
        """
        Test for timing_mode="zero_phase".
        """
        timing_mode = "zero_phase"
        output_str = self.helper(timing_mode=timing_mode)
        self.check_string(output_str)

    def test_timing_mode3(self) -> None:
        """
        Test for timing_mode="raw".
        """
        timing_mode = "raw"
        output_str = self.helper(timing_mode=timing_mode)
        self.check_string(output_str)

    def test_output_mode1(self) -> None:
        """
        Test for output_mode="tuple".
        """
        output_mode = "tuple"
        output_str = self.helper(output_mode=output_mode)
        self.check_string(output_str)

    def test_output_mode2(self) -> None:
        """
        Test for output_mode="smooth".
        """
        output_mode = "smooth"
        output_str = self.helper(output_mode=output_mode)
        self.check_string(output_str)

    def test_output_mode3(self) -> None:
        """
        Test for output_mode="detail".
        """
        output_mode = "detail"
        output_str = self.helper(output_mode=output_mode)
        self.check_string(output_str)

    def test_depth(self) -> None:
        """
        Test for sufficient input data length given `depth`.
        """
        series = self._get_series(seed=1, periods=10)
        # The test should not raise on this call.
        csiprswt.get_swt(series, depth=2, output_mode="detail")
        with self.assertRaises(ValueError):
            # The raise comes from the `get_swt` implementation.
            csiprswt.get_swt(series, depth=3, output_mode="detail")
        with self.assertRaises(ValueError):
            # This raise comes from `pywt`.
            csiprswt.get_swt(series, depth=5, output_mode="detail")

    @staticmethod
    def _get_series(seed: int, periods: int = 20) -> pd.Series:
        return cstrasam.get_iid_standard_gaussian_samples(periods, seed)


class Test_get_swt_1(hunitest.TestCase):
    """
    Test warmup, knowledge time, and time shifting behavior.
    """

    def test_haar_smooth_1(self) -> None:
        """
        Test warmup and knowledge time behavior.

        The warmup for level-2 is so long that we only see the last
        effect at that level of the impulse.
        """
        srs = pd.Series([0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="haar",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=2,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
     1     2
0  NaN   NaN
1  NaN   NaN
2  0.0   NaN
3  0.5   NaN
4  0.5   NaN
5  0.0   NaN
6  0.0  0.25
7  0.0  0.00
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_haar_smooth_2(self) -> None:
        """
        Test warmup and knowledge time behavior.

        We do not have enough warmup to generate level-2 coefficients at
        the time of the impulse. However, the effects of the impulse can
        be seen as soon as the warm-up period is over.
        """
        srs = pd.Series([0, 0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="haar",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=2,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
     1     2
0  NaN   NaN
1  NaN   NaN
2  0.0   NaN
3  0.0   NaN
4  0.5   NaN
5  0.5   NaN
6  0.0  0.25
7  0.0  0.25
8  0.0  0.00
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_haar_smooth_3(self) -> None:
        """
        Test warmup and knowledge time behavior.

        We have just enough warmup to begin producing coefficients at
        the second level at the time of the impulse (index 6).
        """
        srs = pd.Series([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="haar",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=2,
        )
        expected = r"""
      1     2
0   NaN   NaN
1   NaN   NaN
2   0.0   NaN
3   0.0   NaN
4   0.0   NaN
5   0.0   NaN
6   0.5  0.25
7   0.5  0.25
8   0.0  0.25
9   0.0  0.25
10  0.0  0.00
"""
        actual = hpandas.df_to_str(smooth, num_rows=None)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_db2_smooth_1(self) -> None:
        srs = pd.Series([0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="db2",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=1,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
          1
0       NaN
1       NaN
2       NaN
3       NaN
4  0.158494
5  0.591506
6  0.341506
7  0.000000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_db2_smooth_2(self) -> None:
        srs = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="db2",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=2,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
           1         2
0        NaN       NaN
1        NaN       NaN
2        NaN       NaN
3        NaN       NaN
4   0.000000       NaN
5   0.000000       NaN
6   0.000000       NaN
7   0.000000       NaN
8  -0.091506       NaN
9   0.158494       NaN
10  0.591506       NaN
11  0.341506       NaN
12  0.000000  0.039623
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_db2_smooth_3(self) -> None:
        srs = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="db2",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=2,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
           1         2
0        NaN       NaN
1        NaN       NaN
2        NaN       NaN
3        NaN       NaN
4   0.000000       NaN
5   0.000000       NaN
6   0.000000       NaN
7   0.000000       NaN
8  -0.091506       NaN
9   0.158494       NaN
10  0.591506       NaN
11  0.341506       NaN
12  0.000000  0.039623
13  0.000000  0.147877
14  0.000000  0.318630
15  0.000000  0.256130
16 -0.091506  0.210377
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_db3_smooth_1(self) -> None:
        srs = pd.Series([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        smooth = csiprswt.get_swt(
            srs,
            wavelet="db3",
            timing_mode="knowledge_time",
            output_mode="smooth",
            depth=1,
        )
        actual = hpandas.df_to_str(smooth, num_rows=None)
        expected = r"""
           1
0        NaN
1        NaN
2        NaN
3        NaN
4        NaN
5        NaN
6   0.024909
7  -0.060416
8  -0.095467
9   0.325183
10  0.570558
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_get_swt_2(hunitest.TestCase):
    def test_scaling_invariance_1(self) -> None:
        periods = 100
        seed = 1
        depth = 3
        wavelet = "db5"
        timing_mode = "knowledge_time"
        output_mode = "detail_and_last_smooth"
        shift = 0
        scale_factor = 2.0
        atol = 1e-5
        self._test_invariance_helper(
            periods,
            seed,
            depth,
            wavelet,
            timing_mode,
            output_mode,
            shift,
            scale_factor,
            atol,
        )

    # TODO(Paul): Debug trailing coefficients vs NaNs issue.
    # def test_shift_invariance(self) -> None:
    #     periods = 100
    #     seed = 1
    #     depth = 3
    #     wavelet = "db5"
    #     timing_mode = "knowledge_time"
    #     output_mode = "detail"
    #     shift = 1
    #     scale_factor = 1
    #     atol = 1e-5
    #     self._test_invariance_helper(
    #         periods,
    #         seed,
    #         depth,
    #         wavelet,
    #         timing_mode,
    #         output_mode,
    #         shift,
    #         scale_factor,
    #         atol
    #     )

    def _test_invariance_helper(
        self,
        periods,
        seed,
        depth,
        wavelet,
        timing_mode,
        output_mode,
        shift,
        scale_factor,
        atol,
    ) -> None:
        srs = cstrasam.get_iid_standard_gaussian_samples(periods, seed)
        srs_swt_a = csiprswt.get_swt(
            scale_factor * srs,
            depth=depth,
            wavelet=wavelet,
            timing_mode=timing_mode,
            output_mode=output_mode,
        ).shift(shift)
        srs_swt_b = scale_factor * csiprswt.get_swt(
            srs.shift(shift),
            depth=depth,
            wavelet=wavelet,
            timing_mode=timing_mode,
            output_mode=output_mode,
        )
        self.assert_dfs_close(srs_swt_a, srs_swt_b, atol=atol)


class Test_get_swt_3(hunitest.TestCase):
    def test_knowledge_time_1(self) -> None:
        impulse_position = 2**4
        wavelet = "haar"
        levels = 3
        swt = self._test_knowledge_time_helper(
            impulse_position,
            wavelet,
            levels,
        )
        actual = hpandas.df_to_str(swt.iloc[impulse_position], num_rows=None)
        expected = r"""
             16
1        -0.500
2        -0.250
3        -0.125
3_smooth  0.125
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_knowledge_time_2(self) -> None:
        impulse_position = 2**5
        wavelet = "db2"
        levels = 3
        swt = self._test_knowledge_time_helper(
            impulse_position,
            wavelet,
            levels,
        )
        actual = hpandas.df_to_str(swt.iloc[impulse_position], num_rows=None)
        expected = r"""
                32
1        -0.341506
2         0.031250
3        -0.002860
3_smooth -0.000766
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_knowledge_time_3(self) -> None:
        impulse_position = 2**6
        wavelet = "db3"
        levels = 3
        swt = self._test_knowledge_time_helper(
            impulse_position,
            wavelet,
            levels,
        )
        actual = hpandas.df_to_str(swt.iloc[impulse_position], num_rows=None)
        expected = r"""
                64
1        -0.235234
2        -0.005859
3        -0.000146
3_smooth  0.000015
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def _test_knowledge_time_helper(
        self,
        impulse_position: int,
        wavelet: str,
        levels: int,
    ) -> pd.DataFrame:
        srs = pd.Series([0] * 2 * impulse_position)
        srs.iloc[impulse_position] = 1
        swt = csiprswt.get_swt(
            srs,
            wavelet,
            levels,
            timing_mode="knowledge_time",
            output_mode="detail_and_last_smooth",
        )
        max_abs_swt_before_impulse = swt.iloc[:impulse_position].abs().max().max()
        np.testing.assert_almost_equal(max_abs_swt_before_impulse, 0.0)
        return swt


class Test_compute_lag_weights(hunitest.TestCase):
    def test1(self) -> None:
        weights = [-1, -1, 1]
        actual = csiprswt.compute_lag_weights(weights)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
     normalized_weight
lag
0                  1.0
1                  0.0
2                  0.0
3                  0.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        weights = [-1 / np.sqrt(2), -1 / 2, 1 / 2]
        actual = csiprswt.compute_lag_weights(weights, norm=False)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
     normalized_weight
lag
0                  1.0
1                  0.0
2                  0.0
3                  0.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################
# Low/high pass filters
# #############################################################################


class Test_compute_swt_low_pass(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test low-pass filtering.
        """
        steps = 10
        seed = 0
        increments = cstrasam.get_iid_standard_gaussian_samples(steps, seed)
        random_walk = cstrasam.convert_increments_to_random_walk(increments)
        actual = csiprswt.compute_swt_low_pass(random_walk, level=2)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
    n_samples=10_seed=0
0                   NaN
1                   NaN
2                   NaN
3                   NaN
4                   NaN
5                   NaN
6              0.535287
7              0.843994
8              1.363245
9              1.840481
10             1.910962
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_swt_high_pass(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test high-pass filtering.
        """
        steps = 10
        seed = 0
        increments = cstrasam.get_iid_standard_gaussian_samples(steps, seed)
        random_walk = cstrasam.convert_increments_to_random_walk(increments)
        actual = csiprswt.compute_swt_high_pass(random_walk, level=2)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
    n_samples=10_seed=0
0                   NaN
1                   NaN
2                   NaN
3                   NaN
4                   NaN
5                   NaN
6              0.029587
7              1.024880
8              1.452710
9              0.271739
10            -1.064163
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################
# Wavelet properties
# #############################################################################


class Test_get_knowledge_time_warmup_lengths(hunitest.TestCase):
    def helper(self, wavelets, depth, expected) -> None:
        lengths = csiprswt.get_knowledge_time_warmup_lengths(wavelets, depth)
        actual = hpandas.df_to_str(
            lengths,
            num_rows=None,
        )
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test1(self) -> None:
        wavelets = [
            "bior1.3",
            "coif1",
            "db2",
            "dmey",
            "haar",
            "rbio1.3",
            "sym3",
        ]
        depth = 10
        expected = r"""
wavelet  bior1.3  coif1   db2   dmey  haar  rbio1.3  sym3
level
1              6      6     4     62     2        6     6
2             18     18    12    186     6       18    18
3             42     42    28    434    14       42    42
4             90     90    60    930    30       90    90
5            186    186   124   1922    62      186   186
6            378    378   252   3906   126      378   378
7            762    762   508   7874   254      762   762
8           1530   1530  1020  15810   510     1530  1530
9           3066   3066  2044  31682  1022     3066  3066
10          6138   6138  4092  63426  2046     6138  6138
"""
        self.helper(wavelets, depth, expected)


class Test_summarize_discrete_wavelets(hunitest.TestCase):
    def test1(self) -> None:
        df = csiprswt.summarize_discrete_wavelets()
        actual = hpandas.df_to_str(df, num_rows=None)
        self.check_string(actual)


# #############################################################################
# Wavelet variance/covariance
# #############################################################################


def get_daily_gaussian(seed: int) -> pd.Series:
    # TODO(Paul): Do not rely on `statsmodels` for random data.
    process = carsigen.ArmaProcess([], [])
    realization = process.generate_sample(
        {"start": "2000-01-01", "end": "2005-01-01", "freq": "B"}, seed=seed
    )
    return realization


class Test_compute_swt_var(hunitest.TestCase):
    def test_num_non_nan(self) -> None:
        """
        Verify the number of non-NaN data points to be used for the variance.
        """
        srs = get_daily_gaussian(seed=0)
        swt_var = csiprswt.compute_swt_var(srs, depth=6)
        actual = swt_var.count().values[0]
        np.testing.assert_equal(actual, 1179)

    def test_variance_preservation1(self) -> None:
        """
        Verify variance is preserved across time.
        """
        srs = get_daily_gaussian(seed=0)
        swt_var = csiprswt.compute_swt_var(srs, depth=6)
        actual = swt_var.sum()
        np.testing.assert_allclose(actual, [1102.66], atol=0.01)

    def test_variance_preservation2(self) -> None:
        """
        Verify level variance is preserved in sum.
        """
        srs = get_daily_gaussian(seed=0)
        swt_var = csiprswt.compute_swt_var(srs, depth=6, axis=1)
        actual = swt_var.sum()
        np.testing.assert_allclose(actual, [1102.66], atol=0.01)


class Test_compute_swt_var_summary(hunitest.TestCase):
    def test1(self) -> None:
        srs = get_daily_gaussian(seed=0)
        swt_var_summary = csiprswt.compute_swt_var_summary(srs, depth=6)
        actual = hpandas.df_to_str(
            swt_var_summary,
            num_rows=None,
        )
        expected = r"""
    swt_var  cum_swt_var      perc  cum_perc
1  0.492558     0.492558  0.517159  0.517159
2  0.234882     0.727440  0.246613  0.763773
3  0.116992     0.844432  0.122835  0.886608
4  0.049948     0.894380  0.052443  0.939051
5  0.024626     0.919006  0.025856  0.964907
6  0.016248     0.935254  0.017060  0.981966
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_fir_zscore(hunitest.TestCase):
    def test_default_zscoring(self) -> None:
        """
        Apply FIR z-scoring to a random walk.
        """
        steps = 20
        seed = 0
        increments = cstrasam.get_iid_standard_gaussian_samples(steps, seed)
        random_walk = cstrasam.convert_increments_to_random_walk(increments)
        actual = csiprswt.compute_fir_zscore(random_walk, dyadic_tau=2)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
    n_samples=20_seed=0
0                   NaN
1                   NaN
2                   NaN
3                   NaN
4                   NaN
5                   NaN
6                   NaN
7                   NaN
8                   NaN
9              0.302144
10            -1.018463
11            -1.147699
12            -0.668392
13            -1.457491
14            -0.977855
15            -1.130861
16            -0.799927
17            -0.817433
18            -0.574802
19             0.016313
20             1.152972
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
