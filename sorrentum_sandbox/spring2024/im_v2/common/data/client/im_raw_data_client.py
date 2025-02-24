"""
Thin IM client for loading raw data.

Import as:

import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
"""

import logging
import os
from typing import List, Optional

import pandas as pd

import core.finance.bid_ask as cfibiask
import data_schema.dataset_schema_utils as dsdascut
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparquet as hparque
import helpers.hs3 as hs3
import helpers.hsql_implementation as hsqlimpl
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe.universe as imvcounun

_LOG = logging.getLogger(__name__)

# TODO(Juraj): hack applied until a solution for #CmTask6620 is found.
_AWS_REGION = os.environ.get("CK_AWS_DEFAULT_REGION", "eu-north-1")
# TODO(Juraj): This might be moved to helpers.
_S3_BUCKET_BY_STAGE = {
    "test": "cryptokaizen-data-test",
    # TODO(Juraj): hack applied until a solution for #CmTask6620 is found.
    "preprod": "cryptokaizen-data-tokyo.preprod"
    if _AWS_REGION == "ap-northeast-1"
    else "cryptokaizen-data.preprod",
    "prod": "cryptokaizen-data",
}


class RawDataReader:
    """
    Load the raw data from S3 or a DB based on the dataset signature.
    """

    def __init__(self, signature: str, *, stage: str = "prod"):
        """
        Constructor.

        :param signature: dataset signature, e.g.
            `bulk.airflow.resampled_1min.pq.bid_ask.spot.v3.crypto_chassis.binance.v1_0_0`
        :param stage: which stage to execute in, determines which DB stage or S3
            bucket is used.
        """
        # Validate signature schema.
        self.dataset_schema = dsdascut.get_dataset_schema()
        self.signature = signature
        self.args = dsdascut.parse_dataset_signature_to_args(
            signature, self.dataset_schema
        )
        self.stage = stage
        self.dataset_epoch_unit = imvcdttrut.get_vendor_epoch_unit(
            self.args["vendor"], self.args["data_type"]
        )
        universe_list = imvcounun.get_vendor_universe(
            self.args["vendor"],
            "download",
            version=self.args["universe"].replace("_", "."),
        )
        self.universe_list = universe_list[self.args["exchange_id"]]
        if self.args["data_format"] == "parquet":
            self.partition_mode = self._get_partition_mode()
        elif self.args["data_format"] == "postgres":
            self._setup_db_table_access()
        else:
            raise ValueError("Invalid data format `%s`", self.args["data_format"])

    def read_data_head(self) -> pd.DataFrame:
        """
        Load a sample of the data.
        """
        if self.args["data_format"] == "parquet":
            data = self.load_parquet_head()
        elif self.args["data_format"] == "postgres":
            self._setup_db_table_access()
            data = self.load_db_table_head()
        else:
            raise ValueError("Invalid data format `%s`", self.args["data_format"])
        return data

    def read_data(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        *,
        currency_pairs: Optional[List[str]] = None,
        bid_ask_levels: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Load data in a specified time interval.

        :param start_timestamp: start of the filtered interval
        :param end_timestamp: end of the filtered interval
        :param currency_pairs: currency_pairs to select, if None, all
            pairs are loaded
        :param bid_ask_levels: which levels of bid_ask data to load, if
            None, all levels are loaded
        """
        if currency_pairs:
            hdbg.dassert_is_subset(set(currency_pairs), set(self.universe_list))
        if self.args["data_format"] == "parquet":
            # Load the data from Parquet.
            data = self.load_parquet(
                start_timestamp,
                end_timestamp,
                currency_pairs=currency_pairs,
                bid_ask_levels=bid_ask_levels,
            )
        elif self.args["data_format"] == "postgres":
            # Load the data from DB.
            data = self.load_db_table(
                start_timestamp,
                end_timestamp,
                currency_pairs=currency_pairs,
                bid_ask_levels=bid_ask_levels,
            )
        else:
            raise ValueError("Invalid data format `%s`", self.args["data_format"])
        return data

    def load_parquet_head(self) -> pd.DataFrame:
        """
        Load the head of a sample parquet file.

        Currently using `currency_pair=ETH_USDT/year=2022/month=11/data.parquet`
        location for each data type.
        """
        # Build s3 path.
        s3_pq_file_path = self._build_s3_pq_file_path()
        _LOG.info("Loading the data from `%s`", s3_pq_file_path)
        df = hparque.from_parquet(s3_pq_file_path, n_rows=10, aws_profile="ck")
        return df

    def load_db_table_head(self) -> pd.DataFrame:
        """
        Load the head of the DB table corresponding to the dataset signature.
        """
        start_timestamp = end_timestamp = None
        df = imvcddbut.load_db_data(
            self.db_connection,
            self.table_name,
            start_timestamp,
            end_timestamp,
            limit=10,
            exchange_id=self.args["exchange_id"],
        )
        # Remove useless id column.
        df = df.drop("id", axis=1)
        return df

    def load_db_table(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        *,
        deduplicate: bool = False,
        currency_pairs: Optional[List[str]] = None,
        bid_ask_levels: Optional[List[int]] = None,
        bid_ask_format: str = "wide",
        subset: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Load data from a DB table in a specified time interval.

        Refer to `read_data()` for parameter docs.
        """
        hdbg.dassert_in(bid_ask_format, ["wide", "long"])
        if not currency_pairs:
            # Database can store different universes, determine the set based
            # on current signature's universe.
            currency_pairs = self.universe_list
        data = imvcddbut.load_db_data(
            self.db_connection,
            self.table_name,
            start_timestamp,
            end_timestamp,
            currency_pairs=currency_pairs,
            bid_ask_levels=bid_ask_levels,
            exchange_id=self.args["exchange_id"],
        )
        if deduplicate:
            hdbg.dassert_is_not(
                subset,
                None,
                "subset kwarg must be provided when deduplicate=True",
            )
            data = data.drop_duplicates(subset=subset)
        if self.args["data_type"] == "bid_ask" and bid_ask_format == "wide":
            # Set timestamp as index as required by the transform function.
            data = data.set_index("timestamp", drop=True)
            data = cfibiask.transform_bid_ask_long_data_to_wide(data, "timestamp")
        return data

    def load_csv(
        self,
        currency_pair: str,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
    ) -> pd.DataFrame:
        """
        Load CSV data for a specified time frame.

        :param currency_pair: currency pair to load
        :param start_timestamp: start of the filtered interval
        :param end_timestamp: end of the filtered interval
        :return: data frame
        """
        # Build s3 path.
        s3_csv_file_path = self._build_s3_csv_file_path(currency_pair)
        _LOG.info("Loading the data from `%s`", s3_csv_file_path)
        # Load the data.
        df = pd.read_csv(s3_csv_file_path)
        # Filter the data.
        if start_timestamp:
            # Convert timestamps to unix epoch.
            start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
                start_timestamp, "ms"
            )
            df = df[df["timestamp"] >= start_timestamp]
        if end_timestamp:
            end_timestamp = hdateti.convert_timestamp_to_unix_epoch(
                end_timestamp, "ms"
            )
            df = df[df["timestamp"] <= end_timestamp]
        return df

    def load_parquet(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        *,
        currency_pairs: Optional[List[str]] = None,
        bid_ask_levels: Optional[List[int]] = None,
        columns: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Load Parquet data for a specified time frame.

        Refer to `read_data()` for parameter docs.
        """
        if (
            start_timestamp is not None
            and end_timestamp is not None
            and self.partition_mode == "by_year_month_day"
        ):
            filters = hparque.build_filter_with_only_equalities(
                start_timestamp, end_timestamp
            )
        else:
            filters = []
        if start_timestamp:
            start_ts = hdateti.convert_timestamp_to_unix_epoch(
                start_timestamp, unit=self.dataset_epoch_unit
            )
            filters.append(("timestamp", ">=", start_ts))
        if end_timestamp:
            end_ts = hdateti.convert_timestamp_to_unix_epoch(
                end_timestamp, unit=self.dataset_epoch_unit
            )
            filters.append(("timestamp", "<=", end_ts))
        if currency_pairs:
            filters.append(("currency_pair", "in", currency_pairs))
        if bid_ask_levels:
            if "resampled" in self.args["action_tag"]:
                columns = [
                    "timestamp",
                    "currency_pair",
                    "exchange_id",
                    "knowledge_timestamp",
                    "year",
                    "month",
                ]
                for i in bid_ask_levels:
                    for s in ["open", "close", "mean"]:
                        bid_ask_cols_level = list(
                            map(
                                lambda x: f"level_{i}.{x}.{s}",
                                imvcdttrut.BID_ASK_COLS,
                            )
                        )
                        columns.extend(bid_ask_cols_level)
                    for s in ["high", "low"]:
                        bid_ask_cols_level = list(
                            map(
                                lambda x: f"level_{i}.{x}.{s}",
                                [
                                    imvcdttrut.BID_ASK_COLS[0],
                                    imvcdttrut.BID_ASK_COLS[2],
                                ],
                            )
                        )
                        columns.extend(bid_ask_cols_level)
                    for s in ["max", "min"]:
                        bid_ask_cols_level = list(
                            map(
                                lambda x: f"level_{i}.{x}.{s}",
                                [
                                    imvcdttrut.BID_ASK_COLS[1],
                                    imvcdttrut.BID_ASK_COLS[3],
                                ],
                            )
                        )
                        columns.extend(bid_ask_cols_level)
            else:
                filters.append(("level", "in", bid_ask_levels))
        s3_path = self._build_s3_pq_file_path()
        data = hparque.from_parquet(
            s3_path, filters=filters, columns=columns, aws_profile="ck"
        )
        return data

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    def _setup_db_table_access(self) -> None:
        """
        Set up DB connection and get DB table name based on dataset signature.
        """
        self.db_connection = imvcddbut.DbConnectionManager.get_connection(
            self.stage
        )
        self.table_name = dsdascut.get_im_db_table_name_from_signature(
            self.signature, self.dataset_schema
        )
        # Check if the table name exists.
        db_tables = hsqlimpl.get_table_names(self.db_connection)
        hdbg.dassert_in(
            self.table_name, db_tables, f"`{self.table_name} doesn't exist`"
        )
        _LOG.info("Enabled connection to the `%s` DB table", self.table_name)

    def _build_s3_pq_file_path(self) -> str:
        """
        Get the path to Parquet file on S3.
        """
        hdbg.dassert_in(self.stage, _S3_BUCKET_BY_STAGE)
        s3_bucket = f"s3://{_S3_BUCKET_BY_STAGE[self.stage]}"
        s3_path = dsdascut.build_s3_dataset_path_from_args(s3_bucket, self.args)
        return s3_path

    def _build_s3_csv_file_path(self, currency_pair: str) -> str:
        """
        Get the path to CSV file on S3.

        :param currency_pair: currency pair to load
        :return: s3 path
        """
        hdbg.dassert_in(self.stage, _S3_BUCKET_BY_STAGE)
        s3_bucket = f"s3://{_S3_BUCKET_BY_STAGE[self.stage]}"
        _LOG.debug("s3_bucket=", s3_bucket)
        s3_path = dsdascut.build_s3_dataset_path_from_args(s3_bucket, self.args)
        _LOG.debug("s3_path=", s3_path)
        s3_path += f"/{currency_pair}.csv.gz"
        return s3_path

    def _get_partition_mode(self) -> str:
        """
        Get the partition_mode from the directory structure.

        This can help in filtering.
        """
        s3_path = self._build_s3_pq_file_path()
        pattern = "currency_pair=*/year=*/month=*/day=*"
        only_files = True
        use_relative_paths = True
        files = hs3.listdir(
            s3_path, pattern, only_files, use_relative_paths, aws_profile="ck"
        )
        if len(files) != 0:
            partition_mode = "by_year_month_day"
        else:
            partition_mode = None
        return partition_mode


# /////////////////////////////////////////////////////////////////////////////

# TODO(gp): -> raw_data_client_examples.py


def get_bid_ask_realtime_raw_data_reader(
    stage: str, data_vendor: str, universe_version: str
) -> RawDataReader:
    """
    Get raw data reader for the real-time bid/ask price data.

    Currently the DB signature is hardcoded.

    :param stage: which stage to execute in, determines which DB stage
        or S3 bucket is used.
    :param data_vendor: provider of the realtime data, e.g. CCXT or
        Binance
    :param universe_version: version of the universe
    :return: RawDataReader initialized for the realtime bid/ask data
    """
    universe_version = universe_version.replace(".", "_")
    data_vendor = data_vendor.lower()
    bid_ask_db_signature = f"realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.{universe_version}.{data_vendor}.binance.v1_0_0"
    bid_ask_raw_data_reader = RawDataReader(bid_ask_db_signature, stage=stage)
    return bid_ask_raw_data_reader
