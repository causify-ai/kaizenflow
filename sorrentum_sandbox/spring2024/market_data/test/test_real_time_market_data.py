import logging

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hsql as hsql
import im_v2.common.data.client as icdc
import im_v2.common.db.db_utils as imvcddbut
import market_data.market_data_example as mdmadaex

_LOG = logging.getLogger(__name__)


# TODO(Grisha): CmTask7237.
class TestRealTimeMarketData_TestCase(imvcddbut.TestImDbHelper):
    # Override this in a child class to test using a specific table.
    _TABLE_NAME = None

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Create test table.
        universe_version = "infer_from_data"
        im_client = icdc.get_mock_realtime_client(
            universe_version,
            self.connection,
            self._TABLE_NAME,
            resample_1min=True,
        )
        # Set up market data client.
        self.market_data = mdmadaex.get_RealtimeMarketData2_example1(im_client)

    def tear_down_test(self) -> None:
        # Delete the table.
        hsql.remove_table(self.connection, "mock2_marketdata")

    def _test_get_data_for_last_period1(self, expected_df_as_str: str) -> None:
        """
        Test get_data_for_last_period() all conditional periods.
        """
        # Set up processing parameters.
        timedelta = pd.Timedelta("1D")
        ts_col_name = "timestamp"
        actual = self.market_data.get_data_for_last_period(
            timedelta,
            ts_col_name=ts_col_name,
        )
        # pylint: enable=line-too-long
        self._check_dataframe(actual, expected_df_as_str)

    def _test_get_data_for_interval1(self, expected_df_as_str: str) -> None:
        """
        - Ask data for [9:30, 9:45]
        """
        # Specify processing parameters.
        start_ts = pd.Timestamp("2022-04-22 09:30:00-05:00")
        end_ts = pd.Timestamp("2022-04-22 09:45:00-05:00")
        ts_col_name = "timestamp"
        asset_ids = None
        actual = self.market_data.get_data_for_interval(
            start_ts, end_ts, ts_col_name, asset_ids
        )
        self._check_dataframe(actual, expected_df_as_str)

    def _test_get_data_for_interval2(self, expected_df_as_str: str) -> None:
        """
        - Ask data for [10:30, 12:00]
        """
        # Set up processing parameters.
        start_ts = pd.Timestamp("2022-04-22 10:30:00-05:00")
        end_ts = pd.Timestamp("2022-04-22 12:00:00-05:00")
        ts_col_name = "timestamp"
        asset_ids = None
        actual = self.market_data.get_data_for_interval(
            start_ts, end_ts, ts_col_name, asset_ids
        )
        self._check_dataframe(actual, expected_df_as_str)

    def _test_get_data_at_timestamp1(self, expected_df_as_str: str) -> None:
        """
        - Ask data for 9:35
        - The returned data is for 9:35
        """
        # Set up processing parameters.
        ts = pd.Timestamp("2022-04-22 09:30:00-05:00")
        ts_col_name = "timestamp"
        asset_ids = None
        actual = self.market_data.get_data_at_timestamp(
            ts, ts_col_name, asset_ids
        )
        self._check_dataframe(actual, expected_df_as_str)

    def _check_dataframe(
        self,
        actual_df: pd.DataFrame,
        expected_df_as_str: str,
    ) -> None:
        """
        Check test results for Pandas dataframe format.

        We call it `_check_dataframe` and not `check_dataframe` to avoid overriding
        the method of the base class `TestCase`.

        :param actual_df: the result dataframe
        :param expected_df_as_str: expected result in string format
        """
        # Check.
        actual_df = actual_df[sorted(actual_df.columns)]
        actual_df_as_str = hpandas.df_to_str(
            actual_df, print_shape_info=True, tag="df"
        )
        _LOG.info("-> %s", actual_df_as_str)
        self.assert_equal(
            actual_df_as_str,
            expected_df_as_str,
            dedent=True,
            fuzzy_match=True,
        )


# TODO(Shaopeng Z): hangs when outside CK infra.
@pytest.mark.requires_ck_infra
class TestRealTimeMarketData2_forOhlcv(TestRealTimeMarketData_TestCase):
    _TABLE_NAME = "ccxt_ohlcv_futures"

    def test_get_data_for_last_period1(self) -> None:
        """
        Test get_data_for_last_period() all conditional periods.
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 12:30:00-04:00]
        columns=asset_id,close,end_download_timestamp,full_symbol,high,id,knowledge_timestamp,low,open,start_timestamp,ticks,volume
        shape=(121, 12)
        asset_id close end_download_timestamp full_symbol high id knowledge_timestamp low open start_timestamp ticks volume
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 60.0 2022-04-22 00:00:00+00:00 binance::ETH_USDT 40.0 0.0 2022-04-22 00:00:00+00:00 50.0 30.0 2022-04-22 10:29:00-04:00 80.0 70.0
        2022-04-22 10:31:00-04:00 1464553467 NaN NaT binance::ETH_USDT NaN NaN NaT NaN NaN 2022-04-22 10:30:00-04:00 NaN NaN
        2022-04-22 10:32:00-04:00 1464553467 NaN NaT binance::ETH_USDT NaN NaN NaT NaN NaN 2022-04-22 10:31:00-04:00 NaN NaN
        ...
        2022-04-22 12:28:00-04:00 1464553467 NaN NaT binance::ETH_USDT NaN NaN NaT NaN NaN 2022-04-22 12:27:00-04:00 NaN NaN
        2022-04-22 12:29:00-04:00 1464553467 NaN NaT binance::ETH_USDT NaN NaN NaT NaN NaN 2022-04-22 12:28:00-04:00 NaN NaN
        2022-04-22 12:30:00-04:00 1464553467 65.0 2022-04-22 00:00:00+00:00 binance::ETH_USDT 45.0 4.0 2022-04-22 00:00:00+00:00 55.0 35.0 2022-04-22 12:29:00-04:00 75.0 75.0
        """
        # pylint: enable=line-too-long
        self._test_get_data_for_last_period1(expected_df_as_str)

    def test_get_data_for_interval1(self) -> None:
        """
        - Ask data for [9:30, 9:45]
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 10:30:00-04:00]
        columns=asset_id,close,end_download_timestamp,full_symbol,high,id,knowledge_timestamp,low,open,start_timestamp,ticks,volume
        shape=(1, 12)
        asset_id close end_download_timestamp full_symbol high id knowledge_timestamp low open start_timestamp ticks volume
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 60.0 2022-04-22 00:00:00+00:00 binance::ETH_USDT 40.0 0 2022-04-22 00:00:00+00:00 50.0 30.0 2022-04-22 10:29:00-04:00 80.0 70.0
        """
        # pylint: enable=line-too-long
        self._test_get_data_for_interval1(expected_df_as_str)

    def test_get_data_for_interval2(self) -> None:
        """
        - Ask data for [10:30, 12:00]
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 12:30:00-04:00, 2022-04-22 12:30:00-04:00]
        columns=asset_id,close,end_download_timestamp,full_symbol,high,id,knowledge_timestamp,low,open,start_timestamp,ticks,volume
        shape=(1, 12)
        asset_id close end_download_timestamp full_symbol high id knowledge_timestamp low open start_timestamp ticks volume
        end_timestamp
        2022-04-22 12:30:00-04:00 1464553467 65.0 2022-04-22 00:00:00+00:00 binance::ETH_USDT 45.0 4 2022-04-22 00:00:00+00:00 55.0 35.0 2022-04-22 12:29:00-04:00 75.0 75.0
        """
        # pylint: enable=line-too-long
        self._test_get_data_for_interval2(expected_df_as_str)

    def test_get_data_at_timestamp1(self) -> None:
        """
        - Ask data for 9:35
        - The returned data is for 9:35
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 10:30:00-04:00]
        columns=asset_id,close,end_download_timestamp,full_symbol,high,id,knowledge_timestamp,low,open,start_timestamp,ticks,volume
        shape=(1, 12)
        asset_id close end_download_timestamp full_symbol high id knowledge_timestamp low open start_timestamp ticks volume
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 60.0 2022-04-22 00:00:00+00:00 binance::ETH_USDT 40.0 0 2022-04-22 00:00:00+00:00 50.0 30.0 2022-04-22 10:29:00-04:00 80.0 70.0
        """
        # pylint: enable=line-too-long
        self._test_get_data_at_timestamp1(expected_df_as_str)

    def test_get_twap_price1(self) -> None:
        """
        Test `get_twap_price()` for specified parameters.
        """
        # Set up processing parameters.
        start_ts = pd.Timestamp("2022-04-22 10:30:00-05:00")
        end_ts = pd.Timestamp("2022-04-22 15:00:00-05:00")
        ts_col_name = "timestamp"
        asset_ids = None
        column = "close"
        # Get
        actual = self.market_data.get_twap_price(
            start_ts, end_ts, ts_col_name, asset_ids, column
        )
        expected_length = None
        expected_column_names = None
        expected_column_unique_values = None
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 15:00:00-05:00, 2022-04-22 15:00:00-05:00]
        columns=asset_id,start_timestamp,close
        shape=(1, 3)
                                     asset_id           start_timestamp  close
        end_timestamp
        2022-04-22 15:00:00-05:00  1464553467 2022-04-22 10:30:00-05:00   65.0
        """
        # pylint: enable=line-too-long
        # Check the output series.
        self.check_df_output(
            actual,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
            expected_signature=expected_df_as_str,
        )


# TODO(Shaopeng Z): hangs when outside CK infra.
@pytest.mark.requires_ck_infra
class TestRealTimeMarketData2_forBidAskResampled(TestRealTimeMarketData_TestCase):
    _TABLE_NAME = "ccxt_bid_ask_futures_resampled_1min"

    def test_get_data_for_last_period1(self) -> None:
        """
        Test get_data_for_last_period() all conditional periods.
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 12:30:00-04:00]
        columns=asset_id,end_download_timestamp,full_symbol,knowledge_timestamp,level_1.ask_price.close,level_1.ask_price.high,level_1.ask_price.low,level_1.ask_price.mean,level_1.ask_price.open,level_1.ask_size.close,level_1.ask_size.max,level_1.ask_size.mean,level_1.ask_size.min,level_1.ask_size.open,level_1.bid_ask_midpoint.close,level_1.bid_ask_midpoint.max,level_1.bid_ask_midpoint.mean,level_1.bid_ask_midpoint.min,level_1.bid_ask_midpoint.open,level_1.bid_ask_midpoint_autocovar.100ms,level_1.bid_ask_midpoint_var.100ms,level_1.bid_price.close,level_1.bid_price.high,level_1.bid_price.low,level_1.bid_price.mean,level_1.bid_price.open,level_1.bid_size.close,level_1.bid_size.max,level_1.bid_size.mean,level_1.bid_size.min,level_1.bid_size.open,level_1.half_spread.close,level_1.half_spread.max,level_1.half_spread.mean,level_1.half_spread.min,level_1.half_spread.open,level_1.log_size_imbalance.close,level_1.log_size_imbalance.max,level_1.log_size_imbalance.mean,level_1.log_size_imbalance.min,level_1.log_size_imbalance.open,level_1.log_size_imbalance_autocovar.100ms,level_1.log_size_imbalance_var.100ms,start_timestamp
        shape=(121, 44)
        asset_id end_download_timestamp full_symbol knowledge_timestamp level_1.ask_price.close level_1.ask_price.high level_1.ask_price.low level_1.ask_price.mean level_1.ask_price.open level_1.ask_size.close level_1.ask_size.max level_1.ask_size.mean level_1.ask_size.min level_1.ask_size.open level_1.bid_ask_midpoint.close level_1.bid_ask_midpoint.max level_1.bid_ask_midpoint.mean level_1.bid_ask_midpoint.min level_1.bid_ask_midpoint.open level_1.bid_ask_midpoint_autocovar.100ms level_1.bid_ask_midpoint_var.100ms level_1.bid_price.close level_1.bid_price.high level_1.bid_price.low level_1.bid_price.mean level_1.bid_price.open level_1.bid_size.close level_1.bid_size.max level_1.bid_size.mean level_1.bid_size.min level_1.bid_size.open level_1.half_spread.close level_1.half_spread.max level_1.half_spread.mean level_1.half_spread.min level_1.half_spread.open level_1.log_size_imbalance.close level_1.log_size_imbalance.max level_1.log_size_imbalance.mean level_1.log_size_imbalance.min level_1.log_size_imbalance.open level_1.log_size_imbalance_autocovar.100ms level_1.log_size_imbalance_var.100ms start_timestamp
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 2022-04-22 00:00:00+00:00 binance::ETH_USDT 2022-04-22 00:00:00+00:00 30.0 40.0 50.0 60.0 60.0 60.0 40.0 50.0 30.0 50.0 20.0 40.0 30.0 50.0 5.0 30.0 60.0 50.0 60.0 30.0 40.0 40.0 10.0 20.0 30.0 15.0 5.0 30.0 50.0 40.0 60.0 10.0 40.0 60.0 50.0 30.0 15.0 50.0 40.0 2022-04-22 10:29:00-04:00
        2022-04-22 10:31:00-04:00 1464553467 NaT binance::ETH_USDT NaT NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN 2022-04-22 10:30:00-04:00
        2022-04-22 10:32:00-04:00 1464553467 NaT binance::ETH_USDT NaT NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN 2022-04-22 10:31:00-04:00
        ...
        2022-04-22 12:28:00-04:00 1464553467 NaT binance::ETH_USDT NaT NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN 2022-04-22 12:27:00-04:00
        2022-04-22 12:29:00-04:00 1464553467 NaT binance::ETH_USDT NaT NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN 2022-04-22 12:28:00-04:00
        2022-04-22 12:30:00-04:00 1464553467 2022-04-22 00:00:00+00:00 binance::ETH_USDT 2022-04-22 00:00:00+00:00 71.0 31.0 41.0 51.0 61.0 71.0 41.0 51.0 31.0 61.0 20.0 40.0 30.0 50.0 5.0 30.0 60.0 71.0 31.0 41.0 51.0 61.0 21.0 41.0 51.0 31.0 11.0 30.0 50.0 40.0 60.0 10.0 40.0 60.0 50.0 30.0 15.0 50.0 40.0 2022-04-22 12:29:00-04:00
        """
        self._test_get_data_for_last_period1(expected_df_as_str)

    def test_get_data_for_interval1(self) -> None:
        """
        - Ask data for [9:30, 9:45]
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 10:30:00-04:00]
        columns=asset_id,end_download_timestamp,full_symbol,knowledge_timestamp,level_1.ask_price.close,level_1.ask_price.high,level_1.ask_price.low,level_1.ask_price.mean,level_1.ask_price.open,level_1.ask_size.close,level_1.ask_size.max,level_1.ask_size.mean,level_1.ask_size.min,level_1.ask_size.open,level_1.bid_ask_midpoint.close,level_1.bid_ask_midpoint.max,level_1.bid_ask_midpoint.mean,level_1.bid_ask_midpoint.min,level_1.bid_ask_midpoint.open,level_1.bid_ask_midpoint_autocovar.100ms,level_1.bid_ask_midpoint_var.100ms,level_1.bid_price.close,level_1.bid_price.high,level_1.bid_price.low,level_1.bid_price.mean,level_1.bid_price.open,level_1.bid_size.close,level_1.bid_size.max,level_1.bid_size.mean,level_1.bid_size.min,level_1.bid_size.open,level_1.half_spread.close,level_1.half_spread.max,level_1.half_spread.mean,level_1.half_spread.min,level_1.half_spread.open,level_1.log_size_imbalance.close,level_1.log_size_imbalance.max,level_1.log_size_imbalance.mean,level_1.log_size_imbalance.min,level_1.log_size_imbalance.open,level_1.log_size_imbalance_autocovar.100ms,level_1.log_size_imbalance_var.100ms,start_timestamp
        shape=(1, 44)
        asset_id end_download_timestamp full_symbol knowledge_timestamp level_1.ask_price.close level_1.ask_price.high level_1.ask_price.low level_1.ask_price.mean level_1.ask_price.open level_1.ask_size.close level_1.ask_size.max level_1.ask_size.mean level_1.ask_size.min level_1.ask_size.open level_1.bid_ask_midpoint.close level_1.bid_ask_midpoint.max level_1.bid_ask_midpoint.mean level_1.bid_ask_midpoint.min level_1.bid_ask_midpoint.open level_1.bid_ask_midpoint_autocovar.100ms level_1.bid_ask_midpoint_var.100ms level_1.bid_price.close level_1.bid_price.high level_1.bid_price.low level_1.bid_price.mean level_1.bid_price.open level_1.bid_size.close level_1.bid_size.max level_1.bid_size.mean level_1.bid_size.min level_1.bid_size.open level_1.half_spread.close level_1.half_spread.max level_1.half_spread.mean level_1.half_spread.min level_1.half_spread.open level_1.log_size_imbalance.close level_1.log_size_imbalance.max level_1.log_size_imbalance.mean level_1.log_size_imbalance.min level_1.log_size_imbalance.open level_1.log_size_imbalance_autocovar.100ms level_1.log_size_imbalance_var.100ms start_timestamp
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 2022-04-22 00:00:00+00:00 binance::ETH_USDT 2022-04-22 00:00:00+00:00 30.0 40.0 50.0 60.0 60.0 60.0 40.0 50.0 30.0 50.0 20.0 40.0 30.0 50.0 5.0 30.0 60.0 50.0 60.0 30.0 40.0 40.0 10.0 20.0 30.0 15.0 5.0 30.0 50.0 40.0 60.0 10.0 40.0 60.0 50.0 30.0 15.0 50.0 40.0 2022-04-22 10:29:00-04:00
        """
        # pylint: enable=line-too-long
        self._test_get_data_for_interval1(expected_df_as_str)

    def test_get_data_for_interval2(self) -> None:
        """
        - Ask data for [10:30, 12:00]
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 12:30:00-04:00, 2022-04-22 12:30:00-04:00]
        columns=asset_id,end_download_timestamp,full_symbol,knowledge_timestamp,level_1.ask_price.close,level_1.ask_price.high,level_1.ask_price.low,level_1.ask_price.mean,level_1.ask_price.open,level_1.ask_size.close,level_1.ask_size.max,level_1.ask_size.mean,level_1.ask_size.min,level_1.ask_size.open,level_1.bid_ask_midpoint.close,level_1.bid_ask_midpoint.max,level_1.bid_ask_midpoint.mean,level_1.bid_ask_midpoint.min,level_1.bid_ask_midpoint.open,level_1.bid_ask_midpoint_autocovar.100ms,level_1.bid_ask_midpoint_var.100ms,level_1.bid_price.close,level_1.bid_price.high,level_1.bid_price.low,level_1.bid_price.mean,level_1.bid_price.open,level_1.bid_size.close,level_1.bid_size.max,level_1.bid_size.mean,level_1.bid_size.min,level_1.bid_size.open,level_1.half_spread.close,level_1.half_spread.max,level_1.half_spread.mean,level_1.half_spread.min,level_1.half_spread.open,level_1.log_size_imbalance.close,level_1.log_size_imbalance.max,level_1.log_size_imbalance.mean,level_1.log_size_imbalance.min,level_1.log_size_imbalance.open,level_1.log_size_imbalance_autocovar.100ms,level_1.log_size_imbalance_var.100ms,start_timestamp
        shape=(1, 44)
        asset_id end_download_timestamp full_symbol knowledge_timestamp level_1.ask_price.close level_1.ask_price.high level_1.ask_price.low level_1.ask_price.mean level_1.ask_price.open level_1.ask_size.close level_1.ask_size.max level_1.ask_size.mean level_1.ask_size.min level_1.ask_size.open level_1.bid_ask_midpoint.close level_1.bid_ask_midpoint.max level_1.bid_ask_midpoint.mean level_1.bid_ask_midpoint.min level_1.bid_ask_midpoint.open level_1.bid_ask_midpoint_autocovar.100ms level_1.bid_ask_midpoint_var.100ms level_1.bid_price.close level_1.bid_price.high level_1.bid_price.low level_1.bid_price.mean level_1.bid_price.open level_1.bid_size.close level_1.bid_size.max level_1.bid_size.mean level_1.bid_size.min level_1.bid_size.open level_1.half_spread.close level_1.half_spread.max level_1.half_spread.mean level_1.half_spread.min level_1.half_spread.open level_1.log_size_imbalance.close level_1.log_size_imbalance.max level_1.log_size_imbalance.mean level_1.log_size_imbalance.min level_1.log_size_imbalance.open level_1.log_size_imbalance_autocovar.100ms level_1.log_size_imbalance_var.100ms start_timestamp
        end_timestamp
        2022-04-22 12:30:00-04:00 1464553467 2022-04-22 00:00:00+00:00 binance::ETH_USDT 2022-04-22 00:00:00+00:00 71.0 31.0 41.0 51.0 61.0 71.0 41.0 51.0 31.0 61.0 20.0 40.0 30.0 50.0 5.0 30.0 60.0 71.0 31.0 41.0 51.0 61.0 21.0 41.0 51.0 31.0 11.0 30.0 50.0 40.0 60.0 10.0 40.0 60.0 50.0 30.0 15.0 50.0 40.0 2022-04-22 12:29:00-04:00
        """
        # pylint: enable=line-too-long
        self._test_get_data_for_interval2(expected_df_as_str)

    def test_get_data_at_timestamp1(self) -> None:
        """
        - Ask data for 9:35
        - The returned data is for 9:35
        """
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2022-04-22 10:30:00-04:00, 2022-04-22 10:30:00-04:00]
        columns=asset_id,end_download_timestamp,full_symbol,knowledge_timestamp,level_1.ask_price.close,level_1.ask_price.high,level_1.ask_price.low,level_1.ask_price.mean,level_1.ask_price.open,level_1.ask_size.close,level_1.ask_size.max,level_1.ask_size.mean,level_1.ask_size.min,level_1.ask_size.open,level_1.bid_ask_midpoint.close,level_1.bid_ask_midpoint.max,level_1.bid_ask_midpoint.mean,level_1.bid_ask_midpoint.min,level_1.bid_ask_midpoint.open,level_1.bid_ask_midpoint_autocovar.100ms,level_1.bid_ask_midpoint_var.100ms,level_1.bid_price.close,level_1.bid_price.high,level_1.bid_price.low,level_1.bid_price.mean,level_1.bid_price.open,level_1.bid_size.close,level_1.bid_size.max,level_1.bid_size.mean,level_1.bid_size.min,level_1.bid_size.open,level_1.half_spread.close,level_1.half_spread.max,level_1.half_spread.mean,level_1.half_spread.min,level_1.half_spread.open,level_1.log_size_imbalance.close,level_1.log_size_imbalance.max,level_1.log_size_imbalance.mean,level_1.log_size_imbalance.min,level_1.log_size_imbalance.open,level_1.log_size_imbalance_autocovar.100ms,level_1.log_size_imbalance_var.100ms,start_timestamp
        shape=(1, 44)
        asset_id end_download_timestamp full_symbol knowledge_timestamp level_1.ask_price.close level_1.ask_price.high level_1.ask_price.low level_1.ask_price.mean level_1.ask_price.open level_1.ask_size.close level_1.ask_size.max level_1.ask_size.mean level_1.ask_size.min level_1.ask_size.open level_1.bid_ask_midpoint.close level_1.bid_ask_midpoint.max level_1.bid_ask_midpoint.mean level_1.bid_ask_midpoint.min level_1.bid_ask_midpoint.open level_1.bid_ask_midpoint_autocovar.100ms level_1.bid_ask_midpoint_var.100ms level_1.bid_price.close level_1.bid_price.high level_1.bid_price.low level_1.bid_price.mean level_1.bid_price.open level_1.bid_size.close level_1.bid_size.max level_1.bid_size.mean level_1.bid_size.min level_1.bid_size.open level_1.half_spread.close level_1.half_spread.max level_1.half_spread.mean level_1.half_spread.min level_1.half_spread.open level_1.log_size_imbalance.close level_1.log_size_imbalance.max level_1.log_size_imbalance.mean level_1.log_size_imbalance.min level_1.log_size_imbalance.open level_1.log_size_imbalance_autocovar.100ms level_1.log_size_imbalance_var.100ms start_timestamp
        end_timestamp
        2022-04-22 10:30:00-04:00 1464553467 2022-04-22 00:00:00+00:00 binance::ETH_USDT 2022-04-22 00:00:00+00:00 30.0 40.0 50.0 60.0 60.0 60.0 40.0 50.0 30.0 50.0 20.0 40.0 30.0 50.0 5.0 30.0 60.0 50.0 60.0 30.0 40.0 40.0 10.0 20.0 30.0 15.0 5.0 30.0 50.0 40.0 60.0 10.0 40.0 60.0 50.0 30.0 15.0 50.0 40.0 2022-04-22 10:29:00-04:00
        """
        # pylint: enable=line-too-long
        self._test_get_data_at_timestamp1(expected_df_as_str)
