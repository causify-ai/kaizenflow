import logging
import pprint

import pandas as pd

import helpers.hunit_test as hunitest
import helpers.hunit_test_utils as hunteuti
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.limit_price_computer.limit_price_computer_using_spread as olpclpcus

_LOG = logging.getLogger(__name__)


class Test_limit_price_computer_using_spread(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test limit price calculation using side="buy".
        """
        actual = self._calculate_price_helper("buy", 0.1, 0.01, 1464553467, 2, 0)
        expected = r"""
            {'ask_price_mean': 60.5,
            'bid_price_mean': 50.5,
            'latest_ask_price': 61,
            'latest_ask_size': 41,
            'latest_bid_price': 51,
            'latest_bid_size': 31,
            'limit_price': 60.0,
            'num_data_points': 2,
            'passivity_factor': 0.1,
            'used_ask_price': 'latest_ask_price',
            'used_bid_price': 'latest_bid_price',
            'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test limit price calculation using side="sell".
        """
        actual = self._calculate_price_helper("sell", 0.5, 0.01, 1464553467, 3, 0)
        expected = r"""
            {'ask_price_mean': 60.5,
            'bid_price_mean': 50.5,
            'latest_ask_price': 61,
            'latest_ask_size': 41,
            'latest_bid_price': 51,
            'latest_bid_size': 31,
            'limit_price': 56.0,
            'num_data_points': 2,
            'passivity_factor': 0.5,
            'used_ask_price': 'latest_ask_price',
            'used_bid_price': 'latest_bid_price',
            'wave_id': 0}
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_compare_latest_and_average_price(self) -> None:
        """
        Verify that bid_price and ask_price are correctly calculated.
        """
        bid_price_col = "bid_price_l1"
        ask_price_col = "ask_price_l1"
        bid_ask_data = obcttcut.get_test_bid_ask_data()
        actual = []
        # group data by asset_id.
        for asset_id, group in bid_ask_data.groupby("asset_id"):
            bid_ask_price_data = group[
                [
                    bid_price_col,
                    ask_price_col,
                ]
            ]
            output = olpclpcus.LimitPriceComputerUsingSpread._compare_latest_and_average_price(
                bid_ask_price_data, 0.01
            )
            actual.append(str(output))
        # concatenate all asset_id output for test.
        actual_str = "\n".join(actual)
        actual_str = pprint.pformat(actual_str)
        expected_str = r"""
        ("({'latest_bid_price': 51, 'latest_ask_price': 61, 'bid_price_mean': 50.5, "
        "'ask_price_mean': 60.5, 'used_bid_price': 'latest_bid_price', "
        "'used_ask_price': 'latest_ask_price'}, 51, 61)\n"
        "({'latest_bid_price': 32, 'latest_ask_price': 42, 'bid_price_mean': 31.0, "
        "'ask_price_mean': 41.0, 'used_bid_price': 'bid_price_mean', "
        "'used_ask_price': 'ask_price_mean'}, 31.0, 41.0)")
        """
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)

    def _calculate_price_helper(
        self,
        side: str,
        passivity_factor: float,
        max_deviation: float,
        asset_id: int,
        price_precision: int,
        wave_id: int,
        *,
        execution_freq=pd.Timedelta("1T")
    ) -> str:
        """
        Helper function to test calculate price.
        """
        limit_price_computer = olpclpcus.LimitPriceComputerUsingSpread(
            passivity_factor, max_deviation=max_deviation
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


class Test_LimitPriceComputerUsingSpread_Obj_to_str1(
    hunitest.TestCase, hunteuti.Obj_to_str_TestCase
):
    @staticmethod
    def get_object() -> olpclpcus.LimitPriceComputerUsingSpread:
        """
        Build `LimitPriceComputerUsingSpread` object for test.
        """
        passivity_factor = 0.5
        max_deviation = 0.01
        limit_price_computer = olpclpcus.LimitPriceComputerUsingSpread(
            passivity_factor, max_deviation=max_deviation
        )
        return limit_price_computer

    def test_repr1(self) -> None:
        """
        Check `LimitPriceComputerUsingSpread` `__repr__`.
        """
        obj = self.get_object()
        expected_str = r"""
        <oms.limit_price_computer.limit_price_computer_using_spread.LimitPriceComputerUsingSpread at 0x>:
          passivity_factor='0.5' <float>
          max_deviation='0.01' <float>
        """
        self.run_test_repr(obj, expected_str)

    def test_str1(self) -> None:
        """
        Check `LimitPriceComputerUsingSpread` `__str__`.
        """
        obj = self.get_object()
        expected_str = r"""
        LimitPriceComputerUsingSpread at 0x=(passivity_factor=0.5 <float>, max_deviation=0.01 <float>)
        """
        self.run_test_str(obj, expected_str)
