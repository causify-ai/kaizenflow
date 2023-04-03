import logging
from typing import Tuple

import defi.dao_cross.optimize as ddacropt
import defi.dao_cross.order as ddacrord
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestRunSolver1(hunitest.TestCase):
    """
    Run the solver using toy orders.
    """

    @staticmethod
    def get_test_orders(
        limit_price_1: float, limit_price_2: float
    ) -> Tuple[ddacrord.Order, ddacrord.Order]:
        """
        Get toy orders for the unit tests.

        :param limit_price_1: limit price for the buy order
        :param limit_price_2: limit price for the sell order
        :return: buy and sell orders
        """
        # Set dummy variables.
        base_token = "BTC"
        quote_token = "ETH"
        deposit_address = 1
        wallet_address = 1
        # Genereate buy order.
        action = "buy"
        quantity = 5
        order_1 = ddacrord.Order(
            base_token,
            quote_token,
            action,
            quantity,
            limit_price_1,
            deposit_address,
            wallet_address,
        )
        # Generate sell order.
        action = "sell"
        quantity = 6
        order_2 = ddacrord.Order(
            base_token,
            quote_token,
            action,
            quantity,
            limit_price_2,
            deposit_address,
            wallet_address,
        )
        return order_1, order_2

    def test1(self) -> None:
        """
        The limit price condition is True for all orders.
        """
        exchange_rate = 4
        limit_price_1 = 5
        limit_price_2 = 3
        test_orders_1 = self.get_test_orders(limit_price_1, limit_price_2)
        result = ddacropt.run_solver(
            test_orders_1[0], test_orders_1[1], exchange_rate
        )
        # Check that the solution is found and is different from zero.
        self.assertEqual(result["problem_objective_value"], 10)
        # Check executed quantity values.
        self.assertEqual(result["q_base_asterisk_1"], 5)
        self.assertEqual(result["q_base_asterisk_2"], 5)

    def test2(self) -> None:
        """
        The limit price condition is False for at least one order.
        """
        exchange_rate = 4
        limit_price_1 = 5
        limit_price_2 = 5
        test_orders_1 = self.get_test_orders(limit_price_1, limit_price_2)
        result = ddacropt.run_solver(
            test_orders_1[0], test_orders_1[1], exchange_rate
        )
        # Check that the solution is found but it equals zero.
        self.assertEqual(result["problem_objective_value"], 0)
        self.assertEqual(result["q_base_asterisk_1"], 0)
        self.assertEqual(result["q_base_asterisk_2"], 0)
