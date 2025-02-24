import pandas as pd

import helpers.hunit_test as hunitest
import im_v2.common.universe.full_symbol as imvcufusy


class TestDassertIsFullSymbolValid(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test correct format.
        """
        full_symbol = "binance::BTC_USDT"
        imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test2(self) -> None:
        """
        Test incorrect format: `/` symbol.
        """
        full_symbol = "binance::BTC/USDT"
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test3(self) -> None:
        """
        Test incorrect format: whitespace symbol.
        """
        full_symbol = "bi nance::BTC_USDT"
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test4(self) -> None:
        """
        Test incorrect format: digit.
        """
        full_symbol = "bi1nance::BTC2USDT"
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test5(self) -> None:
        """
        Test incorrect format: empty string.
        """
        full_symbol = ""
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test6(self) -> None:
        """
        Test incorrect format: not string.
        """
        full_symbol = 123
        with self.assertRaises(TypeError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test7(self) -> None:
        """
        Test incorrect format: not separated by `::`.
        """
        full_symbol = "binance;;BTC_USDT"
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test8(self) -> None:
        """
        Test correct format series.
        """
        full_symbol = pd.Series(
            ["binance::BTC_USDT", "ftx::ETH_USDT", "exchange::symbol"]
        )
        imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test9(self) -> None:
        """
        Test series with an incorrectly formatted full symbol.
        """
        full_symbol = pd.Series(
            ["binance::BTC_USDT", "ftx::ETH_USDT", "bi nance::BTC USDT"]
        )
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test10(self) -> None:
        """
        Test series with an empty string.
        """
        full_symbol = pd.Series(["binance::BTC_USDT", "ftx::ETH_USDT", ""])
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test11(self) -> None:
        """
        Test series with an integer.
        """
        full_symbol = pd.Series(["binance::BTC_USDT", "ftx::ETH_USDT", 123])
        with self.assertRaises(AssertionError):
            imvcufusy.dassert_is_full_symbol_valid(full_symbol)

    def test12(self) -> None:
        """
        Test that symbol that contains a digit is a valid one.

        E.g.: `binance::1INCH_USDT`.
        """
        full_symbol = "binance::1INCH_USDT"
        imvcufusy.dassert_is_full_symbol_valid(full_symbol)


class TestParseFullSymbol(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test split full symbol into exchange, symbol.
        """
        full_symbol = "ftx::ADA_USDT"
        exchange, symbol = imvcufusy.parse_full_symbol(full_symbol)
        self.assert_equal(exchange, "ftx")
        self.assert_equal(symbol, "ADA_USDT")

    def test2(self) -> None:
        """
        Test split full symbol into exchange, symbol.
        """
        full_symbol = "kucoin::XPR_USDT"
        exchange, symbol = imvcufusy.parse_full_symbol(full_symbol)
        self.assert_equal(exchange, "kucoin")
        self.assert_equal(symbol, "XPR_USDT")

    def test3(self) -> None:
        """
        Test split full symbol column into exchange and symbol columns.
        """
        full_symbol = pd.Series(
            ["binance::BTC_USDT", "ftx::ETH_USDT", "exchange::symbol"]
        )
        exchange, symbol = imvcufusy.parse_full_symbol(full_symbol)
        self.assert_equal(
            exchange.to_string(),
            pd.Series(["binance", "ftx", "exchange"]).to_string(),
        )
        self.assert_equal(
            symbol.to_string(),
            pd.Series(["BTC_USDT", "ETH_USDT", "symbol"]).to_string(),
        )


class TestBuildFullSymbol(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test construct full symbol from exchange, symbol.
        """
        exchange = "bitfinex"
        symbol = "SOL_USDT"
        full_symbol = imvcufusy.build_full_symbol(exchange, symbol)
        self.assert_equal(full_symbol, "bitfinex::SOL_USDT")

    def test2(self) -> None:
        """
        Test construct full symbol from exchange, symbol.
        """
        exchange = "exchange"
        symbol = "symbol"
        full_symbol = imvcufusy.build_full_symbol(exchange, symbol)
        self.assert_equal(full_symbol, "exchange::symbol")

    def test3(self) -> None:
        """
        Test construct full symbol column from exchange and symbol columns.
        """
        exchange = pd.Series(["binance", "ftx", "exchange"])
        symbol = pd.Series(["BTC_USDT", "ETH_USDT", "symbol"])
        actual = imvcufusy.build_full_symbol(exchange, symbol)
        expected = pd.Series(
            ["binance::BTC_USDT", "ftx::ETH_USDT", "exchange::symbol"]
        )
        self.assert_equal(actual.to_string(), expected.to_string())

    def test4(self) -> None:
        """
        Test exchange and symbol have different formats.
        """
        exchange = "binance"
        symbol = pd.Series(["BTC_USDT", "ETH_USDT", "symbol"])
        with self.assertRaises(TypeError):
            imvcufusy.build_full_symbol(exchange, symbol)
