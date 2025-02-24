import defi.tulip.implementation.uni_swap as dtimunsw
import helpers.hunit_test as hunitest


class TestUniswapV1(hunitest.TestCase):
    def test_add_liquidity1(self) -> None:
        """
        Check that liquidity is increased correctly.
        """
        token_reserve = 90
        eth_reserve = 10
        uniswap_pool = dtimunsw.UniswapV1(token_reserve, eth_reserve)
        token_amount = 10
        eth_amount = 5
        uniswap_pool.add_liquidity(token_amount, eth_amount)
        # Check outcomes.
        actual_token_reserve = uniswap_pool.token_reserve
        actual_eth_reserve = uniswap_pool.eth_reserve
        expected_token_reserve = 100
        expected_eth_reserve = 15
        self.assertEqual(expected_token_reserve, actual_token_reserve)
        self.assertEqual(expected_eth_reserve, actual_eth_reserve)

    def test_add_liquidity2(self) -> None:
        """
        Check that liquidity is decreased correctly.
        """
        token_reserve = 5
        eth_reserve = 10
        uniswap_pool = dtimunsw.UniswapV1(token_reserve, eth_reserve)
        token_amount = 5
        eth_amount = -4
        uniswap_pool.add_liquidity(token_amount, eth_amount)
        # Check outcomes.
        actual_token_reserve = uniswap_pool.token_reserve
        actual_eth_reserve = uniswap_pool.eth_reserve
        expected_token_reserve = 10
        expected_eth_reserve = 6
        self.assertEqual(expected_token_reserve, actual_token_reserve)
        self.assertEqual(expected_eth_reserve, actual_eth_reserve)

    def test_get_token_amount1(self) -> None:
        """
        Check that token amount is calculated correctly.
        """
        token_reserve = 100
        eth_reserve = 100
        uniswap_pool = dtimunsw.UniswapV1(token_reserve, eth_reserve)
        eth_amount = 150
        actual_token_amount = uniswap_pool.get_token_amount(eth_amount)
        # Check outcomes.
        expected_token_amount = 60
        self.assertEqual(expected_token_amount, actual_token_amount)

    def test_get_eth_amount(self) -> None:
        """
        Check that ETH amount is calculated correctly.
        """
        token_reserve = 60
        eth_reserve = 5
        uniswap_pool = dtimunsw.UniswapV1(token_reserve, eth_reserve)
        token_amount = 15
        actual_eth_amount = uniswap_pool.get_eth_amount(token_amount)
        # Check outcomes.
        expected_eth_amount = 1
        self.assertEqual(expected_eth_amount, actual_eth_amount)
