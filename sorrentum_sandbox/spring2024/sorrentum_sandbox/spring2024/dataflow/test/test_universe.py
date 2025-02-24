import dataflow.universe as dtfuniver
import helpers.hunit_test as hunitest


class Test_get_universe(hunitest.TestCase):
    """
    Check that `get_universe()` works correctly.
    """

    def check_output(
        self,
        universe_str: str,
        expected: str,
    ) -> None:
        """
        Validate the universe returned by the function for the given
        `universe_str`.

        :param universe_str: string consisting of vendor, universe version and
            top number of assets or all to get. E.g., `ccxt_v7_1-top1` or
            `ccxt_v7_1-all`
        :param expected: the expected output for the given `universe_str`
        """
        actual = str(dtfuniver.get_universe(universe_str))
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test when vendor is CCXT and all symbols are requested.
        """
        universe_str = "ccxt_v7_1-all"
        expected = r"""
        ['binance::APE_USDT', 'binance::AVAX_USDT', 'binance::AXS_USDT', 'binance::BAKE_USDT', 'binance::BNB_USDT', 'binance::BTC_USDT', 'binance::CRV_USDT', 'binance::CTK_USDT', 'binance::DOGE_USDT', 'binance::DOT_USDT', 'binance::DYDX_USDT', 'binance::ETH_USDT', 'binance::FTM_USDT', 'binance::GMT_USDT', 'binance::LINK_USDT', 'binance::MATIC_USDT', 'binance::NEAR_USDT', 'binance::OGN_USDT', 'binance::RUNE_USDT', 'binance::SAND_USDT', 'binance::SOL_USDT', 'binance::STORJ_USDT', 'binance::UNFI_USDT', 'binance::WAVES_USDT', 'binance::XRP_USDT']
        """
        self.check_output(universe_str, expected)

    def test2(self) -> None:
        """
        Test when vendor is Crypto Chassis and only 3 symbols are requested.
        """
        universe_str = "crypto_chassis_v4-top3"
        expected = r"""
        ['binance::ADA_USDT', 'binance::BNB_USDT', 'binance::BTC_USD']
        """
        self.check_output(universe_str, expected)

    def test3(self) -> None:
        """
        Test when vendor is Kibot and only one symbol is requested.
        """
        universe_str = "kibot_v2-top1"
        expected = r"""
        ['AAP']
        """
        self.check_output(universe_str, expected)

    def test4(self) -> None:
        """
        Test when vendor is Bloomberg and only one symbol is requested.
        """
        universe_str = "bloomberg_v1-top1"
        expected = r"""
        ['us_market::MSFT']
        """
        self.check_output(universe_str, expected)

    def test5(self) -> None:
        """
        Test when vendor is mock1 and only one symbol is requested.
        """
        universe_str = "mock1_v1-top1"
        expected = r"""
        ['binance::ADA_USDT']
        """
        self.check_output(universe_str, expected)

    def test6(self) -> None:
        """
        Test when `universe_str` is invalid.
        """
        universe_str = "invalid_string-all"
        with self.assertRaises(AssertionError) as e:
            _ = dtfuniver.get_universe(universe_str)
        actual = str(e.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        'None' is not 'None'
        The vendor and universe version are not found in
        `universe_str = invalid_string-all`.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)
