"""
Centralize checking logical dependencies between values of various arguments
for ETL scripts.

Import as:

import im_v2.common.data.qa.validate_input_args as imvcdqviar
"""
import argparse
import helpers.hdbg as hdbg


def validate_dst_dir_arg(args: argparse.Namespace) -> None:
    """
    Validate destination directory args.
    
    :param args: destination directory args
    """
    if args.get("dst_dir"):
        valid_data_formats = ['csv','parquet']
        data_format = args.get("data_format")
        # TODO(gp): Use dassert
        if data_format not in valid_data_formats:
            raise ValueError(f"--data_format argument cannot be {data_format} it should be one \
                    of the following formats {valid_data_formats}")
        if args.get("db_table"):
            raise ValueError(f"Invalid argument db_table present")
        if args.get("s3_path"):
            raise ValueError(f"Invalid argument s3_path present")


def validate_vendor_arg(vendor: str, args: argparse.Namespace) -> None:
    """
    Validate vendor args.

    :param vendor: vendor name
    :param args: ETL script args
    :return: vendor data extractor
    """
    hdbg.dassert_in(
        vendor,
        ["binance", "ccxt", "crypto_chassis"],
        msg=f"Vendor {vendor} is not supported.",
    )
    if vendor == "crypto_chassis":
        if not args.get("universe_part"):
            raise RuntimeError(
                f"--universe_part argument is mandatory for {vendor}"
            )