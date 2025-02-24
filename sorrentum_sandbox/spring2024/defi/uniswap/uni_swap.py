"""
Import as:

import defi.uni_swap.uni_swap as duswunsw
"""

import helpers.hdbg as hdbg


class UniswapV1:
    """
    Simulate behavior of Uniswap.

    Calculations are based on the Uniswap formula of constant product,
    i.e. if one token's balance in the pool changes, the other token's
    balance must change to the opposite direction by a proportional
    amount to maintain the constant product.
    """

    def __init__(self, token_reserve: float, eth_reserve: float):
        """
        Constructor.

        :param token_reserve: token reserve
        :param eth_reserve: ETH reserve
        """
        self.token_reserve = token_reserve
        self.eth_reserve = eth_reserve

    def add_liquidity(self, token_amount: float, eth_amount: float) -> None:
        """
        Add liquidity by increasing the token and ETH reserves.
        """
        self.token_reserve += token_amount
        self.eth_reserve += eth_amount

    def get_token_amount(self, eth_amount: float) -> float:
        """
        Get the amount of tokens for the given amount of ETH.
        """
        hdbg.dassert_lte(0, eth_amount)
        token_amount = self._get_amount(
            eth_amount, self.eth_reserve, self.token_reserve
        )
        return token_amount

    def get_eth_amount(self, token_amount: float) -> float:
        """
        Get the amount of ETH for the given amount of tokens.
        """
        hdbg.dassert_lte(0, token_amount)
        eth_amount = self._get_amount(
            token_amount, self.token_reserve, self.eth_reserve
        )
        return eth_amount

    def _get_amount(
        self, input_amount: float, input_reserve: float, output_reserve: float
    ) -> float:
        """
        Get the amount of output token that can be bought for the given
        amount of input token and token reserves.

        :param input_amount: input token amount
        :param input_reserve: input token reserve
        :param output_reserve: output token reserve
        :return: output token amount
        """
        hdbg.dassert_lte(0, input_reserve)
        hdbg.dassert_lte(0, output_reserve)
        # Get the amount of output token using Uniswap formula.
        new_input_reserve = input_reserve + input_amount
        output_amount = input_amount * output_reserve / new_input_reserve
        return output_amount
