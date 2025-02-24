#!/usr/bin/env python
"""
Perform syntactic and semantic validation of a specified dataset signature.

Signature is validated by the latest dataset schema version.

Syntax validation checks if the signature is not malformed.
- If the schema specifies dataset signature as `{data_type}.{asset_type}`, then
  `ohlcv.futures` is a valid signatue, but `ohlcv-futures` is not.

Semantic validation checks if the signature tokens are correct.
- If the schema specifies allowed values for `data_type = ["ohlcv", "bid_ask"]`,
  then for dataset signature `{data_type}.{asset_type}` `ohlcv.futures` is a valid
  signature, but `bidask.futures` is not.

Use as:
> data_schema/validate_dataset_signature.py \
    --signature 'bulk.airflow.downloaded_1sec'

Import as:

import data_schema.validate_dataset_signature as dsvadasi
"""

import argparse
import logging

import data_schema.dataset_schema_utils as dsdascut
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--signature",
        action="store",
        required=True,
        type=str,
        help="Dataset signature to validate",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    args = vars(parser.parse_args())
    hdbg.init_logger(verbosity=args["log_level"], use_exec_path=True)
    signature = args["signature"]
    dataset_schema = dsdascut.get_dataset_schema()
    if dsdascut.validate_dataset_signature(signature, dataset_schema):
        _LOG.info(f"Signature '{signature}' is valid.")
    else:
        _LOG.error(f"Signature '{signature}' is invalid!")
        exit(-1)


if __name__ == "__main__":
    _main(_parse())
