import io
import logging
import pprint
from typing import List

import numpy as np
import pandas as pd

import core.finance.bid_ask as cfibiask
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_process_bid_ask(hunitest.TestCase):
    def helper(self, expected_txt: str, requested_cols: List[str]) -> None:
        """
        Initialize a test DataFrame and compare against expected outcome.
        """
        bid_col = "bid"
        ask_col = "ask"
        bid_volume_col = "bid_volume"
        ask_volume_col = "ask_volume"
        df = self._get_df()
        actual = cfibiask.process_bid_ask(
            df,
            bid_col,
            ask_col,
            bid_volume_col,
            ask_volume_col,
            requested_cols=requested_cols,
        )
        expected = pd.read_csv(
            io.StringIO(expected_txt), index_col=0, parse_dates=True
        )
        np.testing.assert_allclose(actual, expected)

    def test_mid(self) -> None:
        requested_cols = ["mid"]
        expected_txt = """
datetime,mid
2016-01-04 12:00:00,100.015
2016-01-04 12:01:00,100.015
2016-01-04 12:02:00,100.000
2016-01-04 12:03:00,100.000
"""
        self.helper(expected_txt, requested_cols)

    def test_geometric_mid(self) -> None:
        requested_cols = ["geometric_mid"]
        expected_txt = """
datetime,geometric_mid
2016-01-04 12:00:00,100.01499987501875
2016-01-04 12:01:00,100.01499987501875
2016-01-04 12:02:00,99.9999995
2016-01-04 12:03:00,99.99999799999998
"""
        self.helper(expected_txt, requested_cols)

    def test_quoted_spread(self) -> None:
        requested_cols = ["quoted_spread"]
        expected_txt = """
datetime,quoted_spread
2016-01-04 12:00:00,0.01
2016-01-04 12:01:00,0.01
2016-01-04 12:02:00,0.02
2016-01-05 12:02:00,0.04
"""
        self.helper(expected_txt, requested_cols)

    def test_relative_spread(self) -> None:
        requested_cols = ["relative_spread"]
        expected_txt = """
datetime,relative_spread
2016-01-04 12:00:00,9.998500224957161e-05
2016-01-04 12:01:00,9.998500224957161e-05
2016-01-04 12:02:00,0.00020000000000010233
2016-01-04 12:03:00,0.00039999999999992044
"""
        self.helper(expected_txt, requested_cols)

    def test_log_relative_spread(self) -> None:
        requested_cols = ["log_relative_spread"]
        expected_txt = """
datetime,log_relative_spread
2016-01-04 12:00:00,9.998500233265872e-05
2016-01-04 12:01:00,9.998500233265872e-05
2016-01-04 12:02:00,0.00020000000066744406
2016-01-04 12:03:00,0.00040000000533346736
"""
        self.helper(expected_txt, requested_cols)

    def test_weighted_mid(self) -> None:
        requested_cols = ["weighted_mid"]
        expected_txt = """
datetime,weighted_mid
2016-01-04 12:00:00,100.015
2016-01-04 12:01:00,100.014
2016-01-04 12:02:00,100.000
2016-01-04 12:03:00,99.993333
"""
        self.helper(expected_txt, requested_cols)

    def test_order_book_imbalance(self) -> None:
        requested_cols = ["order_book_imbalance"]
        self._get_df()
        expected_txt = """
datetime,order_book_imbalance
2016-01-04 12:00:00,0.5
2016-01-04 12:01:00,0.4
2016-01-04 12:02:00,0.5
2016-01-04 12:03:00,0.3333333333
"""
        self.helper(expected_txt, requested_cols)

    def test_centered_order_book_imbalance(self) -> None:
        requested_cols = ["centered_order_book_imbalance"]
        expected_txt = """
datetime,centered_order_book_imbalance
2016-01-04 12:00:00,0.0
2016-01-04 12:01:00,-0.1999999999
2016-01-04 12:02:00,0.0
2016-01-04 12:03:00,-0.3333333333
"""
        self.helper(expected_txt, requested_cols)

    def test_log_order_book_imbalance(self) -> None:
        requested_cols = ["log_order_book_imbalance"]
        expected_txt = """
datetime,centered_order_book_imbalance
2016-01-04 12:00:00,0.0
2016-01-04 12:01:00,-0.405465108
2016-01-04 12:02:00,0.0
2016-01-04 12:03:00,-0.693147181
"""
        self.helper(expected_txt, requested_cols)

    def test_bid_value(self) -> None:
        requested_cols = ["bid_value"]
        self._get_df()
        expected_txt = """
datetime,bid_value
2016-01-04 12:00:00,20002.0
2016-01-04 12:01:00,20002.0
2016-01-04 12:02:00,29997.0
2016-01-04 12:03:00,19996.0
"""
        self.helper(expected_txt, requested_cols)

    def test_ask_value(self) -> None:
        requested_cols = ["ask_value"]
        expected_txt = """
datetime,ask_value
2016-01-04 12:00:00,20004.0
2016-01-04 12:01:00,30006.0
2016-01-04 12:02:00,30003.0
2016-01-04 12:03:00,40008.0
"""
        self.helper(expected_txt, requested_cols)

    def test_mid_value(self) -> None:
        requested_cols = ["mid_value"]
        expected_txt = """
datetime,mid_value
2016-01-04 12:00:00,20003.0
2016-01-04 12:01:00,25004.0
2016-01-04 12:02:00,30000.0
2016-01-04 12:03:00,30002.0
"""
        self.helper(expected_txt, requested_cols)

    def test_multiindex(self) -> None:
        """
        Verify that the bid/ask feature functions work with multiindex.
        """
        requested_cols = None
        bid_col = "bid"
        ask_col = "ask"
        bid_volume_col = "bid_volume"
        ask_volume_col = "ask_volume"
        df = self._get_df(multiindex=True)
        actual = cfibiask.process_bid_ask(
            df,
            bid_col,
            ask_col,
            bid_volume_col,
            ask_volume_col,
            requested_cols=requested_cols,
        )
        expected = r"""               ask_value                    bid_value                centered_order_book_imbalance            geometric_mid             log_order_book_imbalance            log_relative_spread                   mid                 mid_value                order_book_imbalance            quoted_spread            relative_spread            weighted_mid
              3303714233     8968126878    3303714233     8968126878                    3303714233 8968126878    3303714233  8968126878               3303714233 8968126878          3303714233 8968126878 3303714233  8968126878    3303714233     8968126878           3303714233 8968126878    3303714233 8968126878      3303714233 8968126878   3303714233  8968126878
2022-11-02  2.203589e+06  629831.626203  1.822814e+06  454799.188200                     -0.094458  -0.161245      0.385073  319.837510                -0.189481  -0.325329            0.000225   0.000268   0.385073  319.837513  2.013201e+06  542315.407201             0.452771   0.419378      0.000087   0.085686        0.000225   0.000268     0.385069  319.830605
2022-11-03  1.769897e+06  856610.415704  2.535700e+06  413330.404898                      0.177949  -0.349053      0.385128  319.891286                 0.359727  -0.728730            0.000179   0.000005   0.385128  319.891286  2.152799e+06  634970.410301             0.588974   0.325473      0.000069   0.001742        0.000179   0.000005     0.385134  319.890982
"""
        actual = actual.sort_index(axis=1)
        actual = hpandas.df_to_str(actual)
        self.assert_equal(actual, expected)

    @staticmethod
    def _get_df(*, multiindex: bool = False) -> pd.DataFrame:
        """
        Generate a test DataFrame.

        :param multiindex: create a DataFrame with a wide multiindex
        """
        if not multiindex:
            txt = """
    datetime,bid,ask,bid_volume,ask_volume
    2016-01-04 12:00:00,100.01,100.02,200,200
    2016-01-04 12:01:00,100.01,100.02,200,300
    2016-01-04 12:02:00,99.99,100.01,300,300
    2016-01-04 12:03:00,99.98,100.02,200,400
    """
            df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        else:
            df_dict = {
                ("ask", 3303714233): {
                    pd.Timestamp("2022-11-02"): 0.38511623,
                    pd.Timestamp("2022-11-03"): 0.38516256,
                },
                ("ask", 8968126878): {
                    pd.Timestamp("2022-11-02"): 319.88035623,
                    pd.Timestamp("2022-11-03"): 319.89215654,
                },
                ("ask_volume", 3303714233): {
                    pd.Timestamp("2022-11-02"): 5721881.0,
                    pd.Timestamp("2022-11-03"): 4595196.0,
                },
                ("ask_volume", 8968126878): {
                    pd.Timestamp("2022-11-02"): 1968.96,
                    pd.Timestamp("2022-11-03"): 2677.81,
                },
                ("bid", 3303714233): {
                    pd.Timestamp("2022-11-02"): 0.38502958,
                    pd.Timestamp("2022-11-03"): 0.3850937,
                },
                ("bid", 8968126878): {
                    pd.Timestamp("2022-11-02"): 319.79467022,
                    pd.Timestamp("2022-11-03"): 319.89041475,
                },
                ("bid_volume", 3303714233): {
                    pd.Timestamp("2022-11-02"): 4734217.0,
                    pd.Timestamp("2022-11-03"): 6584631.0,
                },
                ("bid_volume", 8968126878): {
                    pd.Timestamp("2022-11-02"): 1422.16,
                    pd.Timestamp("2022-11-03"): 1292.1,
                },
            }
            df = pd.DataFrame(df_dict)
        return df


class Test_transform_bid_ask_long_data_to_wide(hunitest.TestCase):
    """
    Apply the test data from `get_df_with_long_levels()` to check that the
    output is in wide form.
    """

    def get_df_with_long_levels(
        self, symbols: list, levels: list
    ) -> pd.DataFrame:
        timestamp_index = [
            pd.Timestamp("2022-09-08 21:01:00+00:00"),
            pd.Timestamp("2022-09-09 21:01:00+00:00"),
            pd.Timestamp("2022-09-10 21:01:00+00:00"),
        ]
        knowledge_timestamp = [
            pd.Timestamp("2022-09-08 21:01:15+00:00"),
            pd.Timestamp("2022-09-08 21:01:15+00:00"),
            pd.Timestamp("2022-09-08 21:01:15+00:00"),
        ]
        values = {
            "level": levels,
            "currency_pair": symbols,
            "bid_price": pd.Series([2.31, 3.22, 2.33]),
            "bid_size": pd.Series([1.1, 2.2, 3.3]),
            "ask_price": pd.Series([2.34, 3.24, 2.35]),
            "ask_size": pd.Series([4.4, 5.5, 6.6]),
            "knowledge_timestamp": knowledge_timestamp,
            "timestamp": timestamp_index,
            "half_spread": pd.Series([0.005, 0.02, 0.02]),
            "log_size": pd.Series([0.01, 0.03, 0.01]),
        }
        df = pd.DataFrame(data=values)
        df = df.set_index("timestamp")
        return df

    def test1(self) -> None:
        """
        Test transformation with one symbol and one level.
        """
        symbols = ["XRP_USDT", "XRP_USDT", "XRP_USDT"]
        levels = [1, 1, 1]
        expected_outcome = r"""
        currency_pair knowledge_timestamp bid_price_l1 bid_size_l1 ask_price_l1 ask_size_l1 half_spread_l1 log_size_l1
        timestamp
        2022-09-08 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 2.31 1.1 2.34 4.4 0.005 0.01
        2022-09-09 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 3.22 2.2 3.24 5.5 0.020 0.03
        2022-09-10 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 2.33 3.3 2.35 6.6 0.020 0.01
        """
        self._test(symbols, levels, expected_outcome=expected_outcome)

    def test2(self) -> None:
        """
        Test transformation with multiple symbols and one level with default
        argument value of `value_col_prefixes`.
        """
        symbols = ["UNFI_USDT", "WAVES_USDT", "XRP_USDT"]
        levels = [1, 1, 1]
        expected_outcome = r"""
        currency_pair knowledge_timestamp bid_price_l1 bid_size_l1 ask_price_l1 ask_size_l1 half_spread_l1 log_size_l1
        timestamp
        2022-09-08 21:01:00+00:00 UNFI_USDT 2022-09-08 21:01:15+00:00 2.31 1.1 2.34 4.4 0.005 0.01
        2022-09-09 21:01:00+00:00 WAVES_USDT 2022-09-08 21:01:15+00:00 3.22 2.2 3.24 5.5 0.020 0.03
        2022-09-10 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 2.33 3.3 2.35 6.6 0.020 0.01
        """
        self._test(symbols, levels, expected_outcome=expected_outcome)

    def test3(self) -> None:
        """
        Test transformation with one symbol and multiple levels with custom
        argument value of `value_col_prefixes`.
        """
        symbols = ["XRP_USDT", "XRP_USDT", "XRP_USDT"]
        levels = [1, 2, 3]
        extra_col = [0.01, 0.03, 0.01]
        expected_outcome = r"""
        currency_pair knowledge_timestamp bid_price_l1 bid_price_l2 bid_price_l3 bid_size_l1 bid_size_l2 bid_size_l3 ask_price_l1 ask_price_l2 ask_price_l3 ask_size_l1 ask_size_l2 ask_size_l3 half_spread_l1 half_spread_l2 half_spread_l3 log_size_l1 log_size_l2 log_size_l3 new_close_l1 new_close_l2 new_close_l3
        timestamp
        2022-09-08 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 2.31 NaN NaN 1.1 NaN NaN 2.34 NaN NaN 4.4 NaN NaN 0.005 NaN NaN 0.01 NaN NaN 0.01 NaN NaN
        2022-09-09 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 NaN 3.22 NaN NaN 2.2 NaN NaN 3.24 NaN NaN 5.5 NaN NaN 0.02 NaN NaN 0.03 NaN NaN 0.03 NaN
        2022-09-10 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 NaN NaN 2.33 NaN NaN 3.3 NaN NaN 2.35 NaN NaN 6.6 NaN NaN 0.02 NaN NaN 0.01 NaN NaN 0.01
        """
        self._test(
            symbols,
            levels,
            value_col_prefixes=["new", "log", "half"],
            expected_outcome=expected_outcome,
            extra_col=extra_col,
        )

    def test4(self) -> None:
        """
        Test transformation with multiple symbols and multiple levels with
        default argument value of `value_col_prefixes`.
        """
        symbols = ["UNFI_USDT", "WAVES_USDT", "XRP_USDT"]
        levels = [1, 2, 3]
        expected_outcome = r"""
        currency_pair knowledge_timestamp bid_price_l1 bid_price_l2 bid_price_l3 bid_size_l1 bid_size_l2 bid_size_l3 ask_price_l1 ask_price_l2 ask_price_l3 ask_size_l1 ask_size_l2 ask_size_l3 half_spread_l1 half_spread_l2 half_spread_l3 log_size_l1 log_size_l2 log_size_l3
        timestamp
        2022-09-08 21:01:00+00:00 UNFI_USDT 2022-09-08 21:01:15+00:00 2.31 NaN NaN 1.1 NaN NaN 2.34 NaN NaN 4.4 NaN NaN 0.005 NaN NaN 0.01 NaN NaN
        2022-09-09 21:01:00+00:00 WAVES_USDT 2022-09-08 21:01:15+00:00 NaN 3.22 NaN NaN 2.2 NaN NaN 3.24 NaN NaN 5.5 NaN NaN 0.02 NaN NaN 0.03 NaN
        2022-09-10 21:01:00+00:00 XRP_USDT 2022-09-08 21:01:15+00:00 NaN NaN 2.33 NaN NaN 3.3 NaN NaN 2.35 NaN NaN 6.6 NaN NaN 0.02 NaN NaN 0.01
        """
        self._test(symbols, levels, expected_outcome=expected_outcome)

    def test5(self) -> None:
        """
        Test transformation with multiple symbols and one level with custom
        argument value of `value_col_prefixes`.
        """
        symbols = ["UNFI_USDT", "WAVES_USDT", "XRP_USDT"]
        levels = [1, 1, 1]
        extra_col = [0.01, 0.03, 0.01]
        expected_outcome = r"""
        currency_pair  knowledge_timestamp  bid_price_l1  bid_size_l1  ask_price_l1  ask_size_l1  half_spread_l1  log_size_l1  new_close_l1
        timestamp
        2022-09-08 21:01:00+00:00  UNFI_USDT  2022-09-08 21:01:15+00:00  2.31  1.1  2.34  4.4  0.005  0.01  0.01
        2022-09-09 21:01:00+00:00  WAVES_USDT  2022-09-08 21:01:15+00:00  3.22  2.2  3.24  5.5  0.020  0.03  0.03
        2022-09-10 21:01:00+00:00  XRP_USDT  2022-09-08 21:01:15+00:00  2.33  3.3  2.35  6.6  0.020  0.01  0.01
        """
        self._test(
            symbols,
            levels,
            value_col_prefixes=["new", "log", "half"],
            expected_outcome=expected_outcome,
            extra_col=extra_col,
        )

    def _test(
        self,
        symbols: list,
        levels: list,
        value_col_prefixes: list = None,
        expected_outcome: str = None,
        extra_col: list = None,
    ) -> None:
        long_levels_df = self.get_df_with_long_levels(symbols, levels)
        if extra_col is not None:
            long_levels_df["new_close"] = extra_col
        #
        timestamp_col = "timestamp"
        wide_levels_df = cfibiask.transform_bid_ask_long_data_to_wide(
            long_levels_df, timestamp_col, value_col_prefixes=value_col_prefixes
        )
        #
        actual_df = hpandas.df_to_str(wide_levels_df)
        self.assert_equal(
            actual_df,
            expected_outcome,
            dedent=True,
            fuzzy_match=True,
        )


class Test_get_bid_ask_columns_by_level(hunitest.TestCase):
    def test_level_1(self) -> None:
        """
        Test that the function `get_bid_ask_columns_by_level` returns the
        expected columns for a level 1.
        """
        level = 1
        actual_outcome = pprint.pformat(
            cfibiask.get_bid_ask_columns_by_level(level)
        )
        self.check_string(actual_outcome)

    def test_level_3(self) -> None:
        """
        Test that the function `get_bid_ask_columns_by_level` returns the
        expected columns for a level 3.
        """
        level = 3
        actual_outcome = pprint.pformat(
            cfibiask.get_bid_ask_columns_by_level(level)
        )
        self.check_string(actual_outcome)
