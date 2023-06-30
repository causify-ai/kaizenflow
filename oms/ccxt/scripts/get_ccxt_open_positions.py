#!/usr/bin/env python
"""
Get all open positions for an account.

Example use:

# Get open positions and save them to `shared_data` directory.
> oms/ccxt/scripts/get_ccxt_open_positions.py \
    --exchange 'binance' \
    --contract_type 'futures' \
    --stage 'preprod' \
    --secret_id 4 \
    --log_dir '/shared_data/system_log_dir/'
"""
import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import oms.ccxt.ccxt_broker_utils as occcbrut

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--exchange",
        action="store",
        required=True,
        type=str,
        help="Name of the exchange, e.g. 'binance'.",
    )
    parser.add_argument(
        "--contract_type",
        action="store",
        required=True,
        type=str,
        help="'futures' or 'spot'. Note: only futures contracts are supported.",
    )
    parser.add_argument(
        "--stage",
        action="store",
        required=True,
        type=str,
        help="Stage to run at: local, preprod, prod.",
    )
    parser.add_argument(
        "--secret_id",
        action="store",
        required=True,
        type=int,
        help="ID of the API Keys to use as they are stored in AWS SecretsManager.",
    )
    parser.add_argument(
        "--log_dir",
        action="store",
        type=str,
        required=True,
        help="Log dir to save open positions info.",
    )
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
    # Initialize broker.
    broker = occcbrut.get_broker(exchange, contract_type, stage, secret_id)
    # Get open positions.
    occcbrut.get_ccxt_open_positions(broker, log_dir, exchange, contract_type)


if __name__ == "__main__":
    _main(_parse())
