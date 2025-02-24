#!/usr/bin/env python
"""
Convert file from Parquet to CSV.

- Path to Parquet file can be s3 or local
- Destination dir should belong to the same filesystem as Parquet file 
  (e.g., both at s3 or both at local)
- Destination dir can be absolute or relative path
- WARNING: Resulting CSV file does not preserve data types like datetime

Usage example:
> im_v2/common/data/transform/convert_pq_to_csv.py \
    --pq_file_path im_v2/common/data/file_name.pq \
    --dst_dir im_v2/common/notebooks
"""

import argparse
import logging
import os

import helpers.hdbg as hdbg
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hs3 as hs3

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--pq_file_path",
        action="store",
        type=str,
        required=True,
        help="Input Parquet file to convert to CSV format",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        type=str,
        required=False,
        default=None,
        help="""
        Destination dir where to save converted CSV file.
        If not specified, uses the same dir where input file is located
        """,
    )
    parser.add_argument(
        "--aws_profile",
        action="store",
        required=False,
        default=None,
        type=str,
        help="The AWS profile to convert file located at s3 filesystem",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dst_dir = args.dst_dir
    aws_profile = args.aws_profile
    pq_file_path = args.pq_file_path
    hs3.dassert_path_exists(pq_file_path, aws_profile=aws_profile)
    if not dst_dir:
        dst_dir = os.path.dirname(pq_file_path)
    hs3.dassert_path_exists(dst_dir, aws_profile=aws_profile)
    # Make a path to CSV file.
    file_name = os.path.basename(pq_file_path).split(".")[-2]
    csv_file_path = os.path.join(dst_dir, file_name + ".csv")
    # Convert the file.
    df = hparque.from_parquet(pq_file_path, aws_profile=aws_profile)
    _LOG.debug("Saving CSV file at %s", csv_file_path)
    df.to_csv(csv_file_path)


if __name__ == "__main__":
    _main(_parse())
