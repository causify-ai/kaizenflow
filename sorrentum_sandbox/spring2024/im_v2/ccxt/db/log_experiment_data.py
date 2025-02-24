#!/usr/bin/env python
"""
Load bid/ask data from DB and convert into the same format as data logged
during an experiment using CcxtLogger. The data is used during
Master_bid_ask_execution_analysis as an alternative to the data logged during
an experiment. In the full system run experiment there can be a bar with no
trades, which results in no bid/ask being logged for that period (bid/ask data
is logged only before child order execution).

Use as:
> ./im_v2/ccxt/db/log_experiment_data.py \
   --db_stage 'preprod' \
   --start_timestamp_as_str '20240220_124800' \
   --end_timestamp_as_str '20240220_131500' \
   --universe 'v7.5'
   --data_vendor 'CCXT'
   --log_dir 'tmp_log_dir'
"""
import argparse
import logging

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import oms.broker.ccxt.ccxt_logger as obcccclo

_LOG = logging.getLogger(__name__)


def _log_experiment_data(args) -> None:
    """
    Load bid/ask data and store it in csv format.
    """
    logger = obcccclo.CcxtLogger(args.log_dir, mode="write")
    start_timestamp = hdateti.timestamp_as_str_to_timestamp(
        args.start_timestamp_as_str
    )
    end_timestamp = hdateti.timestamp_as_str_to_timestamp(
        args.end_timestamp_as_str
    )
    bid_ask_raw_data_reader = imvcdcimrdc.get_bid_ask_realtime_raw_data_reader(
        args.db_stage, args.data_vendor, args.universe
    )
    # TODO(Juraj): this should match exactly what happens in ccxt_broker.py
    # consider unifyig through lib function.
    bid_ask_data = bid_ask_raw_data_reader.load_db_table(
        start_timestamp,
        end_timestamp,
        bid_ask_levels=[1],
        # We deduplicate the data at this point, if later down the pipeline an
        # assertion for duplicates is raised, it implies problem with the
        # data.
        deduplicate=True,
        subset=[
            "timestamp",
            "currency_pair",
            "bid_price",
            "bid_size",
            "ask_price",
            "ask_size",
            "level",
        ],
    )
    get_wall_clock_time = lambda: hdateti.get_current_time("UTC")
    logger.log_bid_ask_data(
        get_wall_clock_time, bid_ask_data, log_full_experiment_data=True
    )
    _LOG.info("Experiment data logged successfully.")


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _LOG.info(args)
    _log_experiment_data(args)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--start_timestamp_as_str",
        action="store",
        required=True,
        type=str,
        help="Start of the data interval to log",
    )
    parser.add_argument(
        "--end_timestamp_as_str",
        action="store",
        required=True,
        type=str,
        help="End of the data interval to log",
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use",
    )
    parser.add_argument(
        "--log_dir",
        action="store",
        required=True,
        type=str,
        help="Base path to log data into",
    )
    parser.add_argument(
        "--universe",
        action="store",
        required=True,
        type=str,
        help="Universe used for the bid/ask data",
    ),
    parser.add_argument(
        "--data_vendor",
        action="store",
        required=True,
        type=str,
        help="Vendor of the bid/ask data, e.g. CCXT or Binance",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


if __name__ == "__main__":
    _main(_parse())
