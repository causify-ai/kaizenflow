import asyncio

import ccxt
import pytest

import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hsecrets as hsecret
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.ccxt_broker as occxbrok
import oms.order_example as oordexam


class TestCcxtBroker1(hunitest.TestCase):
    async def run_coroutine1(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """
        Submit orders to a CcxtBroker initialized for coinbase prime.
        """
        market_data, _ = mdata.get_ReplayedTimeMarketData_example3(None)
        strategy = "SAU1"
        # Instantiante a broker with specified exchange.
        exchange = self._log_into_coinbasepro_exchange()
        # TODO(Juraj) mock the API calls.
        broker = occxbrok.CcxtBroker(
            exchange,
            "v5",
            "prod",
            "c27158ee-ac73-49bb-a1f3-ec022cac33c2",
            strategy_id=strategy,
            market_data=market_data,
        )
        # Submit an order.
        order = oordexam.get_order_example4()
        orders = [order]
        await broker.submit_orders(orders)
        # Check fills.
        fills = broker.get_fills()
        self.assertEqual(len(fills), 1)
        actual = str(fills[0])
        expected = r"""Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=1000.3449750508295
                    """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.skip(reason="API key for Coinbase Pro not available.")
    # TODO(Danya): Rewrite as a mock.
    def test_submit_and_fill1(self) -> None:
        """
        Verify that orders are submitted and filled.
        """
        event_loop = None
        hasynci.run(self.run_coroutine1(event_loop), event_loop=event_loop)

    # @pytest.mark.skip(reason="Code in development.")
    def test_unsupported_exchange1(self) -> None:
        """
        Verify that CcxtBroker is not instantiated for exchanges without
        trading methods.
        """
        market_data, _ = mdata.get_ReplayedTimeMarketData_example3(None)
        strategy = "SAU1"
        with self.assertRaises(ValueError):
            broker = occxbrok.CcxtBroker(
                ccxt.coinbase(),
                "v3",
                "test",
                "c27158ee-ac73-49bb-a1f3-ec022cac33c2",
                strategy_id=strategy,
                market_data=market_data,
            )

    @staticmethod
    def _log_into_coinbasepro_exchange() -> ccxt.Exchange:
        """
        Log into coinbasepro and return the corresponding `ccxt.Exchange`
        object.
        """
        # Select credentials for provided exchange.
        credentials = hsecret.get_secret("coinbasepro")
        # Enable rate limit.
        credentials["rateLimit"] = True
        # Create a CCXT Exchange class object.
        exchange = ccxt.coinbasepro(credentials)
        hdbg.dassert(
            exchange.checkRequiredCredentials(),
            msg="Required credentials not passed",
        )
        return exchange
