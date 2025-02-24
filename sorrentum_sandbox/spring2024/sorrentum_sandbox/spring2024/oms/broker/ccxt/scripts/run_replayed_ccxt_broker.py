#!/usr/bin/env python

# TODO(gp): This script should only use Broker abstract interface.
"""
Run the order submission via CcxtBroker in an async manner.

Example use:

> oms/broker/ccxt/scripts/run_replayed_ccxt_broker.py \
    --log_dir Replay_experiment_1 \
    --replayed_dir /shared_data/ecs/test/tokyo_broker_only/2024/01/10/20240110_2 \
    --secret_id 4 \
    --universe 'v7.4' \
    -v DEBUG
"""
import argparse
import asyncio
import logging
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hwall_clock_time as hwacltim
import market_data.market_data_example as mdmadaex
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.ccxt_broker_utils as obccbrut
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--secret_id",
        required=False,
        default=4,
        type=int,
        help="Secret ID.",
    )
    parser.add_argument(
        "--replayed_dir",
        action="store",
        required=True,
        type=str,
        default=None,
        help="Logged experiment directory, used for replaying a previously ran experiment.",
    )
    parser.add_argument(
        "--log_dir",
        action="store",
        required=True,
        type=str,
        help="Directory path where log files will be saved.",
    )
    parser.add_argument(
        "--universe",
        action="store",
        required=True,
        type=str,
        help="Version of the universe.",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _execute_one_bar_using_twap(
    args: Dict,
    broker: obccccbr.CcxtBroker,
    execution_freq: str,
    orders: List[oordorde.Order],
    event_loop: asyncio.AbstractEventLoop,
    *,
    close_positions: bool = False,
    previous_start_timestamp: Optional[pd.Timestamp] = None,
    orders_direction: Optional[str] = None,
) -> pd.Timestamp:
    """
    Generate random orders and submit them in a TWAP manner.

    :return: start timestamp of the parent orders
    """
    # # Ceil the timestamp to the nearest minute so end_timestamp can be calculated correctly.
    # start_timestamp = pd.Timestamp.utcnow().ceil('T')
    # Align start_timestamp to a 5 min grid.
    # TODO(Danya): CMTask4860.
    if previous_start_timestamp is None:
        start_timestamp = pd.Timestamp.utcnow().ceil("5T")
    else:
        start_timestamp = previous_start_timestamp + pd.Timedelta(minutes=5)
    _LOG.debug(str(orders))
    hdbg.dassert_no_duplicates([order.asset_id for order in orders])
    # TODO(Danya): A hack to allow correct logging of multiple parent orders
    hwacltim.set_current_bar_timestamp(orders[0].creation_timestamp)
    order_type = "price@custom_twap"
    hasynci.run(
        broker.submit_orders(
            orders,
            order_type,
        ),
        event_loop,
        close_event_loop=False,
    )
    return start_timestamp


def _main(parser: argparse.ArgumentParser) -> None:
    # Initialize time log for in-script operations.
    args = parser.parse_args()
    # Read args from replayed_dir for replay experiment.
    args_logfile = os.path.join(args.replayed_dir, "args.json")
    args_dict = hio.from_json(args_logfile)
    # Set arguments from the log file.
    _LOG.debug("Reading argument from logs.")
    args.clean_up_before_run = args_dict["clean_up_before_run"]
    args.clean_up_after_run = args_dict["clean_up_after_run"]
    args.num_parent_orders_per_bar = args_dict["num_parent_orders_per_bar"]
    args.num_bars = args_dict["num_bars"]
    args.child_order_execution_freq = args_dict["child_order_execution_freq"]
    args.close_positions_using_twap = args_dict["close_positions_using_twap"]
    if "volatility_multiple" in args_dict:
        args.volatility_multiple = args_dict["volatility_multiple"]
    else:
        args.volatility_multiple = [0.75, 0.7, 0.6, 0.8, 1.0]
    # TODO(Toma): add `fill_percents` for `get_CcxtReplayedExchangeBroker` as a parameter to `args.json`.
    log_dir = args.log_dir
    universe = args.universe
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Get parent orders to replay.
    with hasynci.solipsism_context() as event_loop:
        # Create the log directory.
        hio.create_dir(log_dir, incremental=False, abort_if_exists=True)
        # Log args.
        args_logfile = os.path.join(args.log_dir, "args.json")
        hio.to_json(args_logfile, vars(args))
        reader = obcccclo.CcxtLogger(args.replayed_dir)
        oms_parent_order = reader.load_oms_parent_order(
            convert_to_dataframe=False
        )
        replayed_orders = obccccut.create_parent_orders_from_json(
            oms_parent_order,
            args.num_parent_orders_per_bar,
            update_time=False,
        )
        # we will be going back in time to replay the experiments, so we will use
        # the first creation timestamp as a starting point.
        start_timestamp = replayed_orders[0].creation_timestamp
        # `MarketData` is not strictly needed to talk to exchange, but since it is
        #  required to init the `Broker` we pass something to make it work.
        # An asset id of ETH just to create market data.
        asset_ids = [1464553467]
        (
            market_data,
            get_wall_clock_time,
        ) = mdmadaex.get_ReplayedTimeMarketData_example2(
            event_loop,
            start_timestamp,
            start_timestamp + pd.Timedelta(minutes=5),
            0,
            asset_ids,
        )
        # Initialize broker for the trading account.
        secret_id = args.secret_id
        child_order_execution_freq = args.child_order_execution_freq
        if len(args.volatility_multiple) == 1:
            volatility_multiple = args.volatility_multiple[0]
        else:
            volatility_multiple = args.volatility_multiple
        broker = obccbrin.get_CcxtReplayedExchangeBroker(
            secret_id,
            log_dir,
            replayed_dir=args.replayed_dir,
            market_data=market_data,
            event_loop=event_loop,
            universe=universe,
            # TODO(Toma): add `fill_percents` as a parameter to `args.json`. Hardcoded to fill all orders fully for now.
            fill_percents=1.0,
            volatility_multiple=volatility_multiple,
        )
        # Clean up before running the script.
        if args.clean_up_before_run:
            _LOG.debug("Cleaning up before running the script.")
            # TODO(Vlad): Temporarily hardcoded parameters.
            obccbrut.flatten_ccxt_account(
                broker,
                dry_run=False,
                assert_on_non_zero_positions=False,
            )
        try:
            previous_start_timestamp = None
            # orders_direction = "buy"
            for bar in range(args.num_bars):
                start = bar * args.num_parent_orders_per_bar
                orders = replayed_orders[
                    start : start + args.num_parent_orders_per_bar
                ]
                previous_start_timestamp = _execute_one_bar_using_twap(
                    args,
                    broker,
                    child_order_execution_freq,
                    orders,
                    event_loop,
                    previous_start_timestamp=previous_start_timestamp,
                )
                # Switch between buy and sell orders in order to avoid position build-up.
                # orders_direction = "sell" if orders_direction == "buy" else "buy"
        except Exception as e:
            raise e
        # Run the order submission but flatten in case some positions
        #  remained open.
        finally:
            # Clean up after running the script.
            if args.clean_up_after_run:
                _LOG.debug("Cleaning up after running the script.")
                obccbrut.flatten_ccxt_account(
                    broker,
                    dry_run=False,
                    assert_on_non_zero_positions=False,
                )


if __name__ == "__main__":
    seed = int(pd.Timestamp.now().timestamp())
    np.random.seed(seed)
    _LOG.debug("seed=%s", seed)
    _main(_parse())
