#!/usr/bin/env python
"""
Flatten all open positions in the account using CCXT.

Example use:

# Flatten futures live account and assert if some positions are not completely
# closed (i.e. holdings not brought to zero).
> oms/broker/ccxt/scripts/flatten_ccxt_account.py \
    --log_dir ./flatten_log \
    --exchange 'binance' \
    --contract_type 'futures' \
    --stage 'preprod' \
    --secret_id 4 \
    --universe "v7.4" \
    --assert_on_non_zero
"""
import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.ccxt_broker_utils as obccbrut
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.hsecrets.secret_identifier as ohsseide

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--assert_on_non_zero_positions",
        action="store_true",
        required=False,
        help="Assert if the open positions failed to close completely.",
    )
    parser = obccccut.add_CcxtBroker_cmd_line_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    args = vars(args)
    hdbg.init_logger(verbosity=args["log_level"], use_exec_path=True)
    exchange = args["exchange"]
    args["contract_type"]
    stage = args["stage"]
    log_dir = args["log_dir"]
    secret_id = args["secret_id"]
    universe_version = args["universe"]
    assert_on_non_zero_positions = args["assert_on_non_zero_positions"]
    secret_identifier = ohsseide.SecretIdentifier(
        exchange, stage, "trading", secret_id
    )
    broker = obccbrin.get_CcxtBroker_exchange_only_instance1(
        universe_version, secret_identifier, log_dir,
    )
    obccbrut.flatten_ccxt_account(
        broker,
        dry_run=False,
        assert_on_non_zero_positions=assert_on_non_zero_positions,
    )


if __name__ == "__main__":
    _main(_parse())
