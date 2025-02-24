#!/usr/bin/env python

"""
Import as:

import im.ib.connect.devops.sanity_check_ib as imicdschib
"""

# TODO(*): Move to ib/connect
"""
Connect to IB TWS to check if it works.
"""

import argparse
import datetime
import logging
import os
import sys
import time

import ib_insync

import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def get_es_data(ib: ib_insync.ib.IB) -> None:
    contract = ib_insync.Future("ES", "202103", "GLOBEX", includeExpired=True)
    _LOG.info("Getting data for contract=%s", contract)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=datetime.date(2021, 2, 1),
        durationStr="1 D",
        barSizeSetting="1 hour",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )
    _LOG.info(ib_insync.util.df(bars).head())


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.shutup_chatty_modules()
    # Connecting to IB gateway.
    ib = ib_insync.IB()
    host = os.environ["IB_GW_CONNECTION_HOST"]
    port = os.environ["IB_GW_CONNECTION_PORT"]
    rc = -1
    for i in range(args.num_attempts):
        _LOG.info(
            "Connecting to IB %s:%s, attempt %s/%s",
            host,
            port,
            i + 1,
            args.num_attempts,
        )
        try:
            ib.connect(host=host, port=port)
            get_es_data(ib)
            _LOG.info("Success")
            rc = 0
        except (ConnectionError, TimeoutError) as exception:
            _LOG.warning("Failed: %s", exception)
            time.sleep(1)
            continue
        break
    _LOG.info("Disconnecting IB")
    ib.disconnect()
    sys.exit(rc)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--num_attempts",
        action="store",
        default=100,
        type=int,
        help="Number of attempts to connect to IB",
    )
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
