import logging

import helpers.hunit_test as hunitest
import im_v2.ccxt.utils as imv2ccuti

_LOG = logging.getLogger(__name__)


class Test_convert_currency_pair_to_ccxt_format(hunitest.TestCase):
    def test1(self) -> None:
        currency_pair = "BTC_USDT"
        exchange = "binance"
        contract_type = "spot"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = "BTC/USDT"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        currency_pair = "BTC_USDT"
        exchange = "binance"
        contract_type = "futures"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = r"""BTC/USDT:USDT"""
        self.assert_equal(actual, expected)

    def test3(self) -> None:
        currency_pair = "BTC_USDT"
        exchange = "kraken"
        contract_type = "spot"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = "BTC/USDT"
        self.assert_equal(actual, expected)

    def test4(self) -> None:
        currency_pair = "BTC_USD"
        exchange = "krakenfutures"
        contract_type = "futures"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = "BTC/USD:USD"
        self.assert_equal(actual, expected)

    def test5(self) -> None:
        currency_pair = "BTC_USDT"
        exchange = "okx"
        contract_type = "spot"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = "BTC/USDT"
        self.assert_equal(actual, expected)

    def test6(self) -> None:
        currency_pair = "BTC_USDT"
        exchange = "okx"
        contract_type = "futures"
        actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
            currency_pair, exchange, contract_type
        )
        expected = "BTC/USDT:USDT"
        self.assert_equal(actual, expected)

    def test7(self) -> None:
        currency_pair = "BTCUSDT"
        exchange = "okx"
        contract_type = "futures"
        with self.assertRaises(AssertionError) as fail:
            actual = imv2ccuti.convert_currency_pair_to_ccxt_format(
                currency_pair, exchange, contract_type
            )
        actual_error = str(fail.exception)
        expected = r"""
        * Failed assertion *
        '_' in 'BTCUSDT'
        The currency_pair 'BTCUSDT' does not match the format '{str1}_{str2}'.
        """
        self.assert_equal(actual_error, expected, fuzzy_match=True)


class Test_convert_full_symbol_to_binance_symbol(hunitest.TestCase):
    def helper(self, full_symbol: str, expected: str) -> None:
        """
        Helper for the tests that raise an exception.
        """
        with self.assertRaises(AssertionError) as fail:
            imv2ccuti.convert_full_symbol_to_binance_symbol(full_symbol)
        actual_error = str(fail.exception)
        self.assert_equal(actual_error, expected, fuzzy_match=True)

    def test1(self) -> None:
        full_symbol = "binance::AVAX_USDT"
        actual = imv2ccuti.convert_full_symbol_to_binance_symbol(full_symbol)
        expected = "AVAX/USDT:USDT"
        self.assert_equal(actual, expected)

    def test2(self) -> None:
        full_symbol = "binance::1000LUNC_USDT"
        actual = imv2ccuti.convert_full_symbol_to_binance_symbol(full_symbol)
        expected = "1000LUNC/USDT:USDT"
        self.assert_equal(actual, expected)

    def test3(self) -> None:
        full_symbol = "binance_1000LUNC_USDT"
        expected = r"""
        * Failed assertion *
        'None' is not 'None'
        The full_symbol 'binance_1000LUNC_USDT' does not match the format '{exchange}::{CURRENCY1}_{CURRENCY2}'.
        """
        self.helper(full_symbol, expected)

    def test4(self) -> None:
        full_symbol = "::AVAX_USDT"
        expected = r"""
        * Failed assertion *
        'None' is not 'None'
        The full_symbol '::AVAX_USDT' does not match the format '{exchange}::{CURRENCY1}_{CURRENCY2}'.
        """
        self.helper(full_symbol, expected)

    def test5(self) -> None:
        full_symbol = "binance::avax_usdt"
        expected = r"""
        * Failed assertion *
        'None' is not 'None'
        The full_symbol 'binance::avax_usdt' does not match the format '{exchange}::{CURRENCY1}_{CURRENCY2}'.
        """
        self.helper(full_symbol, expected)
