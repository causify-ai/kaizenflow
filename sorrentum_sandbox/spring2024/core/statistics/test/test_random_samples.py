import logging

import pandas as pd

import core.statistics.random_samples as cstrasam
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_iid_standard_gaussian_samples(hunitest.TestCase):
    def test1(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_standard_gaussian_samples(
            n_samples=n_samples,
            seed=seed,
        )
        actual = _get_df_as_str(samples)
        expected = r"""
    n_samples=10_seed=0
1               0.12573
2              -0.13210
3               0.64042
4               0.10490
5              -0.53567
6               0.36160
7               1.30400
8               0.94708
9              -0.70374
10             -1.26542
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_get_iid_rademacher_samples(hunitest.TestCase):
    def test1(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_rademacher_samples(
            n_samples=n_samples,
            seed=seed,
        )
        actual = _get_df_as_str(samples)
        expected = r"""
    n_samples=10_seed=0
1                     1
2                     1
3                     1
4                    -1
5                    -1
6                    -1
7                    -1
8                    -1
9                    -1
10                    1
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_convert_increments_to_random_walk(hunitest.TestCase):
    def test1(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_standard_gaussian_samples(
            n_samples=n_samples,
            seed=seed,
        )
        random_walk = cstrasam.convert_increments_to_random_walk(samples)
        actual = _get_df_as_str(random_walk)
        expected = r"""
    n_samples=10_seed=0
0               0.00000
1               0.12573
2              -0.00637
3               0.63405
4               0.73895
5               0.20328
6               0.56487
7               1.86887
8               2.81595
9               2.11222
10              0.84680
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_annotate_random_walk(hunitest.TestCase):
    def test_standard(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_standard_gaussian_samples(
            n_samples=n_samples,
            seed=seed,
        )
        random_walk = cstrasam.convert_increments_to_random_walk(samples)
        # Test without extended annotations.
        annotation = cstrasam.annotate_random_walk(
            random_walk, add_extended_annotations=False
        )
        actual = _get_df_as_str(annotation)
        expected = r"""
    n_samples=10_seed=0     high      low    close     mean      std
0               0.00000  0.00000  0.00000  0.00000  0.00000      NaN
1               0.12573  0.12573  0.00000  0.12573  0.06287  0.08890
2              -0.00637  0.12573 -0.00637 -0.00637  0.03979  0.07450
3               0.63405  0.63405 -0.00637  0.63405  0.18835  0.30329
4               0.73895  0.73895 -0.00637  0.73895  0.29847  0.36003
5               0.20328  0.73895 -0.00637  0.20328  0.28261  0.32436
6               0.56487  0.73895 -0.00637  0.56487  0.32293  0.31473
7               1.86887  1.86887 -0.00637  1.86887  0.51617  0.61939
8               2.81595  2.81595 -0.00637  2.81595  0.77170  0.96092
9               2.11222  2.81595 -0.00637  2.11222  0.90576  1.00023
10              0.84680  2.81595 -0.00637  0.84680  0.90040  0.94907
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_extended(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_standard_gaussian_samples(
            n_samples=n_samples,
            seed=seed,
        )
        random_walk = cstrasam.convert_increments_to_random_walk(samples)
        # Test with extended annotations.
        annotation = cstrasam.annotate_random_walk(
            random_walk, add_extended_annotations=True
        )
        actual = _get_df_as_str(annotation)
        expected = r"""
    n_samples=10_seed=0     high      low    close     mean      std    range  high_minus_close  adj_high  adj_low  adj_close  adj_mean  adj_std  adj_range  adj_high_minus_close
0               0.00000  0.00000  0.00000  0.00000  0.00000      NaN  0.00000           0.00000   0.00000  0.00000    0.00000   0.00000      NaN    0.00000               0.00000
1               0.12573  0.12573  0.00000  0.12573  0.06287  0.08890  0.12573           0.00000   0.08890  0.00000    0.08890   0.04445  0.06287    0.08890               0.00000
2              -0.00637  0.12573 -0.00637 -0.00637  0.03979  0.07450  0.13210           0.13210   0.07259 -0.00368   -0.00368   0.02297  0.04301    0.07627               0.07627
3               0.63405  0.63405 -0.00637  0.63405  0.18835  0.30329  0.64042           0.00000   0.31702 -0.00319    0.31702   0.09418  0.15165    0.32021               0.00000
4               0.73895  0.73895 -0.00637  0.73895  0.29847  0.36003  0.74532           0.00000   0.33047 -0.00285    0.33047   0.13348  0.16101    0.33332               0.00000
5               0.20328  0.73895 -0.00637  0.20328  0.28261  0.32436  0.74532           0.53567   0.30167 -0.00260    0.08299   0.11537  0.13242    0.30428               0.21869
6               0.56487  0.73895 -0.00637  0.56487  0.32293  0.31473  0.74532           0.17407   0.27930 -0.00241    0.21350   0.12206  0.11896    0.28171               0.06579
7               1.86887  1.86887 -0.00637  1.86887  0.51617  0.61939  1.87525           0.00000   0.66075 -0.00225    0.66075   0.18249  0.21899    0.66300               0.00000
8               2.81595  2.81595 -0.00637  2.81595  0.77170  0.96092  2.82233           0.00000   0.93865 -0.00212    0.93865   0.25723  0.32031    0.94078               0.00000
9               2.11222  2.81595 -0.00637  2.11222  0.90576  1.00023  2.82233           0.70374   0.89048 -0.00202    0.66794   0.28642  0.31630    0.89250               0.22254
10              0.84680  2.81595 -0.00637  0.84680  0.90040  0.94907  2.82233           1.96916   0.84904 -0.00192    0.25532   0.27148  0.28615    0.85096               0.59372
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_summarize_random_walk(hunitest.TestCase):
    def test1(self) -> None:
        n_samples = 10
        seed = 0
        samples = cstrasam.get_iid_standard_gaussian_samples(
            n_samples=n_samples,
            seed=seed,
        )
        random_walk = cstrasam.convert_increments_to_random_walk(samples)
        summary = cstrasam.summarize_random_walk(random_walk)
        actual = _get_df_as_str(summary)
        expected = r"""
           n_samples=10_seed=0
open                   0.00000
high                   2.81595
low                   -0.00637
close                  0.84680
n_steps               10.00000
range                  2.82233
mean                   0.90040
std                    0.94907
adj_high               0.89048
adj_low               -0.00202
adj_close              0.26778
adj_range              0.89250
adj_mean               0.28473
adj_std                0.30012
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_get_staged_random_walk(hunitest.TestCase):
    def test1(self) -> None:
        stage_steps = [0, 1, 2]
        seed = 0
        walk_stages = cstrasam.get_staged_random_walk(
            stage_steps=stage_steps,
            seed=seed,
        )
        # Check first stage.
        actual_0 = _get_df_as_str(walk_stages[0])
        expected_0 = r"""
   n_samples=5_seed=0
0                 0.0
"""
        self.assert_equal(actual_0, expected_0, fuzzy_match=True)
        # Check second stage.
        actual_1 = _get_df_as_str(walk_stages[1])
        expected_1 = r"""
   n_samples=5_seed=0
0             0.12573
1            -0.00637
"""
        self.assert_equal(actual_1, expected_1, fuzzy_match=True)
        # Check third stage.
        actual_2 = _get_df_as_str(walk_stages[2])
        expected_2 = r"""
   n_samples=5_seed=0
0             0.63405
1             0.73895
2             0.20328
"""
        self.assert_equal(actual_2, expected_2, fuzzy_match=True)


class Test_interpolate_with_brownian_bridge(hunitest.TestCase):
    def test1(self) -> None:
        initial_value = 0
        final_value = 1
        volatility = 1
        n_steps = 10
        seed = 0
        brownian_bridge = cstrasam.interpolate_with_brownian_bridge(
            initial_value=initial_value,
            final_value=final_value,
            volatility=volatility,
            n_steps=n_steps,
            seed=seed,
        )
        actual = _get_df_as_str(brownian_bridge)
        expected = r"""
          0
0   0.00000
1   0.11298
2   0.14443
3   0.42017
4   0.52656
5   0.43039
6   0.61796
7   1.10354
8   1.47626
9   1.32694
10  1.00000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


def _get_df_as_str(df: pd.DataFrame) -> pd.DataFrame:
    precision = 5
    str_df = hpandas.df_to_str(
        df.round(precision),
        num_rows=None,
        precision=precision,
    )
    return str_df
