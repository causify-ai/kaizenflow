import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import oms.obsolete.pnl_simulator as oobpnsim

_LOG = logging.getLogger(__name__)


class TestPnlSimulatorFunctions1(hunitest.TestCase):
    def test_get_data1(self) -> None:
        """
        Freeze the output of `_get_data()` as reference for other unit tests.
        """
        df = self._get_data()
        actual_result = hpandas.df_to_str(df, num_rows=None)
        expected_result = """
                                  price         ask         bid    midpoint
        2021-09-12 09:30:00  100.496714  100.722490  100.381066  100.551778
        2021-09-12 09:31:00  100.358450  100.425978  100.057346  100.241662
        2021-09-12 09:32:00  101.006138  102.430887   99.527616  100.979251
        2021-09-12 09:33:00  102.529168  103.073551  101.809324  102.441438
        2021-09-12 09:34:00  102.295015  102.405937  101.834376  102.120157
        2021-09-12 09:35:00  102.060878  103.211871  101.003756  102.107814
        2021-09-12 09:36:00  103.640091  104.015789  103.296472  103.656131
        2021-09-12 09:37:00  104.407525  105.008164  102.644485  103.826325
        2021-09-12 09:38:00  103.938051  104.229745  103.613967  103.921856
        2021-09-12 09:39:00  104.480611  105.082318  104.095529  104.588923
        2021-09-12 09:40:00  104.017193  105.869472  103.340271  104.604872
        2021-09-12 09:41:00  103.551464  103.564961  102.939787  103.252374
        2021-09-12 09:42:00  103.793426  104.851137  102.762426  103.806782
        2021-09-12 09:43:00  101.880146  102.702691  100.948866  101.825778
        2021-09-12 09:44:00  100.155228  101.376072   99.316010  100.346041
        2021-09-12 09:45:00   99.592940   99.801804   99.283728   99.542766
        2021-09-12 09:46:00   98.580109  100.539779   98.248846   99.394313
        2021-09-12 09:47:00   98.894357  100.222543   97.918811   99.070677
        2021-09-12 09:48:00   97.986332   98.183194   97.507158   97.845176
        2021-09-12 09:49:00   96.574029   97.312495   96.388370   96.850433
        2021-09-12 09:50:00   98.039678   98.211046   96.933343   97.572194"""
        expected_result = hprint.dedent(expected_result)
        self.assert_equal(actual_result, expected_result)

    def test_get_twap_price1(self) -> None:
        """
        Test that TWAP is computed properly.
        """
        df = self._get_data()
        for use_cache in [True, False]:
            columns: Optional[List[str]]
            if use_cache:
                columns = ["price", "ask", "bid"]
            else:
                columns = None
            mi = oobpnsim.MarketInterface(df, use_cache, columns=columns)
            timestamp_start = pd.Timestamp("2021-09-12 09:30:00")
            timestamp_end = pd.Timestamp("2021-09-12 09:35:00")
            act = mi.get_twap_price(timestamp_start, timestamp_end, "price")
            #
            exp = df.loc[
                timestamp_start + pd.Timedelta(minutes=1) : timestamp_end
            ]["price"].mean()
            np.testing.assert_almost_equal(act, exp)
            #
            exp = (
                100.358450 + 101.006138 + 102.529168 + 102.295015 + 102.060878
            ) / 5.0
            np.testing.assert_almost_equal(act, exp)

    def test_order_price1(self) -> None:
        df = self._get_data()
        type_ = "price@start"
        num_shares = 100
        timestamp_start = pd.Timestamp("2021-09-12 09:30:00")
        exp: float = df.loc[timestamp_start]["price"]
        np.testing.assert_almost_equal(exp, 100.496714)
        self._test_order(type_, num_shares, exp)

    def test_order_price2(self) -> None:
        df = self._get_data()
        type_ = "price@end"
        num_shares = 100
        timestamp_start = pd.Timestamp("2021-09-12 09:35:00")
        exp = df.loc[timestamp_start]["price"]
        np.testing.assert_almost_equal(exp, 102.060878)
        self._test_order(type_, num_shares, exp)

    def test_order_price3(self) -> None:
        self._get_data()
        type_ = "price@twap"
        num_shares = 100
        exp = (
            100.358450 + 101.006138 + 102.529168 + 102.295015 + 102.060878
        ) / 5.0
        self._test_order(type_, num_shares, exp)

    def test_order_midpoint1(self) -> None:
        self._get_data()
        type_ = "midpoint@start"
        num_shares = 100
        exp = 100.551778
        self._test_order(type_, num_shares, exp)

    def test_order_midpoint2(self) -> None:
        self._get_data()
        type_ = "midpoint@end"
        num_shares = 100
        exp = 102.107814
        self._test_order(type_, num_shares, exp)

    def test_order_midpoint3(self) -> None:
        self._get_data()
        type_ = "midpoint@twap"
        num_shares = 100
        exp = (
            100.241662 + 100.979251 + 102.441438 + 102.120157 + 102.107814
        ) / 5.0
        self._test_order(type_, num_shares, exp)

    def test_order_full_spread1(self) -> None:
        self._get_data()
        type_ = "full_spread@end"
        num_shares = 100
        exp = 103.211871
        self._test_order(type_, num_shares, exp)

    def test_order_full_spread2(self) -> None:
        self._get_data()
        type_ = "full_spread@end"
        num_shares = -100
        exp = 101.003756
        self._test_order(type_, num_shares, exp)

    def test_order_full_spread3(self) -> None:
        self._get_data()
        type_ = "full_spread@twap"
        num_shares = 100
        exp = (100.425978 + 102.430887 + 103.073551 + 102.405937 + 103.211871) / 5
        self._test_order(type_, num_shares, exp)

    def test_order_full_spread4(self) -> None:
        self._get_data()
        type_ = "full_spread@twap"
        num_shares = -100
        exp = (100.057346 + 99.527616 + 101.809324 + 101.834376 + 101.003756) / 5
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread1(self) -> None:
        """
        Same as full_spread.
        """
        self._get_data()
        type_ = "partial_spread_1.0@twap"
        num_shares = 100
        exp = (100.425978 + 102.430887 + 103.073551 + 102.405937 + 103.211871) / 5
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread2(self) -> None:
        self._get_data()
        type_ = "partial_spread_1.0@twap"
        num_shares = -100
        exp = (100.057346 + 99.527616 + 101.809324 + 101.834376 + 101.003756) / 5
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread3(self) -> None:
        """
        Same as midpoint.
        """
        self._get_data()
        type_ = "partial_spread_0.5@twap"
        num_shares = 100
        exp = (
            100.425978
            + 100.057346
            + 102.430887
            + 99.527616
            + 103.073551
            + 101.809324
            + 102.405937
            + 101.834376
            + 103.211871
            + 101.003756
        ) / 10.0
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread4(self) -> None:
        self._get_data()
        type_ = "partial_spread_0.5@twap"
        num_shares = -100
        exp = (
            100.241662 + 100.979251 + 102.441438 + 102.120157 + 102.107814
        ) / 5.0
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread5(self) -> None:
        """
        No spread.
        """
        self._get_data()
        type_ = "partial_spread_0.0@twap"
        num_shares = 100
        exp = (
            100.057346 + 99.527616 + 101.809324 + 101.834376 + 101.003756
        ) / 5.0
        self._test_order(type_, num_shares, exp)

    def test_order_partial_spread6(self) -> None:
        self._get_data()
        type_ = "partial_spread_0.0@twap"
        num_shares = -100
        exp = (
            100.425978 + 102.430887 + 103.073551 + 102.405937 + 103.211871
        ) / 5.0
        self._test_order(type_, num_shares, exp)

    def _test_order(self, type_: str, num_shares: float, exp: float) -> None:
        df = self._get_data()
        for use_cache in [True, False]:
            columns: Optional[List[str]]
            if use_cache:
                columns = ["price", "ask", "bid", "midpoint"]
            else:
                columns = None
            mi = oobpnsim.MarketInterface(df, use_cache, columns=columns)
            timestamp_start = pd.Timestamp("2021-09-12 09:30:00")
            timestamp_end = pd.Timestamp("2021-09-12 09:35:00")
            order = oobpnsim.Order(
                mi, type_, timestamp_start, timestamp_end, num_shares
            )
            act = order.get_execution_price()
            np.testing.assert_almost_equal(act, exp, decimal=5)

    def _get_data(self) -> pd.DataFrame:
        """
        Return fixed random data for the other unit tests.
        """
        num_samples = 21
        seed = 42
        df = oobpnsim.get_random_market_data(num_samples, seed)
        df["midpoint"] = (df["ask"] + df["bid"]) / 2
        df = df.round(6)
        return df


# #############################################################################


def _compute_pnl_level2(
    self_: Any,
    df: pd.DataFrame,
    df_5mins: pd.DataFrame,
    initial_wealth: float,
    config: Dict[str, Any],
) -> pd.DataFrame:
    # Check that with / without cache we get the same results.
    use_cache = False
    columns = None
    mi = oobpnsim.MarketInterface(df, use_cache, columns)
    df_5mins_no_cache = oobpnsim.compute_pnl_level2(
        mi, df_5mins, initial_wealth, config
    )
    #
    use_cache = True
    columns = ["price"]
    mi = oobpnsim.MarketInterface(df, use_cache, columns)
    df_5mins = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
    self_.assert_equal(str(df_5mins_no_cache), str(df_5mins))
    pd.testing.assert_frame_equal(df_5mins_no_cache, df_5mins)
    return df_5mins


class TestPnlSimulator1(hunitest.TestCase):
    """
    Verify that computing PnL using `compute_pnl_level1()`, `compute_lag_pnl()`
    and `compute_pnl_level2()` yield the same results.
    """

    def test1(self) -> None:
        """
        Compute PnL on an handcrafted example.
        """
        df, df_5mins = oobpnsim.get_example_market_data1()
        # Execute.
        self._run(df, df_5mins)

    def test_random1(self) -> None:
        """
        Compute PnL on a random example.
        """
        num_samples = 5 * 3 + 1
        seed = 42
        df, df_5mins = oobpnsim.get_example_market_data2(num_samples, seed)
        # Execute.
        self._run(df, df_5mins)

    def test_random2(self) -> None:
        """
        Compute PnL on a random example.
        """
        num_samples = 5 * 10 + 1
        seed = 43
        df, df_5mins = oobpnsim.get_example_market_data2(num_samples, seed)
        # Execute.
        self._run(df, df_5mins)

    def test_random3(self) -> None:
        """
        Compute PnL on a random example.
        """
        num_samples = 5 * 20 + 1
        seed = 44
        df, df_5mins = oobpnsim.get_example_market_data2(num_samples, seed)
        # Execute.
        self._run(df, df_5mins)

    def _run(self, df: pd.DataFrame, df_5mins: pd.DataFrame) -> None:
        """
        Compute PnL using lag-based approach, level1 simulation, and level2
        simulation, checking that:

        - the intermediate PnL stream match
        - the total return from the different approaches matches
        """
        act = []
        act.append("df=\n%s" % hpandas.df_to_str(df, num_rows=None))
        act.append(
            "df_5mins=\n%s" % hpandas.df_to_str(df_5mins, num_rows=None)
        )
        # Compute pnl using simulation level 1.
        initial_wealth = 1000.0
        (
            final_w,
            tot_ret,
            df_5mins,
        ) = oobpnsim.compute_pnl_level1(initial_wealth, df, df_5mins)
        _ = final_w
        act.append("# tot_ret=%s" % tot_ret)
        act.append(
            "After pnl simulation level 1: df_5mins=\n%s"
            % hpandas.df_to_str(df_5mins, num_rows=None)
        )
        # Compute pnl using lags.
        tot_ret_lag, df_5mins = oobpnsim.compute_lag_pnl(df_5mins)
        act.append(
            "After pnl lag computation: df_5mins=\n%s"
            % hpandas.df_to_str(df_5mins, num_rows=None)
        )
        act.append("# tot_ret_lag=%s" % tot_ret_lag)
        # Compute pnl using simulation level 2.
        config = {
            "price_column": "price",
            "future_snoop_allocation": True,
            "order_type": "price@end",
            "cached_columns": ["price"],
        }
        # Check that with / without cache we get the same results.
        df_5mins = _compute_pnl_level2(self, df, df_5mins, initial_wealth, config)
        act.append(
            "After pnl simulation level 2: df_5mins=\n%s"
            % hpandas.df_to_str(df_5mins, num_rows=None)
        )
        #
        act = "\n".join(act)
        self.check_string(act)
        # Check that all the realized PnL are the same.
        df_5mins["sim2.pnl.shifted(-2)"] = df_5mins["sim2.pnl"].shift(-2)
        for col in ["lag.pnl", "sim1.pnl", "sim2.pnl.shifted(-2)"]:
            df_5mins[col] = df_5mins[col].replace(np.nan, 0)
        np.testing.assert_array_almost_equal(
            df_5mins["lag.pnl"], df_5mins["sim1.pnl"]
        )
        np.testing.assert_array_almost_equal(
            df_5mins["lag.pnl"], df_5mins["sim2.pnl.shifted(-2)"]
        )
        # Check that the total returns are the same.
        np.testing.assert_almost_equal(tot_ret, tot_ret_lag)


# #############################################################################


class TestPnlSimulator2(hunitest.TestCase):
    def test1(self) -> None:
        """
        Run level2 simulation using future information to invest all the
        working capital.
        """
        df, df_5mins = oobpnsim.get_example_market_data1()
        initial_wealth = 1000.0
        config = {
            "price_column": "price",
            "future_snoop_allocation": True,
            "order_type": "price@end",
            "cached_columns": ["price"],
        }
        self._run(df, df_5mins, initial_wealth, config)

    def test2(self) -> None:
        """
        Same as `test1()` but without future information.
        """
        df, df_5mins = oobpnsim.get_example_market_data1()
        initial_wealth = 1000.0
        config = {
            "price_column": "price",
            "future_snoop_allocation": False,
            "order_type": "price@end",
            "cached_columns": ["price"],
        }
        self._run(df, df_5mins, initial_wealth, config)

    def test3(self) -> None:
        """
        Same as `test1()` but without future information.
        """
        num_samples = 5 * 30 + 1
        seed = 45
        df, df_5mins = oobpnsim.get_example_market_data2(num_samples, seed)
        initial_wealth = 10000.0
        config = {
            "price_column": "price",
            "future_snoop_allocation": False,
            "order_type": "price@end",
            "cached_columns": ["price"],
        }
        self._run(df, df_5mins, initial_wealth, config)

    @pytest.mark.skip("For performance measurement")
    def test_perf1(self) -> None:
        """
        Same as `test1()` but without future information.
        """
        num_samples = 5 * 100000 + 1
        seed = 43
        df, df_5mins = oobpnsim.get_example_market_data2(num_samples, seed)
        #
        initial_wealth = 1e6
        #
        config = {
            "price_column": "price",
            "future_snoop_allocation": False,
            "order_type": "price@end",
            "use_cache": True,
        }
        df_5mins = oobpnsim.compute_pnl_level2(
            df, df_5mins, initial_wealth, config
        )

    def _run(
        self,
        df: pd.DataFrame,
        df_5mins: pd.DataFrame,
        initial_wealth: float,
        config: Dict[str, Any],
    ) -> None:
        """
        Run level2 simulation using future information to use invest all the
        working capital.
        """
        act = []
        df_5mins = _compute_pnl_level2(self, df, df_5mins, initial_wealth, config)
        act.append(
            "df_5mins=\n%s" % hpandas.df_to_str(df_5mins, num_rows=None)
        )
        # Check.
        act = "\n".join(act)
        self.check_string(act)


# TODO(gp): Add unit tests for computing PnL with level2 sim using midpoint price,
#  and different spread amount.
