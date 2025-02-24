import datetime
import logging

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import im_v2.common.data.client as icdc
import im_v2.ig.data.client.ig_historical_pq_by_asset_taq_bar_client as imvidcihpbatbc

_LOG = logging.getLogger(__name__)


class TestIgHistoricalPqByTileTaqBarClient1(icdc.ImClientTestCase):
    """
    For all the test methods see description of corresponding private method in
    the parent class.
    """

    # TODO(gp): This should go in an example file.
    @staticmethod
    def get_IgHistoricalPqByTileTaqBarClient_example1():
        vendor = "ig"
        # TODO(gp): Use the weekly data once they also support the shorter
        # Parquet condition filtering since it's faster.
        # root_dir_name = "/cache/tiled.bar_data.all.2010.weekofyear"
        # partition_mode = "by_year_week"
        # aws s3 ls --profile am s3://alphamatic-data/unit_test/tiled_data/tiled.bar_data.all.2010_2022.20220204/igid\=13684
        root_dir_name = "s3://cryptokaizen-unit-test/alphamatic-data/unit_test/tiled_data/tiled.bar_data.all.2010_2022.20220204"
        aws_profile = "ck"
        partition_mode = "by_year_month"
        im_client = imvidcihpbatbc.IgHistoricalPqByTileTaqBarClient(
            vendor, root_dir_name, aws_profile, partition_mode
        )
        return im_client

    # TODO(gp): Add this check to ImClientTestCase so that we can check what is
    #  the output of the derived class.
    @pytest.mark.slow("6 secs")
    def test_read_data_for_multiple_symbols1(self) -> None:
        """
        Test:
        - reading data for one full symbol
        - start_ts = end_ts = None
        """
        im_client = self.get_IgHistoricalPqByTileTaqBarClient_example1()
        #
        full_symbols = ["13684"]
        start_ts = pd.Timestamp("2020-12-01 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-12-02 09:31:00+00:00")
        columns = None
        full_symbol_col_name = "igid"
        actual_df = im_client._read_data_for_multiple_symbols(
            full_symbols, start_ts, end_ts, columns, full_symbol_col_name
        )
        txt = []
        txt.append("df=%s" % hpandas.df_to_str(actual_df, print_dtypes=True))
        txt = "\n".join(txt)
        self.check_string(txt)

    @pytest.mark.superslow("30 secs")
    def test_read_data1(self) -> None:
        im_client = self.get_IgHistoricalPqByTileTaqBarClient_example1()
        full_symbol = "13684"
        #
        expected_length = 121187
        expected_column_names = [
            "all_day_notional",
            "all_day_volume",
            "ask",
            "ask_high",
            "ask_low",
            "ask_size",
            "bid",
            "bid_high",
            "bid_low",
            "bid_size",
            "close",
            "currency",
            "day_high",
            "day_low",
            "day_notional",
            "day_num_spread",
            "day_num_trade",
            "day_sided_ask_count",
            "day_sided_ask_notional",
            "day_sided_ask_shares",
            "day_sided_bid_count",
            "day_sided_bid_notional",
            "day_sided_bid_shares",
            "day_spread",
            "day_vol_prc_sqr",
            "day_volume",
            "igid",
            "good_ask",
            "good_ask_size",
            "good_bid",
            "good_bid_size",
            "high",
            "interval",
            "last_trade",
            "last_trade_time",
            "last_trade_volume",
            "low",
            # "month",
            "notional",
            "open",
            "sided_ask_count",
            "sided_ask_notional",
            "sided_ask_shares",
            "sided_bid_count",
            "sided_bid_notional",
            "sided_bid_shares",
            "start_time",
            "ticker",
            "timestamp_db",
            "vendor_date",
            "volume",
            # "year",
        ]
        expected_column_unique_values = None
        expected_signature = "__CHECK_STRING__"
        self._test_read_data1(
            im_client,
            full_symbol,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
            expected_signature=expected_signature,
        )

    @pytest.mark.slow("6 secs")
    def test_read_data5(self) -> None:
        im_client = self.get_IgHistoricalPqByTileTaqBarClient_example1()
        full_symbols = ["13684"]
        start_ts = pd.Timestamp("2020-12-01 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-12-02 09:31:00+00:00")
        #
        expected_length = 479
        expected_column_names = [
            "all_day_notional",
            "all_day_volume",
            "ask",
            "ask_high",
            "ask_low",
            "ask_size",
            "bid",
            "bid_high",
            "bid_low",
            "bid_size",
            "close",
            "currency",
            "day_high",
            "day_low",
            "day_notional",
            "day_num_spread",
            "day_num_trade",
            "day_sided_ask_count",
            "day_sided_ask_notional",
            "day_sided_ask_shares",
            "day_sided_bid_count",
            "day_sided_bid_notional",
            "day_sided_bid_shares",
            "day_spread",
            "day_vol_prc_sqr",
            "day_volume",
            "igid",
            "good_ask",
            "good_ask_size",
            "good_bid",
            "good_bid_size",
            "high",
            "interval",
            "last_trade",
            "last_trade_time",
            "last_trade_volume",
            "low",
            # "month",
            "notional",
            "open",
            "sided_ask_count",
            "sided_ask_notional",
            "sided_ask_shares",
            "sided_bid_count",
            "sided_bid_notional",
            "sided_bid_shares",
            "start_time",
            "ticker",
            "timestamp_db",
            "vendor_date",
            "volume",
            # "year",
        ]
        expected_column_unique_values = {
            "vendor_date": [datetime.date(2020, 12, 1)]
        }
        expected_signature = "__CHECK_STRING__"
        self._test_read_data5(
            im_client,
            full_symbols,
            start_ts,
            end_ts,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
            expected_signature=expected_signature,
        )
