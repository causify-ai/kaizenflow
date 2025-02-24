#!/usr/bin/env python
"""
Get all open positions for an account.

Example use:

# Get open positions and save them to `shared_data` directory.
> oms/broker/ccxt/scripts/get_ccxt_open_positions.py \
    --exchange 'binance' \
    --contract_type 'futures' \
    --stage 'preprod' \
    --secret_id 4 \
    --log_dir '/shared_data/system_log_dir/'
"""
import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hprint as hprint
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
    parser = obccccut.add_CcxtBroker_cmd_line_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    exchange = args.exchange
    contract_type = args.contract_type
    stage = args.stage
    secret_id = args.secret_id
    log_dir = args.log_dir
    universe_version = args.universe
    secret_identifier = ohsseide.SecretIdentifier(
        exchange, stage, "trading", secret_id
    )
    broker = obccbrin.get_CcxtBroker_exchange_only_instance1(
        universe_version, secret_identifier, log_dir,
    )
    open_positions = broker.get_open_positions()
    _LOG.info("Open positions : %s", hprint.pprint_pformat(open_positions))

if __name__ == "__main__":
    _main(_parse())
