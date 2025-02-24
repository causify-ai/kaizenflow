import numpy as np

import defi.tulip.implementation.order as dtuimord
import helpers.hunit_test as hunitest


class TestExecuteOrder(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check that the buy order is correctly executed.
        """
        # Create an order for execution.
        timestamp = np.nan
        base_token = "BTC"
        quote_token = "ETH"
        #
        buy_order = dtuimord.Order(
            timestamp=timestamp,
            action="buy",
            quantity=1.2,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        proposed_price = buy_order.limit_price - 1
        # Execute the order and get results.
        result = dtuimord.execute_order(buy_order, proposed_price)
        expected_result = [
            (-buy_order.quantity * proposed_price, buy_order.quote_token),
            (buy_order.quantity, buy_order.base_token),
        ]
        self.assertEqual(result, expected_result)

    def test2(self) -> None:
        """
        Check that the buy order is not executed.
        """
        # Create an order for execution.
        timestamp = np.nan
        base_token = "BTC"
        quote_token = "ETH"
        #
        buy_order = dtuimord.Order(
            timestamp=timestamp,
            action="buy",
            quantity=1.2,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        # Propose an order price such that it is less than the limit price.
        proposed_price = buy_order.limit_price + 1
        # Execute the order and get results.
        result = dtuimord.execute_order(buy_order, proposed_price)
        expected_result = None
        self.assertEqual(result, expected_result)

    def test3(self) -> None:
        """
        Check that the sell order is not executed.
        """
        # Create an order for execution.
        timestamp = np.nan
        base_token = "BTC"
        quote_token = "ETH"
        #
        sell_order = dtuimord.Order(
            timestamp=timestamp,
            action="sell",
            quantity=1.2,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        # Propose an order price such that it is less than the limit price.
        proposed_price = sell_order.limit_price - 1
        # Execute the order and get results.
        result = dtuimord.execute_order(sell_order, proposed_price)
        expected_result = None
        self.assertEqual(result, expected_result)

    def test4(self) -> None:
        """
        Check that the sell order is correctly executed.
        """
        # Create an order for execution.
        timestamp = np.nan
        base_token = "BTC"
        quote_token = "ETH"
        #
        sell_order = dtuimord.Order(
            timestamp=timestamp,
            action="sell",
            quantity=1.2,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        # Propose an order price such that it is less than the limit price.
        proposed_price = sell_order.limit_price + 1
        # Execute the order and get results.
        result = dtuimord.execute_order(sell_order, proposed_price)
        expected_result = [
            (sell_order.quantity * proposed_price, sell_order.quote_token),
            (sell_order.quantity, sell_order.base_token),
        ]
        self.assertEqual(result, expected_result)
