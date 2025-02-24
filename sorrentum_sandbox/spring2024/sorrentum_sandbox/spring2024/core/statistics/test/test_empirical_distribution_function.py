import logging

import pandas as pd

import core.statistics.empirical_distribution_function as csemdifu
import core.statistics.random_samples as cstrasam
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_empirical_cdf1(hunitest.TestCase):
    def test_gaussian(self) -> None:
        data = cstrasam.get_iid_standard_gaussian_samples(
            10,
            seed=0,
        )
        empirical_cdf = csemdifu.compute_empirical_cdf(data)
        actual = get_df_as_str(empirical_cdf)
        expected = r"""
          n_samples=10_seed=0.ecdf
n_samples=10_seed=0
-1.26542                       0.1
-0.70374                       0.2
-0.53567                       0.3
-0.13210                       0.4
 0.10490                       0.5
 0.12573                       0.6
 0.36160                       0.7
 0.64042                       0.8
 0.94708                       0.9
 1.30400                       1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_with_duplicates(self) -> None:
        data = cstrasam.get_iid_standard_gaussian_samples(
            10,
            seed=0,
        )
        # Create a duplicate value (replace 0.12573 with 0.10490).
        data.loc[1] = data.loc[4]
        empirical_cdf = csemdifu.compute_empirical_cdf(data)
        actual = get_df_as_str(empirical_cdf)
        expected = r"""
          n_samples=10_seed=0.ecdf
n_samples=10_seed=0
-1.26542                       0.1
-0.70374                       0.2
-0.53567                       0.3
-0.13210                       0.4
 0.10490                       0.6
 0.36160                       0.7
 0.64042                       0.8
 0.94708                       0.9
 1.30400                       1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_empirical_cdf_with_bounds1(hunitest.TestCase):
    def test_gaussian1(self) -> None:
        empirical_cdf_with_bounds = self.get_gaussian_empirical_cdf_with_bounds(
            n_samples=10,
            seed=0,
            alpha=0.2,
        )
        actual = get_df_as_str(empirical_cdf_with_bounds)
        expected = r"""
          n_samples=10_seed=0.ecdf  lower_CI  upper_CI
n_samples=10_seed=0
-1.26542                       0.1   0.00000   0.43931
-0.70374                       0.2   0.00000   0.53931
-0.53567                       0.3   0.00000   0.63931
-0.13210                       0.4   0.06069   0.73931
 0.10490                       0.5   0.16069   0.83931
 0.12573                       0.6   0.26069   0.93931
 0.36160                       0.7   0.36069   1.00000
 0.64042                       0.8   0.46069   1.00000
 0.94708                       0.9   0.56069   1.00000
 1.30400                       1.0   0.66069   1.00000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_gaussian2(self) -> None:
        empirical_cdf_with_bounds = self.get_gaussian_empirical_cdf_with_bounds(
            n_samples=20,
            seed=1,
            alpha=0.1,
        )
        actual = get_df_as_str(empirical_cdf_with_bounds)
        expected = r"""
          n_samples=20_seed=1.ecdf  lower_CI  upper_CI
n_samples=20_seed=1
-1.30316                      0.05   0.00000   0.32367
-0.78191                      0.10   0.00000   0.37367
-0.73645                      0.15   0.00000   0.42367
-0.53695                      0.20   0.00000   0.47367
-0.48212                      0.25   0.00000   0.52367
-0.29246                      0.30   0.02633   0.57367
-0.25719                      0.35   0.07633   0.62367
-0.16291                      0.40   0.12633   0.67367
 0.02842                      0.45   0.17633   0.72367
 0.03972                      0.50   0.22633   0.77367
 0.29413                      0.55   0.27633   0.82367
 0.33044                      0.60   0.32633   0.87367
 0.34558                      0.65   0.37633   0.92367
 0.36457                      0.70   0.42633   0.97367
 0.44637                      0.75   0.47633   1.00000
 0.54671                      0.80   0.52633   1.00000
 0.58112                      0.85   0.57633   1.00000
 0.59885                      0.90   0.62633   1.00000
 0.82162                      0.95   0.67633   1.00000
 0.90536                      1.00   0.72633   1.00000
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def get_gaussian_empirical_cdf_with_bounds(
        self,
        n_samples,
        seed,
        alpha,
    ) -> pd.DataFrame:
        data = cstrasam.get_iid_standard_gaussian_samples(n_samples, seed)
        empirical_cdf = csemdifu.compute_empirical_cdf_with_bounds(data, alpha)
        return empirical_cdf

    def test_combine_empirical_cdfs(self) -> None:
        input_data = [
            {"n_samples": 10, "seed": 0},
            {"n_samples": 15, "seed": 0},
            {"n_samples": 10, "seed": 1},
        ]
        ecdfs = []
        for sample_data in input_data:
            data = cstrasam.get_iid_standard_gaussian_samples(
                sample_data["n_samples"],
                sample_data["seed"],
            )
            empirical_cdf = csemdifu.compute_empirical_cdf(data)
            ecdfs.append(empirical_cdf)
        actual_df = csemdifu.combine_empirical_cdfs(ecdfs)
        actual = get_df_as_str(actual_df)
        expected = r"""
          n_samples=10_seed=0.ecdf  n_samples=15_seed=0.ecdf  n_samples=10_seed=1.ecdf
-2.32503                       0.0                   0.06667                       0.0
-1.30316                       0.0                   0.06667                       0.1
-1.26542                       0.1                   0.13333                       0.1
-1.24591                       0.1                   0.20000                       0.1
-0.70374                       0.2                   0.26667                       0.1
-0.62327                       0.2                   0.33333                       0.1
-0.53695                       0.2                   0.33333                       0.2
-0.53567                       0.3                   0.40000                       0.2
-0.21879                       0.3                   0.46667                       0.2
-0.13210                       0.4                   0.53333                       0.2
 0.04133                       0.4                   0.60000                       0.2
 0.10490                       0.5                   0.66667                       0.2
 0.12573                       0.6                   0.73333                       0.2
 0.29413                       0.6                   0.73333                       0.3
 0.33044                       0.6                   0.73333                       0.4
 0.34558                       0.6                   0.73333                       0.5
 0.36160                       0.7                   0.80000                       0.5
 0.36457                       0.7                   0.80000                       0.6
 0.44637                       0.7                   0.80000                       0.7
 0.58112                       0.7                   0.80000                       0.8
 0.64042                       0.8                   0.86667                       0.8
 0.82162                       0.8                   0.86667                       0.9
 0.90536                       0.8                   0.86667                       1.0
 0.94708                       0.9                   0.93333                       1.0
 1.30400                       1.0                   1.00000                       1.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


def get_df_as_str(df: pd.DataFrame) -> pd.DataFrame:
    precision = 5
    str_df = hpandas.df_to_str(
        df.round(precision),
        num_rows=None,
        precision=precision,
    )
    return str_df
