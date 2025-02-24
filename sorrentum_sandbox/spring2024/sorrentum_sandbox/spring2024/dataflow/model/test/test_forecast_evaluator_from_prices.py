import logging
from typing import List

import numpy as np
import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestForecastEvaluatorFromPrices1(hunitest.TestCase):
    @staticmethod
    def get_data(
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
        asset_ids: List[int],
        *,
        bar_duration: str = "5T",
    ) -> pd.DataFrame:
        df = cfidaexa.get_forecast_price_based_dataframe(
            start_datetime,
            end_datetime,
            asset_ids,
            bar_duration=bar_duration,
        )
        return df

    def test_to_str_intraday_1_asset(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data,
            target_gmv=1e4,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        expected = r"""
# holdings_shares=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  10.0
2022-01-03 09:50:00-05:00  10.0
2022-01-03 09:55:00-05:00 -10.0
2022-01-03 10:00:00-05:00 -10.0
# holdings_notional=
                               101
2022-01-03 09:40:00-05:00      NaN
2022-01-03 09:45:00-05:00  9973.93
2022-01-03 09:50:00-05:00  9976.60
2022-01-03 09:55:00-05:00 -9974.12
2022-01-03 10:00:00-05:00 -9975.38
# executed_trades_shares=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  10.0
2022-01-03 09:50:00-05:00   0.0
2022-01-03 09:55:00-05:00 -20.0
2022-01-03 10:00:00-05:00   0.0
# executed_trades_notional=
                                101
2022-01-03 09:40:00-05:00       NaN
2022-01-03 09:45:00-05:00   9973.93
2022-01-03 09:50:00-05:00      0.00
2022-01-03 09:55:00-05:00 -19948.23
2022-01-03 10:00:00-05:00      0.00
# pnl=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  0.00
2022-01-03 09:50:00-05:00  2.66
2022-01-03 09:55:00-05:00 -2.48
2022-01-03 10:00:00-05:00 -1.26
# statistics=
                            pnl  gross_volume  net_volume      gmv      nmv
2022-01-03 09:40:00-05:00   NaN           NaN         NaN      NaN      NaN
2022-01-03 09:45:00-05:00  0.00       9973.93     9973.93  9973.93  9973.93
2022-01-03 09:50:00-05:00  2.66          0.00        0.00  9976.60  9976.60
2022-01-03 09:55:00-05:00 -2.48      19948.23   -19948.23  9974.12 -9974.12
2022-01-03 10:00:00-05:00 -1.26          0.00        0.00  9975.38 -9975.38
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_annotate_forecasts_with_extended_stats_1_asset(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        _, stats_df = forecast_evaluator.annotate_forecasts(
            data,
            target_gmv=1e4,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
            compute_extended_stats=True,
        )
        precision = 2
        actual = hpandas.df_to_str(stats_df, num_rows=None, precision=precision)
        expected = r"""
                            pnl  gross_volume  net_volume      gmv      nmv  gpc  npc  wnl
2022-01-03 09:40:00-05:00   NaN           NaN         NaN      NaN      NaN  NaN  NaN  NaN
2022-01-03 09:45:00-05:00  0.00       9973.93     9973.93  9973.93  9973.93  1.0  1.0  0.0
2022-01-03 09:50:00-05:00  2.66          0.00        0.00  9976.60  9976.60  1.0  1.0  1.0
2022-01-03 09:55:00-05:00 -2.48      19948.23   -19948.23  9974.12 -9974.12  1.0 -1.0 -1.0
2022-01-03 10:00:00-05:00 -1.26          0.00        0.00  9975.38 -9975.38  1.0 -1.0 -1.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_1_asset_longitudinal(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("data=\n%s", data)
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data,
            style="longitudinal",
            prediction_abs_threshold=0.0,
            target_dollar_risk_per_name=10.0,
            volatility_lower_bound=0.0,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        expected = r"""
# holdings_shares=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  14.0
2022-01-03 09:50:00-05:00  13.0
2022-01-03 09:55:00-05:00 -17.0
2022-01-03 10:00:00-05:00 -20.0
# holdings_notional=
                                101
2022-01-03 09:40:00-05:00       NaN
2022-01-03 09:45:00-05:00  13963.51
2022-01-03 09:50:00-05:00  12969.57
2022-01-03 09:55:00-05:00 -16956.00
2022-01-03 10:00:00-05:00 -19950.75
# executed_trades_shares=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  14.0
2022-01-03 09:50:00-05:00  -1.0
2022-01-03 09:55:00-05:00 -30.0
2022-01-03 10:00:00-05:00  -3.0
# executed_trades_notional=
                                101
2022-01-03 09:40:00-05:00       NaN
2022-01-03 09:45:00-05:00  13963.51
2022-01-03 09:50:00-05:00   -997.66
2022-01-03 09:55:00-05:00 -29922.35
2022-01-03 10:00:00-05:00  -2992.61
# pnl=
                            101
2022-01-03 09:40:00-05:00   NaN
2022-01-03 09:45:00-05:00  0.00
2022-01-03 09:50:00-05:00  3.73
2022-01-03 09:55:00-05:00 -3.22
2022-01-03 10:00:00-05:00 -2.14
# statistics=
                            pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 09:40:00-05:00   NaN           NaN         NaN       NaN       NaN
2022-01-03 09:45:00-05:00  0.00      13963.51    13963.51  13963.51  13963.51
2022-01-03 09:50:00-05:00  3.73        997.66     -997.66  12969.57  12969.57
2022-01-03 09:55:00-05:00 -3.22      29922.35   -29922.35  16956.00 -16956.00
2022-01-03 10:00:00-05:00 -2.14       2992.61    -2992.61  19950.75 -19950.75
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_annotate_forecasts_with_extended_stats_3_assets(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        _, stats_df = forecast_evaluator.annotate_forecasts(
            data,
            target_gmv=1e4,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
            compute_extended_stats=True,
        )
        precision = 2
        actual = hpandas.df_to_str(stats_df, num_rows=None, precision=precision)
        expected = r"""
                             pnl  gross_volume  net_volume      gmv      nmv  gpc  npc  wnl
2022-01-03 09:40:00-05:00    NaN           NaN         NaN      NaN      NaN  NaN  NaN  NaN
2022-01-03 09:45:00-05:00   0.00       9974.12     7978.96  9974.12  7978.96  2.0  0.0  0.0
2022-01-03 09:50:00-05:00   1.38       9976.74    -7979.55  9975.80     0.79  2.0  0.0  0.0
2022-01-03 09:55:00-05:00  -2.76       9983.16    -1986.56  9985.14 -1988.54  2.0  0.0 -2.0
2022-01-03 10:00:00-05:00  13.60       1996.17    -1996.17  9972.34 -3971.11  2.0  0.0  2.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data,
            target_gmv=1e5,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        expected = r"""
# holdings_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   NaN   NaN   NaN
2022-01-03 09:45:00-05:00  87.0   0.0 -13.0
2022-01-03 09:50:00-05:00  48.0 -52.0   0.0
2022-01-03 09:55:00-05:00   0.0 -62.0  38.0
2022-01-03 10:00:00-05:00   0.0 -68.0  32.0
# holdings_notional=
                                101       201       301
2022-01-03 09:40:00-05:00       NaN       NaN       NaN
2022-01-03 09:45:00-05:00  86773.21      0.00 -12968.54
2022-01-03 09:50:00-05:00  47887.66 -51870.06      0.00
2022-01-03 09:55:00-05:00      0.00 -61863.98  37983.85
2022-01-03 10:00:00-05:00      0.00 -67725.29  32006.56
# executed_trades_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   NaN   NaN   NaN
2022-01-03 09:45:00-05:00  87.0   0.0 -13.0
2022-01-03 09:50:00-05:00 -39.0 -52.0  13.0
2022-01-03 09:55:00-05:00 -48.0 -10.0  38.0
2022-01-03 10:00:00-05:00   0.0  -6.0  -6.0
# executed_trades_notional=
                                101       201       301
2022-01-03 09:40:00-05:00       NaN       NaN       NaN
2022-01-03 09:45:00-05:00  86773.21      0.00 -12968.54
2022-01-03 09:50:00-05:00 -38908.72 -51870.06  12981.70
2022-01-03 09:55:00-05:00 -47875.76  -9978.06  37983.85
2022-01-03 10:00:00-05:00      0.00  -5975.76  -6001.23
# pnl=
                             101     201    301
2022-01-03 09:40:00-05:00    NaN     NaN    NaN
2022-01-03 09:45:00-05:00   0.00    0.00   0.00
2022-01-03 09:50:00-05:00  23.17    0.00 -13.16
2022-01-03 09:55:00-05:00 -11.90  -15.86   0.00
2022-01-03 10:00:00-05:00   0.00  114.45  23.94
# statistics=
                              pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 09:40:00-05:00     NaN           NaN         NaN       NaN       NaN
2022-01-03 09:45:00-05:00    0.00      99741.75    73804.67  99741.75  73804.67
2022-01-03 09:50:00-05:00   10.01     103760.48   -77797.08  99757.72  -3982.40
2022-01-03 09:55:00-05:00  -27.76      95837.66   -19869.97  99847.83 -23880.13
2022-01-03 10:00:00-05:00  138.39      11976.99   -11976.99  99731.85 -35718.74
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets_asset_specific_quantization(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        asset_id_to_share_decimals = {
            101: -1,
            201: 0,
            301: 1,
        }
        actual = forecast_evaluator.to_str(
            data,
            target_gmv=1e5,
            quantization=None,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
            asset_id_to_share_decimals=asset_id_to_share_decimals,
        )
        expected = r"""
# holdings_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   NaN   NaN   NaN
2022-01-03 09:45:00-05:00  90.0   0.0 -13.1
2022-01-03 09:50:00-05:00  50.0 -52.0   0.0
2022-01-03 09:55:00-05:00   0.0 -62.0  38.2
2022-01-03 10:00:00-05:00   0.0 -68.0  32.1
# holdings_notional=
                                101       201       301
2022-01-03 09:40:00-05:00       NaN       NaN       NaN
2022-01-03 09:45:00-05:00  89765.39      0.00 -13068.30
2022-01-03 09:50:00-05:00  49882.98 -51870.06      0.00
2022-01-03 09:55:00-05:00      0.00 -61863.98  38183.76
2022-01-03 10:00:00-05:00      0.00 -67725.29  32106.58
# executed_trades_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   NaN   NaN   NaN
2022-01-03 09:45:00-05:00  90.0   0.0 -13.1
2022-01-03 09:50:00-05:00 -40.0 -52.0  13.1
2022-01-03 09:55:00-05:00 -50.0 -10.0  38.2
2022-01-03 10:00:00-05:00   0.0  -6.0  -6.1
# executed_trades_notional=
                                101       201       301
2022-01-03 09:40:00-05:00       NaN       NaN       NaN
2022-01-03 09:45:00-05:00  89765.39      0.00 -13068.30
2022-01-03 09:50:00-05:00 -39906.38 -51870.06  13081.56
2022-01-03 09:55:00-05:00 -49870.58  -9978.06  38183.76
2022-01-03 10:00:00-05:00      0.00  -5975.76  -6101.25
# pnl=
                             101     201    301
2022-01-03 09:40:00-05:00    NaN     NaN    NaN
2022-01-03 09:45:00-05:00   0.00    0.00   0.00
2022-01-03 09:50:00-05:00  23.97    0.00 -13.26
2022-01-03 09:55:00-05:00 -12.40  -15.86   0.00
2022-01-03 10:00:00-05:00   0.00  114.45  24.06
# statistics=
                              pnl  gross_volume  net_volume        gmv       nmv
2022-01-03 09:40:00-05:00     NaN           NaN         NaN        NaN       NaN
2022-01-03 09:45:00-05:00    0.00     102833.69    76697.09  102833.69  76697.09
2022-01-03 09:50:00-05:00   10.71     104858.00   -78694.88  101753.04  -1987.08
2022-01-03 09:55:00-05:00  -28.26      98032.40   -21664.88  100047.74 -23680.22
2022-01-03 10:00:00-05:00  138.51      12077.01   -12077.01   99831.87 -35618.72
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets_longitudinal(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("data=\n%s", data)
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        actual = forecast_evaluator.to_str(
            data,
            style="longitudinal",
            prediction_abs_threshold=5e-4,
            target_dollar_risk_per_name=10.0,
            volatility_lower_bound=0.0,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        expected = r"""
# holdings_shares=
                            101   201  301
2022-01-03 09:40:00-05:00   NaN   NaN  NaN
2022-01-03 09:45:00-05:00  14.0   0.0 -5.0
2022-01-03 09:50:00-05:00   0.0 -14.0  0.0
2022-01-03 09:55:00-05:00   0.0 -11.0  0.0
2022-01-03 10:00:00-05:00 -20.0 -13.0  0.0
# holdings_notional=
                                101       201     301
2022-01-03 09:40:00-05:00       NaN       NaN     NaN
2022-01-03 09:45:00-05:00  13963.51      0.00 -4987.9
2022-01-03 09:50:00-05:00      0.00 -13965.02     0.0
2022-01-03 09:55:00-05:00      0.00 -10975.87     0.0
2022-01-03 10:00:00-05:00 -19950.75 -12947.48     0.0
# executed_trades_shares=
                            101   201  301
2022-01-03 09:40:00-05:00   NaN   NaN  NaN
2022-01-03 09:45:00-05:00  14.0   0.0 -5.0
2022-01-03 09:50:00-05:00 -14.0 -14.0  5.0
2022-01-03 09:55:00-05:00   0.0   3.0  0.0
2022-01-03 10:00:00-05:00 -20.0  -2.0  0.0
# executed_trades_notional=
                                101       201      301
2022-01-03 09:40:00-05:00       NaN       NaN      NaN
2022-01-03 09:45:00-05:00  13963.51      0.00 -4987.90
2022-01-03 09:50:00-05:00 -13967.23 -13965.02  4992.96
2022-01-03 09:55:00-05:00      0.00   2993.42     0.00
2022-01-03 10:00:00-05:00 -19950.75  -1991.92     0.00
# pnl=
                            101    201   301
2022-01-03 09:40:00-05:00   NaN    NaN   NaN
2022-01-03 09:45:00-05:00  0.00   0.00  0.00
2022-01-03 09:50:00-05:00  3.73   0.00 -5.06
2022-01-03 09:55:00-05:00  0.00  -4.27  0.00
2022-01-03 10:00:00-05:00  0.00  20.31  0.00
# statistics=
                             pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 09:40:00-05:00    NaN           NaN         NaN       NaN       NaN
2022-01-03 09:45:00-05:00   0.00      18951.41     8975.60  18951.41   8975.60
2022-01-03 09:50:00-05:00  -1.33      32925.21   -22939.29  13965.02 -13965.02
2022-01-03 09:55:00-05:00  -4.27       2993.42     2993.42  10975.87 -10975.87
2022-01-03 10:00:00-05:00  20.31      21942.68   -21942.68  32898.24 -32898.24
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets_varying_gmv(self) -> None:
        start_timestamp = pd.Timestamp(
            "2022-01-03 09:35:00", tz="America/New_York"
        )
        end_timestamp = pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York")
        data = self.get_data(
            start_timestamp,
            end_timestamp,
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        target_gmv = pd.Series(
            [0.0, 1e3, 1e4, 1e3, 1e2],
            pd.date_range(
                start_timestamp + pd.Timedelta("5T"), end_timestamp, freq="5T"
            ),
        )
        actual = forecast_evaluator.to_str(
            data,
            target_gmv=target_gmv,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        expected = r"""
# holdings_shares=
                           101  201  301
2022-01-03 09:40:00-05:00  NaN  NaN  NaN
2022-01-03 09:45:00-05:00  0.0  NaN  0.0
2022-01-03 09:50:00-05:00  0.0 -1.0  0.0
2022-01-03 09:55:00-05:00  0.0 -6.0  4.0
2022-01-03 10:00:00-05:00  0.0 -1.0  0.0
# holdings_notional=
                           101      201     301
2022-01-03 09:40:00-05:00  NaN      NaN     NaN
2022-01-03 09:45:00-05:00  0.0      NaN     0.0
2022-01-03 09:50:00-05:00  0.0  -997.50     0.0
2022-01-03 09:55:00-05:00  0.0 -5986.84  3998.3
2022-01-03 10:00:00-05:00  0.0  -995.96     0.0
# executed_trades_shares=
                           101  201  301
2022-01-03 09:40:00-05:00  NaN  NaN  NaN
2022-01-03 09:45:00-05:00  0.0  NaN  0.0
2022-01-03 09:50:00-05:00  0.0 -1.0  0.0
2022-01-03 09:55:00-05:00  0.0 -5.0  4.0
2022-01-03 10:00:00-05:00  0.0  5.0 -4.0
# executed_trades_notional=
                           101      201      301
2022-01-03 09:40:00-05:00  NaN      NaN      NaN
2022-01-03 09:45:00-05:00  0.0      NaN     0.00
2022-01-03 09:50:00-05:00  0.0  -997.50     0.00
2022-01-03 09:55:00-05:00  0.0 -4989.03  3998.30
2022-01-03 10:00:00-05:00  0.0  4979.80 -4000.82
# pnl=
                           101    201   301
2022-01-03 09:40:00-05:00  NaN    NaN   NaN
2022-01-03 09:45:00-05:00  0.0    NaN  0.00
2022-01-03 09:50:00-05:00  0.0   0.00  0.00
2022-01-03 09:55:00-05:00  0.0  -0.30  0.00
2022-01-03 10:00:00-05:00  0.0  11.08  2.52
# statistics=
                            pnl  gross_volume  net_volume      gmv      nmv
2022-01-03 09:40:00-05:00   NaN           NaN         NaN      NaN      NaN
2022-01-03 09:45:00-05:00   0.0          0.00        0.00     0.00     0.00
2022-01-03 09:50:00-05:00   0.0        997.50     -997.50   997.50  -997.50
2022-01-03 09:55:00-05:00  -0.3       8987.33     -990.73  9985.14 -1988.54
2022-01-03 10:00:00-05:00  13.6       8980.62      978.98   995.96  -995.96
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_save_portfolio_load_portfolio(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        #
        log_dir = self.get_scratch_space()
        _ = forecast_evaluator.save_portfolio(
            data,
            log_dir,
            target_gmv=1e6,
            quantization=0,
            liquidate_at_end_of_day=False,
            burn_in_bars=0,
        )
        #
        portfolio_df, stats_df = forecast_evaluator.load_portfolio_and_stats(
            log_dir
        )
        # Ensure that the `int` asset id type is recovered.
        asset_id_idx = portfolio_df.columns.levels[1]
        self.assertEqual(asset_id_idx.dtype.type, np.int64)
        #
        precision = 2
        portfolio_df_str = hpandas.df_to_str(
            portfolio_df, num_rows=None, precision=precision
        )
        expected_portfolio_df_str = r"""
                            price                  volatility                     prediction                     holdings_shares               holdings_notional                       executed_trades_shares               executed_trades_notional                           pnl
                              101     201      301        101       201       301        101       201       301             101    201    301               101        201        301                    101    201    301                      101        201        301     101      201     301
2022-01-03 09:35:00-05:00  998.90  999.66   999.87        NaN       NaN       NaN   8.43e-04 -1.77e-04 -2.38e-04             NaN    NaN    NaN               NaN        NaN        NaN                    NaN    NaN    NaN                      NaN        NaN        NaN     NaN      NaN     NaN
2022-01-03 09:40:00-05:00  998.17  999.60   998.00   7.25e-04  5.14e-05  1.87e-03   8.58e-04  4.26e-04 -1.84e-03             NaN    NaN    NaN               NaN        NaN        NaN                    NaN    NaN    NaN                      NaN        NaN        NaN     NaN      NaN     NaN
2022-01-03 09:45:00-05:00  997.39  998.63   997.58   7.57e-04  7.29e-04  1.28e-03   4.75e-04 -9.85e-04  1.70e-04           871.0    0.0 -131.0         868729.51       0.00 -130683.00                  871.0    0.0 -131.0                868729.51       0.00 -130683.00    0.00     0.00    0.00
2022-01-03 09:50:00-05:00  997.66  997.50   998.59   6.02e-04  9.21e-04  1.17e-03  -4.51e-04 -1.11e-03 -1.76e-04           483.0 -519.0    0.0         481869.56 -517703.09       0.00                 -388.0 -519.0  131.0               -387091.91 -517703.09  130815.57  231.96     0.00 -132.57
2022-01-03 09:55:00-05:00  997.41  997.81   999.57   5.07e-04  7.64e-04  1.11e-03  -7.55e-04 -7.61e-04  7.68e-05             0.0 -620.0  382.0              0.00 -618639.79  381837.62                 -483.0 -101.0  382.0               -481749.79 -100778.42  381837.62 -119.77  -158.29    0.00
2022-01-03 10:00:00-05:00  997.54  995.96  1000.20   4.27e-04  1.21e-03  9.87e-04  -8.15e-04  6.48e-04  1.54e-03             0.0 -680.0  321.0              0.00 -677252.94  321065.77                    0.0  -60.0  -61.0                     0.00  -59757.61  -61012.50    0.00  1144.47  240.65
"""
        self.assert_equal(
            portfolio_df_str, expected_portfolio_df_str, fuzzy_match=True
        )
        #
        stats_df_str = hpandas.df_to_str(
            stats_df, num_rows=None, precision=precision
        )
        expected_stats_df_str = r"""
                                 pnl  gross_volume  net_volume       gmv        nmv
2022-01-03 09:40:00-05:00        NaN           NaN         NaN       NaN        NaN
2022-01-03 09:45:00-05:00       0.00      9.99e+05   738046.51  9.99e+05  738046.51
2022-01-03 09:50:00-05:00      99.39      1.04e+06  -773979.43  1.00e+06  -35833.52
2022-01-03 09:55:00-05:00    -278.06      9.64e+05  -200690.59  1.00e+06 -236802.17
2022-01-03 10:00:00-05:00    1385.12      1.21e+05  -120770.11  9.98e+05 -356187.17"""
        self.assert_equal(stats_df_str, expected_stats_df_str, fuzzy_match=True)

    def test_apply_trimming_no_optional(self) -> None:
        """
        Test with no optional columns.
        """
        # Generate test data.
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        # Apply trimming.
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
        )
        precision = 2
        # Process data.
        actual = forecast_evaluator._apply_trimming(data)
        actual = hpandas.df_to_str(actual, num_rows=None, precision=precision)
        expected = r"""
                            price volatility prediction
                              101        101        101
2022-01-03 09:40:00-05:00  998.17   7.25e-04   8.58e-04
2022-01-03 09:45:00-05:00  997.39   7.57e-04   4.75e-04
2022-01-03 09:50:00-05:00  997.66   6.02e-04  -4.51e-04
2022-01-03 09:55:00-05:00  997.41   5.07e-04  -7.55e-04
2022-01-03 10:00:00-05:00  997.54   4.27e-04  -8.15e-04
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_apply_trimming_optional_col1(self) -> None:
        """
        Test with two unique optional columns.
        """
        # Generate test data.
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        # Add optional columns with cloning the existing columns.
        buy_price = pd.concat([data["price"]], keys=["buy_price"], axis=1)
        sell_price = pd.concat([data["price"]], keys=["sell_price"], axis=1)
        data = pd.concat([data, buy_price, sell_price], axis=1)
        # Apply trimming.
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            buy_price_col="buy_price",
            sell_price_col="sell_price",
        )
        precision = 2
        # Process data.
        actual = forecast_evaluator._apply_trimming(data)
        actual = hpandas.df_to_str(actual, num_rows=None, precision=precision)
        expected = r"""
                            price volatility prediction buy_price sell_price
                              101        101        101       101        101
2022-01-03 09:40:00-05:00  998.17   7.25e-04   8.58e-04    998.17     998.17
2022-01-03 09:45:00-05:00  997.39   7.57e-04   4.75e-04    997.39     997.39
2022-01-03 09:50:00-05:00  997.66   6.02e-04  -4.51e-04    997.66     997.66
2022-01-03 09:55:00-05:00  997.41   5.07e-04  -7.55e-04    997.41     997.41
2022-01-03 10:00:00-05:00  997.54   4.27e-04  -8.15e-04    997.54     997.54
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_apply_trimming_optional_col2(self) -> None:
        """
        Test with optional columns duplicating the existing columns.
        """
        # Generate test data.
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        # Add optional columns with cloning the existing columns.
        sell_price = pd.concat([data["price"]], keys=["sell_price"], axis=1)
        data = pd.concat([data, sell_price], axis=1)
        # Apply trimming.
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            buy_price_col="prediction",
            sell_price_col="sell_price",
        )
        precision = 2
        # Process data.
        actual = forecast_evaluator._apply_trimming(data)
        actual = hpandas.df_to_str(actual, num_rows=None, precision=precision)
        expected = r"""
                            price volatility prediction sell_price
                              101        101        101        101
2022-01-03 09:40:00-05:00  998.17   7.25e-04   8.58e-04     998.17
2022-01-03 09:45:00-05:00  997.39   7.57e-04   4.75e-04     997.39
2022-01-03 09:50:00-05:00  997.66   6.02e-04  -4.51e-04     997.66
2022-01-03 09:55:00-05:00  997.41   5.07e-04  -7.55e-04     997.41
2022-01-03 10:00:00-05:00  997.54   4.27e-04  -8.15e-04     997.54
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
