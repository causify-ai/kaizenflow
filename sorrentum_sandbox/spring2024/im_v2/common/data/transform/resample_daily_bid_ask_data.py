#!/usr/bin/env python
"""
Load bid/ask parquet data from S3 exchange dir, resample to 1 minute and upload
back.

This assumes that the underlying data is sampled at a 1 second resolution.

# Usage sample:
> im_v2/common/data/transform/resample_daily_bid_ask_data.py \
    --start_timestamp '20230101-000000' \
    --end_timestamp '20230102-000000' \
    --src_signature 'periodic_daily.airflow.downloaded_1sec.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0' \
    --src_s3_path 's3://cryptokaizen-data-test/' \
    --dst_signature 'periodic_daily.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0' \
    --dst_s3_path 's3://cryptokaizen-data-test/' \
    --universe_part 3 1

Import as:

import im_v2.common.data.transform.resample_daily_bid_ask_data as imvcdtrdba
"""
import argparse
import logging
from typing import Callable, List, Optional, Tuple

import pandas as pd

import core.finance.bid_ask as cfibiask
import data_schema.dataset_schema_utils as dsdascut
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.data.transform.transform_utils as imvcdttrut

_LOG = logging.getLogger(__name__)


def _build_parquet_filters(
    dataset_action_tag: str,
    start: str,
    end: str,
    epoch_unit: str,
    bid_ask_levels: Optional[List[int]],
) -> List[Tuple]:
    """
    Build parquet filters from timestamps.

    This functions includes optimizations to load data faster for
    certain type of parquet tiling.
    """
    # Convert dates to unix timestamps.
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    start_as_ts = hdateti.convert_timestamp_to_unix_epoch(start, unit=epoch_unit)
    end_as_ts = hdateti.convert_timestamp_to_unix_epoch(end, unit=epoch_unit)
    filters = []
    # Improve performance when fetching data by applying filters on tiles.
    if dataset_action_tag == "archived_200ms":
        if bid_ask_levels:
            filters.append(("level", "in", bid_ask_levels))
        if start.year == end.year:
            filters.append(("year", "=", start.year))
            if start.month == end.month:
                filters.append(("month", "=", start.month))
                if start.day == end.day:
                    filters.append(("day", "=", start.day))
    filters.extend(
        [("timestamp", ">=", start_as_ts), ("timestamp", "<=", end_as_ts)]
    )
    _LOG.info(filters)
    return filters


def _preprocess_src_data(
    dataset_action_tag: str, data: pd.DataFrame
) -> pd.DataFrame:
    """
    Apply dataset specifying preprocessing operations.
    """
    if dataset_action_tag == "archived_200ms":
        # Timestamp is in the index, column is obsolete
        data = data.drop("timestamp", axis=1)
        data = cfibiask.transform_bid_ask_long_data_to_wide(data, "timestamp")
    return data


def _get_s3_path_from_signature(signature: str, base_s3_path: str) -> str:
    """
    Get the S3 path from the dataset signature.

    :param signature: dataset signature,
      e.g. `bulk.airflow.resampled_1min.pq.bid_ask.spot.v3.crypto_chassis.binance.v1_0_0`
    :param base_s3_path: base S3 path, e.g. `s3://bucket-name/`
    """
    dataset_schema = dsdascut.get_dataset_schema()
    args = dsdascut.parse_dataset_signature_to_args(signature, dataset_schema)
    s3_path = dsdascut.build_s3_dataset_path_from_args(base_s3_path, args)
    return s3_path


def _run(args: argparse.Namespace, aws_profile: hs3.AwsProfile = "ck") -> None:
    # Get arguments from the dataset signatures.
    dataset_schema = dsdascut.get_dataset_schema()
    scr_signature_args = dsdascut.parse_dataset_signature_to_args(
        args.src_signature, dataset_schema
    )
    dst_signature_args = dsdascut.parse_dataset_signature_to_args(
        args.src_signature, dataset_schema
    )
    # Define the unit of the timestamp column.
    data_type = "bid_ask"
    epoch_unit = imvcdttrut.get_vendor_epoch_unit(
        scr_signature_args["vendor"], data_type
    )
    # Check that the source and destination data format are parquet.
    hdbg.dassert_eq(scr_signature_args["data_format"], "parquet")
    hdbg.dassert_eq(dst_signature_args["data_format"], "parquet")
    # Define filters for data period.
    # Note(Juraj): it's better from Airflow execution perspective
    #  to keep the interval closed: [start, end].
    #  AKA the client takes care of providing the correct interval.
    bid_ask_levels = list(range(1, args.bid_ask_levels + 1))
    filters = _build_parquet_filters(
        scr_signature_args["action_tag"],
        args.start_timestamp,
        args.end_timestamp,
        epoch_unit,
        bid_ask_levels,
    )
    # filters = [("timestamp", ">=", start), ("timestamp", "<=", end)]
    src_s3_path = _get_s3_path_from_signature(
        args.src_signature, args.src_s3_path
    )
    data = hparque.from_parquet(
        src_s3_path, filters=filters, aws_profile=aws_profile
    )
    _LOG.info("Source data loaded.")
    # TODO(Juraj): we are aware of duplicate data problem #7230 but for the
    # sake of resampled data availability we allow occasional duplicate with different values.
    duplicate_cols_subset = [
            "timestamp",
            "exchange_id",
            "currency_pair",
            "level",
    ] 
    # Ensure there are no duplicates, in this case
    #  using duplicates would compute the wrong resampled values.
    data = data.drop_duplicates(subset=duplicate_cols_subset)
    data = _preprocess_src_data(scr_signature_args["action_tag"], data)
    data_resampled = []
    input_currency_pairs = data["currency_pair"].unique()
    if args.universe_part:
        input_currency_pairs = imvcdeexut._split_universe(
            input_currency_pairs, args.universe_part[0], args.universe_part[1]
        )
    for currency_pair in input_currency_pairs:
        data_single = data[data["currency_pair"] == currency_pair]
        if data_single.empty:
            _LOG.warning(
                "Empty Dataframe: no data for %s in %s-%s time period",
                currency_pair,
                args.start_timestamp,
                args.end_timestamp,
            )
            continue
        data_resampled_single = imvcdttrut.resample_multilevel_bid_ask_data_to_1min(
            data_single, number_levels_of_order_book=args.bid_ask_levels
        )
        if not data_resampled_single.empty:
            data_resampled_single["currency_pair"] = currency_pair
            data_resampled.append(data_resampled_single)
        else:
            _LOG.warning(
                "Empty Dataframe: no resampled data for %s "
                "in %s-%s time period",
                currency_pair,
                args.start_timestamp,
                args.end_timestamp,
            )
    # Transform the dataset to make save_parquet applicable.
    if data_resampled:
        data_resampled = pd.concat(data_resampled).reset_index()
        output_currency_pairs = data_resampled["currency_pair"].unique()
        # The set of input symbols should be equal to the set of output symbols
        # since this is a resampling transformation.
        if args.assert_all_resampled and not list(input_currency_pairs) == list(
            output_currency_pairs
        ):
            raise RuntimeError(
                "Missing symbols in the resampled data: %s",
                hprint.set_diff_to_str(
                    input_currency_pairs,
                    output_currency_pairs,
                    sep_char=",",
                    add_space=True,
                ),
            )
        data_resampled["timestamp"] = data_resampled["timestamp"].apply(
            lambda x: hdateti.convert_timestamp_to_unix_epoch(x, epoch_unit)
        )
        data_resampled = imvcdttrut.add_knowledge_timestamp_col(
            data_resampled, "UTC"
        )
        _LOG.info(
            hpandas.df_to_str(
                data_resampled, print_shape_info=True, tag="Resampled data"
            )
        )
        dst_s3_path = _get_s3_path_from_signature(
            args.dst_signature, args.dst_s3_path
        )
        # We sometimes run batch resampling tasks, for that it is more convenient to
        # set mode as "append", in the default mode concurrent access to the single
        # parquet file might no be possible if two processes need it at the same time.
        imvcdeexut.save_parquet(
            data_resampled,
            dst_s3_path,
            epoch_unit,
            aws_profile,
            "bid_ask",
            mode="append",
        )
    else:
        _LOG.warning("Resampled dataset is empty!")


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_s3_path",
        action="store",
        required=True,
        type=str,
        help="Base S3 path to the source parquet dataset.",
    )
    parser.add_argument(
        "--dst_s3_path",
        action="store",
        required=True,
        type=str,
        help="Base S3 path to the destination parquet dataset.",
    )
    parser.add_argument(
        "--src_signature",
        action="store",
        type=str,
        required=True,
        help="Source parquet dataset signature to resample to 1 minute frequency",
    )
    parser.add_argument(
        "--dst_signature",
        action="store",
        type=str,
        required=True,
        help="Destination signature where to save resampled parquet files",
    )
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the downloaded data period",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the downloaded data period",
    )
    parser.add_argument(
        "--assert_all_resampled",
        action="store_true",
        required=False,
        default=False,
        help="Raise an exception if the set of symbols in the input is not"
        " equal to the set of symbols in the output data.",
    )
    parser.add_argument(
        "--bid_ask_levels",
        default=10,
        action="store",
        required=False,
        type=int,
        help='Filter data to get top "n" levels of bid-ask data.',
    )
    parser.add_argument(
        "--universe_part",
        action="store",
        required=False,
        type=int,
        nargs=2,
        help="Pass two int argument x,y. Split universe into N chunks each contains X symbols. \
            groups of 10 pairs, 'y' denotes which part should be downloaded \
            (e.g. 10, 1 - download first 10 symbols)",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args)


if __name__ == "__main__":
    _main(_parse())
