#!/usr/bin/env python
"""
Load and validate data within a specified time period from a CSV file.

# Load OHLCV data for binance:
> load_and_validate.py \
    --start_timestamp '2022-10-20 12:00:00+00:00' \
    --end_timestamp '2022-10-21 12:00:00+00:00' \
    --source_dir 'binance_data' \
    --dataset_signature 'bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0'
"""
import argparse
import logging
import os
from datetime import timedelta
from typing import Any, Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.common.client as ssacocli
import sorrentum_sandbox.common.validate as ssacoval
import sorrentum_sandbox.examples.binance.validate as ssesbiva

_LOG = logging.getLogger(__name__)


# #############################################################################
# CsvClient
# #############################################################################


class CsvClient(ssacocli.DataClient):
    """
    Class for loading CSV data from local filesystem into main memory.
    """

    def __init__(self, source_dir: str) -> None:
        """
        Constructor.

        :param source_dir: path to source data from.
        """
        self.source_dir = source_dir

    def load(
        self,
        dataset_signature: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Load CSV data specified by a unique signature from a desired source
        directory for a specified time period.

        The method assumes data having a 'timestamp' column.
        """
        dataset_signature += ".csv"
        source_path = os.path.join(self.source_dir, dataset_signature)
        data = pd.read_csv(source_path)
        # Filter by [start_timestamp, end_timestamp).
        if start_timestamp:
            hdateti.dassert_has_tz(start_timestamp)
            start_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
                start_timestamp
            )
            data = data[data.timestamp >= start_timestamp_as_unix]
        if end_timestamp:
            hdateti.dassert_has_tz(end_timestamp)
            end_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
                end_timestamp
            )
            data = data[data.timestamp < end_timestamp_as_unix]
        return data


# #############################################################################
# Script.
# #############################################################################


def _add_load_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. 2022-02-09 10:00:00+00:00",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--source_dir",
        action="store",
        required=True,
        type=str,
        help="Absolute path to the directory to source data from",
    )
    parser.add_argument(
        "--dataset_signature",
        action="store",
        required=True,
        type=str,
        help="Signature of the dataset (uniquely specifies a particular data set)",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_load_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(use_exec_path=True)
    # Convert timestamps.
    start_timestamp = pd.Timestamp(args.start_timestamp)
    end_timestamp = pd.Timestamp(args.end_timestamp)
    # Load data.
    csv_client = CsvClient(args.source_dir)
    data = csv_client.load(
        args.dataset_signature,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    # Validate data.
    empty_dataset_check = ssesbiva.EmptyDatasetCheck()
    # Conforming to the (a, b] interval convention, remove 1 minute from the
    # end_timestamp.
    gaps_in_timestamp_check = ssesbiva.GapsInTimestampCheck(
        start_timestamp, end_timestamp - timedelta(minutes=1)
    )
    dataset_validator = ssacoval.SingleDatasetValidator(
        [empty_dataset_check, gaps_in_timestamp_check]
    )
    dataset_validator.run_all_checks([data])


if __name__ == "__main__":
    _main(_parse())
