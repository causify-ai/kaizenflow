import logging

import numpy as np
import pandas as pd

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import research_amp.cc.algotrading as ramccalg

_LOG = logging.getLogger(__name__)


class TestAlgotrading1(hunitest.TestCase):
    @staticmethod
    def get_test_dataframe() -> pd.DataFrame:
        """
        Create a DataFrame with columns required for algotrading transforms.
        """
        df = pd.DataFrame.from_dict(
            {
                pd.Timestamp("2022-12-13 19:00:00-0500", tz="America/New_York"): {
                    "ask_value": 53805.9582,
                    "bid_value": 25894.324,
                    "mid": 0.31405,
                    "ask_price": 0.3141,
                    "ask_size": 171302.0,
                    "bid_price": 0.314,
                    "bid_size": 82466.0,
                    "full_symbol": "binance::ADA_USDT",
                    "knowledge_timestamp": pd.Timestamp(
                        "2022-12-15 11:01:35.784679+0000", tz="UTC"
                    ),
                    "start_ts": pd.Timestamp(
                        "2022-12-13 18:59:00-0500", tz="America/New_York"
                    ),
                    "limit_buy_price": np.nan,
                    "limit_sell_price": np.nan,
                    "is_buy": False,
                    "is_sell": False,
                    "exec_buy_price": 0.4,
                    "exec_sell_price": 0.4,
                },
                pd.Timestamp("2022-12-13 19:00:01-0500", tz="America/New_York"): {
                    "ask_value": 53805.9582,
                    "bid_value": 25807.032,
                    "mid": 0.31405,
                    "ask_price": 0.3141,
                    "ask_size": 171302.0,
                    "bid_price": 0.314,
                    "bid_size": 82188.0,
                    "full_symbol": "binance::ADA_USDT",
                    "knowledge_timestamp": pd.Timestamp(
                        "2022-12-15 11:01:35.784679+0000", tz="UTC"
                    ),
                    "start_ts": pd.Timestamp(
                        "2022-12-13 18:59:01-0500", tz="America/New_York"
                    ),
                    "limit_buy_price": np.nan,
                    "limit_sell_price": np.nan,
                    "is_buy": False,
                    "is_sell": False,
                    "exec_buy_price": 0.4,
                    "exec_sell_price": 0.4,
                },
                pd.Timestamp("2022-12-13 19:00:03-0500", tz="America/New_York"): {
                    "ask_value": 53798.1057,
                    "bid_value": 25807.032,
                    "mid": 0.31405,
                    "ask_price": 0.3141,
                    "ask_size": 171277.0,
                    "bid_price": 0.314,
                    "bid_size": 82188.0,
                    "full_symbol": "binance::ADA_USDT",
                    "knowledge_timestamp": pd.Timestamp(
                        "2022-12-15 11:01:35.784679+0000", tz="UTC"
                    ),
                    "start_ts": pd.Timestamp(
                        "2022-12-13 18:59:03-0500", tz="America/New_York"
                    ),
                    "limit_buy_price": np.nan,
                    "limit_sell_price": np.nan,
                    "is_buy": False,
                    "is_sell": False,
                    "exec_buy_price": 0.4,
                    "exec_sell_price": 0.4,
                },
            },
            orient="index",
        )
        return df

    def test_add_limit_order_prices1(self) -> None:
        """
        Verify that limit order prices are calculated correctly.
        """
        df = self.get_test_dataframe()
        # Drop irrelevant columns.
        df = df.drop(["limit_buy_price", "limit_sell_price"], axis=1)
        # .
        mid_col_name = "mid"
        debug_mode = False
        abs_spread = 0.001
        out_df = ramccalg.add_limit_order_prices(
            df, mid_col_name, debug_mode, abs_spread=abs_spread
        )
        # Check result.
        actual = hpandas.df_to_str(out_df)
        self.check_string(actual)

    def test_compute_repricing_df1(self) -> None:
        """
        Verify that execution prices are calculated correctly.
        """
        df = self.get_test_dataframe()
        # Drop irrelevant columns.
        df = df.drop(["exec_buy_price", "exec_sell_price"], axis=1)
        report_stats = False
        out_df = ramccalg.compute_repricing_df(df, report_stats)
        actual = hpandas.df_to_str(out_df)
        self.check_string(actual)

    def test_compute_execution_df1(self) -> None:
        """
        Verify that the number of successful trades is calculated correctly.
        """
        df = self.get_test_dataframe()
        report_stats = False
        out_df = ramccalg.compute_execution_df(df, report_stats)
        actual = hpandas.df_to_str(out_df)
        self.check_string(actual)
