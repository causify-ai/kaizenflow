#!/usr/bin/env python
"""
Compute average price, limits and execution price for the given universe.

Example use:

# Compute average price for CryptoChassis universe v3 with provided start_ts and end_ts.
> research_amp/cc/precompute_average_price.py \
    --start_ts '2022-12-14 00:00:00+00:00' \
    --end_ts '2022-12-15 00:00:00+00:00' \
    --universe_version 'v3' \
    --dst_dir '/shared_data/CMTask3550_test/'
"""
import argparse
import logging
import os

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import research_amp.cc.algotrading as ramccalg

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    # TODO(Danya): add 'vendor' parameter.
    # TODO(Danya): add parallel processing args.
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--start_ts",
        action="store",
        required=True,
        type=str,
        help="Start of the period for average price calculation, e.g. '2023-01-11 09:00:00'",
    )
    parser.add_argument(
        "--end_ts",
        action="store",
        required=True,
        type=str,
        help="End of the period for average price calculation, e.g. '2023-01-11 20:00:00'",
    )
    parser.add_argument(
        "--universe_version",
        action="store",
        required=True,
        type=str,
        help="Trading universe to download data for, e.g. 'v3'",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        required=True,
        type=str,
        help="Folder in which to store the output, e.g. '/data/shared/average_price_twap/'",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    start_ts = pd.Timestamp(args.start_ts)
    end_ts = pd.Timestamp(args.end_ts)
    hdateti.dassert_timestamp_lt(start_ts, end_ts)
    #
    universe_version = args.universe_version
    dst_dir = args.dst_dir
    hdbg.dassert_path_exists(dst_dir)
    # Create a subfolder for the experiment run.
    current_ts = hdateti.get_current_timestamp_as_string("ET")
    dst_subdir = os.path.join(dst_dir, f"avg_price_{current_ts}")
    hio.create_dir(dst_subdir, incremental=False)
    #
    _LOG.debug("Building configs...")
    configs = ramccalg.build_CMTask3350_configs(
        start_ts, end_ts, universe_version
    )
    for asset_config in configs:
        # Get full symbol from asset id.
        asset_id = asset_config[("market_data_config", "asset_ids")]
        hdbg.dassert_is_integer(asset_id)
        client = asset_config[("client_config", "client")]
        full_symbol = client.get_full_symbols_from_asset_ids([asset_id])[0]
        _LOG.debug(hprint.to_str("asset_id full_symbol"))
        _LOG.debug("Computing dataframes...")
        reprice_df, exec_df = ramccalg.compute_average_price_df_from_config(
            asset_config
        )
        # Convert timestamps to string.
        start_ts_filename = start_ts.strftime("%Y%m%d-%H%M%S")
        end_ts_filename = end_ts.strftime("%Y%m%d-%H%M%S")
        # Get file names and paths.
        file_name_reprice = (
            f"reprice_{full_symbol}_{start_ts_filename}_{end_ts_filename}.csv.gz"
        )
        file_name_exec = (
            f"exec_{full_symbol}_{start_ts_filename}_{end_ts_filename}.csv.gz"
        )
        path_reprice = os.path.join(dst_subdir, file_name_reprice)
        path_exec = os.path.join(dst_subdir, file_name_exec)
        _LOG.debug(hprint.to_str("path_reprice path_exec"))
        # Save DataFrames.
        reprice_df.to_csv(path_reprice, compression="gzip")
        exec_df.to_csv(path_exec, compression="gzip")
        _LOG.debug("Saved data to %s", dst_subdir)


if __name__ == "__main__":
    _main(_parse())
