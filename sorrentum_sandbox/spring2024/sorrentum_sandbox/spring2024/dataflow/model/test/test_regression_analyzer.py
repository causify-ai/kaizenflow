import logging

import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.regression_analyzer as dtfmoreana
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestRegressionAnalyzer1(hunitest.TestCase):
    def test_compute_moments(self) -> None:
        start_datetime = pd.Timestamp("2021-01-03 09:30", tz="America/New_York")
        end_datetime = pd.Timestamp("2021-01-31 09:30", tz="America/New_York")
        asset_ids = [100, 200]
        num_features = 2
        feature_df = cfidaexa.get_forecast_dataframe(
            start_datetime, end_datetime, asset_ids, num_features=num_features
        )
        regression_analyzer = dtfmoreana.RegressionAnalyzer(
            x_cols=[1, 2],
            y_col="returns",
        )
        coefficients = regression_analyzer.compute_regression_coefficients(
            feature_df
        )
        stats = ["beta_z_scored", "p_val_2s"]
        moments = regression_analyzer.compute_moments(coefficients, stats)
        actual = hpandas.df_to_str(
            moments.round(3), handle_signed_zeros=True, num_rows=None, precision=3
        )
        expected = r"""
              beta_z_scored                      p_val_2s
           mean    std skew kurtosis     mean    std skew kurtosis
1        -0.289  0.155  0.0     -2.0    0.774  0.118  0.0     -2.0
2        -0.163  0.806  0.0     -2.0    0.574  0.156  0.0     -2.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)
