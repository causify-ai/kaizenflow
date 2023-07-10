import unittest.mock as umock

import pandas as pd

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.cc_optimizer_utils as occoputi
import oms.ccxt.abstract_ccxt_broker as ocabccbr
import oms.ccxt.ccxt_broker_v1 as occcbrv1
import oms.hsecrets.secret_identifier as ohsseide


class TestCcOptimizerUtils1(hunitest.TestCase):
    get_secret_patch = umock.patch.object(ocabccbr.hsecret, "get_secret")
    ccxt_patch = umock.patch.object(ocabccbr, "ccxt", spec=ocabccbr.ccxt)

    @staticmethod
    def get_test_orders(below_min: bool) -> pd.DataFrame:
        """
        Create orders for testing.

        :param below_min: whether order amount should be below limit.
        """
        df_columns = [
            "asset_id",
            "holdings_shares",
            "price",
            "holdings_notional",
            "wall_clock_timestamp",
            "prediction",
            "volatility",
            "spread",
            "target_holdings_notional",
            "target_trades_notional",
            "target_trades_shares",
            "target_holdings_shares",
        ]
        if below_min:
            # Create DataFrame with orders below limit.
            order_df = pd.DataFrame(
                columns=df_columns,
                data=[
                    [
                        8717633868,
                        -1.000,
                        21.696667,
                        -21.696667,
                        pd.Timestamp("2022-09-12 11:06:09.144373-04:00"),
                        -0.133962,
                        0.002366,
                        0,
                        -1.01,
                        -0.01,
                        -0.04655092876707745,
                        -0.000460900284822549,
                    ],
                    [
                        6051632686,
                        -2.000,
                        5.429500,
                        -10.859000,
                        pd.Timestamp("2022-09-12 11:06:09.144373-04:00"),
                        0.001705,
                        0.002121,
                        0,
                        -2.01,
                        0.01,
                        1.5,
                        0.0018417902200939314,
                    ],
                ],
            )
        else:
            # Create DataFrame with orders above limit.
            order_df = pd.DataFrame(
                columns=df_columns,
                data=[
                    [
                        8717633868,
                        -1.000,
                        21.696667,
                        -21.696667,
                        pd.Timestamp("2022-09-12 11:06:09.144373-04:00"),
                        -0.133962,
                        0.002366,
                        0,
                        -27.075329,
                        -5.378662,
                        3.42342342,
                        4.342423432,
                    ],
                    [
                        6051632686,
                        -2.000,
                        5.429500,
                        -10.859000,
                        pd.Timestamp("2022-09-12 11:06:09.144373-04:00"),
                        0.001705,
                        0.002121,
                        0,
                        -33.701572,
                        -22.8425729,
                        2.512351512,
                        5.513513512,
                    ],
                ],
            )
        order_df = order_df.set_index("asset_id")
        return order_df

    @staticmethod
    def get_mock_broker() -> occcbrv1.CcxtBroker_v1:
        """
        Build mock `CcxtBroker` for tests.
        """
        # TODO(Danya): Move this constructor up to be used in all tests.
        universe_version = "v7"
        portfolio_id = "ccxt_portfolio_mock"
        exchange_id = "binance"
        account_type = "trading"
        stage = "preprod"
        contract_type = "futures"
        strategy_id = "dummy_strategy_id"
        bid_ask_im_client = None
        market_data = umock.create_autospec(spec=mdata.MarketData, instance=True)
        secret_id = ohsseide.SecretIdentifier(exchange_id, stage, account_type, 1)
        # Initialize broker.
        broker = occcbrv1.CcxtBroker_v1(
            exchange_id,
            account_type,
            portfolio_id,
            contract_type,
            secret_id,
            bid_ask_im_client=bid_ask_im_client,
            strategy_id=strategy_id,
            market_data=market_data,
            universe_version=universe_version,
            stage=stage,
        )
        # Set order limits manually, bypassing the API.
        broker.market_info = {
            8717633868: {
                "min_amount": 1.0,
                "min_cost": 10.0,
                "amount_precision": 3,
            },
            6051632686: {
                "min_amount": 1.0,
                "min_cost": 10.0,
                "amount_precision": 3,
            },
        }
        return broker

    def setUp(self) -> None:
        super().setUp()
        # Create new mocks from patch's `start()` method.
        self.get_secret_mock: umock.MagicMock = self.get_secret_patch.start()
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        # Set dummy credentials for all tests.
        self.get_secret_mock.return_value = {"apiKey": "test", "secret": "test"}

    def tearDown(self) -> None:
        self.get_secret_patch.stop()
        self.ccxt_patch.stop()
        # Deallocate in reverse order to avoid race conditions.
        super().tearDown()

    def test_apply_prod_limits1(self) -> None:
        """
        Verify that a correct order is not altered.
        """
        # Build orders and broker.
        below_min = False
        order_df = self.get_test_orders(below_min)
        broker = self.get_mock_broker()
        round_mode = "round"
        actual = occoputi.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual)

    def test_apply_prod_limits2(self) -> None:
        """
        Verify that an order below limit is updated.
        """
        # Build orders and broker.
        below_min = True
        order_df = self.get_test_orders(below_min)
        broker = self.get_mock_broker()
        round_mode = "round"
        # Run.
        actual = occoputi.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual)

    def test_apply_prod_limits3(self) -> None:
        """
        Check that the assertion is raised when a number is not rounded.
        """
        # Build orders and broker.
        below_min = False
        order_df = self.get_test_orders(below_min)
        broker = self.get_mock_broker()
        round_mode = "check"
        # Run.
        with self.assertRaises(AssertionError):
            _ = occoputi.apply_cc_limits(order_df, broker, round_mode)

    def test_apply_testnet_limits1(self) -> None:
        """
        Verify that orders are altered on testnet.
        """
        # Build orders and broker.
        below_min = True
        order_df = self.get_test_orders(below_min)
        broker = self.get_mock_broker()
        round_mode = "round"
        # Set broker stage to imitate testnet.
        broker.stage = "local"
        # Run.
        actual = occoputi.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual)
