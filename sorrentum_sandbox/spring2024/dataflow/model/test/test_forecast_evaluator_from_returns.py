import logging
from typing import List

import numpy as np
import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.forecast_evaluator_from_returns as dtfmfefrre
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestForecastEvaluator1(hunitest.TestCase):
    @staticmethod
    def get_data(
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
        asset_ids: List[int],
        *,
        bar_duration: str = "5T",
    ) -> pd.DataFrame:
        df = cfidaexa.get_forecast_dataframe(
            start_datetime,
            end_datetime,
            asset_ids,
            bar_duration=bar_duration,
        )
        return df

    def test_to_str_intraday_1_asset_floating_gmv(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(data)
        expected = r"""
# holdings marked to market=
                            101
2022-01-03 09:35:00-05:00   NaN
2022-01-03 09:40:00-05:00  0.76
2022-01-03 09:45:00-05:00  0.94
2022-01-03 09:50:00-05:00  0.55
2022-01-03 09:55:00-05:00 -0.63
2022-01-03 10:00:00-05:00 -1.25
# pnl=
                                101
2022-01-03 09:35:00-05:00       NaN
2022-01-03 09:40:00-05:00       NaN
2022-01-03 09:45:00-05:00 -5.97e-04
2022-01-03 09:50:00-05:00  2.52e-04
2022-01-03 09:55:00-05:00 -1.38e-04
2022-01-03 10:00:00-05:00 -8.00e-05
# statistics=
                                pnl  gross_volume  net_volume   gmv   nmv
2022-01-03 09:35:00-05:00       NaN           NaN         NaN   NaN   NaN
2022-01-03 09:40:00-05:00       NaN           NaN         NaN  0.76  0.76
2022-01-03 09:45:00-05:00 -5.97e-04          0.18        0.18  0.94  0.94
2022-01-03 09:50:00-05:00  2.52e-04          0.39       -0.39  0.55  0.55
2022-01-03 09:55:00-05:00 -1.38e-04          1.19       -1.19  0.63 -0.63
2022-01-03 10:00:00-05:00 -8.00e-05          0.61       -0.61  1.25 -1.25"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_1_asset_targeted_gmv(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(data, target_gmv=10000)
        expected = """
# holdings marked to market=
                               101
2022-01-03 09:35:00-05:00      NaN
2022-01-03 09:40:00-05:00  10000.0
2022-01-03 09:45:00-05:00  10000.0
2022-01-03 09:50:00-05:00  10000.0
2022-01-03 09:55:00-05:00 -10000.0
2022-01-03 10:00:00-05:00 -10000.0
# pnl=
                            101
2022-01-03 09:35:00-05:00   NaN
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00 -7.82
2022-01-03 09:50:00-05:00  2.67
2022-01-03 09:55:00-05:00 -2.49
2022-01-03 10:00:00-05:00 -1.26
# statistics=
                            pnl  gross_volume  net_volume      gmv      nmv
2022-01-03 09:35:00-05:00   NaN           NaN         NaN      NaN      NaN
2022-01-03 09:40:00-05:00   NaN           NaN         NaN  10000.0  10000.0
2022-01-03 09:45:00-05:00 -7.82           0.0         0.0  10000.0  10000.0
2022-01-03 09:50:00-05:00  2.67           0.0         0.0  10000.0  10000.0
2022-01-03 09:55:00-05:00 -2.49       20000.0    -20000.0  10000.0 -10000.0
2022-01-03 10:00:00-05:00 -1.26           0.0         0.0  10000.0 -10000.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets_floating_gmv(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(data)
        expected = r"""
# holdings marked to market=
                            101   201   301
2022-01-03 09:35:00-05:00   NaN   NaN   NaN
2022-01-03 09:40:00-05:00  0.76 -0.51 -1.83
2022-01-03 09:45:00-05:00  0.94  1.85 -1.31
2022-01-03 09:50:00-05:00  0.55 -1.51  0.15
2022-01-03 09:55:00-05:00 -0.63 -1.30 -0.16
2022-01-03 10:00:00-05:00 -1.25 -1.04  0.07
# pnl=
                                101       201       301
2022-01-03 09:35:00-05:00       NaN       NaN       NaN
2022-01-03 09:40:00-05:00       NaN       NaN       NaN
2022-01-03 09:45:00-05:00 -5.97e-04  5.01e-04  7.76e-04
2022-01-03 09:50:00-05:00  2.52e-04 -2.09e-03 -1.33e-03
2022-01-03 09:55:00-05:00 -1.38e-04 -4.61e-04  1.51e-04
2022-01-03 10:00:00-05:00 -8.00e-05  2.42e-03 -1.03e-04
# statistics=
                                pnl  gross_volume  net_volume   gmv   nmv
2022-01-03 09:35:00-05:00       NaN           NaN         NaN   NaN   NaN
2022-01-03 09:40:00-05:00       NaN           NaN         NaN  3.11 -1.58
2022-01-03 09:45:00-05:00  6.80e-04          3.06        3.06  4.10  1.47
2022-01-03 09:50:00-05:00 -3.17e-03          5.21       -2.27  2.21 -0.80
2022-01-03 09:55:00-05:00 -4.47e-04          1.71       -1.30  2.10 -2.10
2022-01-03 10:00:00-05:00  2.23e-03          1.11       -0.11  2.36 -2.22"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets_targeted_gmv(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(data, target_gmv=100000)
        expected = r"""
# holdings marked to market=
                                101       201       301
2022-01-03 09:35:00-05:00       NaN       NaN       NaN
2022-01-03 09:40:00-05:00  24548.14 -16542.73 -58909.12
2022-01-03 09:45:00-05:00  22980.66  44990.75 -32028.58
2022-01-03 09:50:00-05:00  24989.54 -68079.02   6931.45
2022-01-03 09:55:00-05:00 -30184.34 -62023.19  -7792.47
2022-01-03 10:00:00-05:00 -52732.47 -44162.35   3105.17
# pnl=
                             101     201    301
2022-01-03 09:35:00-05:00    NaN     NaN    NaN
2022-01-03 09:40:00-05:00    NaN     NaN    NaN
2022-01-03 09:45:00-05:00 -19.19   16.08  24.94
2022-01-03 09:50:00-05:00   6.14  -51.04 -32.47
2022-01-03 09:55:00-05:00  -6.21  -20.81   6.82
2022-01-03 10:00:00-05:00  -3.82  114.85  -4.91
# statistics=
                              pnl  gross_volume  net_volume       gmv        nmv
2022-01-03 09:35:00-05:00     NaN           NaN         NaN       NaN        NaN
2022-01-03 09:40:00-05:00     NaN           NaN         NaN  100000.0  -50903.71
2022-01-03 09:45:00-05:00   21.83      89981.50    86846.54  100000.0   35942.83
2022-01-03 09:50:00-05:00  -77.38     154038.67   -72100.86  100000.0  -36158.03
2022-01-03 09:55:00-05:00  -20.21      75953.62   -63841.97  100000.0 -100000.00
2022-01-03 10:00:00-05:00  106.12      51306.62     6210.34  100000.0  -93789.66"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_multiday_1_asset_targeted_gmv(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-05 10:00:00", tz="America/New_York"),
            asset_ids=[101],
            bar_duration="1H",
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(data, target_gmv=100000)
        expected = r"""
# holdings marked to market=
                                101
2022-01-03 10:30:00-05:00       NaN
2022-01-03 11:30:00-05:00 -100000.0
2022-01-03 12:30:00-05:00 -100000.0
2022-01-03 13:30:00-05:00 -100000.0
2022-01-03 14:30:00-05:00 -100000.0
2022-01-03 15:30:00-05:00  100000.0
2022-01-04 10:30:00-05:00 -100000.0
2022-01-04 11:30:00-05:00 -100000.0
2022-01-04 12:30:00-05:00  100000.0
2022-01-04 13:30:00-05:00 -100000.0
2022-01-04 14:30:00-05:00 -100000.0
2022-01-04 15:30:00-05:00 -100000.0
# pnl=
                             101
2022-01-03 10:30:00-05:00    NaN
2022-01-03 11:30:00-05:00    NaN
2022-01-03 12:30:00-05:00  78.18
2022-01-03 13:30:00-05:00 -26.70
2022-01-03 14:30:00-05:00  24.86
2022-01-03 15:30:00-05:00 -12.65
2022-01-04 10:30:00-05:00  84.30
2022-01-04 11:30:00-05:00 -85.79
2022-01-04 12:30:00-05:00 -47.52
2022-01-04 13:30:00-05:00 -45.08
2022-01-04 14:30:00-05:00  75.49
2022-01-04 15:30:00-05:00  81.48
# statistics=
                             pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 10:30:00-05:00    NaN           NaN         NaN       NaN       NaN
2022-01-03 11:30:00-05:00    NaN           NaN         NaN  100000.0 -100000.0
2022-01-03 12:30:00-05:00  78.18           0.0         0.0  100000.0 -100000.0
2022-01-03 13:30:00-05:00 -26.70           0.0         0.0  100000.0 -100000.0
2022-01-03 14:30:00-05:00  24.86           0.0         0.0  100000.0 -100000.0
2022-01-03 15:30:00-05:00 -12.65      200000.0    200000.0  100000.0  100000.0
2022-01-04 10:30:00-05:00  84.30      200000.0   -200000.0  100000.0 -100000.0
2022-01-04 11:30:00-05:00 -85.79           0.0         0.0  100000.0 -100000.0
2022-01-04 12:30:00-05:00 -47.52      200000.0    200000.0  100000.0  100000.0
2022-01-04 13:30:00-05:00 -45.08      200000.0   -200000.0  100000.0 -100000.0
2022-01-04 14:30:00-05:00  75.49           0.0         0.0  100000.0 -100000.0
2022-01-04 15:30:00-05:00  81.48           0.0         0.0  100000.0 -100000.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_log_portfolio_read_portfolio(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        #
        log_dir = self.get_scratch_space()
        _ = forecast_evaluator.log_portfolio(data, log_dir, target_gmv=1e6)
        #
        portfolio_df, stats_df = forecast_evaluator.read_portfolio(log_dir)
        # Ensure that the `int` asset id type is recovered.
        asset_id_idx = portfolio_df.columns.levels[1]
        self.assertEqual(asset_id_idx.dtype.type, np.int64)
        #
        precision = 2
        portfolio_df_str = hpandas.df_to_str(
            portfolio_df, num_rows=None, precision=precision
        )
        expected_portfolio_df_str = r"""
                                      returns                     volatility                     prediction                       position                           pnl
                                101       201       301        101       201       301        101       201       301        101        201        301     101      201     301
2022-01-03 09:35:00-05:00 -1.10e-03 -3.44e-04 -1.30e-04   1.10e-03  3.44e-04  1.30e-04   8.43e-04 -1.77e-04 -2.38e-04        NaN        NaN        NaN     NaN      NaN     NaN
2022-01-03 09:40:00-05:00 -7.25e-04 -5.14e-05 -1.87e-03   9.10e-04  2.31e-04  1.40e-03   8.58e-04  4.26e-04 -1.84e-03  245481.44 -165427.34 -589091.23     NaN      NaN     NaN
2022-01-03 09:45:00-05:00 -7.82e-04 -9.72e-04 -4.23e-04   8.59e-04  6.54e-04  1.10e-03   4.75e-04 -9.85e-04  1.70e-04  229806.64  449907.51 -320285.85 -191.92   160.84  249.39
2022-01-03 09:50:00-05:00  2.67e-04 -1.13e-03  1.01e-03   7.10e-04  8.53e-04  1.07e-03  -4.51e-04 -1.11e-03 -1.76e-04  249895.36 -680790.17   69314.47   61.35  -510.41 -324.74
2022-01-03 09:55:00-05:00 -2.49e-04  3.06e-04  9.84e-04   6.06e-04  7.29e-04  1.05e-03  -7.55e-04 -7.61e-04  7.68e-05 -301843.37 -620231.88  -77924.75  -62.12  -208.12   68.19
2022-01-03 10:00:00-05:00  1.26e-04 -1.85e-03  6.30e-04   5.17e-04  1.16e-03  9.47e-04  -8.15e-04  6.48e-04  1.54e-03 -527324.75 -441623.54   31051.72  -38.18  1148.47  -49.10"""
        self.assert_equal(
            portfolio_df_str, expected_portfolio_df_str, fuzzy_match=True
        )
        #
        stats_df_str = hpandas.df_to_str(
            stats_df, num_rows=None, precision=precision
        )
        expected_stats_df_str = r"""
                               pnl  gross_volume  net_volume        gmv         nmv
2022-01-03 09:35:00-05:00      NaN           NaN         NaN        NaN         NaN
2022-01-03 09:40:00-05:00      NaN           NaN         NaN  1000000.0  -509037.13
2022-01-03 09:45:00-05:00   218.31      9.00e+05   868465.44  1000000.0   359428.31
2022-01-03 09:50:00-05:00  -773.80      1.54e+06  -721008.65  1000000.0  -361580.34
2022-01-03 09:55:00-05:00  -202.05      7.60e+05  -638419.66  1000000.0 -1000000.00
2022-01-03 10:00:00-05:00  1061.20      5.13e+05    62103.43  1000000.0  -937896.57"""
        self.assert_equal(stats_df_str, expected_stats_df_str, fuzzy_match=True)

    def test_to_str_intraday_4_assets_dollar_neutrality_demean(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301, 401],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data, target_gmv=100000, dollar_neutrality="demean"
        )
        expected = r"""
# holdings marked to market=
                                101       201       301       401
2022-01-03 09:35:00-05:00       NaN       NaN       NaN       NaN
2022-01-03 09:40:00-05:00   1596.04 -15953.07 -34046.93  48403.96
2022-01-03 09:45:00-05:00   1107.39  21556.28 -50000.00  27336.33
2022-01-03 09:50:00-05:00  30974.64 -30610.07  19025.36 -19389.93
2022-01-03 09:55:00-05:00 -15483.81 -27443.47  -7072.72  50000.00
2022-01-03 10:00:00-05:00 -28692.80 -21307.20  19427.21  30572.79
# pnl=
                            101    201    301    401
2022-01-03 09:35:00-05:00   NaN    NaN    NaN    NaN
2022-01-03 09:40:00-05:00   NaN    NaN    NaN    NaN
2022-01-03 09:45:00-05:00 -1.25  15.51  14.41  29.29
2022-01-03 09:50:00-05:00  0.30 -24.46 -50.69  -7.01
2022-01-03 09:55:00-05:00 -7.70  -9.36  18.72  12.88
2022-01-03 10:00:00-05:00 -1.96  50.82  -4.46 -36.87
# statistics=
                             pnl  gross_volume  net_volume       gmv  nmv
2022-01-03 09:35:00-05:00    NaN           NaN         NaN       NaN  NaN
2022-01-03 09:40:00-05:00    NaN           NaN         NaN  100000.0  0.0
2022-01-03 09:45:00-05:00  57.97      75018.70         0.0  100000.0  0.0
2022-01-03 09:50:00-05:00 -81.87     197785.22         0.0  100000.0  0.0
2022-01-03 09:55:00-05:00  14.54     145113.06         0.0  100000.0  0.0
2022-01-03 10:00:00-05:00   7.53      65272.40         0.0  100000.0  0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_4_assets_dollar_neutrality_side_preserving(
        self,
    ) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301, 401],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data, target_gmv=100000, dollar_neutrality="side_preserving"
        )
        expected = r"""
# holdings marked to market=
                                101       201       301       401
2022-01-03 09:35:00-05:00       NaN       NaN       NaN       NaN
2022-01-03 09:40:00-05:00   7734.32 -10962.44 -39037.56  42265.68
2022-01-03 09:45:00-05:00   9640.87  18874.57 -50000.00  21484.55
2022-01-03 09:50:00-05:00  39142.80 -28556.19  10857.20 -21443.81
2022-01-03 09:55:00-05:00 -15092.17 -31011.59  -3896.24  50000.00
2022-01-03 10:00:00-05:00 -27211.19 -22788.81   8110.25  41889.75
# pnl=
                            101    201    301    401
2022-01-03 09:35:00-05:00   NaN    NaN    NaN    NaN
2022-01-03 09:40:00-05:00   NaN    NaN    NaN    NaN
2022-01-03 09:45:00-05:00 -6.05  10.66  16.53  25.57
2022-01-03 09:50:00-05:00  2.57 -21.41 -50.69  -5.51
2022-01-03 09:55:00-05:00 -9.73  -8.73  10.68  14.25
2022-01-03 10:00:00-05:00 -1.91  57.42  -2.45 -36.87
# statistics=
                             pnl  gross_volume  net_volume       gmv  nmv
2022-01-03 09:35:00-05:00    NaN           NaN         NaN       NaN  NaN
2022-01-03 09:40:00-05:00    NaN           NaN         NaN  100000.0  0.0
2022-01-03 09:45:00-05:00  46.71      63487.13         0.0  100000.0  0.0
2022-01-03 09:50:00-05:00 -75.05     180718.25         0.0  100000.0  0.0
2022-01-03 09:55:00-05:00   6.47     142887.62         0.0  100000.0  0.0
2022-01-03 10:00:00-05:00  16.19      40458.55         0.0  100000.0  0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_multiday_overnight_returns_injected(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 15:15:00", tz="America/New_York"),
            pd.Timestamp("2022-01-04 10:00:00", tz="America/New_York"),
            asset_ids=[101],
            bar_duration="15T",
        )
        overnight_returns = pd.DataFrame(
            [-0.001],
            [
                pd.Timestamp("2022-01-04 09:30:00", tz="America/New_York"),
            ],
            [101],
        )
        forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        pnl, stats = forecast_evaluator.compute_overnight_pnl(
            data, overnight_returns, target_gmv=1e5
        )
        round_precision = 6
        precision = 2
        actual = []
        actual.append(
            "# pnl=\n%s"
            % hpandas.df_to_str(
                pnl.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        actual.append(
            "# statistics=\n%s"
            % hpandas.df_to_str(
                stats.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        actual = "\n".join(actual)
        expected = r"""
# pnl=
                             101
2022-01-04 09:30:00-05:00 -100.0
# statistics=
                             pnl  gross_volume  net_volume       gmv       nmv
2022-01-04 09:30:00-05:00 -100.0             0           0  100000.0  100000.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)
