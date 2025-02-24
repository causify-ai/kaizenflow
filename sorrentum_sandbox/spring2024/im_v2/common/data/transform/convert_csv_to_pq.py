#!/usr/bin/env python
"""
Convert data from CSV to Parquet files and partition dataset by asset.

A Parquet file partitioned by assets looks like:
```
dst_dir/
    year=2021/
        month=12/
           day=11/
               asset=BTC_USDT/
                    data.parquet
               asset=ETH_USDT/
                    data.parquet
```

Usage sample:

> im_v2/common/data/transform/convert_csv_to_pq.py \
     --src_dir 's3://<ck-data>/historical/binance/' \
     --dst_dir 's3://<ck-data>/historical/binance_parquet/' \
     --datetime_col 'timestamp' \
     --asset_col 'currency_pair'
"""

import argparse
import logging
import os

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hs3 as hs3
import im_v2.common.data.transform.transform_utils as imvcdttrut

_LOG = logging.getLogger(__name__)


def _run(args: argparse.Namespace, *, aws_profile: hs3.AwsProfile) -> None:
    # Check that the `aws_profile` is valid.
    if aws_profile:
        _ = hs3.get_s3fs(aws_profile)
    files = hs3.listdir(
        args.src_dir,
        "*.csv*",
        only_files=True,
        use_relative_paths=True,
        aws_profile=aws_profile,
    )
    _LOG.info("Files found at %s:\n%s", args.src_dir, "\n".join(files))
    for file in files:
        full_path = os.path.join(args.src_dir, file)
        _LOG.debug("Converting %s...", full_path)
        df = pd.read_csv(full_path)
        # Set datetime index.
        reindexed_df = imvcdttrut.reindex_on_datetime(df, args.datetime_col)
        # Add date partition columns to the dataframe.
        df, partition_cols = hparque.add_date_partition_columns(
            reindexed_df, "by_year_month"
        )
        hparque.to_partitioned_parquet(
            df,
            [args.asset_col] + partition_cols,
            args.dst_dir,
            aws_profile=aws_profile,
        )
    hparque.list_and_merge_pq_files(args.dst_dir, aws_profile=aws_profile)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_dir",
        action="store",
        type=str,
        required=True,
        help="Dir with input CSV files to convert to Parquet format",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        type=str,
        required=True,
        help="Destination dir where to save converted Parquet files",
    )
    parser.add_argument(
        "--datetime_col",
        action="store",
        type=str,
        required=True,
        help="Name of column containing datetime information",
    )
    parser.add_argument(
        "--asset_col",
        action="store",
        type=str,
        default=None,
        help="Name of column containing asset name for partitioning by asset",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip files that have already been converted",
    )
    parser.add_argument(
        "--aws_profile",
        action="store",
        required=True,
        type=str,
        help="The AWS profile to use for .aws/credentials or for env vars",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args, aws_profile=args.aws_profile)


if __name__ == "__main__":
    _main(_parse())
