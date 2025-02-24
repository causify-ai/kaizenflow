#!/usr/bin/env python
"""
Save chainlink compute data to database

Use as:

> ./compute_to_db.py --all --target_table 'chainlink_compute'
> ./compute_to_db.py --start_roundid 92233720368547792846 --target_table 'chainlink_compute'
"""
import argparse

import helpers.hdbg as hdbg
import helpers.hparser as hparser

import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.db as sisebidb
import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.compute as compute



def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    # when specified the start_roundid argument, 
    # the data from the specified roundid to the latest roundid will be computed and store in the chainlink_compute table.
    parser.add_argument(
        "--start_roundid",
        action="store",
        required=False,
        type=int,
        help="the first data to compute",
    )
    # when specified the all argument, 
    # all the data in chainlink_history and chainlink_real_time will be computed and store in the chainlink_compute table 
    parser.add_argument(
        "--all",
        action="store_true",
        required=False,
        help="compute all data",
    )
    # table to store the compute data
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Name of the db table to save data into"
    )

    return parser


def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_download_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    
    # Compute data.
    if args.all:
        raw_data = compute.computer()
    elif args.start_roundid:
        raw_data = compute.computer(start_roundid = args.start_roundid)

    # Save data to DB.
    db_conn = sisebidb.get_db_connection()
    saver = sisebidb.PostgresDataFrameSaver(db_conn)
    saver.save(raw_data, args.target_table)


if __name__ == "__main__":
    _main(_parse())