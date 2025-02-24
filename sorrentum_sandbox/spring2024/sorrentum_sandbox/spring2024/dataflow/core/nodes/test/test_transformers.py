import io
import logging

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import dataflow.core.nodes.test.helpers as cdnth
import dataflow.core.nodes.transformers as dtfconotra
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestGroupedColDfToDfTransformer1(hunitest.TestCase):
    def test_column_arithmetic(self) -> None:
        data = self._get_data()

        def divide(df: pd.DataFrame, col1: str, col2: str) -> pd.DataFrame:
            quotient = (df[col1] / df[col2]).rename("div")
            return quotient.to_frame()

        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("ret",), ("vol",)],
                "out_col_group": (),
                "transformer_func": divide,
                "transformer_kwargs": {
                    "col1": "ret",
                    "col2": "vol",
                },
            },
        )
        node = dtfconotra.GroupedColDfToDfTransformer("adj", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,div,div,ret,ret,vol,vol
,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.4,-0.4,0.5,-0.5,1.25,1.25
2016-01-04 09:31:00,0.25,0.25,0.25,0.25,1.0,1.0
2016-01-04 09:32:00,-0.8,0.8,-1.0,1.0,1.25,1.25
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,ret,ret,vol,vol
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.5,-0.5,1.25,1.25
2016-01-04 09:31:00,0.25,0.25,1,1
2016-01-04 09:32:00,-1,1,1.25,1.25
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestGroupedColDfToDfTransformer2(hunitest.TestCase):
    def test_resampling(self) -> None:
        data = self._get_data()

        def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
            return df.resample(rule=rule).sum(min_count=1)

        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("ret",), ("vol",)],
                "out_col_group": (),
                "transformer_func": resample,
                "transformer_kwargs": {
                    "rule": "5T",
                },
                "reindex_like_input": False,
                "join_output_with_input": False,
            },
        )
        node = dtfconotra.GroupedColDfToDfTransformer(
            "resample", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        expected_txt = """
,ret,ret,vol,vol
,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.75,-0.25,2.25,2.25
2016-01-04 09:35:00,-1,1,1.25,1.25
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,ret,ret,vol,vol
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.5,-0.5,1.25,1.25
2016-01-04 09:31:00,0.25,0.25,1,1
2016-01-04 09:36:00,-1,1,1.25,1.25
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestGroupedColDfToDfTransformer3(hunitest.TestCase):
    def test_multicolumn_processing1(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("close",),
                    ("mid",),
                ],
                "out_col_group": (),
                "transformer_func": lambda x: x.pct_change(),
                "col_mapping": {
                    "close": "close_ret_0",
                    "mid": "mid_ret_0",
                },
            }
        )
        node = dtfconotra.GroupedColDfToDfTransformer(
            "compute_ret_0", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        expected_txt = """
,close_ret_0,close_ret_0,mid_ret_0,mid_ret_0,close,close,mid,mid
,MN0,MN1,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,,,,,100.0,100.0,101.00,99.00
2016-01-04 09:31:00,0.05,-0.02,0.05,-0.02,105.0,98.0,106.05,97.02
2016-01-04 09:32:00,-0.5,-0.5,-0.5,-0.5,52.5,49.0,53.025,48.51
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_multicolumn_processing2(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("close",),
                    ("mid",),
                ],
                "out_col_group": (),
                "transformer_func": lambda x: x.pct_change(),
                "col_mapping": {
                    "close": "close_ret_0",
                    "mid": "mid_ret_0",
                },
                "join_output_with_input": False,
            }
        )
        node = dtfconotra.GroupedColDfToDfTransformer(
            "compute_ret_0", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        expected_txt = """
,close_ret_0,close_ret_0,mid_ret_0,mid_ret_0
,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,NaN,NaN,NaN,NaN
2016-01-04 09:31:00,0.05,-0.02,0.05,-0.02
2016-01-04 09:32:00,-0.5,-0.5,-0.5,-0.5
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,mid,mid
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,100.00,100.00,101.00,99.00
2016-01-04 09:31:00,105.00,98.00,106.05,97.02
2016-01-04 09:32:00,52.50,49.00,53.025,48.51
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestGroupedColDfToDfTransformer4(hunitest.TestCase):
    def test_drop_nans(self) -> None:
        data = self._get_data()

        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("close",), ("mid",)],
                "out_col_group": (),
                "transformer_func": lambda x: x.diff(),
                "col_mapping": {
                    "close": "close_diff",
                    "mid": "mid_diff",
                },
                "drop_nans": True,
                "join_output_with_input": False,
            },
        )
        node = dtfconotra.GroupedColDfToDfTransformer("diff", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,close_diff,close_diff,mid_diff,mid_diff
,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,NaN,NaN,NaN,NaN
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,5.0,,0.0,
2016-01-05 09:31:00,5.0,2.0,6.049999999999997,-0.980000000000004
2016-01-05 09:32:00,-52.5,-49.0,-53.025,-48.51
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_without_reindexing(self) -> None:
        data = self._get_data()

        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("close",), ("mid",)],
                "out_col_group": (),
                "transformer_func": lambda x: x.diff(),
                "col_mapping": {
                    "close": "close_diff",
                    "mid": "mid_diff",
                },
                "drop_nans": True,
                "reindex_like_input": False,
                "join_output_with_input": False,
            },
        )
        node = dtfconotra.GroupedColDfToDfTransformer("diff", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,close_diff,close_diff,mid_diff,mid_diff
,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,5.0,,0.0,
2016-01-05 09:31:00,5.0,2.0,6.049999999999997,-0.980000000000004
2016-01-05 09:32:00,-52.5,-49.0,-53.025,-48.51
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,mid,mid
datetime,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,100,98.00
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,100,NaN
2016-01-05 09:31:00,105.00,98.00,106.05,97.02
2016-01-05 09:32:00,52.50,49.00,53.025,48.51
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestCrossSectionalDfToDfTransformer1(hunitest.TestCase):
    def test_demean(self) -> None:
        data = self._get_data()

        def demean(df: pd.DataFrame) -> pd.DataFrame:
            mean = df.mean(axis=1)
            demeaned = df.subtract(mean, axis=0)
            return demeaned

        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("ret",)],
                "out_col_groups": [("ret.demeaned",)],
                "transformer_func": demean,
            },
        )
        node = dtfconotra.CrossSectionalDfToDfTransformer(
            "adj", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        expected_txt = """
,ret.demeaned,ret.demeaned,ret,ret,vol,vol
,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.5,-0.5,0.5,-0.5,1.25,1.25
2016-01-04 09:31:00,0.0,0.0,0.25,0.25,1,1
2016-01-04 09:32:00,-1.0,1.0,-1.0,1.0,1.25,1.25
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_rank(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("ret",),
                    ("vol",),
                ],
                "out_col_groups": [
                    ("ret.ranked",),
                    ("vol.ranked",),
                ],
                "transformer_func": lambda x: x.rank(axis=1),
            },
        )
        node = dtfconotra.CrossSectionalDfToDfTransformer(
            "adj", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = """
                          ret.ranked      vol.ranked        ret         vol
datetime                   MN0  MN1        MN0  MN1   MN0   MN1   MN0   MN1
2016-01-04 09:30:00        2.0  1.0        1.5  1.5  0.50 -0.50  1.25  1.25
2016-01-04 09:31:00        1.5  1.5        1.5  1.5  0.25  0.25  1.00  1.00
2016-01-04 09:32:00        1.0  2.0        1.5  1.5 -1.00  1.00  1.25  1.25"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,ret,ret,vol,vol
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,0.5,-0.5,1.25,1.25
2016-01-04 09:31:00,0.25,0.25,1,1
2016-01-04 09:32:00,-1,1,1.25,1.25
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestSeriesToDfTransformer1(hunitest.TestCase):
    def test1(self) -> None:
        def add_lags(srs: pd.Series, num_lags: int) -> pd.DataFrame:
            lags = []
            for lag in range(0, num_lags):
                lags.append(srs.shift(lag).rename("lag_" + str(lag)))
            out_df = pd.concat(lags, axis=1)
            return out_df

        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": (),
                "transformer_func": add_lags,
                "transformer_kwargs": {
                    "num_lags": 3,
                },
            }
        )
        node = dtfconotra.SeriesToDfTransformer("add_lags", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,lag_0,lag_0,lag_1,lag_1,lag_2,lag_2,close,close,volume,volume
,MN0,MN1,MN0,MN1,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,94.7,100.2,,,,,94.7,100.2,30000,40000
2016-01-04 09:31:00,94.9,100.25,94.7,100.2,,,94.9,100.25,35000,44000
2016-01-04 09:32:00,95.35,100.23,94.9,100.25,94.7,100.2,95.35,100.23,40000,45000
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,volume,volume
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,94.70,100.20,30000,40000
2016-01-04 09:31:00,94.90,100.25,35000,44000
2016-01-04 09:32:00,95.35,100.23,40000,45000
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestSeriesToDfTransformer2(hunitest.TestCase):
    def test_drop_nans(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": (),
                "transformer_func": self._add_lags,
                "transformer_kwargs": {
                    "num_lags": 2,
                },
                "drop_nans": True,
                "join_output_with_input": False,
            }
        )
        node = dtfconotra.SeriesToDfTransformer("add_lags", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,lag_0,lag_0,lag_1,lag_1
,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,NaN,NaN
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,95.00,NaN
2016-01-05 09:31:00,105.00,98.00,100.00,96.00
2016-01-05 09:32:00,52.50,49.00,105.00,98.00
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_then_join(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": (),
                "transformer_func": self._add_lags,
                "transformer_kwargs": {
                    "num_lags": 2,
                },
                "drop_nans": True,
            }
        )
        node = dtfconotra.SeriesToDfTransformer("add_lags", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,lag_0,lag_0,lag_1,lag_1,close,close,mid,mid
,MN0,MN1,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,NaN,NaN,95.00,96.00,100.00,98.00
2016-01-04 16:01:00,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,95.00,NaN,100.00,NaN,100.00,NaN
2016-01-05 09:31:00,105.00,98.00,100.00,96.00,105.00,98.00,106.05,97.02
2016-01-05 09:32:00,52.50,49.00,105.00,98.00,52.50,49.00,53.025,48.51
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_without_reindexing(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": (),
                "transformer_func": self._add_lags,
                "transformer_kwargs": {
                    "num_lags": 2,
                },
                "drop_nans": True,
                "reindex_like_input": False,
                "join_output_with_input": False,
            }
        )
        node = dtfconotra.SeriesToDfTransformer("add_lags", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,lag_0,lag_0,lag_1,lag_1
,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,95.00,NaN
2016-01-05 09:31:00,105.00,98.00,100.00,96.00
2016-01-05 09:32:00,52.50,49.00,105.00,98.00
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_without_reindexing_then_attempt_join(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": (),
                "transformer_func": self._add_lags,
                "transformer_kwargs": {
                    "num_lags": 2,
                },
                "drop_nans": True,
                "reindex_like_input": False,
                "join_output_with_input": True,
            }
        )
        node = dtfconotra.SeriesToDfTransformer("add_lags", **config.to_dict())
        with self.assertRaises(AssertionError):
            node.fit(data)["df_out"]

    @staticmethod
    def _add_lags(srs: pd.Series, num_lags: int) -> pd.DataFrame:
        lags = []
        for lag in range(0, num_lags):
            lags.append(srs.shift(lag).rename("lag_" + str(lag)))
        out_df = pd.concat(lags, axis=1)
        return out_df

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,mid,mid
datetime,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,100,98.00
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,100,NaN
2016-01-05 09:31:00,105.00,98.00,106.05,97.02
2016-01-05 09:32:00,52.50,49.00,53.025,48.51
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestSeriesToSeriesTransformer1(hunitest.TestCase):
    def test1(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("ret_0",),
                "transformer_func": lambda x: x.pct_change(),
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer(
            "compute_ret_0", **config.to_dict()
        )
        actual = node.fit(data)["df_out"]
        expected_txt = """
,ret_0,ret_0,close,close,volume,volume
,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,,,100.0,100.0,30000,40000
2016-01-04 09:31:00,0.05,-0.02,105.0,98.0,35000,44000
2016-01-04 09:32:00,-0.5,-0.5,52.5,49.0,40000,45000
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,volume,volume
datetime,MN0,MN1,MN0,MN1
2016-01-04 09:30:00,100.00,100.00,30000,40000
2016-01-04 09:31:00,105.00,98.00,35000,44000
2016-01-04 09:32:00,52.50,49.00,40000,45000
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestSeriesToSeriesTransformer2(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `fit()` call.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("ret_0",),
                "transformer_func": lambda x: x.pct_change(),
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("sklearn", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` call.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("ret_0",),
                "transformer_func": lambda x: x.pct_change(),
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("sklearn", **config.to_dict())
        expected, actual = cdnth.get_fit_predict_outputs(data, node)
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=342)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=134
        )
        realization = realization.rename(columns=lambda x: "MN" + str(x))
        realization = np.exp(0.1 * realization.cumsum())
        volume = pd.DataFrame(
            index=realization.index, columns=realization.columns, data=100
        )
        data = pd.concat([realization, volume], axis=1, keys=["close", "volume"])
        return data


class TestSeriesToSeriesTransformer3(hunitest.TestCase):
    def test_drop_nans(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("diff",),
                "transformer_func": lambda x: x.diff(),
                "drop_nans": True,
                "join_output_with_input": False,
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("diff", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,diff,diff
,MN0,MN1
2016-01-04 16:00:00,NaN,NaN
2016-01-04 16:01:00,NaN,NaN
2016-01-05 09:29:00,NaN,NaN
2016-01-05 09:30:00,5.0,NaN
2016-01-05 09:31:00,5.0,2.0
2016-01-05 09:32:00,-52.5,-49.0
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_then_join(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("diff",),
                "transformer_func": lambda x: x.diff(),
                "drop_nans": True,
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("diff", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,diff,diff,close,close,mid,mid
,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,NaN,NaN,95.00,96.00,100,98.00
2016-01-04 16:01:00,NaN,NaN,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,5.0,NaN,100.00,NaN,100,NaN
2016-01-05 09:31:00,5.0,2.0,105.00,98.00,106.05,97.02
2016-01-05 09:32:00,-52.5,-49.0,52.50,49.00,53.025,48.51
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_without_reindexing(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("diff",),
                "transformer_func": lambda x: x.diff(),
                "drop_nans": True,
                "reindex_like_input": False,
                "join_output_with_input": False,
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("diff", **config.to_dict())
        actual = node.fit(data)["df_out"]
        expected_txt = """
,diff,diff
,MN0,MN1
2016-01-04 16:00:00,NaN,NaN
2016-01-05 09:30:00,5.0,NaN
2016-01-05 09:31:00,5.0,2.0
2016-01-05 09:32:00,-52.5,-49.0
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
            parse_dates=True,
            header=[0, 1],
        )
        self.assert_dfs_close(actual, expected)

    def test_drop_nans_without_reindexing_then_attempt_join(self) -> None:
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close",),
                "out_col_group": ("diff",),
                "transformer_func": lambda x: x.diff(),
                "drop_nans": True,
                "reindex_like_input": False,
                "join_output_with_input": True,
            }
        )
        node = dtfconotra.SeriesToSeriesTransformer("diff", **config.to_dict())
        with self.assertRaises(AssertionError):
            node.fit(data)["df_out"]

    def _get_data(self) -> pd.DataFrame:
        txt = """
,close,close,mid,mid
datetime,MN0,MN1,MN0,MN1
2016-01-04 16:00:00,95.00,96.00,100,98.00
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,100.00,NaN,100,NaN
2016-01-05 09:31:00,105.00,98.00,106.05,97.02
2016-01-05 09:32:00,52.50,49.00,53.025,48.51
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        return df


class TestFunctionWrapper(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `fit()` call.
        """
        data = self._get_df()

        def multiply(df: pd.DataFrame, col1: str, col2: str) -> pd.DataFrame:
            product = (df[col1] * df[col2]).rename("pv")
            return product.to_frame()

        config = cconfig.Config.from_dict(
            {
                "func": multiply,
                "func_kwargs": {
                    "col1": "close",
                    "col2": "volume",
                },
            }
        )
        node = dtfconotra.FunctionWrapper("sklearn", **config.to_dict())
        actual = node.fit(data)["df_out"]
        txt = """
datetime,pv
2016-01-04 09:30:00,1.769e+08
2016-01-04 09:31:00,3.316e+07
2016-01-04 09:32:00,3.999e+07
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        pd.testing.assert_frame_equal(actual, expected, rtol=1e-2)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        """
        Return a df without NaNs.
        """
        txt = """
datetime,close,volume
2016-01-04 09:30:00,94.7,1867590
2016-01-04 09:31:00,94.98,349119
2016-01-04 09:32:00,95.33,419479
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df


class TestTwapVwapComputer(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test building 5-min TWAP/VWAP bars from 1-min close/volume bars.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "rule": "5T",
                "price_col": "close",
                "volume_col": "volume",
            }
        )
        node = dtfconotra.TwapVwapComputer("twapvwap", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` call.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "rule": "5T",
                "price_col": "close",
                "volume_col": "volume",
            }
        )
        node = dtfconotra.TwapVwapComputer("twapvwap", **config.to_dict())
        expected, actual = cdnth.get_fit_predict_outputs(data, node)
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate AR(1) returns and Poisson volume.
        """
        date_range_kwargs = {
            "start": "2001-01-04 09:30:00",
            "end": "2001-01-04 10:00:00",
            "freq": "T",
        }
        ar_params = [0.5]
        arma_process = carsigen.ArmaProcess(ar_params, [])
        rets = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs,
            scale=1,
            burnin=0,
            seed=100,
        )
        prices = np.exp(0.25 * rets.cumsum())
        prices.name = "close"
        poisson_process = carsigen.PoissonProcess(mu=100)
        volume = poisson_process.generate_sample(
            date_range_kwargs=date_range_kwargs,
            seed=100,
        )
        volume.name = "volume"
        df = pd.concat([prices, volume], axis=1)
        return df


class TestMultiindexTwapVwapComputer(hunitest.TestCase):
    @pytest.mark.skip("See CmTask5898.")
    def test1(self) -> None:
        """
        Test building 5-min TWAP/VWAP bars from 1-min close/volume bars.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "rule": "5T",
                "price_col_group": ("close",),
                "volume_col_group": ("volume",),
                "out_col_group": (),
            }
        )
        node = dtfconotra.MultiindexTwapVwapComputer(
            "twapvwap", **config.to_dict()
        )
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` call.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "rule": "5T",
                "price_col_group": ("close",),
                "volume_col_group": ("volume",),
                "out_col_group": (),
            }
        )
        node = dtfconotra.MultiindexTwapVwapComputer(
            "twapvwap", **config.to_dict()
        )
        expected, actual = cdnth.get_fit_predict_outputs(data, node)
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate AR(1) returns and Poisson volume.
        """
        date_range_kwargs = {
            "start": "2001-01-04 09:30:00",
            "end": "2001-01-04 10:00:00",
            "freq": "T",
        }
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=402)
        rets = mn_process.generate_sample(
            date_range_kwargs=date_range_kwargs, seed=343
        )
        rets = rets.rename(columns=lambda x: "MN" + str(x))
        prices = np.exp(0.1 * rets.cumsum())
        poisson_process = carsigen.PoissonProcess(mu=100)
        volume_srs = poisson_process.generate_sample(
            date_range_kwargs=date_range_kwargs,
            seed=100,
        )
        volume = pd.DataFrame(index=volume_srs.index, columns=rets.columns)
        for col in volume.columns:
            volume[col] = volume_srs
        df = pd.concat([prices, volume], axis=1, keys=["close", "volume"])
        return df
