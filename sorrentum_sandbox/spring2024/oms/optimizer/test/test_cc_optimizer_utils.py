import unittest.mock as umock

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.hsecrets.secret_identifier as ohsseide
import oms.optimizer.cc_optimizer_utils as ooccoput


class TestCcOptimizerUtils1(hunitest.TestCase):
    get_secret_patch = umock.patch.object(obccccut.hsecret, "get_secret")
    ccxt_patch = umock.patch.object(obccccut, "ccxt", spec=obccccut.ccxt)
    # We don't want to interact with real DB in the tests.
    raw_data_reader_patch = umock.patch.object(
        obcaccbr.imvcdcimrdc, "RawDataReader", create_autospec=True
    )
    mock_timestamp_to_str_patch = umock.patch.object(
        obcccclo.hdateti, "timestamp_to_str", autospec=True, spec_set=True
    )

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
    def get_mock_broker() -> obccccbr.CcxtBroker:
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
        log_dir = "mock/log"
        logger = obcccclo.CcxtLogger(log_dir, mode="write")
        market_data = umock.create_autospec(spec=mdata.MarketData, instance=True)
        secret_id = ohsseide.SecretIdentifier(exchange_id, stage, account_type, 1)
        sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
            secret_id, contract_type, exchange_id, account_type
        )
        # Initialize broker.
        broker = obccccbr.CcxtBroker(
            logger=logger,
            bid_ask_im_client=bid_ask_im_client,
            strategy_id=strategy_id,
            market_data=market_data,
            universe_version=universe_version,
            stage=stage,
            exchange_id=exchange_id,
            account_type=account_type,
            portfolio_id=portfolio_id,
            contract_type=contract_type,
            secret_identifier=secret_id,
            sync_exchange=sync_exchange,
            async_exchange=async_exchange,
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

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Create new mocks from patch's `start()` method.
        self.get_secret_mock: umock.MagicMock = self.get_secret_patch.start()
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        self.raw_data_reader_mock: umock.MagicMock = (
            self.raw_data_reader_patch.start()
        )
        self.mock_timestamp_to_str: umock.MagicMock = (
            self.mock_timestamp_to_str_patch.start()
        )
        # Return random timestamp for logging by mocking.
        self.mock_timestamp_to_str.return_value = pd.Timestamp(
            "2022-08-05 09:30:55+00:00"
        )
        # Set dummy credentials for all tests.
        self.get_secret_mock.return_value = {"apiKey": "test", "secret": "test"}

    def tear_down_test(self) -> None:
        self.get_secret_patch.stop()
        self.ccxt_patch.stop()
        self.raw_data_reader_patch.stop()
        self.mock_timestamp_to_str_patch.stop()

    def test_apply_prod_limits1(self) -> None:
        """
        Verify that a correct order is not altered.
        """
        # Build orders and broker.
        below_min = False
        order_df = self.get_test_orders(below_min)
        broker = self.get_mock_broker()
        round_mode = "round"
        actual = ooccoput.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual, fuzzy_match=True)

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
        actual = ooccoput.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual, fuzzy_match=True)

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
            _ = ooccoput.apply_cc_limits(order_df, broker, round_mode)

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
        actual = ooccoput.apply_cc_limits(order_df, broker, round_mode)
        actual = hpandas.df_to_str(actual)
        self.check_string(actual, fuzzy_match=True)
