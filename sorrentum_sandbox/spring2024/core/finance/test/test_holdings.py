import logging

import numpy as np
import pandas as pd

import core.finance.holdings as cfinhold
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_quantize_holdings(hunitest.TestCase):
    @staticmethod
    def get_holdings() -> pd.DataFrame:
        index = pd.date_range(
            "2000-01-01 09:35:00",
            "2000-01-01 10:05:00",
            freq="5T",
            tz="America/New_York",
        )
        shares = [
            [0.00, 0.00],
            [-49.90, 100.10],
            [-50.00, 100.00],
            [-50.01, 99.00],
            [-99.00, 50.01],
            [-100.00, 50.00],
            [-100.10, 49.90],
        ]
        columns = [101, 202]
        holdings = pd.DataFrame(shares, index, columns)
        return holdings

    def test_no_quantization(self) -> None:
        holdings = self.get_holdings()
        quantization = 30
        holdings = cfinhold.quantize_holdings(holdings, quantization)
        actual = hpandas.df_to_str(holdings, num_rows=None)
        expected = r"""
                              101     202
2000-01-01 09:35:00-05:00    0.00    0.00
2000-01-01 09:40:00-05:00  -49.90  100.10
2000-01-01 09:45:00-05:00  -50.00  100.00
2000-01-01 09:50:00-05:00  -50.01   99.00
2000-01-01 09:55:00-05:00  -99.00   50.01
2000-01-01 10:00:00-05:00 -100.00   50.00
2000-01-01 10:05:00-05:00 -100.10   49.90"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_round_to_nearest_share(self) -> None:
        holdings = self.get_holdings()
        quantization = 0
        holdings = cfinhold.quantize_holdings(holdings, quantization)
        actual = hpandas.df_to_str(holdings, num_rows=None)
        expected = r"""
                             101    202
2000-01-01 09:35:00-05:00    0.0    0.0
2000-01-01 09:40:00-05:00  -50.0  100.0
2000-01-01 09:45:00-05:00  -50.0  100.0
2000-01-01 09:50:00-05:00  -50.0   99.0
2000-01-01 09:55:00-05:00  -99.0   50.0
2000-01-01 10:00:00-05:00 -100.0   50.0
2000-01-01 10:05:00-05:00 -100.0   50.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_round_to_nearest_lot(self) -> None:
        holdings = self.get_holdings()
        quantization = -2
        holdings = cfinhold.quantize_holdings(holdings, quantization)
        actual = hpandas.df_to_str(
            holdings, handle_signed_zeros=True, num_rows=None
        )
        expected = r"""
                             101    202
2000-01-01 09:35:00-05:00    0.0    0.0
2000-01-01 09:40:00-05:00    0.0  100.0
2000-01-01 09:45:00-05:00    0.0  100.0
2000-01-01 09:50:00-05:00 -100.0  100.0
2000-01-01 09:55:00-05:00 -100.0  100.0
2000-01-01 10:00:00-05:00 -100.0    0.0
2000-01-01 10:05:00-05:00 -100.0    0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_adjust_holdings_for_overnight(hunitest.TestCase):
    @staticmethod
    def get_holdings_and_price() -> pd.DataFrame:
        """
        Generate holdings and prices for two assets.

        Asset 101 experiences an overnight drop in price.
        Asset 201 has a 3-for-1 split.

        The assumption on overnight adjustments is that only the
        beginning-of-day holdings need to be adjusted. Behind this assumption
        is the implicit calculation of holdings from "target holdings" based
        on target dollar positions and point-in-time prices. This means that
        beginning-of-day "holdings" are calculated from the previous day's
        prices, whereas intraday holdings are calculated using the current
        day's prices (and so do not need adjustment).
        """
        index = [
            pd.Timestamp("2000-01-01 14:30:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 15:00:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 15:30:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 16:00:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-02 09:30:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-02 10:00:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-02 10:30:00-05:00", tz="America/New_York"),
        ]
        shares = [
            [0.00, 0.00],
            [-49.90, 100.10],
            [np.nan, 100.00],
            [-50.01, 99.00],
            # See the docstring for notes on asset_id=202's bod holdings.
            [-99.00, 100.00],
            [-100.00, 305.00],
            [-100.10, 306.90],
        ]
        prices = [
            [0.00, 0.00],
            [92.91, 285.10],
            [np.nan, 290.05],
            [100.01, 300.00],
            [70.00, 100.00],
            [71.00, 115.50],
            [68.10, 110.90],
        ]
        columns = [101, 202]
        holdings = pd.DataFrame(shares, index, columns)
        price = pd.DataFrame(prices, index, columns)
        return holdings, price

    def test_liquidate_at_end_of_day(self) -> None:
        """
        Liquidate positions at final bar (no overnight holding).
        """
        holdings, price = self.get_holdings_and_price()
        #
        liquidate_at_end_of_day = True
        adjust_for_splits = False
        ffill_limit = 0
        holdings = cfinhold.adjust_holdings_for_overnight(
            holdings,
            price,
            liquidate_at_end_of_day,
            adjust_for_splits,
            ffill_limit,
        )
        actual = hpandas.df_to_str(
            holdings, handle_signed_zeros=True, num_rows=None
        )
        expected = r"""
                             101    202
2000-01-01 14:30:00-05:00    0.0    0.0
2000-01-01 15:00:00-05:00  -49.9  100.1
2000-01-01 15:30:00-05:00    NaN  100.0
2000-01-01 16:00:00-05:00    0.0    0.0
2000-01-02 09:30:00-05:00    0.0    0.0
2000-01-02 10:00:00-05:00 -100.0  305.0
2000-01-02 10:30:00-05:00    0.0    0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_liquidate_at_end_of_day_with_ffill(self) -> None:
        """
        Forward fill up to `ffill_limit` NaN's with last available holdings.
        """
        holdings, price = self.get_holdings_and_price()
        #
        liquidate_at_end_of_day = True
        adjust_for_splits = False
        ffill_limit = 1
        holdings = cfinhold.adjust_holdings_for_overnight(
            holdings,
            price,
            liquidate_at_end_of_day,
            adjust_for_splits,
            ffill_limit,
        )
        actual = hpandas.df_to_str(
            holdings, handle_signed_zeros=True, num_rows=None
        )
        expected = r"""
                             101    202
2000-01-01 14:30:00-05:00    0.0    0.0
2000-01-01 15:00:00-05:00  -49.9  100.1
2000-01-01 15:30:00-05:00  -49.9  100.0
2000-01-01 16:00:00-05:00    0.0    0.0
2000-01-02 09:30:00-05:00    0.0    0.0
2000-01-02 10:00:00-05:00 -100.0  305.0
2000-01-02 10:30:00-05:00    0.0    0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_adjust_for_splits(self) -> None:
        """
        Adjust for 202's 3-for-1 split.

        See docstring for `get_holdings_and_price()` for underlying
        assumptions.
        """
        holdings, price = self.get_holdings_and_price()
        #
        liquidate_at_end_of_day = False
        adjust_for_splits = True
        ffill_limit = 0
        holdings = cfinhold.adjust_holdings_for_overnight(
            holdings,
            price,
            liquidate_at_end_of_day,
            adjust_for_splits,
            ffill_limit,
        )
        actual = hpandas.df_to_str(holdings, num_rows=None)
        expected = r"""
                              101    202
2000-01-01 14:30:00-05:00     NaN    NaN
2000-01-01 15:00:00-05:00  -49.90  100.1
2000-01-01 15:30:00-05:00     NaN  100.0
2000-01-01 16:00:00-05:00  -50.01   99.0
2000-01-02 09:30:00-05:00  -50.01  297.0
2000-01-02 10:00:00-05:00 -100.00  305.0
2000-01-02 10:30:00-05:00 -100.10  306.9"""
        self.assert_equal(actual, expected, fuzzy_match=True)
