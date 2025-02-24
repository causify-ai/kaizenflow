#!/usr/bin/env python
"""
Script to remove duplicates from a OHLCV data table.

In this context, a row is considered duplicate, when there exists another row
which has identical timestamp, currency pair and exchange ID but different row
ID and knowledge timestamp.

# Delete duplicates from OHLCV table in dev stage
> im_v2/common/db/delete_duplicates_from_ohlcv_table.py \
        --db_stage 'dev' \
        --db_table 'ccxt_ohlcv_test'
"""

import argparse

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im_v2.common.db.db_utils as imvcddbut


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        type=str,
        default="local",
        help="Stage to use: local, dev or prod.",
    )
    parser.add_argument(
        "--db_table",
        action="store",
        required=True,
        type=str,
        help="DB table to remove duplicates from.",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.dassert_in(args.db_stage, ["local", "dev", "prod"])
    imvcddbut.delete_duplicate_rows_from_ohlcv_table(args.db_stage, args.db_table)


if __name__ == "__main__":
    _main(_parse())
