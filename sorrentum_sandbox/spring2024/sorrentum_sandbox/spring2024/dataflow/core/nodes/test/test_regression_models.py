import io
import logging
import os

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import dataflow.core.nodes.regression_models as dtfcnoremo
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestLinearRegression(hunitest.TestCase):
    @pytest.mark.skip(reason="This test generates the input data")
    def test_generate_input_data(self) -> None:
        """
        Uncomment the skip tag and run this test to update the input data.
        """
        file_name = self._get_test_data_file_name()
        # Generate the data.
        data = self._get_data(seed=1)
        # Save the data to the proper location.
        hio.create_enclosing_dir(file_name, incremental=True)
        data.to_csv(file_name)
        _LOG.info("Generated file '%s'", file_name)
        # Read the data back and make sure it is the same.
        data2 = self._get_frozen_input()
        #
        hunitest.compare_df(data, data2)

    @pytest.mark.skip(
        reason="This test fails on some computers due to AmpTask1649"
    )
    def test0(self) -> None:
        """
        Check that the randomly generated data is the same as our development
        computers.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Current seed=%s", np.random.get_state()[1][0])
            _LOG.debug("Generating data")
        data = self._get_data(seed=1)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Current seed=%s", np.random.get_state()[1][0])
            _LOG.debug("data=\n%s", str(data))
            _LOG.debug("Checking against golden")
        df_str = hpandas.df_to_str(data, num_rows=None, precision=3)
        self.check_string(df_str)

    def test1(self) -> None:
        """
        Test `fit()`.
        """
        # Load test data.
        data = self._get_frozen_input()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4    y.shift_-1  y.shift_-1_hat
2000-01-03 -0.865  1.074 -1.604  0.966 -0.705  1.771    1.799
2000-01-04  1.771 -0.705  1.262 -2.374 -0.447 -0.581   -1.010
2000-01-05 -0.581  1.238 -0.811  2.345 -0.465  1.238    1.934
2000-01-06  1.238  0.368  0.713 -0.275 -0.654  1.416    0.478
2000-01-07  1.416 -1.190 -0.044 -0.780  0.719  0.863   -1.403
2000-01-10  0.863  0.562  0.317 -0.267 -0.741  0.200    0.734
2000-01-11  0.200  1.190  0.655 -0.604 -0.187  0.424    0.308
2000-01-12  0.424 -0.843  0.785  1.700 -0.057  0.188    0.088
2000-01-13  0.188 -0.659  1.321  1.135 -0.871  0.873    0.573
2000-01-14  0.873 -0.729 -0.262  0.064  1.973    NaN      NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test `fit()` with nonzero smoothing.
        """
        # Load test data.
        data = self._get_frozen_input()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "smoothing": 2,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4    y.shift_-1  y.shift_-1_hat
2000-01-03 -0.865  1.074 -1.604  0.966 -0.705  1.771    1.637
2000-01-04  1.771 -0.705  1.262 -2.374 -0.447 -0.581   -0.696
2000-01-05 -0.581  1.238 -0.811  2.345 -0.465  1.238    1.658
2000-01-06  1.238  0.368  0.713 -0.275 -0.654  1.416    0.540
2000-01-07  1.416 -1.190 -0.044 -0.780  0.719  0.863   -1.304
2000-01-10  0.863  0.562  0.317 -0.267 -0.741  0.200    0.775
2000-01-11  0.200  1.190  0.655 -0.604 -0.187  0.424    0.310
2000-01-12  0.424 -0.843  0.785  1.700 -0.057  0.188    0.034
2000-01-13  0.188 -0.659  1.321  1.135 -0.871  0.873    0.623
2000-01-14  0.873 -0.729 -0.262  0.064  1.973    NaN      NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        # Load test data.
        data = self._get_frozen_input()
        data_fit = data.loc[
            :"2000-01-10"  # type: ignore[misc]
        ]  # type: error[misc]  # type: ignore[misc]
        data_predict = data.loc[
            "2000-01-10":  # type: ignore[misc]
        ]  # type: error[misc]  # type: ignore[misc]
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "smoothing": 2,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4    y.shift_-1  y.shift_-1_hat
2000-01-10  0.863  0.562  0.317 -0.267 -0.741  0.200    1.047
2000-01-11  0.200  1.190  0.655 -0.604 -0.187  0.424    0.462
2000-01-12  0.424 -0.843  0.785  1.700 -0.057  0.188   -0.294
2000-01-13  0.188 -0.659  1.321  1.135 -0.871  0.873    0.482
2000-01-14  0.873 -0.729 -0.262  0.064  1.973    NaN   -2.768
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test4(self) -> None:
        """
        Test `fit()` with weights.
        """
        # Load test data.
        data = self._get_frozen_input()
        data["weight"] = pd.Series(
            index=data.index, data=range(1, data.shape[0] + 1)
        )
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "sample_weight_col": "weight",
                "steps_ahead": 1,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4  weight    y.shift_-1  y.shift_-1_hat
2000-01-03 -0.865  1.074 -1.604  0.966 -0.705       1  1.771    0.310
2000-01-04  1.771 -0.705  1.262 -2.374 -0.447       2 -0.581    0.062
2000-01-05 -0.581  1.238 -0.811  2.345 -0.465       3  1.238    0.741
2000-01-06  1.238  0.368  0.713 -0.275 -0.654       4  1.416    0.630
2000-01-07  1.416 -1.190 -0.044 -0.780  0.719       5  0.863   -0.784
2000-01-10  0.863  0.562  0.317 -0.267 -0.741       6  0.200    0.583
2000-01-11  0.200  1.190  0.655 -0.604 -0.187       7  0.424    0.247
2000-01-12  0.424 -0.843  0.785  1.700 -0.057       8  0.188    0.662
2000-01-13  0.188 -0.659  1.321  1.135 -0.871       9  0.873    1.267
2000-01-14  0.873 -0.729 -0.262  0.064  1.973      10    NaN      NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test5(self) -> None:
        """
        Test `predict()` after `fit()`, both with weights.
        """
        # Load test data.
        data = self._get_frozen_input()
        data["weight"] = pd.Series(
            index=data.index, data=range(1, data.shape[0] + 1)
        )
        data_fit = data.loc[
            :"2000-01-10"  # type: ignore[misc]
        ]  # type: error[misc]  # type: ignore[misc]
        data_predict = data.loc[
            "2000-01-10":  # type: ignore[misc]
        ]  # type: error[misc]  # type: ignore[misc]
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "sample_weight_col": "weight",
                "steps_ahead": 1,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4  weight    y.shift_-1  y.shift_-1_hat
2000-01-10  0.863  0.562  0.317 -0.267 -0.741       6  0.200    0.373
2000-01-11  0.200  1.190  0.655 -0.604 -0.187       7  0.424    0.063
2000-01-12  0.424 -0.843  0.785  1.700 -0.057       8  0.188   -0.061
2000-01-13  0.188 -0.659  1.321  1.135 -0.871       9  0.873    0.083
2000-01-14  0.873 -0.729 -0.262  0.064  1.973      10    NaN   -1.139
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test6(self) -> None:
        """
        Test `fit()` with `p_val_threshold`.
        """
        # Load test data.
        data = self._get_frozen_input()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "p_val_threshold": 0.2,
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = """
                y     x1     x2     x3     x4    y.shift_-1  y.shift_-1_hat
2000-01-03 -0.865  1.074 -1.604  0.966 -0.705  1.771    0.961
2000-01-04  1.771 -0.705  1.262 -2.374 -0.447 -0.581   -0.411
2000-01-05 -0.581  1.238 -0.811  2.345 -0.465  1.238    1.217
2000-01-06  1.238  0.368  0.713 -0.275 -0.654  1.416    0.492
2000-01-07  1.416 -1.190 -0.044 -0.780  0.719  0.863   -0.910
2000-01-10  0.863  0.562  0.317 -0.267 -0.741  0.200    0.572
2000-01-11  0.200  1.190  0.655 -0.604 -0.187  0.424   -0.039
2000-01-12  0.424 -0.843  0.785  1.700 -0.057  0.188    0.632
2000-01-13  0.188 -0.659  1.321  1.135 -0.871  0.873    1.167
2000-01-14  0.873 -0.729 -0.262  0.064  1.973    NaN      NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test7(self) -> None:
        """
        Test `fit()` with `feature_weights`.
        """
        # Load test data.
        data = self._get_frozen_input()
        # Generate output using a certain regression config but manually
        # specified feature weights.
        config1 = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "p_val_threshold": 0.2,
                "col_mode": "merge_all",
                "feature_weights": [1, 1, 1, 1],
            }
        )
        node1 = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config1.to_dict(),
        )
        df_out1 = node1.fit(data)["df_out"]
        # Generate output using a different regression config but the same
        # (as above) manually specified feature weights.
        config2 = cconfig.Config.from_dict(
            {
                "x_vars": ["x1", "x2", "x3", "x4"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "smoothing": 2,
                "col_mode": "merge_all",
                "feature_weights": [1, 1, 1, 1],
            }
        )
        node2 = dtfcnoremo.LinearRegression(
            "linear_regression",
            **config2.to_dict(),
        )
        df_out2 = node2.fit(data)["df_out"]
        # The two outputs should agree because the input data and
        # user-supplied feature weights were the same (even though other
        # regression parameters were different).
        self.assert_dfs_close(df_out1, df_out2)

    def _get_test_data_file_name(self) -> str:
        """
        Return the name of the file containing the data for testing this class.
        """
        dir_name = self.get_input_dir(use_only_test_class=True)
        file_name = os.path.join(dir_name, "data.csv")
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("file_name=%s", file_name)
        return file_name

    def _get_frozen_input(self) -> pd.DataFrame:
        """
        Read the data generated by `test_generate_input_data()` through
        `_get_data()`.
        """
        file_name = self._get_test_data_file_name()
        # Since pickle is not portable, we use CSV to serialize the data.
        # Unfortunately CSV is a lousy serialization format and loses metadata so
        # we need to patch it up to make it look exactly the original one.
        df = pd.read_csv(file_name, index_col=0, parse_dates=True)
        df = df.asfreq("B")
        return df

    def _get_data(self, seed: int) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        cov = pd.DataFrame(
            np.array(
                [
                    [1, 0.05, 0.3, -0.2, 0.1],
                    [0.05, 1, 0, 0, 0],
                    [0.3, 0, 1, 0, 0],
                    [-0.2, 0, 0, 1, 0],
                    [0.1, 0, 0, 0, 1],
                ],
            )
        )
        mn_process = carsigen.MultivariateNormalProcess(cov=cov)
        data = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=seed
        )
        data.columns = ["y", "x1", "x2", "x3", "x4"]
        return data


class TestMultiindexLinearRegression(hunitest.TestCase):
    @staticmethod
    def get_data() -> pd.DataFrame:
        df_as_csv = """
data,x1,x1,x2,x2,x3,x3,y,y
id_,MN1,MN2,MN1,MN2,MN1,MN2,MN1,MN2
end_ts,,,,,,,,
2020-09-23 04:25:00-04:00,-0.184,-0.636,-1.286,-0.867,0.158,-0.21,1.548,2.026
2020-09-23 04:30:00-04:00,0.855,0.033,-0.228,-0.987,-0.298,-0.448,-0.162,1.961
2020-09-23 04:35:00-04:00,0.136,1.011,0.831,0.22,-0.508,-0.606,-0.434,-0.061
2020-09-23 04:40:00-04:00,-0.406,0.08,0.361,1.067,-0.297,-0.414,0.377,-0.221
2020-09-23 04:45:00-04:00,0.363,-0.002,-0.156,0.585,0.111,0.079,-0.349,-0.218
2020-09-23 04:50:00-04:00,-0.04,0.837,0.14,0.456,0.317,0.802,-0.269,-1.891
2020-09-23 04:55:00-04:00,-0.356,-1.012,-0.037,0.33,0.241,0.86,0.444,0.133
2020-09-23 05:00:00-04:00,0.275,-0.439,-0.239,-0.813,0.201,0.584,-0.105,1.011
2020-09-23 05:05:00-04:00,-0.927,0.776,-0.367,-0.557,-0.298,0.343,1.748,-0.541
2020-09-23 05:10:00-04:00,0.731,-0.163,-0.424,0.475,-0.381,-0.347,0.286,-0.214
"""
        buffer = io.StringIO(df_as_csv)
        df = pd.read_csv(buffer, header=[0, 1], index_col=0, parse_dates=[0])
        return df

    def test1(self) -> None:
        """
        Test `fit()`.
        """
        # Load test data.
        data = self.get_data()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("x1",),
                    ("x2",),
                    ("x3",),
                    ("y",),
                ],
                "out_col_group": (),
                "x_vars": ["x1", "x2", "x3"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "nan_mode": "drop",
            },
        )
        node = dtfcnoremo.MultiindexLinearRegression(
            "multiindex_linear_regression",
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        actual = hpandas.df_to_str(df_out.round(3), num_rows=None, precision=3)
        expected = r"""
                                    y.shift_-2        y.shift_-2_hat            x1            x2            x3             y
                             MN1    MN2     MN1    MN2    MN1    MN2    MN1    MN2    MN1    MN2    MN1    MN2
end_ts
2020-09-23 04:25:00-04:00 -0.434 -0.061   0.187 -0.065 -0.184 -0.636 -1.286 -0.867  0.158 -0.210  1.548  2.026
2020-09-23 04:30:00-04:00  0.377 -0.221  -0.185  0.081  0.855  0.033 -0.228 -0.987 -0.298 -0.448 -0.162  1.961
2020-09-23 04:35:00-04:00 -0.349 -0.218  -0.465 -0.023  0.136  1.011  0.831  0.220 -0.508 -0.606 -0.434 -0.061
2020-09-23 04:40:00-04:00 -0.269 -1.891  -0.298 -0.498 -0.406  0.080  0.361  1.067 -0.297 -0.414  0.377 -0.221
2020-09-23 04:45:00-04:00  0.444  0.133   0.126 -0.135  0.363 -0.002 -0.156  0.585  0.111  0.079 -0.349 -0.218
2020-09-23 04:50:00-04:00 -0.105  1.011   0.260  0.552 -0.040  0.837  0.140  0.456  0.317  0.802 -0.269 -1.891
2020-09-23 04:55:00-04:00  1.748 -0.541   0.183 -0.014 -0.356 -1.012 -0.037  0.330  0.241  0.860  0.444  0.133
2020-09-23 05:00:00-04:00  0.286 -0.214   0.201  0.384  0.275 -0.439 -0.239 -0.813  0.201  0.584 -0.105  1.011
2020-09-23 05:05:00-04:00    NaN    NaN     NaN    NaN -0.927  0.776 -0.367 -0.557 -0.298  0.343  1.748 -0.541
2020-09-23 05:10:00-04:00    NaN    NaN     NaN    NaN  0.731 -0.163 -0.424  0.475 -0.381 -0.347  0.286 -0.214
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
