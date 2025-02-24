#!/usr/bin/env python
"""
NOTE: This script is deprecated refer to .../data/qa/notebooks/*.ipynb

Compare data on DB and S3, raising when difference was found.

Use as:
# Compare daily S3 and realtime data for binance.
> im_v2/ccxt/data/extract/compare_realtime_and_historical.py \
   --db_stage 'dev' \
   --start_timestamp 20221008-000000 \
   --end_timestamp 20221013-000000 \
   --exchange_id 'binance' \
   --data_type 'ohlcv' \
   --contract_type 'futures' \
   --db_table 'ccxt_ohlcv_preprod' \
   --aws_profile 'ck' \
   --resample_1min \
   --s3_vendor 'crypto_chassis' \
   --s3_path 's3://cryptokaizen-data-test/reorg/daily_staged.airflow.pq'

Import as:

import im_v2.ccxt.data.extract.compare_realtime_and_historical as imvcdecrah
"""
import argparse
import logging
import os
from typing import Dict, List

import pandas as pd
import psycopg2

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hs3 as hs3
import helpers.hsql as hsql
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.universe.full_symbol as imvcufusy
import im_v2.im_lib_tasks as imvimlita

_LOG = logging.getLogger(__name__)


def build_dummy_data_reconciliation_config() -> cconfig.ConfigList:
    """
    Dummy function to pass into amp/dev_scripts/notebooks/run_notebook.py as a
    configu_builder parameter.
    """
    config = cconfig.Config.from_dict({"dummy": "value"})
    config_list = cconfig.ConfigList([config])
    return config_list


def build_data_reconciliation_config_env_var(
    config_as_dict: Dict[str, str]
) -> str:
    """
    Transform config dict to a python code string.

    The string can be passed into a single var which can be ready via
    Config.from_env_var at notebook level.

    :param config_as_dict: config dict for data reconciliation
    """
    # config = cconfig.Config.from_dict(config_as_dict)
    # config_str = config.to_python()
    # return config_str


# #############################################################################


def get_multilevel_bid_ask_column_names(depth: int = 10) -> List[str]:
    """
    Construct list of bid ask column names for multilevel setup.

    Example for depth = 2
        [bid_price_l1, bid_size_l1, ask_size_l1, ask_price_l1, bid_price_l2,...]
    """
    multilevel_bid_ask_cols = []
    for i in range(1, depth + 1):
        bid_ask_cols_level = map(lambda x: f"{x}_l{i}", imvcdttrut.BID_ASK_COLS)
        for col in bid_ask_cols_level:
            multilevel_bid_ask_cols.append(col)
    return multilevel_bid_ask_cols


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--start_timestamp",
        action="store",
        required=True,
        type=str,
        help="Beginning of the compared period",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the compared period",
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use, e.g. `dev`",
    )
    parser.add_argument(
        "--exchange_id",
        action="store",
        required=True,
        type=str,
        help="Exchange for which the comparison should be done",
    )
    parser.add_argument(
        "--data_type",
        action="store",
        required=True,
        type=str,
        help="Data type to compare: 'bid_ask' or 'ohlcv'",
    )
    parser.add_argument(
        "--contract_type",
        action="store",
        required=True,
        type=str,
        help="Contract type: 'spot' or 'futures'",
    )
    parser.add_argument(
        "--db_table",
        action="store",
        required=True,
        type=str,
        help="DB table to use, e.g. 'ccxt_ohlcv_spot'",
    )
    parser.add_argument(
        "--s3_vendor",
        action="store",
        required=True,
        type=str,
        help="Vendor folder to use on s3 for daily data: 'ccxt' or 'crypto_chassis'",
    )
    parser.add_argument(
        "--resample_1min",
        action="store_true",
        help="If the data should be resampled to 1 min'",
    )
    parser.add_argument(
        "--resample_1sec",
        action="store_true",
        help="If the data should be resampled to 1 sec'",
    )
    parser.add_argument(
        "--bid_ask_accuracy",
        action="store",
        required=False,
        default=None,
        type=int,
        help="An accuracy threshold (in %) to apply when reconciling bid/ask data"
        + "If the data differ above this threshold an error is raised.",
    )
    parser.add_argument(
        "--bid_ask_depth",
        action="store",
        required=False,
        default=10,
        type=int,
        help="Market depth to compare to (applicable for data_type=bid_ask)."
        + " Allowed values are 1-10 (Default is 10)",
    )

    parser = hparser.add_verbosity_arg(parser)
    # For `--s3_path` argument we only specify the top level path for the daily staged data,
    # the code handles appending the exchange, e.g. `binance` and data type, e.g. `bid_ask`
    # as the part of the path.
    parser = hs3.add_s3_args(parser)
    return parser  # type: ignore[no-any-return]


# TODO(Juraj): Move this into a qa/ folder.
class RealTimeHistoricalReconciler:
    def __init__(self, args) -> None:
        hdbg.dassert_in(
            args.data_type,
            ["bid_ask", "ohlcv"],
            f"Invalid data type: {args.data_type} is not in [`bid_ask`, `ohlcv`]",
        )
        if args.data_type == "bid_ask":
            hdbg.dassert_is(
                (args.resample_1min != args.resample_1sec),
                True,
                "One resampling option should be chosen",
            )
            # Check that bid_ask_accuracy param
            #  is set to a valid percentage.
            hdbg.dassert_lgt(0, args.bid_ask_accuracy, 100, True, True)
            self.bid_ask_accuracy = args.bid_ask_accuracy
        self.data_type = args.data_type
        universe_version = "infer_from_data"
        # Set DB connection.
        db_connection = self.get_db_connection(args)
        # Initialize CCXT client.
        self.ccxt_rt_im_client = icdcl.CcxtSqlRealTimeImClient(
            universe_version,
            db_connection,
            args.db_table,
            resample_1min=args.resample_1min,
        )
        self.aws_profile = args.aws_profile
        self.s3_path = self._build_s3_path(
            args.s3_path,
            args.data_type,
            args.contract_type,
            args.exchange_id,
            args.s3_vendor,
            args.resample_1min,
            args.resample_1sec,
        )
        # Process time period.
        self.start_ts = pd.Timestamp(args.start_timestamp)
        self.end_ts = pd.Timestamp(args.end_timestamp)
        self.resample_1sec = args.resample_1sec
        #
        self.universe = self._get_universe(args.s3_vendor)
        self.expected_columns = {
            "ohlcv": [
                "timestamp",
                "full_symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
            "bid_ask": [
                "timestamp",
                "full_symbol",
            ]
            + get_multilevel_bid_ask_column_names(args.bid_ask_depth),
        }
        # Get CCXT data.
        self.ccxt_rt = self._get_rt_data()
        # Get daily data.
        self.daily_data = self._get_daily_data()

    @staticmethod
    def get_db_connection(args):
        """
        Set-up the connection to the database.

        :param args:
        check the  type of the connection
        """
        # Connect to database.
        env_file = imvimlita.get_db_env_path(args.db_stage)
        try:
            # Connect with the parameters from the env file.
            connection_params = hsql.get_connection_info_from_env_file(env_file)
            connection = hsql.get_connection(*connection_params)
        except psycopg2.OperationalError:
            # Connect with the dynamic parameters (usually during tests).
            actual_details = hsql.db_connection_to_tuple(
                args.connection
            )._asdict()
            connection_params = hsql.DbConnectionInfo(
                host=actual_details["host"],
                dbname=actual_details["dbname"],
                port=int(actual_details["port"]),
                user=actual_details["user"],
                password=actual_details["password"],
            )
            connection = hsql.get_connection(*connection_params)
        return connection

    def run(self) -> None:
        """
        Compare real time and daily data.
        """
        # Compare real time and daily data.
        if self.data_type == "ohlcv":
            self._compare_ohlcv(self.ccxt_rt, self.daily_data)
        else:
            self._compare_bid_ask(self.ccxt_rt, self.daily_data)
        return

    @staticmethod
    def _build_s3_path(
        s3_path: str,
        data_type: str,
        contract_type: str,
        exchange_id: str,
        s3_vendor: str,
        resample_1min: bool,
        resample_1sec: bool,
    ) -> str:
        """
        Build the s3 path, e.g. s3://cryptokaizen-
        data.preprod/reorg/daily_staged.airflow.pq/ohlcv-
        futures/crypto_chassis/binance.

        :param s3_path: the root path, e.g. s3://cryptokaizen-data.preprod/reorg/daily_staged.airflow.pq
        :param data_type: the type of the data, `bid_ask` or `ohlcv`
        :param contract_type: `spot` of `futures`
        :param resample_1min: if the data should be resampled to 1 minute
        :param resample_1sec: if the data should be resampled to 1 second
        :return: the path of target s3 directory
        """
        if data_type == "bid_ask":
            if resample_1min:
                vendor_folder = "crypto_chassis.resampled_1min"
            if resample_1sec:
                vendor_folder = "crypto_chassis.downloaded_1sec"
        else:
            # Ohlcv data can be both `crypto_chassis` or `ccxt`.
            vendor_folder = s3_vendor
        if contract_type == "futures":
            data_type = f"{data_type}-futures"
        s3_path = os.path.join(s3_path, data_type, vendor_folder, exchange_id)
        return s3_path

    @staticmethod
    def _filter_duplicates(data: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicates from data based on exchange id and timestamp.

        Keeps the row with the latest 'knowledge_timestamp' value.

        :param data: Dataframe to process
        :return: data with duplicates removed
        """
        duplicate_columns = ["full_symbol", "timestamp"]
        # Sort values.
        use_index = False
        _LOG.info("Dataframe length before duplicate rows removed: %s", len(data))
        # Remove duplicates.
        data = hpandas.drop_duplicates(
            data, use_index, subset=duplicate_columns
        ).sort_index()
        # Sort values.
        data = data.sort_values("timestamp", ascending=True)
        _LOG.info("Dataframe length after duplicate rows removed: %s", len(data))
        return data

    # TODO(Juraj): Cleanup/Remove this code.
    # @staticmethod
    # def _clean_data_for_orderbook_level(
    #    df: pd.DataFrame, level: int = 1
    # ) -> pd.DataFrame:
    #    """
    #    Specify the order book level in CCXT bid ask data.
    #
    #    :param df: Data with multiple levels (e.g., bid_price_1, bid_price_2, etc.)
    #    :return: Data where specific level has common name (i.e., bid_price)
    #    """
    #    level_cols = [col for col in df.columns if col.endswith(f"_{level}")]
    #    level_cols_cleaned = [elem[:-2] for elem in level_cols]
    #    #
    #    zip_iterator = zip(level_cols, level_cols_cleaned)
    #    col_dict = dict(zip_iterator)
    #    #
    #    df = df.rename(columns=col_dict)
    #    #
    #    return df

    @staticmethod
    def _resample_to_1sec(data: pd.DataFrame) -> pd.DataFrame:
        """
        Resample the data to 1 second.

        :param data: raw data
        :return: data resampled to 1 sec
        """
        data = data.set_index("timestamp")
        data_resampled = []
        for full_symbol in data["full_symbol"].unique():
            data_part = data[data["full_symbol"] == full_symbol]
            # Resample to 1 sec.
            data_part = (
                data_part[["bid_size", "bid_price", "ask_size", "ask_price"]]
                # Label right is used to match conventions used by CryptoChassis.
                .resample("S", label="right").mean()
            )
            # Add the full_symbol column back.
            data_part["full_symbol"] = full_symbol
            data_resampled.append(data_part)
        df_resampled = pd.concat(data_resampled)
        return df_resampled.reset_index()

    def _get_rt_data(self) -> pd.DataFrame:
        """
        Load and process real time data.
        """
        # Load real time data from the database.
        ccxt_rt = self.ccxt_rt_im_client.read_data(
            self.universe, self.start_ts, self.end_ts, None, "assert"
        )
        ccxt_rt = ccxt_rt.reset_index()
        # if self.data_type == "bid_ask":
        #    # CCXT timestamp data goes up to milliseconds, so one needs to round it to minutes.
        #    ccxt_rt["timestamp"] = ccxt_rt["timestamp"].apply(
        #        lambda x: x.round(freq="T")
        #    )
        #    # Choose the specific order level (first level by default).
        #    ccxt_rt = self._clean_data_for_orderbook_level(ccxt_rt)
        # Remove duplicated columns and reindex real time data.
        _LOG.info("Filter duplicates in real time data")
        ccxt_rt = self._preprocess_data(ccxt_rt)

        if self.resample_1sec:
            ccxt_rt = self._resample_to_1sec(ccxt_rt)
        # Reindex the data.
        ccxt_rt_reindex = ccxt_rt.set_index(["timestamp", "full_symbol"])
        return ccxt_rt_reindex

    def _get_daily_data(self) -> pd.DataFrame:
        """
        Load and process daily data.
        """
        # List files for given exchange.
        timestamp_filters = hparque.get_parquet_filters_from_timestamp_interval(
            "by_year_month", self.start_ts, self.end_ts
        )
        # Load daily data from s3 parquet.
        daily_data = hparque.from_parquet(
            self.s3_path, filters=timestamp_filters, aws_profile=self.aws_profile
        )
        if "timestamp" in daily_data.columns:
            # Sometimes the data contains `timestamp` column which is not needed
            # since there is always a timestamp in the index.
            daily_data = daily_data.drop(columns=["timestamp"])
        daily_data = daily_data.reset_index()
        daily_data = daily_data.loc[daily_data["timestamp"] >= self.start_ts]
        daily_data = daily_data.loc[daily_data["timestamp"] <= self.end_ts]
        # Build full symbol column.
        daily_data["full_symbol"] = imvcufusy.build_full_symbol(
            daily_data["exchange_id"], daily_data["currency_pair"]
        )
        # Filter out currency pair which are not in universe determined for the
        #  comparison at hand.
        daily_data = daily_data[daily_data["full_symbol"].isin(self.universe)]
        # Remove deprecated columns.
        daily_data = daily_data.drop(columns=["exchange_id", "currency_pair"])
        # Remove duplicated columns and reindex daily data.
        _LOG.info("Filter duplicates in daily data")
        daily_data = self._preprocess_data(daily_data)
        # Reindex the data.
        daily_data_reindex = daily_data.set_index(["timestamp", "full_symbol"])
        return daily_data_reindex

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter rows and columns.

        :param data: the data to process
        :return: filtered data with no duplicates
        """
        # Remove duplicated rows in the data.
        data = self._filter_duplicates(data)
        expected_columns = self.expected_columns[self.data_type]
        missing_columns = set(expected_columns) - set(data.columns)
        if len(missing_columns) != 0:
            _LOG.warning("Missing expected columns %s", missing_columns)
            # Fill missing columns with None so reconciliation can continue.
            data[list(missing_columns)] = None
        data = data[expected_columns]
        return data

    def _compare_general(
        self, rt_data: pd.DataFrame, daily_data: pd.DataFrame
    ) -> List[str]:
        """
        Compare general attributes of the datasets (missing rows, gaps in
        data).

        :return list of error strings specifying what is wrong with the data.
        """
        # Inform if both dataframes are empty,
        # most likely there is a wrong arg value given.
        if rt_data.empty and daily_data.empty:
            message = (
                "Both realtime and staged data are missing, \n"
                + "Did you provide correct arguments?"
            )
            hdbg.dfatal(message=message)
        # Get missing data.
        rt_missing_data, daily_missing_data = hpandas.find_gaps_in_dataframes(
            rt_data, daily_data
        )
        error_message = []
        if not rt_missing_data.empty:
            error_message.append("Missing real time data:")
            error_message.append(
                hpandas.get_df_signature(
                    rt_missing_data, num_rows=len(rt_missing_data)
                )
            )
        if not daily_missing_data.empty:
            error_message.append("Missing daily data:")
            error_message.append(
                hpandas.get_df_signature(
                    daily_missing_data, num_rows=len(daily_missing_data)
                )
            )
        # Assert neither of the datasets has contains gaps
        #  in datetime index.
        # All of the checks are done by minute apart from checking raw bid_ask data.
        # TODO(Juraj): This is still not a 100% check, it should be applied
        #  to each symbol respectively.
        freq = "S" if self.resample_1sec else "T"
        rt_data_gaps = hpandas.find_gaps_in_time_series(
            rt_data.index.get_level_values(0).unique(),
            self.start_ts,
            self.end_ts,
            freq,
        )
        if not rt_data_gaps.empty:
            error_message.append("Gaps in real time data:")
            error_message.append(
                hpandas.get_df_signature(
                    rt_data_gaps.to_frame(), num_rows=len(rt_data_gaps)
                )
            )
        daily_data_gaps = hpandas.find_gaps_in_time_series(
            daily_data.index.get_level_values(0).unique(),
            self.start_ts,
            self.end_ts,
            freq,
        )
        if not daily_data_gaps.empty:
            error_message.append("Gaps in daily data:")
            error_message.append(
                hpandas.get_df_signature(
                    daily_data_gaps.to_frame(), num_rows=len(daily_data_gaps)
                )
            )
        return error_message

    def _compare_ohlcv(
        self, rt_data: pd.DataFrame, daily_data: pd.DataFrame
    ) -> None:
        """
        Compare OHLCV real time and daily data.

        :param rt_data: real time data
        :param daily_data: daily data
        """
        # Perform general comparison.
        error_message = self._compare_general(rt_data, daily_data)
        # Compare dataframe contents.
        data_difference = hpandas.compare_dataframe_rows(rt_data, daily_data)
        if not data_difference.empty:
            error_message.append("Differing table contents:")
            error_message.append(
                hpandas.get_df_signature(
                    data_difference, num_rows=len(data_difference)
                )
            )
        if error_message:
            hdbg.dfatal(message="\n".join(error_message))
        _LOG.info("No differences were found between real time and daily data")

    def _compare_bid_ask(
        self, rt_data: pd.DataFrame, daily_data: pd.DataFrame
    ) -> None:
        """
        Compare order book real time and daily data.

        :param rt_data: real time data
        :param daily_data: daily data
        """
        # Perform general comparison.
        error_message = self._compare_general(rt_data, daily_data)
        data = rt_data.merge(
            daily_data,
            how="outer",
            left_index=True,
            right_index=True,
            suffixes=("_ccxt", "_cc"),
        )
        # Move the same metrics from two vendors together.
        data = data.reindex(sorted(data.columns), axis=1)
        #
        _LOG.info("Start date = %s", data.reset_index()["timestamp"].min())
        _LOG.info("End date = %s", data.reset_index()["timestamp"].max())
        _LOG.info(
            "Avg observations per coin = %s",
            len(data) / len(data.reset_index()["full_symbol"].unique()),
        )
        # Move the same metrics from two vendors together.
        data = data.reindex(sorted(data.columns), axis=1)
        # NaNs observation.
        _LOG.info(
            "Number of observations with NaN in any of the columns = %s",
            len(data[data.isna().any(axis=1)]),
        )
        _LOG.info(
            "Number of observations with NaNs for both vendors = %s",
            len(data[data.isna().all(axis=1)]),
        )
        # Remove NaNs.
        # TODO(Juraj): If NaNs appear, log and add to the error message.
        data = hpandas.dropna(data, report_stats=True)
        #
        # Full symbol will not be relevant in calculation loops below.
        bid_ask_cols = self.expected_columns[self.data_type]
        bid_ask_cols.remove("full_symbol")
        bid_ask_cols.remove("timestamp")
        # Each bid ask value will have a notional and a relative difference between two sources.
        for col in bid_ask_cols:
            # Notional difference: CC value - DB value.
            data[f"{col}_diff"] = data[f"{col}_cc"] - data[f"{col}_ccxt"]
            # Relative value: (CC value - DB value)/DB value.
            data[f"{col}_relative_diff_pct"] = (
                100
                * (data[f"{col}_cc"] - data[f"{col}_ccxt"])
                / data[f"{col}_ccxt"]
            )
        #
        # Calculate the mean value of differences for each coin.
        diff_stats = []
        grouper = data.groupby(["full_symbol"])
        for col in bid_ask_cols:
            diff_stats.append(grouper[f"{col}_diff"].mean())
            diff_stats.append(grouper[f"{col}_relative_diff_pct"].mean())
        #
        diff_stats = pd.concat(diff_stats, axis=1)
        # Show stats for differences for prices.
        diff_stats_prices_cols = filter(lambda col: "price" in col, bid_ask_cols)
        diff_stats_prices_cols = list(
            map(lambda col: f"{col}_relative_diff_pct", diff_stats_prices_cols)
        )
        diff_stats_prices = diff_stats[diff_stats_prices_cols]
        _LOG.info(
            "Difference stats for prices: %s",
            hpandas.get_df_signature(
                diff_stats_prices, num_rows=len(diff_stats_prices)
            ),
        )
        # Define the maximum acceptable difference in %.
        threshold = self.bid_ask_accuracy
        # Log the difference.
        for index, row in diff_stats_prices.iterrows():
            for price_col in diff_stats_prices_cols:
                if abs(row[price_col]) > threshold:
                    price_col_base = price_col.rstrip("_relative_diff_pct")
                    message = (
                        f"Difference between {price_col_base} in real time and daily "
                        f"data for `{index}` coin is more than {threshold}%."
                    )
                    error_message.append(message)
        # Show stats for differences for sizes.
        diff_stats_sizes_cols = filter(lambda col: "size" in col, bid_ask_cols)
        diff_stats_sizes_cols = list(
            map(lambda col: f"{col}_relative_diff_pct", diff_stats_sizes_cols)
        )
        diff_stats_sizes = diff_stats[diff_stats_sizes_cols]
        _LOG.info(
            "Difference stats for sizes: %s",
            hpandas.get_df_signature(
                diff_stats_sizes, num_rows=len(diff_stats_sizes)
            ),
        )
        # Log the difference.
        for index, row in diff_stats_sizes.iterrows():
            for size_col in diff_stats_sizes_cols:
                if abs(row[size_col]) > threshold:
                    size_col_base = size_col.rstrip("_relative_diff_pct")
                    message = (
                        f"Difference between {size_col_base} in real time and daily "
                        f"data for `{index}` coin is more than {threshold}%."
                    )
                    error_message.append(message)
        if error_message:
            hdbg.dfatal(message="\n".join(error_message))
        _LOG.info("No differences were found between real time and daily data")
        return

    def _get_universe(self, s3_vendor: str) -> List[str]:
        """
        Get the universe used for reconciliation.

        :param s3_vendor: determines origin of the data, i.e. CCXT or CryptoChassis
         which determines if we should do an intersection of vendor universes or use
         CCXT only universe.
        """
        # CCXT real time universe.
        ccxt_universe = self.ccxt_rt_im_client.get_universe()
        # CC daily universe.
        # TODO(Juraj): replace this hardcoded temporary solution.
        cc_universe = [
            "binance::ADA_USDT",
            "binance::BNB_USDT",
            "binance::BTC_USD",
            "binance::BTC_USDT",
            "binance::DOGE_USDT",
            "binance::DOT_USDT",
            "binance::EOS_USDT",
            "binance::ETH_USD",
            "binance::ETH_USDT",
            "binance::SOL_USDT",
            "binance::XRP_USDT",
        ]
        if s3_vendor == "ccxt":
            universe = ccxt_universe
        else:
            # Intersection of universes that will be used for analysis.
            universe = list(set(ccxt_universe) & set(cc_universe))
        return universe


def _run(args: argparse.Namespace) -> None:
    reconciler = RealTimeHistoricalReconciler(args)
    # Run reconciliation process.
    reconciler.run()


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args)


if __name__ == "__main__":
    _main(_parse())
