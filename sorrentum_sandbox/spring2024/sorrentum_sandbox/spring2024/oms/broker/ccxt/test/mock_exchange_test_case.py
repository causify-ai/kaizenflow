"""
Import as:

import oms.broker.ccxt.test.mock_exchange_test_case as obcctmetc
"""
import asyncio
import datetime
import pprint
import unittest.mock as umock
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hunit_test as hunitest
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu
import market_data.market_data_example as mdmadaex
import market_data.replayed_market_data as mdremada
import oms.broker.broker as obrobrok
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.mock_ccxt_exchange as obcmccex
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.child_order_quantity_computer as ochorquco
import oms.fill as omfill
import oms.hsecrets.secret_identifier as ohsseide
import oms.limit_price_computer as oliprcom
import oms.order.order as oordorde


def _generate_test_bid_ask_data(
    start_ts: pd.Timestamp,
    asset_id_symbol_mapping: Dict[int, str],
    num_minutes: int,
) -> pd.DataFrame:
    """
    Generate artificial bid/ask data for testing.

    :param start_ts: timestamp of the first generated row
    :param num_minutes: how many minutes of bid/ask data to generate #
        currency_pair exchange_id end_download_timestamp
        knowledge_timestamp bid_size_l1 ask_size_l1 bid_price_l1
        ask_price_l1 ccxt_symbols asset_id timestamp 2023-08-11
        12:49:52.835000+00:00 GMT_USDT binance 2023-08-11
        12:49:52.975836+00:00 2023-08-11 12:49:53.205151+00:00
        38688.0 279499.0 0.2034 0.2035
        GMT/USDT:USDT 1030828978 2023-08-11 12:49:52.835000+00:00
        GMT_USDT binance 2023-08-11 12:49:53.482785+00:00 2023-08-11
        12:49:55.324804+00:00 38688.0 279499.0 0.2034
        0.2035 GMT/USDT:USDT 1030828978
    """
    # Set seed to generate predictable values.
    np.random.seed(0)
    data = []
    for asset_id, full_symbol in asset_id_symbol_mapping.items():
        bid_size_l1, ask_size_l1, bid_price_l1, ask_price_l1 = (
            np.random.randint(10, 40) for _ in range(4)
        )
        for i in range(num_minutes):
            timestamp_iter = start_ts + datetime.timedelta(minutes=i)
            row = [
                i,
                timestamp_iter,
                asset_id,
                bid_size_l1,
                ask_size_l1,
                bid_price_l1,
                ask_price_l1,
                full_symbol,
                timestamp_iter,
                timestamp_iter,
            ]
            data.append(row)
            timestamp_iter += datetime.timedelta(seconds=1)
            row = [
                i,
                timestamp_iter,
                asset_id,
                bid_size_l1,
                ask_size_l1,
                bid_price_l1,
                ask_price_l1,
                full_symbol,
                timestamp_iter,
                timestamp_iter,
            ]
            data.append(row)
    df = pd.DataFrame(columns=obcttcut._TEST_BID_ASK_COLS, data=data).set_index(
        "timestamp"
    )
    return df


def _get_test_broker(
    bid_ask_im_client: Optional[icdc.ImClient],
    market_data: mdremada.ReplayedMarketData,
    mock_exchange: obcmccex.MockCcxtExchange,
    limit_price_computer: oliprcom.AbstractLimitPriceComputer,
    child_order_quantity_computer: ochorquco.AbstractChildOrderQuantityComputer,
    *,
    log_dir: Optional[str] = "mock/log",
    num_trades_per_order: int = 1,
) -> obccccbr.CcxtBroker:
    """
    Build the mocked `AbstractCcxtBroker` for unit testing.

    See `AbstractCcxtBroker` for params description.
    """
    universe_version = obcttcut._UNIVERSE_VERSION
    account_type = "trading"
    contract_type = "futures"
    secret_id = 1
    exchange_id = "binance"
    stage = "preprod"
    portfolio_id = "ccxt_portfolio_mock"
    secret_id = ohsseide.SecretIdentifier(
        exchange_id, stage, account_type, secret_id
    )
    with umock.patch.object(
        obcaccbr.AbstractCcxtBroker,
        "_get_market_info",
        return_value=obcmccex._DUMMY_MARKET_INFO,
    ):
        # Inject mock raw data reader
        mock_data_reader = umock.MagicMock()
        mock_data_reader.load_db_table = (
            obcttcut._generate_raw_data_reader_bid_ask_data
        )
        # Create logger.
        logger = obcccclo.CcxtLogger(log_dir, mode="write")
        # TODO(Juraj): this is a hacky way, we mock ccxt lib meaning
        # the broker initially received mock exchange and then we replace
        # it with fake.
        broker = obccccbr.CcxtBroker(
            exchange_id=exchange_id,
            account_type=account_type,
            portfolio_id=portfolio_id,
            contract_type=contract_type,
            secret_identifier=secret_id,
            bid_ask_im_client=bid_ask_im_client,
            bid_ask_raw_data_reader=mock_data_reader,
            strategy_id="dummy_strategy_id",
            market_data=market_data,
            universe_version=universe_version,
            stage=stage,
            log_dir=log_dir,
            logger=logger,
            limit_price_computer=limit_price_computer,
            max_order_submit_retries=3,
            child_order_quantity_computer=child_order_quantity_computer,
            sync_exchange=mock_exchange,
            async_exchange=mock_exchange,
        )
        return broker


class MockExchangeTestCase(hunitest.TestCase):
    # Mock logging as it is not necessary.
    # TODO(gp): Re-enable since we should always exercise the logging in the same
    # way it runs in real code.
    mock_log_last_wave_results_patch = umock.patch.object(
        obccccbr.CcxtBroker,
        "_log_last_wave_results",
        autospec=True,
        spec_set=True,
    )
    mock_log_oms_parent_orders_patch = umock.patch.object(
        obcccclo.CcxtLogger, "log_oms_parent_orders", autospec=True, spec_set=True
    )

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        omfill.Fill._fill_id = 0
        oordorde.Order._order_id = 0
        obrobrok.Broker._submitted_order_id = 0
        self.mock_log_last_wave_results: umock.MagicMock = (
            self.mock_log_last_wave_results_patch.start()
        )
        self.mock_log_oms_parent_orders: umock.MagicMock = (
            self.mock_log_oms_parent_orders_patch.start()
        )
        # Return None because we don't need logging.
        self.mock_log_last_wave_results.return_value = None
        self.mock_log_oms_parent_orders.return_value = None

    def tear_down_test(self) -> None:
        self.mock_log_last_wave_results_patch.stop()
        self.mock_log_oms_parent_orders_patch.stop()

    # //////////////////////////////////////////////////////////////////////////

    def get_test_broker(
        self,
        creation_timestamp: pd.Timestamp,
        positions: Dict,
        event_loop: asyncio.AbstractEventLoop,
        fill_percents: Union[float, List[float]],
        limit_price_computer: oliprcom.AbstractLimitPriceComputer,
        child_order_quantity_computer: ochorquco.AbstractChildOrderQuantityComputer,
        *,
        bid_ask_df: pd.DataFrame = None,
        num_trades_per_order: int = 1,
        num_exceptions: int = 0,
        **broker_kwargs,
    ) -> Tuple[List[oordorde.Order], obccccbr.CcxtBroker]:
        """
        Get a fully initialized broker object for unit testing.

        Base method used by test cases.

        :param orders: orders to place
        :param positions: simulated positions the experiment should
            start with, example structure found can be in
            MockCcxtExchange
        :param fill_percents:
          - if list: how much % of the child order is filled in each wave,
            each element of the list is used for single wave
          - if float: how much % of the child order is filled, the same for all waves
        :param num_trades_per_order: number of trades to be simulated
            for child order
        :return: fully initialized broker object
        """
        num_minutes = 10
        if bid_ask_df is None:
            bid_ask_df = _generate_test_bid_ask_data(
                creation_timestamp,
                obcttcut._ASSET_ID_SYMBOL_MAPPING,
                num_minutes,
            )
        bid_ask_im_client = self._get_mock_bid_ask_im_client(bid_ask_df)
        # The second element in the returned tuple is a callable.
        (
            market_data,
            get_wall_clock_time,
        ) = mdmadaex.get_ReplayedTimeMarketData_example2(
            event_loop,
            # For solipsism to work correctly it is important to set the
            # correct time interval.
            creation_timestamp,
            creation_timestamp + pd.Timedelta(minutes=num_minutes),
            0,
            list(obcttcut._ASSET_ID_SYMBOL_MAPPING.keys()),
        )
        mock_exchange_delay = 2
        mock_exchange = obcmccex.MockCcxtExchange_withErrors(
            num_exceptions,
            mock_exchange_delay,
            event_loop,
            get_wall_clock_time,
            fill_percents,
            num_trades_per_order=num_trades_per_order,
        )
        broker = _get_test_broker(
            bid_ask_im_client,
            market_data,
            mock_exchange,
            limit_price_computer=limit_price_computer,
            child_order_quantity_computer=child_order_quantity_computer,
            num_trades_per_order=num_trades_per_order,
            **broker_kwargs,
        )
        broker._async_exchange._positions = positions
        return broker

    @staticmethod
    def _get_mock_bid_ask_im_client(df: pd.DataFrame) -> icdc.ImClient:
        """
        Get Mock bid / ask ImClient using synthetical data.
        """
        # Get universe.
        universe_mode = "trade"
        vendor = "CCXT"
        version = obcttcut._UNIVERSE_VERSION
        universe = ivcu.get_vendor_universe(
            vendor,
            universe_mode,
            version=version,
            as_full_symbol=True,
        )
        # Build ImClient.
        im_client = icdc.DataFrameImClient(df, universe)
        return im_client

    @staticmethod
    def _get_test_orders(
        creation_timestamp: pd.Timestamp,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
    ) -> List[oordorde.Order]:
        """
        Build a list of toy orders for unit testing.

        :param creation_timestamp: creation_timestamp to set to the
            order objects
        :param start_timestamp: start timestamp to set to the order
            objects
        :param creation_timestamp: end timestamp to set to the order
            objects
        """
        orders_str = "\n".join(
            [
                f"Order: order_id=0 creation_timestamp={creation_timestamp} asset_id=1464553467 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares=2500.0 diff_num_shares=10 tz=America/New_York extra_params={{}}",
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id=1467591036 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares=1000.0 diff_num_shares=-20.0 tz=America/New_York extra_params={{}}",
            ]
        )
        # Get orders.
        orders = oordorde.orders_from_string(orders_str)
        return orders

    @staticmethod
    def _get_fills_percents(
        n_orders: int,
        perc_per_wave: List[float],
    ) -> List[float]:
        """
        Distribute the fill percents among the orders and waves.

        E.g. if we have 2 orders and [1.0, 0.7] fill percents for each
        wave, where 1.0 is a fill rate for the first wave and 0.7 is for
        the second wave, the result will be [1.0, 1.0, 0.7, 0.7].
        """
        fills_percents = []
        for percent in perc_per_wave:
            fills_percents.extend([percent] * n_orders)
        return fills_percents

    def _test_get_fills(
        self,
        broker: obccccbr.CcxtBroker,
        expected: str,
    ) -> None:
        """
        Test `get_fills()` with async.
        """
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_fills_async()
            fills = hasynci.run(coroutine, event_loop=event_loop)
            actual_fills = pprint.pformat(fills)
            self.assert_equal(actual_fills, expected, fuzzy_match=True)

    def _test_ccxt_fills(
        self,
        broker: obccccbr.CcxtBroker,
        orders: List[oordorde.Order],
        tag: str,
    ) -> List[Dict[Any, Any]]:
        """
        Verify if child order fills are generated correctly.
        """
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_ccxt_fills(orders)
            ccxt_fills = hasynci.run(coroutine, event_loop=event_loop)
        actual = pprint.pformat(ccxt_fills)
        self.check_string(actual, tag=tag, fuzzy_match=True)
        return ccxt_fills

    def _test_ccxt_trades(
        self,
        broker: obccccbr.CcxtBroker,
        ccxt_fills: List[obcmccex.CcxtOrderStructure],
        tag: str,
    ) -> None:
        """
        Verify if CCXT trades are generated correctly.
        """
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_ccxt_trades(ccxt_fills)
            ccxt_trades = hasynci.run(coroutine, event_loop=event_loop)
        actual = pprint.pformat(ccxt_trades)
        self.check_string(actual, tag=tag, fuzzy_match=True)

    def _test_submit_twap_orders(
        self,
        orders: List[oordorde.Order],
        positions: List[Dict],
        fill_percents: Union[float, List[float]],
        limit_price_computer: oliprcom.AbstractLimitPriceComputer,
        child_order_quantity_computer: ochorquco.AbstractChildOrderQuantityComputer,
        *,
        bid_ask_df: pd.DataFrame = None,
        num_trades_per_order: int = 1,
        **broker_kwargs,
    ) -> Tuple[List[oordorde.Order], obccccbr.CcxtBroker]:
        """
        Verify that a TWAP order(s) is submitted correctly.

        Base method used by test cases.

        :param orders: orders to place
        :param positions: simulated positions the experiment should start with,
            example structure found in `MockCcxtExchange`
        :param fill_percents:
          - if list: how much % of the child order is filled in each wave,
            each element of the list is used for single wave
          - if float: how much % of the child order is filled, the same for all waves
        :param num_trades_per_order: number of trades to be simulated for child
            order
        :return: all orders generated by twap_submit_orders and a corresponding
            broker object
        """
        with hasynci.solipsism_context() as event_loop:
            broker = self.get_test_broker(
                orders[0].creation_timestamp,
                positions,
                event_loop,
                fill_percents,
                bid_ask_df=bid_ask_df,
                num_trades_per_order=num_trades_per_order,
                limit_price_computer=limit_price_computer,
                child_order_quantity_computer=child_order_quantity_computer,
                **broker_kwargs,
            )
            execution_freq = "1T"
            # TODO(Juraj): How to set timestamp for the test orders?
            # On one hand we do not want to freeze time but passing real wall
            # clock time might results in irrepeatable test?
            coroutine = broker._submit_twap_orders(
                orders, execution_freq=execution_freq
            )
            receipt, orders = hasynci.run(coroutine, event_loop=event_loop)
            # Check the receipt.
            self.assert_equal(receipt, "order_0")
        return orders, broker

    def _test_submit_orders(
        self,
        orders: List[oordorde.Order],
        orders_type: str,
        positions: Dict,
        fill_percents: Union[float, List[float]],
        limit_price_computer: oliprcom.AbstractLimitPriceComputer,
        child_order_quantity_computer: ochorquco.AbstractChildOrderQuantityComputer,
        *,
        bid_ask_df: pd.DataFrame = None,
        num_trades_per_order: int = 1,
        **broker_kwargs,
    ) -> Tuple[List[oordorde.Order], obccccbr.CcxtBroker]:
        """
        Test the orders submission.

        :param orders: orders to place
        :param orders_type: type of orders to submit, e.g. "price@twap",
            "price@custom_twap", "limit", "market"
        :param positions: simulated positions the experiment should
            start with
        :param fill_percents:
          - if list: how much % of the child order is filled in each wave,
            each element of the list is used for single wave
          - if float: how much % of the child order is filled, the same for all waves
        :param num_trades_per_order: number of trades to be simulated
            for child order
        """
        with hasynci.solipsism_context() as event_loop:
            broker = self.get_test_broker(
                orders[0].creation_timestamp,
                positions,
                event_loop,
                fill_percents,
                bid_ask_df=bid_ask_df,
                num_trades_per_order=num_trades_per_order,
                limit_price_computer=limit_price_computer,
                child_order_quantity_computer=child_order_quantity_computer,
                **broker_kwargs,
            )
            coroutine = broker.submit_orders(
                orders,
                orders_type,
            )
            receipt, orders = hasynci.run(coroutine, event_loop=event_loop)
            # Check the receipt.
            # TODO(Juraj): this does not hold in all cases.
            # self.assert_equal(receipt, "order_0")
        return orders, broker
