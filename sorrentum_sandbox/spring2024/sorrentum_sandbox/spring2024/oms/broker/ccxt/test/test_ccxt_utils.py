import logging
import pprint
import unittest.mock as umock
from typing import List, Optional

import numpy as np
import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.hsecrets.secret_identifier as ohsseide
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# The value is reused in various place for interface reasons.
_UNIVERSE_VERSION = "v7"

# Columns returned by RawDataReader.
_TEST_RAW_BID_ASK_COLS = [
    "timestamp",
    "currency_pair",
    "exchange_id",
    "bid_size_l1",
    "ask_size_l1",
    "bid_price_l1",
    "ask_price_l1",
    "end_download_timestamp",
    "knowledge_timestamp",
]

_TEST_BID_ASK_COLS = [
    "id",
    "timestamp",
    "asset_id",
    "bid_size_l1",
    "ask_size_l1",
    "bid_price_l1",
    "ask_price_l1",
    "full_symbol",
    "end_download_timestamp",
    "knowledge_timestamp",
]

_ASSET_ID_SYMBOL_MAPPING = {
    1464553467: "binance::ETH_USDT",
    1467591036: "binance::BTC_USDT",
    6051632686: "binance::APE_USDT",
}


_DUMMY_MARKET_INFO = {
    1464553467: {"amount_precision": 3, "max_leverage": 1},
    1467591036: {"amount_precision": 3, "max_leverage": 1},
    6051632686: {"amount_precision": 3, "max_leverage": 1},
}


# #############################################################################
# Prepare data for tests
# #############################################################################


def _get_test_order() -> List[oordorde.Order]:
    """
    Build toy list of 1 order for tests.
    """
    # Prepare test data.
    order_str = "Order: order_id=0 creation_timestamp=2022-08-05 10:36:44.976104-04:00\
    asset_id=1464553467 type_=price@twap start_timestamp=2022-08-05 10:36:44.976104-04:00\
    end_timestamp=2022-08-05 10:38:44.976104-04:00 curr_num_shares=0.0 diff_num_shares=0.121\
    tz=America/New_York extra_params={}"
    # Get orders.
    orders = oordorde.orders_from_string(order_str)
    return orders


def _get_test_order_fills1() -> List[oordorde.Order]:
    """
    Get CCXT order structures for child orders associated with
    `_get_test_order` on the "buy" side.

    `info` field is not included to make fills more readable.
    """
    fills = [
        {
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "buy",
            "price": 1783.455,
            "stopPrice": "",
            "amount": 0.14,
            "cost": 249.6837,
            "average": 1783.455,
            "filled": 0.14,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
        {
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "buy",
            "price": 1800.0,
            "stopPrice": "",
            "amount": 0.14,
            "cost": 252.0,
            "average": 1800.0,
            "filled": 0.14,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
    ]
    return fills


def _get_test_order_fills2() -> List[oordorde.Order]:
    """
    Get CCXT order structures for child orders associated with
    `_get_test_order` on the "sell" side.

    `info` field is not included to make fills more readable.
    """
    fills = [
        {
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "sell",
            "price": 1783.455,
            "stopPrice": "",
            "amount": 0.14,
            "cost": 249.6837,
            "average": 1783.455,
            "filled": 0.14,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
        {
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "sell",
            "price": 1800.0,
            "stopPrice": "",
            "amount": 0.14,
            "cost": 252.0,
            "average": 1800.0,
            "filled": 0.14,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
    ]
    return fills


def get_test_bid_ask_data() -> pd.DataFrame:
    """
    Build artificial bid / ask data for the test.
    """
    df = pd.DataFrame(
        columns=[
            "id",
            "timestamp",
            "asset_id",
            "bid_size_l1",
            "ask_size_l1",
            "bid_price_l1",
            "ask_price_l1",
            "full_symbol",
            "end_download_timestamp",
            "knowledge_timestamp",
        ],
        # fmt: off
        data=[
            [
                0,
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                1464553467,
                30,
                40,
                50,
                60,
                "binance::ETH_USDT",
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York")
            ],
            [
                1,
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                1464553467,
                31,
                41,
                51,
                61,
                "binance::ETH_USDT",
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York")
            ],
            [
                2,
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                1467591036,
                10,
                20,
                30,
                40,
                "binance::BTC_USDT",
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York")
            ],
            [
                3,
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                1467591036,
                12,
                22,
                32,
                42,
                "binance::BTC_USDT",
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York")
            ],
        ]
        # pylint: enable=line-too-long
        # fmt: on
    )
    df = df.set_index("timestamp")
    return df


def _generate_raw_data_reader_bid_ask_data(
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    *,
    bid_ask_levels: List[int] = None,
    random_seed: int = 0,
    # This function is used to mock RawDataReader's load_db_table,
    # the parameters are added to match its signature.
    deduplicate: bool = True,
    subset: Optional[List[str]],
) -> pd.DataFrame:
    """
    Return dummy bid/ask data for the given period.

    The function emulates what RawDataReader
    returns for dataset signature
    realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0.
    (except for the universe size).
    See Master_raw_data_gallery notebook to preview what the format should look like.

    :param start_ts: start of the interval to generate
    :param end_ts: end of the interval to generate
    """
    # Set seed to generate predictable values.
    np.random.seed(random_seed)
    # Default value of bid ask level should be None, so setting default value expicitly.
    # ref. https://stackoverflow.com/questions/18141652/python-function-with-default-list-argument
    bid_ask_levels = [1] if bid_ask_levels is None else bid_ask_levels
    start_ts_unix = hdateti.convert_timestamp_to_unix_epoch(start_ts)
    end_ts_unix = hdateti.convert_timestamp_to_unix_epoch(end_ts)
    data = []
    for asset_id, full_symbol in _ASSET_ID_SYMBOL_MAPPING.items():
        currency_pair = full_symbol.lstrip("binance::")
        bid_size_l1, ask_size_l1, bid_price_l1, ask_price_l1 = (
            np.random.randint(10, 40) for _ in range(4)
        )
        # Generate row at every 500 miliseconds timestmap.
        for ts_unix in range(start_ts_unix, end_ts_unix + 500, 500):
            row = [
                ts_unix,
                currency_pair,
                "binance",
                bid_size_l1,
                ask_size_l1,
                bid_price_l1,
                ask_price_l1,
                hdateti.convert_unix_epoch_to_timestamp(ts_unix),
                hdateti.convert_unix_epoch_to_timestamp(ts_unix),
            ]
            data.append(row)
    df = pd.DataFrame(columns=_TEST_RAW_BID_ASK_COLS, data=data).set_index(
        "timestamp"
    )
    return df


# #############################################################################


class Test_roll_up_child_order_fills_into_parent(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test child order fills aggregation for "buy".
        """
        # Get test order and corresponding fills.
        parent_order = _get_test_order()[0]
        child_order_fills = _get_test_order_fills1()
        # Calculate the fill amount and price.
        (
            fill_amount,
            fill_price,
        ) = obccccut.roll_up_child_order_fills_into_parent(
            parent_order, child_order_fills
        )
        self.assertEqual(fill_amount, 0.28)
        self.assertEqual(fill_price, 1791.7274999999997)

    def test2(self) -> None:
        """
        Test child order fills aggregation for non-filled orders.
        """
        # Get test order and corresponding fills.
        parent_order = _get_test_order()[0]
        child_order_fills = _get_test_order_fills1()
        # Assign empty value to fill amount.
        child_order_fills[0]["filled"] = 0
        child_order_fills[1]["filled"] = 0
        # Calculate the fill amount and price.
        (
            fill_amount,
            fill_price,
        ) = obccccut.roll_up_child_order_fills_into_parent(
            parent_order, child_order_fills
        )
        self.assertEqual(fill_amount, 0)
        self.assertTrue(np.isnan(fill_price))

    def test3(self) -> None:
        """
        Test child order fills aggregation for "sell".
        """
        # Get test order and corresponding fills.
        parent_order = _get_test_order()[0]
        child_order_fills = _get_test_order_fills2()
        # Calculate the fill amount and price.
        (
            fill_amount,
            fill_price,
        ) = obccccut.roll_up_child_order_fills_into_parent(
            parent_order, child_order_fills
        )
        self.assertEqual(fill_amount, -0.28)
        self.assertEqual(fill_price, 1791.7274999999997)

    def test4(self) -> None:
        """
        Test assertion on mixed buy/sell child orders in aggregation.
        """
        parent_order = _get_test_order()[0]
        child_order_buy_fills = _get_test_order_fills1()
        child_order_sell_fills = _get_test_order_fills2()
        child_order_fills = child_order_buy_fills + child_order_sell_fills
        with np.testing.assert_raises(AssertionError):
            obccccut.roll_up_child_order_fills_into_parent(
                parent_order, child_order_fills
            )

    def test5(self) -> None:
        """
        Test child order fills aggregation for "sell", with specified rounding.
        """
        # Get test order and corresponding fills.
        parent_order = _get_test_order()[0]
        child_order_fills = _get_test_order_fills2()
        # Calculate the fill amount and price.
        (
            fill_amount,
            fill_price,
        ) = obccccut.roll_up_child_order_fills_into_parent(
            parent_order, child_order_fills, price_quantization=2
        )
        self.assertEqual(fill_amount, -0.28)
        self.assertEqual(fill_price, 1791.73)


class Test_create_ccxt_exchange(hunitest.TestCase):
    get_secret_patch = umock.patch.object(obccccut.hsecret, "get_secret")
    ccxt_patch = umock.patch.object(obccccut, "ccxt", spec=obccccut.ccxt)
    ccxtpro_patch = umock.patch.object(obccccut, "ccxtpro", spec=obccccut.ccxtpro)

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
        # The order initialization matters here -> since ccxt.pro is included in ccxt
        #  it needs to go first.
        self.ccxtpro_mock: umock.MagicMock = self.ccxtpro_patch.start()
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        # Set dummy credentials for all tests.
        self.get_secret_mock.return_value = {"apiKey": "test", "secret": "test"}

    def tear_down_test(self) -> None:
        self.get_secret_patch.stop()
        self.ccxtpro_patch.stop()
        self.ccxt_patch.stop()

    def test_log_into_exchange1(self) -> None:
        """
        Verify that login is done correctly with `spot` contract type.
        """
        self._test_log_into_exchange_class("trading", "spot")

    def test_log_into_exchange2(self) -> None:
        """
        Verify that login is done correctly with `futures` contract type.
        """
        self._test_log_into_exchange_class("trading", "futures")

    def test_log_into_exchange3(self) -> None:
        """
        Verify that login is done correctly with `sandbox` account type.
        """
        self._test_log_into_exchange_class("sandbox", "futures")

    def _test_log_into_exchange_class(
        self,
        account_type: str,
        contract_type: str,
        *,
        secret_id: int = 1,
    ) -> None:
        """
        Verify login is performed correctly.

        - Verify that login is done correctly with given contract type.
        - Verify constructed secret for obtaining credentials from AWS secrets.
        - Verify that `sandbox` mode is set where applicable.
        """
        exchange_id = "binance"
        stage = "preprod"
        exchange_mock = self.ccxt_mock.binance
        secret_identifier = ohsseide.SecretIdentifier(
            exchange_id, stage, account_type, secret_id
        )
        sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
            secret_identifier,
            contract_type,
            exchange_id,
            account_type,
        )
        # Check exchange mock assertions.
        actual_args = pprint.pformat(tuple(exchange_mock.call_args))
        call_args_dict = {"apiKey": "test", "rateLimit": False, "secret": "test"}
        if contract_type == "futures":
            call_args_dict["options"] = {"defaultType": "future"}
        expected_args = pprint.pformat(((call_args_dict,), {}))
        self.assert_equal(actual_args, expected_args, fuzzy_match=True)
        # We initialize both _sync and _async object using single function call
        # hence ``get_secret()`` should be called once.
        self.assertEqual(self.get_secret_mock.call_count, 1)
        actual_args = tuple(self.get_secret_mock.call_args)
        expected_args = ((f"binance.preprod.{account_type}.{secret_id}",), {})
        self.assertEqual(actual_args, expected_args)
        # Check broker assertions.
        actual_method_calls = str(async_exchange.method_calls)
        expected_method_call = "call.set_sandbox_mode(True)"
        if account_type == "sandbox":
            self.assertIn(expected_method_call, actual_method_calls)
        else:
            self.assertNotIn(expected_method_call, actual_method_calls)


class Test_drop_bid_ask_duplicates(hunitest.TestCase):
    def test1(self) -> None:
        """
        Verify that bid/ask data with no duplicates is not altered.
        """
        # Generate data.
        start_ts = pd.Timestamp(
            "2024-02-20 10:35:46-04:00", tz="America/New_York"
        )
        end_ts = pd.Timestamp("2024-02-20 10:35:47-04:00", tz="America/New_York")
        bid_ask_data = _generate_raw_data_reader_bid_ask_data(
            start_ts, end_ts, subset=None
        )
        # Drop duplicates.
        bid_ask_processed, duplicated_rows = obccccut.drop_bid_ask_duplicates(
            bid_ask_data
        )
        # Verify that the dataframe is not altered.
        bid_ask_processed = hpandas.df_to_str(bid_ask_processed)
        bid_ask_data = hpandas.df_to_str(bid_ask_data)
        # Check.
        self.assertEqual(bid_ask_processed, bid_ask_data)
        self.assertEqual(duplicated_rows, None)

    def test2(self) -> None:
        """
        Verify that a single bid/ask data duplicate is dropped.
        """
        # Generate data.
        start_ts = pd.Timestamp(
            "2024-02-20 10:35:46-04:00", tz="America/New_York"
        )
        end_ts = pd.Timestamp("2024-02-20 10:35:47-04:00", tz="America/New_York")
        bid_ask_data = _generate_raw_data_reader_bid_ask_data(
            start_ts, end_ts, subset=None
        )
        # Add duplicate.
        duplicate = bid_ask_data.iloc[0:1]
        bid_ask_data_duplicated = pd.concat([bid_ask_data, duplicate])
        # Drop duplicates.
        non_duplicated_rows, duplicated_rows = obccccut.drop_bid_ask_duplicates(
            bid_ask_data_duplicated
        )
        # Convert to string for comparison.
        act_duplicated_rows = hpandas.df_to_str(duplicated_rows)
        exp_duplicated_rows = hpandas.df_to_str(duplicate)
        # Check.
        self.assertEqual(act_duplicated_rows, exp_duplicated_rows)

    def test3(self) -> None:
        """
        Verify that the error is raised if number of duplicates is above limit.
        """
        # Generate data.
        start_ts = pd.Timestamp(
            "2024-02-20 10:35:46-04:00", tz="America/New_York"
        )
        end_ts = pd.Timestamp("2024-02-20 10:35:47-04:00", tz="America/New_York")
        bid_ask_data = _generate_raw_data_reader_bid_ask_data(
            start_ts, end_ts, subset=None
        )
        # Add duplicate.
        duplicate = bid_ask_data.iloc[0:3]
        bid_ask_data_duplicated = pd.concat([bid_ask_data, duplicate])
        # Check.
        # Verify that the method raises the assertion.
        with self.assertRaises(AssertionError):
            obccccut.drop_bid_ask_duplicates(
                bid_ask_data_duplicated, max_num_dups=2
            )
        # Check the assertion message content.
        try:
            obccccut.drop_bid_ask_duplicates(
                bid_ask_data_duplicated, max_num_dups=2
            )
        except AssertionError as e:
            exp_error = r"""
################################################################################
* Failed assertion *
3 <= 2
Number of duplicated rows over 2
################################################################################
            """
            self.assert_equal(str(e), exp_error)
