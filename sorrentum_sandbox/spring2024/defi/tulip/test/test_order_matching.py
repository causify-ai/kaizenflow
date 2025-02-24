from typing import List

import pandas as pd

import defi.tulip.implementation.order as dtuimord
import defi.tulip.implementation.order_matching as dtimorma
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest


class TestMatchOrders1(hunitest.TestCase):
    @staticmethod
    def get_test_orders() -> List[dtuimord.Order]:
        timestamp = pd.Timestamp("2023-01-01 00:00:01+00:00")
        base_token = "BTC"
        quote_token = "ETH"
        #
        order_1 = dtuimord.Order(
            timestamp=timestamp,
            action="buy",
            quantity=1.2,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        order_2 = dtuimord.Order(
            timestamp=timestamp + pd.Timedelta("2s"),
            action="buy",
            quantity=2.3,
            base_token=base_token,
            limit_price=2.3,
            quote_token=quote_token,
            deposit_address=2,
            wallet_address=2,
        )
        order_3 = dtuimord.Order(
            timestamp=timestamp + pd.Timedelta("3s"),
            action="sell",
            quantity=1.8,
            base_token=base_token,
            limit_price=2.1,
            quote_token=quote_token,
            deposit_address=3,
            wallet_address=3,
        )
        order_4 = dtuimord.Order(
            timestamp=timestamp + pd.Timedelta("4s"),
            action="buy",
            quantity=2.1,
            base_token=base_token,
            limit_price=0.4,
            quote_token=quote_token,
            deposit_address=4,
            wallet_address=4,
        )
        order_5 = dtuimord.Order(
            timestamp=timestamp + pd.Timedelta("5s"),
            action="sell",
            quantity=1.5,
            base_token=base_token,
            limit_price=0.5,
            quote_token=quote_token,
            deposit_address=1,
            wallet_address=1,
        )
        order_6 = dtuimord.Order(
            timestamp=timestamp + pd.Timedelta("6s"),
            action="sell",
            quantity=1.1,
            base_token=base_token,
            limit_price=0.1,
            quote_token=quote_token,
            deposit_address=6,
            wallet_address=6,
        )
        orders = [order_1, order_2, order_3, order_4, order_5, order_6]
        return orders

    def test1(self) -> None:
        """
        All the orders have similar base and quote tokens.
        """
        orders = self.get_test_orders()
        clearing_price = 1
        base_token = "BTC"
        quote_token = "ETH"
        # Match orders.
        actual_df = dtimorma.match_orders(
            orders, clearing_price, base_token, quote_token
        )
        # Check the unique tokens.
        actual_tokens = sorted(list(actual_df["token"].unique()))
        expected_tokens = ["BTC", "ETH"]
        self.assertEqual(actual_tokens, expected_tokens)
        # Check that the DaoCross conservation law is fullfilled.
        btc_quantity = actual_df[actual_df["token"] == "BTC"]["amount"].sum()
        eth_quantity = actual_df[actual_df["token"] == "ETH"]["amount"].sum()
        self.assertEqual(btc_quantity * clearing_price, eth_quantity)
        # Check the signature.
        actual_signature = hpandas.df_to_str(
            actual_df,
            print_shape_info=True,
            tag="df",
        )
        expected_signature = r"""
        # df=
        index=[0, 5]
        columns=token,amount,from,to
        shape=(6, 4)
        token  amount  from  to
        0   BTC     1.2     1   1
        1   ETH     1.2     1   1
        2   BTC     0.3     1   2
        3   ETH     0.3     2   1
        4   BTC     1.1     6   2
        5   ETH     1.1     2   6
        """
        self.assert_equal(
            actual_signature,
            expected_signature,
            dedent=True,
            fuzzy_match=True,
        )

    def test2(self) -> None:
        """
        All buy orders are replaced by their equivalent.
        """
        mixed_orders = []
        orders = self.get_test_orders()
        clearing_price = 1
        for order in orders:
            if order.action == "buy":
                # Replace "buy" order with its "sell" equivalent.
                order = dtimorma.get_equivalent_order(order, clearing_price)
            mixed_orders.append(order)
        base_token = "BTC"
        quote_token = "ETH"
        # Match orders.
        actual_df = dtimorma.match_orders(
            mixed_orders, clearing_price, base_token, quote_token
        )
        # Check the unique tokens.
        actual_tokens = sorted(list(actual_df["token"].unique()))
        expected_tokens = ["BTC", "ETH"]
        self.assertEqual(actual_tokens, expected_tokens)
        # Check that the DaoCross conservation law is fullfilled.
        btc_quantity = actual_df[actual_df["token"] == "BTC"]["amount"].sum()
        eth_quantity = actual_df[actual_df["token"] == "ETH"]["amount"].sum()
        self.assertEqual(btc_quantity * clearing_price, eth_quantity)
        # Check the signature.
        actual_signature = hpandas.df_to_str(
            actual_df,
            print_shape_info=True,
            tag="df",
        )
        expected_signature = r"""
        # df=
        index=[0, 5]
        columns=token,amount,from,to
        shape=(6, 4)
        token  amount  from  to
        0   BTC     1.2     1   1
        1   ETH     1.2     1   1
        2   BTC     0.3     1   2
        3   ETH     0.3     2   1
        4   BTC     1.1     6   2
        5   ETH     1.1     2   6
        """
        self.assert_equal(
            actual_signature,
            expected_signature,
            dedent=True,
            fuzzy_match=True,
        )
        
    def test3(self) -> None:
        """
        All orders are randomly generated.
        """
        orders = []
        for i in range(6):
            order = dtuimord.get_random_order(seed=i)
            orders.append(order)
        clearing_price = 1
        base_token = "ETH"
        quote_token = "BTC"
        # Match orders.
        actual_df = dtimorma.match_orders(
            orders, clearing_price, base_token, quote_token
        )
        # Check the unique tokens.
        actual_tokens = sorted(list(actual_df["token"].unique()))
        expected_tokens = ["BTC", "ETH"]
        self.assertEqual(actual_tokens, expected_tokens)
        # Check that the DaoCross conservation law is fullfilled.
        btc_quantity = actual_df[actual_df["token"] == "BTC"]["amount"].sum()
        eth_quantity = actual_df[actual_df["token"] == "ETH"]["amount"].sum()
        self.assertEqual(btc_quantity * clearing_price, eth_quantity)
        # Check the signature.
        actual_signature = hpandas.df_to_str(
            actual_df,
            print_shape_info=True,
            tag="df",
        )
        expected_signature = r"""
        # df=
        index=[0, 7]
        columns=token,amount,from,to
        shape=(8, 4)
        token  amount  from  to
        0   ETH       4    -3   0
        1   BTC       4     0  -3
        2   ETH       5    -3   0
        ...
        5   BTC       1     2  -3
        6   ETH       8    -2   2
        7   BTC       8     2  -2
        """
        self.assert_equal(
            actual_signature,
            expected_signature,
            dedent=True,
            fuzzy_match=True,
        )

class TestGetEquivalentOrder1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check that equivalent order is returned correctly.
        """
        timestamp = pd.Timestamp("2023-01-01 00:00:01+00:00")
        action = "sell"
        quantity = 3.2
        base_token = "BTC"
        limit_price = 0.25
        quote_token = "ETH"
        deposit_address = 1
        wallet_address = 1
        #
        input_order = dtuimord.Order(
            timestamp=timestamp,
            action=action,
            quantity=quantity,
            base_token=base_token,
            limit_price=limit_price,
            quote_token=quote_token,
            deposit_address=deposit_address,
            wallet_address=wallet_address,
        )
        clearing_price = 0.5
        # Get equivalent order and check its signature.
        output_order = dtimorma.get_equivalent_order(input_order, clearing_price)
        expected_signature = "timestamp=2023-01-01 00:00:01+00:00 action=buy quantity=1.6 base_token=ETH limit_price=4.0 quote_token=BTC deposit_address=1 wallet_address=1"
        self.assertEqual(output_order.__repr__(), expected_signature)
