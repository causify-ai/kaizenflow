import logging

import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.forecast_mixer as dtfmofomix
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestForecastMixer1(hunitest.TestCase):
    def test_generate_portfolio_bar_metrics_df(self) -> None:
        start_datetime = pd.Timestamp("2021-01-03 09:30", tz="America/New_York")
        end_datetime = pd.Timestamp("2021-01-03 10:30", tz="America/New_York")
        asset_ids = [100, 200]
        num_features = 2
        prediction_df = cfidaexa.get_forecast_dataframe(
            start_datetime, end_datetime, asset_ids, num_features=num_features
        )
        forecast_mixer = dtfmofomix.ForecastMixer(
            returns_col="returns",
            volatility_col="volatility",
            prediction_cols=[1, 2],
        )
        weights = pd.DataFrame(
            [
                [1, 1],
                [1, -1],
            ],
            [1, 2],
            ["sum", "diff"],
        )
        bar_metrics_df = forecast_mixer.generate_portfolio_bar_metrics_df(
            prediction_df, weights, target_gmv=1e6
        )
        precision = 2
        actual = hpandas.df_to_str(
            bar_metrics_df.round(precision), num_rows=None, precision=precision
        )
        expected = r"""
                                                       sum                                                    diff
                               pnl gross_volume net_volume        gmv         nmv      pnl gross_volume net_volume        gmv         nmv
2021-01-03 09:35:00-05:00      NaN          NaN        NaN        NaN         NaN      NaN          NaN        NaN        NaN         NaN
2021-01-03 09:40:00-05:00      NaN          NaN        NaN  1000000.0  -957156.97      NaN          NaN        NaN  1000000.0   587225.89
2021-01-03 09:45:00-05:00  1283.59     2.00e+06   1.48e+06  1000000.0   519132.80  -893.20     1.59e+06  -1.59e+06  1000000.0 -1000000.00
2021-01-03 09:50:00-05:00   327.36     4.81e+05   4.81e+05  1000000.0  1000000.00  -401.41     8.45e+04   0.00e+00  1000000.0 -1000000.00
2021-01-03 09:55:00-05:00  -323.39     1.55e+06  -1.55e+06  1000000.0  -546464.71   304.71     2.00e+06   2.00e+06  1000000.0  1000000.00
2021-01-03 10:00:00-05:00   332.05     3.74e+04   3.74e+04  1000000.0  -509113.16    92.41     5.56e+05   0.00e+00  1000000.0  1000000.00
2021-01-03 10:05:00-05:00  -238.19     5.74e+05  -4.91e+05  1000000.0 -1000000.00   756.02     9.51e+05  -9.51e+05  1000000.0    49345.63
2021-01-03 10:10:00-05:00  1316.80     1.33e+06   1.33e+06  1000000.0   329560.38  1492.29     2.00e+06  -9.02e+04  1000000.0   -40806.57
2021-01-03 10:15:00-05:00   744.07     1.66e+06  -1.33e+06  1000000.0 -1000000.00  -859.88     9.59e+05  -9.59e+05  1000000.0 -1000000.00
2021-01-03 10:20:00-05:00   446.30     1.01e+06   1.01e+06  1000000.0     6171.38   447.87     1.78e+06   1.12e+06  1000000.0   117927.84
2021-01-03 10:25:00-05:00   500.49     1.47e+06   9.94e+05  1000000.0  1000000.00  -531.87     2.00e+06  -8.41e+05  1000000.0  -722795.55
2021-01-03 10:30:00-05:00  -774.93     7.83e+05  -7.83e+05  1000000.0   216610.31   609.69     2.24e+05  -2.24e+05  1000000.0  -947292.77"""
        self.assert_equal(actual, expected, fuzzy_match=True)
