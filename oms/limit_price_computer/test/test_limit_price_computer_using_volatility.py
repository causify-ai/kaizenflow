import logging
import pprint
from typing import List, Union

import pandas as pd

import helpers.hunit_test as hunitest
import helpers.hunit_test_utils as hunteuti
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.limit_price_computer.limit_price_computer_using_volatility as olpclpcuv

_LOG = logging.getLogger(__name__)


class Test_limit_price_computer_using_volatility(
    hunitest.TestCase, hunteuti.Obj_to_str_TestCase
):
    def test1(self) -> None:
        """
        Test limit price calculation using side="buy" and constant volatility
        multiplier.
        """
        side = "buy"
        volatility_multiple = 0.1
        asset_id = 1464553467
        price_precision = 2
        execution_freq = pd.Timedelta("1T")
        wave_id = 0
        actual = self._calculate_price_helper(
            side,
            volatility_multiple,
            asset_id,
            price_precision,
            execution_freq,
            wave_id,
        )
        expected = r"""
        {'ask_vol': 7.745966692414834,
        'ask_vol_bps': 1269.8306053139074,
        'bid_vol': 7.745966692414834,
        'bid_vol_bps': 1518.8169985127126,
        'latest_ask_price': 61.0,
        'latest_ask_size': 41,
        'latest_bid_price': 51.0,
        'latest_bid_size': 31,
        'latest_mid_price': 56.0,
        'limit_price': 60.23,
        'num_data_points': 2,
        'num_data_points_resampled': 11,
        'scaling_multiplier': 24.49489742783178,
        'spread': 10.0,
        'spread_bps': 1785.7142857142858,
        'total_vol': 7.745966692414834,
        'total_vol_bps': 1383.2083379312205,
        'total_vol_to_spread_bps': 0.7745966692414834,
        'volatility_multiple': 0.1,
        'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    # #########################################################################

    def test2(self) -> None:
        """
        Test limit price calculation using side="sell" and constant volatility
        multiplier.
        """
        side = "sell"
        volatility_multiple = 0.5
        asset_id = 1464553467
        price_precision = 3
        execution_freq = pd.Timedelta("1T")
        wave_id = 0
        actual = self._calculate_price_helper(
            side,
            volatility_multiple,
            asset_id,
            price_precision,
            execution_freq,
            wave_id,
        )
        expected = r"""
        {'ask_vol': 7.745966692414834,
        'ask_vol_bps': 1269.8306053139074,
        'bid_vol': 7.745966692414834,
        'bid_vol_bps': 1518.8169985127126,
        'latest_ask_price': 61.0,
        'latest_ask_size': 41,
        'latest_bid_price': 51.0,
        'latest_bid_size': 31,
        'latest_mid_price': 56.0,
        'limit_price': 54.873,
        'num_data_points': 2,
        'num_data_points_resampled': 11,
        'scaling_multiplier': 24.49489742783178,
        'spread': 10.0,
        'spread_bps': 1785.7142857142858,
        'total_vol': 7.745966692414834,
        'total_vol_bps': 1383.2083379312205,
        'total_vol_to_spread_bps': 0.7745966692414834,
        'volatility_multiple': 0.5,
        'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    # #########################################################################

    def test3(self) -> None:
        """
        Test limit price calculation using side="sell" and volatility
        multiplier as a list.
        """
        side = "sell"
        volatility_multiple = [0.1, 0.5, 1, 1.5, 2]
        asset_id = 1464553467
        price_precision = 3
        execution_freq = pd.Timedelta("1T")
        # Generate a price dict for 5 waves.
        actual_results = []
        for i in range(len(volatility_multiple)):
            wave_id = i
            actual_result = self._calculate_price_helper(
                side,
                volatility_multiple,
                asset_id,
                price_precision,
                execution_freq,
                wave_id,
            )
            actual_results.append(actual_result)
        # Verify that result for a single wave is correct.
        actual_0 = actual_results[0]
        expected_0 = r"""
        {'ask_vol': 7.745966692414834,
        'ask_vol_bps': 1269.8306053139074,
        'bid_vol': 7.745966692414834,
        'bid_vol_bps': 1518.8169985127126,
        'latest_ask_price': 61.0,
        'latest_ask_size': 41,
        'latest_bid_price': 51.0,
        'latest_bid_size': 31,
        'latest_mid_price': 56.0,
        'limit_price': 51.775,
        'num_data_points': 2,
        'num_data_points_resampled': 11,
        'scaling_multiplier': 24.49489742783178,
        'spread': 10.0,
        'spread_bps': 1785.7142857142858,
        'total_vol': 7.745966692414834,
        'total_vol_bps': 1383.2083379312205,
        'total_vol_to_spread_bps': 0.7745966692414834,
        'volatility_multiple': 0.1,
        'wave_id': 0}
            """
        self.assert_equal(actual_0, expected_0, fuzzy_match=True)

    # #########################################################################

    def test4(self) -> None:
        """
        Test limit price calculation using side="sell", constant volatility
        multiplier, and 30s execution frequency.
        """
        side = "sell"
        volatility_multiple = 0.5
        asset_id = 1464553467
        price_precision = 3
        execution_freq = pd.Timedelta("30S")
        wave_id = 0
        actual = self._calculate_price_helper(
            side,
            volatility_multiple,
            asset_id,
            price_precision,
            execution_freq,
            wave_id,
        )
        expected = r"""
        {'ask_vol': 5.477225575051662,
        'ask_vol_bps': 897.9058319756823,
        'bid_vol': 5.477225575051662,
        'bid_vol_bps': 1073.9657990297376,
        'latest_ask_price': 61.0,
        'latest_ask_size': 41,
        'latest_bid_price': 51.0,
        'latest_bid_size': 31,
        'latest_mid_price': 56.0,
        'limit_price': 53.739,
        'num_data_points': 2,
        'num_data_points_resampled': 11,
        'scaling_multiplier': 17.320508075688775,
        'spread': 10.0,
        'spread_bps': 1785.7142857142858,
        'total_vol': 5.477225575051662,
        'total_vol_bps': 978.0759955449396,
        'total_vol_to_spread_bps': 0.5477225575051662,
        'volatility_multiple': 0.5,
        'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    # #########################################################################

    def test5(self) -> None:
        """
        Test limit price calculation using side="sell", constant volatility
        multiplier, and 10s execution frequency.
        """
        side = "sell"
        volatility_multiple = 0.5
        asset_id = 1464553467
        price_precision = 3
        execution_freq = pd.Timedelta("10S")
        wave_id = 0
        actual = self._calculate_price_helper(
            side,
            volatility_multiple,
            asset_id,
            price_precision,
            execution_freq,
            wave_id,
        )
        expected = r"""
        {'ask_vol': 3.1622776601683795,
        'ask_vol_bps': 518.406173798095,
        'bid_vol': 3.1622776601683795,
        'bid_vol_bps': 620.0544431702705,
        'latest_ask_price': 61.0,
        'latest_ask_size': 41,
        'latest_bid_price': 51.0,
        'latest_bid_size': 31,
        'latest_mid_price': 56.0,
        'limit_price': 52.581,
        'num_data_points': 2,
        'num_data_points_resampled': 11,
        'scaling_multiplier': 10.0,
        'spread': 10.0,
        'spread_bps': 1785.7142857142858,
        'total_vol': 3.1622776601683795,
        'total_vol_bps': 564.692439315782,
        'total_vol_to_spread_bps': 0.31622776601683794,
        'volatility_multiple': 0.5,
        'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    # #########################################################################

    def test_invalid_side1(self) -> None:
        """
        Check that an assertion is raised when a non-existent side value is
        supplied.
        """
        with self.assertRaises(ValueError) as cm:
            self._calculate_price_helper(
                "non-existent-side", 0.5, 1464553467, 3, pd.Timedelta("1T"), 0
            )
        act = str(cm.exception)
        exp = r"Invalid side='non-existent-side'"
        self.assert_equal(act, exp, fuzzy_match=True)

    # #########################################################################

    def test_repr1(self) -> None:
        """
        Check `LimitPriceComputerUsingVolatility` `__repr__`.
        """
        obj = self.get_object()
        expected_str = r"""
        <oms.limit_price_computer.limit_price_computer_using_volatility.LimitPriceComputerUsingVolatility at 0x>:
          _volatility_multiple='0.5' <float>
        """
        self.run_test_repr(obj, expected_str)

    # #########################################################################

    def test_str1(self) -> None:
        """
        Check `LimitPriceComputerUsingVolatility` `__str__`.
        """
        obj = self.get_object()
        expected_str = r"""
        LimitPriceComputerUsingVolatility at 0x=(_volatility_multiple=0.5 <float>)
        """
        self.run_test_str(obj, expected_str)

    # #########################################################################

    @staticmethod
    def get_object() -> olpclpcuv.LimitPriceComputerUsingVolatility:
        """
        Build `LimitPriceComputerUsingVolatility` object for test.
        """
        volatility_multiple = 0.5
        limit_price_computer = olpclpcuv.LimitPriceComputerUsingVolatility(
            volatility_multiple
        )
        return limit_price_computer
    def _calculate_price_helper(
        self,
        side: str,
        volatility_multiple: Union[List, float],
        asset_id: int,
        price_precision: int,
        execution_freq: pd.Timedelta,
        wave_id: int,
    ) -> str:
        """
        Helper function to test calculate price.
        """
        limit_price_computer = olpclpcuv.LimitPriceComputerUsingVolatility(
            volatility_multiple
        )
        data = obcttcut.get_test_bid_ask_data()
        data = data[data["asset_id"] == asset_id]
        price_dict = limit_price_computer.calculate_limit_price(
            data, side, price_precision, execution_freq, wave_id
        )
        # Remove timestamp keys from the output.
        timestamp_keys = [
            "exchange_timestamp",
            "knowledge_timestamp",
            "end_download_timestamp",
        ]
        for key in timestamp_keys:
            del price_dict[key]
        actual = pprint.pformat(price_dict)
        return actual
