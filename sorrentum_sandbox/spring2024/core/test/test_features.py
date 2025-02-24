import io
import logging
from typing import List

import numpy as np
import pandas as pd
import pytest

import core.features as cofeatur
import core.statistics.random_samples as cstrasam
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_cross_feature_pairs(hunitest.TestCase):
    def test1(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pairs(
            df,
            [
                ("x1", "x2", ["difference"], "x1x2"),
                ("x3", "x4", ["compressed_mean"], "x3x4"),
            ],
        )
        txt = """
datetime,x1x2.difference,x3x4.compressed_mean
2016-01-04 12:00:00,-1.414214,0.012021
2016-01-04 12:01:00,-0.707107,NaN
2016-01-04 12:02:00,1.414214,0.002546
2016-01-04 12:03:00,NaN,0.002616
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        txt = """
datetime,x1,x2,x3,x4
2016-01-04 12:00:00,-1,1,0.002,0.015
2016-01-04 12:01:00,0,1,0.0015,NaN
2016-01-04 12:02:00,1,-1,0.0017,0.0019
2016-01-04 12:03:00,NaN,-1,0.0021,0.0016
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df


class Test_cross_feature_pair(hunitest.TestCase):
    def test_difference1(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(df, "x1", "x2", ["difference"])
        txt = """
datetime,difference
2016-01-04 12:00:00,-1.414214
2016-01-04 12:01:00,-0.707107
2016-01-04 12:02:00,1.414214
2016-01-04 12:03:00,NaN
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_difference2(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(df, "x3", "x4", ["difference"])
        txt = """
datetime,difference
2016-01-04 12:00:00,-0.009192
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-0.000141
2016-01-04 12:03:00,0.000354
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_compressed_difference1(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x1", "x2", ["compressed_difference"]
        )
        txt = """
datetime,compressed_difference
2016-01-04 12:00:00,-1.358092
2016-01-04 12:01:00,-0.699832
2016-01-04 12:02:00,1.358092
2016-01-04 12:03:00,NaN
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_compressed_difference2(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x3", "x4", ["compressed_difference"]
        )
        txt = """
datetime,compressed_difference
2016-01-04 12:00:00,-0.009192
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-.000141
2016-01-04 12:03:00,0.000354
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_normalized_difference1(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x1", "x2", ["normalized_difference"]
        )
        txt = """
datetime,normalized_difference
2016-01-04 12:00:00,-1.0
2016-01-04 12:01:00,-1.0
2016-01-04 12:02:00,1.0
2016-01-04 12:03:00,NaN
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, atol=1e-7)

    def test_normalized_difference2(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x3", "x4", ["normalized_difference"]
        )
        txt = """
datetime,normalized_difference
2016-01-04 12:00:00,-0.764706
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-0.055556
2016-01-04 12:03:00,0.135135
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_normalized_difference_to_gaussian2(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x3", "x4", ["normalized_difference_to_gaussian"]
        )
        txt = """
datetime,normalized_difference_to_gaussian
2016-01-04 12:00:00,-1.186831
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-0.069685
2016-01-04 12:03:00,0.170185
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_difference_of_logs(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(
            df, "x3", "x4", ["difference_of_logs"]
        )
        txt = """
datetime,difference_of_logs
2016-01-04 12:00:00,-2.014903
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-0.111226
2016-01-04 12:03:00,0.271934
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_mean(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(df, "x3", "x4", ["mean"])
        txt = """
datetime,mean
2016-01-04 12:00:00,0.012021
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,0.002546
2016-01-04 12:03:00,0.002616
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_compressed_mean(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(df, "x3", "x4", ["compressed_mean"])
        txt = """
datetime,compressed_mean
2016-01-04 12:00:00,0.012021
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,0.002546
2016-01-04 12:03:00,0.002616
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_mean_of_logs(self) -> None:
        df = self._get_df()
        actual = cofeatur.cross_feature_pair(df, "x3", "x4", ["mean_of_logs"])
        txt = """
datetime,mean_of_logs
2016-01-04 12:00:00,-5.207157
2016-01-04 12:01:00,NaN
2016-01-04 12:02:00,-6.321514
2016-01-04 12:03:00,-6.301785
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        txt = """
datetime,x1,x2,x3,x4
2016-01-04 12:00:00,-1,1,0.002,0.015
2016-01-04 12:01:00,0,1,0.0015,NaN
2016-01-04 12:02:00,1,-1,0.0017,0.0019
2016-01-04 12:03:00,NaN,-1,0.0021,0.0016
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df


class Test_compute_normalized_statistical_leverage_scores(hunitest.TestCase):
    # TODO(Paul): We may need to rewrite these to be insensitive to signs.
    def test_identity_1(self) -> None:
        mat = np.array(
            [
                [1, 0],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_statistical_leverage_scores(df)
        txt = """
proj_dim,x1,x2
1,1.0,0.0
2,0.5,0.5
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_identity_2(self) -> None:
        mat = np.array(
            [
                [1, 0],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_statistical_leverage_scores(
            df,
            demean_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,0.5,0.5
2,0.5,0.5
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_1(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_statistical_leverage_scores(df)
        txt = """
proj_dim,x1,x2
1,0.276393,0.723607
2,0.5,0.5
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_2(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_statistical_leverage_scores(
            df,
            demean_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,0.2,0.8
2,0.5,0.5
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_3(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_statistical_leverage_scores(
            df,
            demean_cols=True,
            normalize_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,0.5,0.5
2,0.5,0.5
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)


class Test_compute_normalized_principal_loadings(hunitest.TestCase):
    # TODO(Paul): We may need to rewrite these to be insensitive to signs.
    def test_identity_1(self) -> None:
        mat = np.array(
            [
                [1, 0],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(df)
        txt = """
proj_dim,x1,x2
1,0.707107,0
2,0,0.707107
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_identity_2(self) -> None:
        mat = np.array(
            [
                [1, 0],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(
            df,
            demean_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,-0.5,0.5
2,0.0,0.0
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_identity_3(self) -> None:
        mat = np.array(
            [
                [1, 0],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(
            df, demean_cols=True, normalize_cols=True
        )
        txt = """
proj_dim,x1,x2
1,-0.707107,0.707107
2,0.0,0.0
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_1(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(df)
        txt = """
proj_dim,x1,x2
1,0.601501,-0.973249
2,0.371748,0.229753
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_2(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(
            df,
            demean_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,-0.5,1.0
2,0.0,0.0
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_upper_triangular_3(self) -> None:
        mat = np.array(
            [
                [1, -1],
                [0, 1],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2"])
        actual = cofeatur.compute_normalized_principal_loadings(
            df,
            demean_cols=True,
            normalize_cols=True,
        )
        txt = """
proj_dim,x1,x2
1,-0.707107,0.707107
2,0.0,0.0
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)


class Test_compare_subspaces(hunitest.TestCase):
    def test1(self) -> None:
        mat1 = np.array(
            [
                [1, 0],
                [0, 1],
                [0, 0],
            ]
        )
        mat2 = np.array(
            [
                [1, 0],
                [0, 1 / np.sqrt(2)],
                [0, 1 / np.sqrt(2)],
            ]
        )
        df1 = pd.DataFrame(mat1)
        df2 = pd.DataFrame(mat2)
        actual = cofeatur.compare_subspaces(df1, df2)
        txt = """
singular_value,canonical_corr,principal_angle
1,1.0,0.0
2,0.707107,0.785398
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)


class Test_compute_effective_rank(hunitest.TestCase):
    def test1(self) -> None:
        mat = np.array(
            [
                [1, 0.9, 0],
                [-1, -1, 1],
                [0, 0, -1],
                [0, 0.1, 0],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2", "x3"])
        alphas = [1, 2, np.inf]
        actual = [cofeatur.compute_effective_rank(df, x) for x in alphas]
        expected = [
            1.6892598840830737,
            1.503275283591628,
            1.2692575763946805,
        ]
        np.testing.assert_allclose(actual, expected)

    def test2(self) -> None:
        mat = np.array(
            [
                [1, 0, 0],
                [0, 1, 0.1],
                [0, 0, 1],
                [0, 0, 0],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2", "x3"])
        alphas = [1, 2, np.inf]
        actual = [cofeatur.compute_effective_rank(df, x) for x in alphas]
        expected = [
            2.99004975854808,
            2.9801980198019793,
            2.7236739848627627,
        ]
        np.testing.assert_allclose(actual, expected)


# #############################################################################


class _TestHelper(hunitest.TestCase):
    def _assert_lists_equal(self, actual: List[str], expected: List[str]) -> None:
        self.assert_equal(",".join(actual), ",".join(expected))

    # TODO(gp): For now we allow multiple values due to numerical instability.
    # Paul will try to make the tests more stable.
    def _assert_list_in(
        self, actual: List[str], expected: List[List[str]]
    ) -> None:
        expected_lists = [",".join(l) for l in expected]
        self.assertIn(",".join(actual), expected_lists)


class Test_select_cols_by_greedy_grassmann(_TestHelper):
    def test1(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_grassmann(df)
        expected = [["x4", "x1", "x3", "x2"], ["x4", "x1", "x2", "x3"]]
        self._assert_list_in(actual, expected)

    # TODO(gp): Consider enabling the disabled tests due to numerical
    # instability and use the approach with `_assert_list_in`.
    @pytest.mark.skip(reason="Apparent instability")
    def test2(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_grassmann(df, demean_cols=True)
        expected = ["x3", "x1", "x4", "x2"]
        self._assert_lists_equal(actual, expected)

    @pytest.mark.skip(reason="Apparent instability")
    def test3(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_grassmann(df, normalize_cols=True)
        expected = ["x3", "x2", "x4", "x1"]
        self._assert_lists_equal(actual, expected)

    @pytest.mark.skip(reason="Apparent instability")
    def test4(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_grassmann(
            df,
            demean_cols=True,
            normalize_cols=True,
        )
        expected = ["x3", "x2", "x4", "x1"]
        self._assert_lists_equal(actual, expected)

    def _get_df(self) -> pd.DataFrame:
        mat = np.array(
            [
                [1, 0, 1, 1],
                [0, 1, 1, 1],
                [0, 0, 0, 1],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2", "x3", "x4"])
        return df


class Test_select_cols_by_greedy_volume(_TestHelper):
    def test1(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_volume(df)
        expected = [["x4", "x1", "x3", "x2"], ["x4", "x1", "x2", "x3"]]
        self._assert_list_in(actual, expected)

    @pytest.mark.skip(reason="Apparent instability")
    def test2(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_volume(df, demean_cols=True)
        expected = ["x3", "x2", "x4", "x1"]
        self._assert_lists_equal(actual, expected)

    def test3(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_volume(df, normalize_cols=True)
        expected = ["x4", "x1", "x2", "x3"]
        self._assert_lists_equal(actual, expected)

    @pytest.mark.skip(reason="Apparent instability")
    def test4(self) -> None:
        df = self._get_df()
        actual = cofeatur.select_cols_by_greedy_volume(
            df,
            demean_cols=True,
            normalize_cols=True,
        )
        expected = ["x3", "x2", "x4", "x1"]
        self._assert_lists_equal(actual, expected)

    def _get_df(self) -> pd.DataFrame:
        mat = np.array(
            [
                [1, 0, 1, 1],
                [0, 1, 1, 1],
                [0, 0, 0, 1],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]
        )
        df = pd.DataFrame(mat, columns=["x1", "x2", "x3", "x4"])
        return df


class Test_combine_cols_instance1(_TestHelper):
    def test1(self) -> None:
        col1 = cstrasam.get_iid_standard_gaussian_samples(10, 1).rename("col1")
        col2 = cstrasam.get_iid_standard_gaussian_samples(10, 2).rename("col2")
        col3 = cstrasam.get_iid_standard_gaussian_samples(10, 3).rename("col3")
        df = pd.concat([col1, col2, col3], axis=1)
        actual = cofeatur.combine_cols_instance1(df, ("col1", "col2", "col3"))
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
          do        la        ti
1   1.261131  3.464507  6.277219
2  -1.143294 -6.275000  5.140596
3   0.171854  1.094035  0.788074
4  -1.969558  6.227982  0.354063
5   0.991382 -6.415660  4.309076
6   0.608196 -3.660017  3.275155
7  -1.398199 -2.762529  6.993136
8   0.493964 -3.225074  2.260149
9  -0.141902 -3.213586  3.344312
10  1.544598  7.901230  8.194480
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
