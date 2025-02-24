import logging

import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.stats_computer as dtfmostcom
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestStatsComputer1(hunitest.TestCase):
    def test_compute_portfolio_stats1(self) -> None:
        sc = dtfmostcom.StatsComputer()
        portfolio_df = self._get_portfolio()
        df, _ = sc.compute_portfolio_stats(portfolio_df, "1T")
        actual = hpandas.df_to_str(
            df, handle_signed_zeros=True, num_rows=None, precision=2
        )
        expected = r"""
                                              0
ratios     sharpe_ratio                       5.68
           sharpe_ratio_standard_error        7.09
           sr.tval                            0.80
           sr.pval                            0.42
           kratio                            -0.47
dollar     gmv_mean                     1000000.00
           gmv_stdev                          0.00
           annualized_mean_return        229413.34
           annualized_volatility          40401.37
           max_drawdown                    7107.29
           pnl_mean                           1.46
           pnl_std                          102.07
           turnover_mean                  99997.96
           turnover_stdev                   310.89
           market_bias_mean                  -0.02
           market_bias_stdev                142.12
percentage annualized_mean_return            22.94
           annualized_volatility              4.04
           max_drawdown                       0.71
           pnl_mean                           0.00
           pnl_std                            0.01
           turnover_mean                     10.00
           turnover_stdev                     0.03
           market_bias_mean                   0.00
           market_bias_stdev                  0.01"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    @staticmethod
    def _get_portfolio(seed=1347) -> pd.DataFrame:
        start_timestamp = pd.Timestamp(
            "2001-01-03 09:30:00-05:00", tz="America/New_York"
        )
        end_timestamp = pd.Timestamp(
            "2001-01-10 16:00:00-05:00", tz="America/New_York"
        )
        df = cfidaexa.get_portfolio_bar_metrics_dataframe(
            start_timestamp,
            end_timestamp,
            bar_duration="1T",
            mean_turnover_percentage=10,
            seed=seed,
        )
        return df
