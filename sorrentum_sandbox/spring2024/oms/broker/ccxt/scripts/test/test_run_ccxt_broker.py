import argparse
import os
import unittest.mock as umock

import pytest

import helpers.hunit_test as hunitest
import oms.broker.ccxt.scripts.run_ccxt_broker as obcsrccbr


class TestRunCcxtBroker1(hunitest.TestCase):
    """
    Smoke test run_ccxt_broker.py by initializing broker used in real
    experiments.
    """

    @pytest.mark.slow("~12 seconds")
    def test1(
        self,
    ) -> None:
        log_dir = os.path.join(self.get_scratch_space(), "logs")
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Assign args to call the function.
        kwargs = {
            "log_dir": log_dir,
            "universe": "v7.4",
            "secret_id": 4,
            "log_level": "DEBUG",
            "parent_order_duration_in_min": 3,
            "num_parent_orders_per_bar": 5,
            "num_bars": 1,
            "clean_up_after_run": False,
            "clean_up_before_run": False,
            "close_positions_using_twap": False,
            "db_stage": "preprod",
            "child_order_execution_freq": "1T",
            "incremental": False,
            "volatility_multiple": [0.75],
            "include_btc_usdt": "false",
        }
        mock_parse = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = mock_parse
        with umock.patch.object(
            obcsrccbr, "_execute_one_bar_using_twap", return_value=None
        ) as mock_execution:
            with umock.patch.object(
                obcsrccbr.obcaccbr.AbstractCcxtBroker, "_set_leverage_for_all_symbols", return_value=None
            ) as mock_leverage:
                with umock.patch.object(
                    obcsrccbr.obcaccbr.AbstractCcxtBroker, "_get_market_info", return_value=None
                ) as mock_market_info:
                    with umock.patch.object(
                        obcsrccbr.obccbrin.icdcl, "get_CcxtSqlRealTimeImClient_example1", return_value=None
                    ) as mock_market_info:
                        with umock.patch.object(
                            obcsrccbr.obccbrin.imvcdcimrdc, "get_bid_ask_realtime_raw_data_reader", return_value=None
                        ) as mock_market_info:
                            with umock.patch.object(
                                obcsrccbr, "_generate_prices_from_data_reader", return_value=None
                            ) as mock_market_info:
                                obcsrccbr._main(mock_argument_parser)
