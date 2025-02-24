import logging
from typing import List

import numpy as np
import pandas as pd
import pytest

import core.finance.ablation as cfinabla
import core.finance_data_example as cfidaexa
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

_LOG = logging.getLogger(__name__)


class TestForecastEvaluatorWithOptimizer1(hunitest.TestCase):
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

    @staticmethod
    def get_data2() -> pd.DataFrame:
        tz = "America/New_York"
        idx = [
            pd.Timestamp("2022-01-03 09:35:00", tz=tz),
            pd.Timestamp("2022-01-03 09:40:00", tz=tz),
            pd.Timestamp("2022-01-03 09:45:00", tz=tz),
            pd.Timestamp("2022-01-03 09:50:00", tz=tz),
        ]
        asset_ids = [100, 200]
        prediction_data = [
            [-0.25, -0.34],
            [0.13, 0.5],
            [0.84, -0.97],
            [0.86, -0.113],
        ]
        price_data = [
            [100.0, 100.3],
            [100.1, 100.5],
            [100.05, 100.4],
            [100.2, 100.5],
        ]
        volatility_data = [
            [0.00110, 0.00048],
            [0.00091, 0.00046],
            [0.00086, 0.00060],
            [0.00071, 0.00068],
        ]
        prediction_df = pd.DataFrame(prediction_data, idx, asset_ids)
        price_df = pd.DataFrame(price_data, idx, asset_ids)
        volatility_df = pd.DataFrame(volatility_data, idx, asset_ids)
        dag_df = pd.concat(
            {
                "price": price_df,
                "volatility": volatility_df,
                "prediction": prediction_df,
            },
            axis=1,
        )
        return dag_df

    @staticmethod
    def get_config_dict() -> dict:
        dict_ = {
            "dollar_neutrality_penalty": 0.0,
            "constant_correlation": 0.0,
            "constant_correlation_penalty": 0.0,
            "relative_holding_penalty": 0.0,
            "relative_holding_max_frac_of_gmv": 0.6,
            "target_gmv": 1e4,
            "target_gmv_upper_bound_penalty": 0.0,
            "target_gmv_hard_upper_bound_multiple": 1.00,
            "transaction_cost_penalty": 0.0,
            "solver": "ECOS",
        }
        return dict_

    def test_to_str1(self) -> None:
        data = self.get_data2()
        config_dict = self.get_config_dict()
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            optimizer_config_dict=config_dict,
        )
        actual = forecast_evaluator.to_str(
            data,
            quantization=0,
        )
        expected = r"""
# holdings_shares=
                            100   200
2022-01-03 09:35:00-05:00   0.0   0.0
2022-01-03 09:40:00-05:00 -60.0 -40.0
2022-01-03 09:45:00-05:00  40.0  60.0
2022-01-03 09:50:00-05:00   0.0   0.0
# holdings_notional=
                              100     200
2022-01-03 09:35:00-05:00     0.0     0.0
2022-01-03 09:40:00-05:00 -6006.0 -4020.0
2022-01-03 09:45:00-05:00  4002.0  6024.0
2022-01-03 09:50:00-05:00     0.0     0.0
# executed_trades_shares=
                             100    200
2022-01-03 09:35:00-05:00    0.0    0.0
2022-01-03 09:40:00-05:00  -60.0  -40.0
2022-01-03 09:45:00-05:00  100.0  100.0
2022-01-03 09:50:00-05:00  -40.0  -60.0
# executed_trades_notional=
                               100      200
2022-01-03 09:35:00-05:00      0.0      0.0
2022-01-03 09:40:00-05:00  -6006.0  -4020.0
2022-01-03 09:45:00-05:00  10005.0  10040.0
2022-01-03 09:50:00-05:00  -4008.0  -6030.0
# pnl=
                           100  200
2022-01-03 09:35:00-05:00  0.0  0.0
2022-01-03 09:40:00-05:00  0.0  0.0
2022-01-03 09:45:00-05:00  3.0  4.0
2022-01-03 09:50:00-05:00  6.0  6.0
# statistics=
                            pnl  gross_volume  net_volume      gmv      nmv
2022-01-03 09:35:00-05:00   0.0           0.0         0.0      0.0      0.0
2022-01-03 09:40:00-05:00   0.0       10026.0    -10026.0  10026.0 -10026.0
2022-01-03 09:45:00-05:00   7.0       20045.0     20045.0  10026.0  10026.0
2022-01-03 09:50:00-05:00  12.0       10038.0    -10038.0      0.0      0.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_1_asset(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101],
        )
        config_dict = self.get_config_dict()
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            optimizer_config_dict=config_dict,
        )
        actual = forecast_evaluator.to_str(
            data,
            quantization=0,
            liquidate_at_end_of_day=False,
        )
        expected = r"""
# holdings_shares=
                           101
2022-01-03 09:40:00-05:00  0.0
2022-01-03 09:45:00-05:00  6.0
2022-01-03 09:50:00-05:00  6.0
2022-01-03 09:55:00-05:00 -6.0
2022-01-03 10:00:00-05:00 -6.0
# holdings_notional=
                               101
2022-01-03 09:40:00-05:00     0.00
2022-01-03 09:45:00-05:00  5984.36
2022-01-03 09:50:00-05:00  5985.96
2022-01-03 09:55:00-05:00 -5984.47
2022-01-03 10:00:00-05:00 -5985.23
# executed_trades_shares=
                            101
2022-01-03 09:40:00-05:00   0.0
2022-01-03 09:45:00-05:00   6.0
2022-01-03 09:50:00-05:00   0.0
2022-01-03 09:55:00-05:00 -12.0
2022-01-03 10:00:00-05:00   0.0
# executed_trades_notional=
                                101
2022-01-03 09:40:00-05:00      0.00
2022-01-03 09:45:00-05:00   5984.36
2022-01-03 09:50:00-05:00      0.00
2022-01-03 09:55:00-05:00 -11968.94
2022-01-03 10:00:00-05:00      0.00
# pnl=
                            101
2022-01-03 09:40:00-05:00  0.00
2022-01-03 09:45:00-05:00  0.00
2022-01-03 09:50:00-05:00  1.60
2022-01-03 09:55:00-05:00 -1.49
2022-01-03 10:00:00-05:00 -0.76
# statistics=
                            pnl  gross_volume  net_volume      gmv      nmv
2022-01-03 09:40:00-05:00  0.00          0.00        0.00     0.00     0.00
2022-01-03 09:45:00-05:00  0.00       5984.36     5984.36  5984.36  5984.36
2022-01-03 09:50:00-05:00  1.60          0.00        0.00  5985.96  5985.96
2022-01-03 09:55:00-05:00 -1.49      11968.94   -11968.94  5984.47 -5984.47
2022-01-03 10:00:00-05:00 -0.76          0.00        0.00  5985.23 -5985.23
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_to_str_intraday_3_assets(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        config_dict = self.get_config_dict()
        config_dict["target_gmv"] = 1e5
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            optimizer_config_dict=config_dict,
        )
        actual = forecast_evaluator.to_str(
            data,
            quantization=0,
            liquidate_at_end_of_day=False,
        )
        expected = r"""
# holdings_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   0.0   0.0   0.0
2022-01-03 09:45:00-05:00  40.0   0.0 -60.0
2022-01-03 09:50:00-05:00  40.0 -60.0   0.0
2022-01-03 09:55:00-05:00 -40.0 -60.0   0.0
2022-01-03 10:00:00-05:00 -40.0 -60.0   0.0
# holdings_notional=
                                101       201       301
2022-01-03 09:40:00-05:00      0.00      0.00      0.00
2022-01-03 09:45:00-05:00  39895.73      0.00 -59854.81
2022-01-03 09:50:00-05:00  39906.38 -59850.07      0.00
2022-01-03 09:55:00-05:00 -39896.46 -59868.37      0.00
2022-01-03 10:00:00-05:00 -39901.51 -59757.61      0.00
# executed_trades_shares=
                            101   201   301
2022-01-03 09:40:00-05:00   0.0   0.0   0.0
2022-01-03 09:45:00-05:00  40.0   0.0 -60.0
2022-01-03 09:50:00-05:00   0.0 -60.0  60.0
2022-01-03 09:55:00-05:00 -80.0   0.0   0.0
2022-01-03 10:00:00-05:00   0.0   0.0   0.0
# executed_trades_notional=
                                101       201       301
2022-01-03 09:40:00-05:00      0.00      0.00      0.00
2022-01-03 09:45:00-05:00  39895.73      0.00 -59854.81
2022-01-03 09:50:00-05:00      0.00 -59850.07  59915.53
2022-01-03 09:55:00-05:00 -79792.93      0.00      0.00
2022-01-03 10:00:00-05:00      0.00      0.00      0.00
# pnl=
                             101     201    301
2022-01-03 09:40:00-05:00   0.00    0.00   0.00
2022-01-03 09:45:00-05:00   0.00    0.00   0.00
2022-01-03 09:50:00-05:00  10.65    0.00 -60.72
2022-01-03 09:55:00-05:00  -9.92  -18.30   0.00
2022-01-03 10:00:00-05:00  -5.05  110.75   0.00
# statistics=
                              pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 09:40:00-05:00    0.00          0.00        0.00      0.00      0.00
2022-01-03 09:45:00-05:00    0.00      99750.54   -19959.08  99750.54 -19959.08
2022-01-03 09:50:00-05:00  -50.06     119765.59       65.46  99756.45 -19943.69
2022-01-03 09:55:00-05:00  -28.22      79792.93   -79792.93  99764.83 -99764.83
2022-01-03 10:00:00-05:00  105.71          0.00        0.00  99659.12 -99659.12
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_save_portfolio_load_portfolio(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        config_dict = self.get_config_dict()
        config_dict["target_gmv"] = 1e5
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            optimizer_config_dict=config_dict,
        )
        #
        log_dir = self.get_scratch_space()
        _ = forecast_evaluator.save_portfolio(
            data,
            log_dir,
            target_gmv=1e5,
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
                            price                  volatility                     prediction                     holdings_shares             holdings_notional                     executed_trades_shares             executed_trades_notional                        pnl
                              101     201      301        101       201       301        101       201       301             101   201   301               101       201       301                    101   201   301                      101       201       301    101     201    301
2022-01-03 09:35:00-05:00  998.90  999.66   999.87        NaN       NaN       NaN   8.43e-04 -1.77e-04 -2.38e-04             NaN   NaN   NaN               NaN       NaN       NaN                    NaN   NaN   NaN                      NaN       NaN       NaN    NaN     NaN    NaN
2022-01-03 09:40:00-05:00  998.17  999.60   998.00   7.25e-04  5.14e-05  1.87e-03   8.58e-04  4.26e-04 -1.84e-03             0.0   0.0   0.0              0.00      0.00      0.00                    0.0   0.0   0.0                     0.00      0.00      0.00   0.00    0.00   0.00
2022-01-03 09:45:00-05:00  997.39  998.63   997.58   7.57e-04  7.29e-04  1.28e-03   4.75e-04 -9.85e-04  1.70e-04            40.0   0.0 -60.0          39895.73      0.00 -59854.81                   40.0   0.0 -60.0                 39895.73      0.00 -59854.81   0.00    0.00   0.00
2022-01-03 09:50:00-05:00  997.66  997.50   998.59   6.02e-04  9.21e-04  1.17e-03  -4.51e-04 -1.11e-03 -1.76e-04            40.0 -60.0   0.0          39906.38 -59850.07      0.00                    0.0 -60.0  60.0                     0.00 -59850.07  59915.53  10.65    0.00 -60.72
2022-01-03 09:55:00-05:00  997.41  997.81   999.57   5.07e-04  7.64e-04  1.11e-03  -7.55e-04 -7.61e-04  7.68e-05           -40.0 -60.0   0.0         -39896.46 -59868.37      0.00                  -80.0   0.0   0.0                -79792.93      0.00      0.00  -9.92  -18.30   0.00
2022-01-03 10:00:00-05:00  997.54  995.96  1000.20   4.27e-04  1.21e-03  9.87e-04  -8.15e-04  6.48e-04  1.54e-03           -40.0 -60.0   0.0         -39901.51 -59757.61      0.00                    0.0   0.0   0.0                     0.00      0.00      0.00  -5.05  110.75   0.00
"""
        self.assert_equal(
            portfolio_df_str, expected_portfolio_df_str, fuzzy_match=True
        )
        #
        stats_df_str = hpandas.df_to_str(
            stats_df, num_rows=None, precision=precision
        )
        expected_stats_df_str = r"""
                              pnl  gross_volume  net_volume       gmv       nmv
2022-01-03 09:40:00-05:00    0.00          0.00        0.00      0.00      0.00
2022-01-03 09:45:00-05:00    0.00      99750.54   -19959.08  99750.54 -19959.08
2022-01-03 09:50:00-05:00  -50.06     119765.59       65.46  99756.45 -19943.69
2022-01-03 09:55:00-05:00  -28.22      79792.93   -79792.93  99764.83 -99764.83
2022-01-03 10:00:00-05:00  105.71          0.00        0.00  99659.12 -99659.12
"""
        self.assert_equal(stats_df_str, expected_stats_df_str, fuzzy_match=True)


class TestForecastEvaluatorWithOptimizer2(hunitest.TestCase):
    @staticmethod
    def get_data(
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
        asset_ids: List[int],
        *,
        bar_duration: str = "30T",
    ) -> pd.DataFrame:
        df = cfidaexa.get_forecast_price_based_dataframe(
            start_datetime,
            end_datetime,
            asset_ids,
            bar_duration=bar_duration,
        )
        df = cfinabla.set_non_ath_to_nan(df)
        return df

    @staticmethod
    def get_config_dict() -> dict:
        dict_ = {
            "dollar_neutrality_penalty": 0.01,
            "constant_correlation": 0.5,
            "constant_correlation_penalty": 0.25,
            "relative_holding_penalty": 0.0,
            "relative_holding_max_frac_of_gmv": 0.8,
            "target_gmv": 1e5,
            "target_gmv_upper_bound_penalty": 0.0,
            "target_gmv_hard_upper_bound_multiple": 1.00,
            "transaction_cost_penalty": 0.001,
            "solver": "ECOS",
        }
        return dict_

    @pytest.mark.skip("Slightly different results on different machines.")
    def test_multiday(self) -> None:
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-05 16:00:00", tz="America/New_York"),
            asset_ids=[101, 201, 301],
        )
        config_dict = self.get_config_dict()
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            price_col="price",
            volatility_col="volatility",
            prediction_col="prediction",
            optimizer_config_dict=config_dict,
        )
        _, stats_df = forecast_evaluator.annotate_forecasts(
            data,
            quantization=0,
        )
        precision = 2
        actual = hpandas.df_to_str(stats_df.round(precision), precision=precision)
        expected = r"""
                            pnl  gross_volume  net_volume       gmv    nmv
2022-01-03 10:30:00-05:00  0.00          0.00        0.00      0.00   0.00
2022-01-03 11:00:00-05:00  0.00      25961.32       29.09  25961.32  29.09
2022-01-03 11:30:00-05:00  3.29          0.00        0.00  25971.53  32.38
...
2022-01-05 15:00:00-05:00  53.05          0.00        0.00  100283.46 -147.07
2022-01-05 15:30:00-05:00  59.23          0.00        0.00  100195.83  -87.84
2022-01-05 16:00:00-05:00 -36.72     100280.69      124.56       0.00    0.00
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
