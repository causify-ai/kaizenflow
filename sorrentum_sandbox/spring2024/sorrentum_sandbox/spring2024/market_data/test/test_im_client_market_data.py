import os
from typing import List

import pandas as pd
import pytest

import core.finance as cofinanc
import helpers.henv as henv
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu
import market_data as mdata

# #############################################################################
# TestImClientMarketData1
# #############################################################################


# TODO(Grisha): @Dan, can we use CcxtHistoricalPqByTileClient?
class TestImClientMarketData1(mdata.MarketData_get_data_TestCase):
    """
    For all the test methods see description of corresponding private method in
    the parent class.
    """

    @staticmethod
    def get_expected_column_names() -> List[str]:
        """
        Return a list of expected column names.
        """
        expected_column_names = [
            "asset_id",
            "full_symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "start_ts",
        ]
        return expected_column_names

    # //////////////////////////////////////////////////////////////////////////////

    def test_is_online1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        # Run.
        actual = market_data.is_online()
        self.assertTrue(actual)

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_data_for_last_period1(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("1D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period2(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("2D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period3(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("1W")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period4(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("10T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period5(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("5T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period6(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("1T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period7(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("365D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_at_timestamp1(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 2
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:05:00-04:00, 2018-08-16 20:05:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(2, 8)
                                     asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:05:00-04:00  1467591036  binance::BTC_USDT  6291.970000  6299.320000  6285.400000  6294.990000  18.986206 2018-08-16 20:04:00-04:00
        2018-08-16 20:05:00-04:00  3187272957   kucoin::ETH_USDT   285.400196   285.884637   285.400196   285.884637   0.006141 2018-08-16 20:04:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_at_timestamp1(
            market_data,
            ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_at_timestamp2(self) -> None:
        """
        Test that an empty dataframe is returned when timestamp is not aligned
        to 1-minute frequency, e.g., "2018-08-17T00:05:10+00:00".
        """
        # Prepare inputs.
        resample_1min = True
        im_client = icdcl.get_CcxtParquetByAssetClient_example1(resample_1min)
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        ts = pd.Timestamp("2018-08-17T00:05:10+00:00")
        # Check.
        with self.assertRaises(AssertionError) as e:
            ts_col_name = "end_ts"
            _ = market_data.get_data_at_timestamp(ts, ts_col_name, asset_ids)
        exp = """
        ################################################################################
        * Failed assertion *
        0 < 0
        Empty df=
        Empty DataFrame
        Columns: [full_symbol, open, high, low, close, volume]
        Index: []
        ################################################################################
        """
        self.assert_equal(str(e.exception), exp, fuzzy_match=True)

    @pytest.mark.skip(
        reason="CmTask #1633 Add unit test for universe in MarketData."
    )
    def test_get_data_for_interval1(self) -> None:
        # Prepare inputs.
        asset_ids = None
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 8
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = """
        # df=
        index=[2018-08-16 20:01:00-04:00, 2018-08-16 20:04:00-04:00]
        columns=asset_id,open,high,low,close,volume,currency_pair,exchange_id,start_ts
        shape=(8, 9)
                                            asset_id         open         high          low        close     volume currency_pair exchange_id                  start_ts
        end_ts
        2018-08-16 20:01:00-04:00  binance::BTC_USDT  6311.640000  6311.770000  6302.810000  6302.810000  16.781206      BTC_USDT     binance 2018-08-16 20:00:00-04:00
        2018-08-16 20:01:00-04:00   kucoin::ETH_USDT   286.712987   286.712987   286.712987   286.712987   0.017500      ETH_USDT      kucoin 2018-08-16 20:00:00-04:00
        2018-08-16 20:02:00-04:00  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226      BTC_USDT     binance 2018-08-16 20:01:00-04:00
        ...
        2018-08-16 20:03:00-04:00   kucoin::ETH_USDT   285.400193   285.400193   285.400193   285.400193   0.020260      ETH_USDT      kucoin 2018-08-16 20:02:00-04:00
        2018-08-16 20:04:00-04:00  binance::BTC_USDT  6294.520000  6299.980000  6290.000000  6296.100000  22.088586      BTC_USDT     binance 2018-08-16 20:03:00-04:00
        2018-08-16 20:04:00-04:00   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655      ETH_USDT      kucoin 2018-08-16 20:03:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval1(
            market_data,
            start_ts,
            end_ts,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval2(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 8
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:01:00-04:00, 2018-08-16 20:04:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(8, 8)
                                     asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:01:00-04:00  1467591036  binance::BTC_USDT  6311.640000  6311.770000  6302.810000  6302.810000  16.781206 2018-08-16 20:00:00-04:00
        2018-08-16 20:01:00-04:00  3187272957   kucoin::ETH_USDT   286.712987   286.712987   286.712987   286.712987   0.017500 2018-08-16 20:00:00-04:00
        2018-08-16 20:02:00-04:00  1467591036  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226 2018-08-16 20:01:00-04:00
        ...
        2018-08-16 20:03:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.400193   285.400193   285.400193   0.020260 2018-08-16 20:02:00-04:00
        2018-08-16 20:04:00-04:00  1467591036  binance::BTC_USDT  6294.520000  6299.980000  6290.000000  6296.100000  22.088586 2018-08-16 20:03:00-04:00
        2018-08-16 20:04:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655 2018-08-16 20:03:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval2(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval3(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 10
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:01:00-04:00, 2018-08-16 20:05:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(10, 8)
                                     asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:01:00-04:00  1467591036  binance::BTC_USDT  6311.640000  6311.770000  6302.810000  6302.810000  16.781206 2018-08-16 20:00:00-04:00
        2018-08-16 20:01:00-04:00  3187272957   kucoin::ETH_USDT   286.712987   286.712987   286.712987   286.712987   0.017500 2018-08-16 20:00:00-04:00
        2018-08-16 20:02:00-04:00  1467591036  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226 2018-08-16 20:01:00-04:00
        ...
        2018-08-16 20:04:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655 2018-08-16 20:03:00-04:00
        2018-08-16 20:05:00-04:00  1467591036  binance::BTC_USDT  6291.970000  6299.320000  6285.400000  6294.990000  18.986206 2018-08-16 20:04:00-04:00
        2018-08-16 20:05:00-04:00  3187272957   kucoin::ETH_USDT   285.400196   285.884637   285.400196   285.884637   0.006141 2018-08-16 20:04:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval3(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval4(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 8
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:02:00-04:00, 2018-08-16 20:05:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(8, 8)
                                     asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:02:00-04:00  1467591036  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226 2018-08-16 20:01:00-04:00
        2018-08-16 20:02:00-04:00  3187272957   kucoin::ETH_USDT   286.405988   286.405988   285.400193   285.400197   0.162255 2018-08-16 20:01:00-04:00
        2018-08-16 20:03:00-04:00  1467591036  binance::BTC_USDT  6299.970000  6299.970000  6286.930000  6294.520000  34.611797 2018-08-16 20:02:00-04:00
        ...
        2018-08-16 20:04:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655 2018-08-16 20:03:00-04:00
        2018-08-16 20:05:00-04:00  1467591036  binance::BTC_USDT  6291.970000  6299.320000  6285.400000  6294.990000  18.986206 2018-08-16 20:04:00-04:00
        2018-08-16 20:05:00-04:00  3187272957   kucoin::ETH_USDT   285.400196   285.884637   285.400196   285.884637   0.006141 2018-08-16 20:04:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval4(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval5(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 6
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:02:00-04:00, 2018-08-16 20:04:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(6, 8)
                                     asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:02:00-04:00  1467591036  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226 2018-08-16 20:01:00-04:00
        2018-08-16 20:02:00-04:00  3187272957   kucoin::ETH_USDT   286.405988   286.405988   285.400193   285.400197   0.162255 2018-08-16 20:01:00-04:00
        2018-08-16 20:03:00-04:00  1467591036  binance::BTC_USDT  6299.970000  6299.970000  6286.930000  6294.520000  34.611797 2018-08-16 20:02:00-04:00
        2018-08-16 20:03:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.400193   285.400193   285.400193   0.020260 2018-08-16 20:02:00-04:00
        2018-08-16 20:04:00-04:00  1467591036  binance::BTC_USDT  6294.520000  6299.980000  6290.000000  6296.100000  22.088586 2018-08-16 20:03:00-04:00
        2018-08-16 20:04:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655 2018-08-16 20:03:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval5(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_twap_price1(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 2
        expected_column_names = None
        expected_column_unique_values = None
        exp_df_as_str = r"""
        # df=
        index=[2018-08-17 00:05:00+00:00, 2018-08-17 00:05:00+00:00]
        columns=asset_id,start_ts,close
        shape=(2, 3)
                                     asset_id                  start_ts    close
        end_ts
        2018-08-17 00:05:00+00:00  1467591036 2018-08-17 00:01:00+00:00  6295.72
        2018-08-17 00:05:00+00:00  3187272957 2018-08-17 00:01:00+00:00   285.64
        """
        # Run.
        self._test_get_twap_price1(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
            expected_signature=exp_df_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_last_end_time1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        exp_last_end_time = pd.Timestamp("2018-08-17T01:39:00+00:00")
        # Run.
        self._test_get_last_end_time1(market_data, exp_last_end_time)

    def test_get_last_price1(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        #
        expected_length = 2
        expected_unique_values = None
        expected_column_names = [
            "asset_id",
            "close",
        ]
        exp_as_str = r"""
        # df=
        index=[2018-08-16 21:39:00-04:00, 2018-08-16 21:39:00-04:00]
        columns=close,asset_id
        shape=(2, 2)
                                        close    asset_id
        end_ts
        2018-08-16 21:39:00-04:00      6342.95  1467591036
        2018-08-16 21:39:00-04:00       292.16  3187272957
        """
        # Run.
        self._test_get_last_price1(
            market_data,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_unique_values,
            exp_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_should_be_online1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        resample_1min = True
        im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        wall_clock_time = pd.Timestamp("2018-08-17T00:01:00")
        # Run.
        self._test_should_be_online1(market_data, wall_clock_time)


# #############################################################################
# TestImClientMarketData2
# #############################################################################


class TestImClientMarketData2(mdata.MarketData_get_data_TestCase):
    """
    For all the test methods see description of corresponding private method in
    the parent class.
    """

    @staticmethod
    def get_ImClient() -> icdc.DataFrameImClient:
        vendor = "mock1"
        mode = "trade"
        universe = ivcu.get_vendor_universe(
            vendor, mode, version="v1", as_full_symbol=True
        )
        df = cofinanc.get_MarketData_df6(universe)
        im_client = icdc.get_DataFrameImClient_example1(df)
        return im_client

    @staticmethod
    def get_expected_column_names() -> List[str]:
        """
        Return a list of expected column names.
        """
        expected_column_names = [
            "asset_id",
            "full_symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "feature1",
            "start_ts",
        ]
        return expected_column_names

    # //////////////////////////////////////////////////////////////////////////////

    def test_is_online1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns=columns, column_remap=column_remap
        )
        # Run.
        actual = market_data.is_online()
        self.assertTrue(actual)

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_data_for_last_period1(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
        )
        timedelta = pd.Timedelta("1D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period2(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("2D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period3(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("1W")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period4(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("10T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period5(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("5T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period6(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("1T")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_for_last_period7(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        timedelta = pd.Timedelta("365D")
        # Run.
        self._test_get_data_for_last_period(market_data, timedelta)

    def test_get_data_at_timestamp1(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        #
        expected_length = 2
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:35:00-05:00, 2000-01-01 09:35:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(2, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:35:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_at_timestamp1(
            market_data,
            ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    @pytest.mark.skip(
        reason="CmTask #1633 Add unit test for universe in MarketData."
    )
    def test_get_data_for_interval1(self) -> None:
        # Prepare inputs.
        asset_ids = None
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 14
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:35:00-05:00, 2000-01-01 09:41:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(14, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:35:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:36:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        ...
        2000-01-01 09:40:00-05:00  3303714233  binance::ADA_USDT   100   101   99  100.0       9      -1.0 2000-01-01 09:39:00-05:00
        2000-01-01 09:41:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        2000-01-01 09:41:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval1(
            market_data,
            start_ts,
            end_ts,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval2(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 14
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:35:00-05:00, 2000-01-01 09:41:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(14, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:35:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:36:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        ...
        2000-01-01 09:40:00-05:00  3303714233  binance::ADA_USDT   100   101   99  100.0       9      -1.0 2000-01-01 09:39:00-05:00
        2000-01-01 09:41:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        2000-01-01 09:41:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval2(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval3(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 16
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:35:00-05:00, 2000-01-01 09:42:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(16, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:35:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0       4       1.0 2000-01-01 09:34:00-05:00
        2000-01-01 09:36:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        ...
        2000-01-01 09:41:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        2000-01-01 09:42:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0      11       1.0 2000-01-01 09:41:00-05:00
        2000-01-01 09:42:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      11       1.0 2000-01-01 09:41:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval3(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval4(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 14
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:36:00-05:00, 2000-01-01 09:42:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(14, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:36:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        2000-01-01 09:36:00-05:00  3303714233  binance::ADA_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        2000-01-01 09:37:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       6      -1.0 2000-01-01 09:36:00-05:00
        ...
        2000-01-01 09:41:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        2000-01-01 09:42:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0      11       1.0 2000-01-01 09:41:00-05:00
        2000-01-01 09:42:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      11       1.0 2000-01-01 09:41:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval4(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_get_data_for_interval5(self) -> None:
        # Prepare inputs.
        asset_ids = [3303714233, 1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 12
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:36:00-05:00, 2000-01-01 09:41:00-05:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,feature1,start_ts
        shape=(12, 9)
                                     asset_id        full_symbol  open  high  low  close  volume  feature1                  start_ts
        end_ts
        2000-01-01 09:36:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        2000-01-01 09:36:00-05:00  3303714233  binance::ADA_USDT   100   101   99  100.0       5      -1.0 2000-01-01 09:35:00-05:00
        2000-01-01 09:37:00-05:00  1467591036  binance::BTC_USDT   100   101   99  100.0       6      -1.0 2000-01-01 09:36:00-05:00
        ...
        2000-01-01 09:40:00-05:00  3303714233  binance::ADA_USDT   100   101   99  100.0       9      -1.0 2000-01-01 09:39:00-05:00
        2000-01-01 09:41:00-05:00  1467591036  binance::BTC_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        2000-01-01 09:41:00-05:00  3303714233  binance::ADA_USDT   100   101   99  101.0      10       1.0 2000-01-01 09:40:00-05:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval5(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_twap_price1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036, 3303714233]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        start_ts = pd.Timestamp("2000-01-01T09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01T09:42:00-05:00")
        #
        expected_length = 2
        expected_column_names = None
        expected_column_unique_values = None
        exp_df_as_str = r"""
        # df=
        index=[2000-01-01 09:42:00-05:00, 2000-01-01 09:42:00-05:00]
        columns=asset_id,start_ts,close
        shape=(2, 3)
                                     asset_id                  start_ts   close
        end_ts
        2000-01-01 09:42:00-05:00  1467591036 2000-01-01 09:35:00-05:00  100.29
        2000-01-01 09:42:00-05:00  3303714233 2000-01-01 09:35:00-05:00  100.29
        """
        # Run.
        self._test_get_twap_price1(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
            expected_signature=exp_df_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_last_end_time1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        exp_last_end_time = pd.Timestamp("2000-01-01T12:10:00-05:00")
        # Run.
        self._test_get_last_end_time1(market_data, exp_last_end_time)

    def test_get_last_price1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036, 3303714233]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        #
        expected_length = 2
        expected_unique_values = None
        expected_column_names = [
            "asset_id",
            "close",
        ]
        exp_as_str = r"""
        # df=
        index=[2000-01-01 12:10:00-05:00, 2000-01-01 12:10:00-05:00]
        columns=close,asset_id
        shape=(2, 2)
                                close    asset_id
        end_ts
        2000-01-01 12:10:00-05:00  100.0  1467591036
        2000-01-01 12:10:00-05:00  100.0  3303714233
        """
        # Run.
        self._test_get_last_price1(
            market_data,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_unique_values,
            exp_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_should_be_online1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        im_client = self.get_ImClient()
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client, asset_ids, columns, column_remap
        )
        wall_clock_time = pd.Timestamp("2000-01-01T09:42:00-05:00")
        # Run.
        self._test_should_be_online1(market_data, wall_clock_time)


# #############################################################################
# TestImClientMarketData3
# #############################################################################


# TODO(Dan): Replace `TestImClientMarketData1` on this one when extended.
# TODO(Dan): use local data instead of S3.
@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
@pytest.mark.slow("~8 seconds by GH actions.")
class TestImClientMarketData3(mdata.MarketData_get_data_TestCase):
    """
    For all the test methods see description of corresponding private method in
    the parent class.
    """

    @staticmethod
    def get_expected_column_names() -> List[str]:
        """
        Return a list of expected column names.
        """
        expected_column_names = [
            "asset_id",
            "full_symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "start_ts",
        ]
        return expected_column_names

    def get_im_client(
        self, resample_1min: bool
    ) -> icdcl.CcxtHistoricalPqByTileClient:
        """
        Get `CcxtHistoricalPqByTileClient` based on data from S3.

        :param resample_1min: whether to resample data to 1 minute or
            not
        :return: Ccxt historical client
        """
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        root_dir = os.path.join(s3_input_dir, "historical.manual.pq")
        dataset = "ohlcv"
        contract_type = "spot"
        data_snapshot = "20220705"
        download_universe_version = "v7_3"
        im_client = icdcl.get_CcxtHistoricalPqByTileClient_example2(
            root_dir,
            resample_1min,
            dataset,
            contract_type,
            data_snapshot,
            download_universe_version,
        )
        return im_client

    # //////////////////////////////////////////////////////////////////////////////

    def test_is_online1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = None
        column_remap = None
        filter_data_mode = "assert"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        # Run.
        actual = market_data.is_online()
        self.assertTrue(actual)

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_data_for_interval5(self) -> None:
        # Prepare inputs.
        asset_ids = [3187272957, 1467591036]
        columns = None
        column_remap = None
        filter_data_mode = "assert"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_length = 6
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2018-08-16 20:02:00-04:00, 2018-08-16 20:04:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,start_ts
        shape=(6, 8)
                                    asset_id        full_symbol         open         high          low        close     volume                  start_ts
        end_ts
        2018-08-16 20:02:00-04:00  1467591036  binance::BTC_USDT  6311.640000  6311.770000  6302.810000  6302.810000  16.781206 2018-08-16 20:01:00-04:00
        2018-08-16 20:02:00-04:00  3187272957   kucoin::ETH_USDT   286.405988   286.405988   285.400193   285.400197   0.162255 2018-08-16 20:01:00-04:00
        2018-08-16 20:03:00-04:00  1467591036  binance::BTC_USDT  6302.810000  6306.000000  6292.790000  6297.260000  55.373226 2018-08-16 20:02:00-04:00
        2018-08-16 20:03:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.400193   285.400193   285.400193   0.020260 2018-08-16 20:02:00-04:00
        2018-08-16 20:04:00-04:00  1467591036  binance::BTC_USDT  6299.970000  6299.970000  6286.930000  6294.520000  34.611797 2018-08-16 20:03:00-04:00
        2018-08-16 20:04:00-04:00  3187272957   kucoin::ETH_USDT   285.400193   285.884638   285.400193   285.884638   0.074655 2018-08-16 20:03:00-04:00
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval5(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_filter_columns1(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = ["asset_id", "full_symbol", "close", "start_ts"]
        column_remap = None
        filter_data_mode = "assert"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_column_names = ["asset_id", "full_symbol", "close", "start_ts"]
        # Run.
        self._test_filter_columns1(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_column_names,
        )

    def test_filter_columns1_2(self) -> None:
        """
        Test that columns are filtered correctly when full symbol column is not
        requested.
        """
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = ["asset_id", "close", "start_ts"]
        column_remap = None
        filter_data_mode = "assert"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_column_names = ["asset_id", "close", "start_ts"]
        # Run.
        self._test_filter_columns1(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_column_names,
        )

    def test_filter_columns2(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = ["full_symbol", "close"]
        column_remap = None
        filter_data_mode = "assert"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        # Run.
        self._test_filter_columns2(market_data, asset_ids)

    def test_filter_columns3(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036]
        columns = ["full_symbol", "close"]
        column_remap = None
        filter_data_mode = "warn_and_trim"
        resample_1min = False
        im_client = self.get_im_client(resample_1min)
        market_data = mdata.get_HistoricalImClientMarketData_example1(
            im_client,
            asset_ids,
            columns,
            column_remap,
            filter_data_mode=filter_data_mode,
        )
        start_ts = pd.Timestamp("2018-08-17T00:01:00+00:00")
        end_ts = pd.Timestamp("2018-08-17T00:05:00+00:00")
        #
        expected_column_names = ["full_symbol", "close"]
        # Run.
        self._test_filter_columns3(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_column_names,
        )
