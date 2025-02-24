import logging
import random
from typing import List, Tuple

import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import im_v2.common.data.client as icdc
import im_v2.common.data.client.historical_pq_clients_example as imvcdchpce
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestHistoricalPqByTileClient1
# #############################################################################


class TestHistoricalPqByTileClient1(icdc.ImClientTestCase):
    @pytest.mark.requires_ck_infra
    def test_read_data1(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbol = "binance::BTC_USDT"
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, [full_symbol], resample_1min
        )
        # Compare the expected values.
        expected_length = 4320
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {"full_symbol": ["binance::BTC_USDT"]}
        expected_signature = r"""# df=
        index=[2021-12-30 00:00:00+00:00, 2022-01-01 23:59:00+00:00]
        columns=full_symbol,close
        shape=(4320, 2)
                                   full_symbol  close
        timestamp
        2021-12-30 00:00:00+00:00   binance::BTC_USDT      0
        2021-12-30 00:01:00+00:00   binance::BTC_USDT      1
        2021-12-30 00:02:00+00:00   binance::BTC_USDT      2
        ...
        2022-01-01 23:57:00+00:00   binance::BTC_USDT   4317
        2022-01-01 23:58:00+00:00   binance::BTC_USDT   4318
        2022-01-01 23:59:00+00:00   binance::BTC_USDT   4319"""
        self._test_read_data1(
            im_client,
            full_symbol,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.requires_ck_infra
    def test_read_data2(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Compare the expected values.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        expected_length = 8640
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-12-30 00:00:00+00:00, 2022-01-01 23:59:00+00:00]
        columns=full_symbol,close
        shape=(8640, 2)
                                   full_symbol  close
        timestamp
        2021-12-30 00:00:00+00:00   binance::BTC_USDT      0
        2021-12-30 00:00:00+00:00   kucoin::FIL_USDT      0
        2021-12-30 00:01:00+00:00   binance::BTC_USDT      1
        ...
        2022-01-01 23:58:00+00:00   kucoin::FIL_USDT   4318
        2022-01-01 23:59:00+00:00   binance::BTC_USDT   4319
        2022-01-01 23:59:00+00:00   kucoin::FIL_USDT   4319"""
        self._test_read_data2(
            im_client,
            full_symbols,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.requires_ck_infra
    def test_read_data3(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Compare the expected values.
        expected_length = 2640
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2022-01-01 02:00:00+00:00, 2022-01-01 23:59:00+00:00]
        columns=full_symbol,close
        shape=(2640, 2)
                                   full_symbol  close
        timestamp
        2022-01-01 02:00:00+00:00   binance::BTC_USDT   3000
        2022-01-01 02:00:00+00:00   kucoin::FIL_USDT   3000
        2022-01-01 02:01:00+00:00   binance::BTC_USDT   3001
        ...
        2022-01-01 23:58:00+00:00   kucoin::FIL_USDT   4318
        2022-01-01 23:59:00+00:00   binance::BTC_USDT   4319
        2022-01-01 23:59:00+00:00   kucoin::FIL_USDT   4319"""
        start_timestamp = pd.Timestamp("2022-01-01 02:00:00+00:00")
        self._test_read_data3(
            im_client,
            full_symbols,
            start_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.requires_ck_infra
    def test_read_data4(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Compare the expected values.
        expected_length = 6002
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-12-30 00:00:00+00:00, 2022-01-01 02:00:00+00:00]
        columns=full_symbol,close
        shape=(6002, 2)
                                   full_symbol  close
        timestamp
        2021-12-30 00:00:00+00:00   binance::BTC_USDT      0
        2021-12-30 00:00:00+00:00   kucoin::FIL_USDT      0
        2021-12-30 00:01:00+00:00   binance::BTC_USDT      1
        ...
        2022-01-01 01:59:00+00:00   kucoin::FIL_USDT   2999
        2022-01-01 02:00:00+00:00   binance::BTC_USDT   3000
        2022-01-01 02:00:00+00:00   kucoin::FIL_USDT   3000"""
        end_timestamp = pd.Timestamp("2022-01-01 02:00:00+00:00")
        self._test_read_data4(
            im_client,
            full_symbols,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.requires_ck_infra
    def test_read_data5(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Compare the expected values.
        expected_length = 242
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-12-31 23:00:00+00:00, 2022-01-01 01:00:00+00:00]
        columns=full_symbol,close
        shape=(242, 2)
                                   full_symbol  close
        timestamp
        2021-12-31 23:00:00+00:00   binance::BTC_USDT   2820
        2021-12-31 23:00:00+00:00   kucoin::FIL_USDT   2820
        2021-12-31 23:01:00+00:00   binance::BTC_USDT   2821
        ...
        2022-01-01 00:59:00+00:00   kucoin::FIL_USDT   2939
        2022-01-01 01:00:00+00:00   binance::BTC_USDT   2940
        2022-01-01 01:00:00+00:00   kucoin::FIL_USDT   2940"""
        start_timestamp = pd.Timestamp("2021-12-31 23:00:00+00:00")
        end_timestamp = pd.Timestamp("2022-01-01 01:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.skip("CMTask1510: Faulty symbol not detected.")
    def test_read_data6(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT, kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Run test.
        full_symbol = "kucoin::MOCK"
        self._test_read_data6(im_client, full_symbol)

    @pytest.mark.requires_ck_infra
    def test_read_data7(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = False
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Compare the expected values.
        expected_length = 8640
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-12-30 00:00:00+00:00, 2022-01-01 23:59:00+00:00]
        columns=full_symbol,close
        shape=(8640, 2)
                                   full_symbol  close
        timestamp
        2021-12-30 00:00:00+00:00   binance::BTC_USDT      0
        2021-12-30 00:00:00+00:00   kucoin::FIL_USDT      0
        2021-12-30 00:01:00+00:00   binance::BTC_USDT      1
        ...
        2022-01-01 23:58:00+00:00   kucoin::FIL_USDT   4318
        2022-01-01 23:59:00+00:00   binance::BTC_USDT   4319
        2022-01-01 23:59:00+00:00   kucoin::FIL_USDT   4319"""
        self._test_read_data7(
            im_client,
            full_symbols,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    # TODO(Dan): Update test data generator with adding one more column to it.
    @pytest.mark.requires_ck_infra
    def test_filter_columns1(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        expected_columns = ["full_symbol", "close"]
        self._test_filter_columns1(im_client, full_symbols, expected_columns)

    @pytest.mark.requires_ck_infra
    def test_filter_columns2(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, full_symbols, resample_1min
        )
        # Run test.
        full_symbol = "binance::BTC_USDT"
        expected_columns = ["full_symbol", "whatever"]
        self._test_filter_columns2(im_client, full_symbol, expected_columns)

    @pytest.mark.skip(reason="Enable after Lime477")
    def test_filter_columns3(self) -> None:
        full_symbol = "binance::BTC_USDT"
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, [full_symbol], resample_1min
        )
        expected_columns = ["close"]
        self._test_filter_columns3(im_client, full_symbol, expected_columns)

    @pytest.mark.skip(reason="Enable after Lime477")
    def test_filter_columns4(self) -> None:
        full_symbol = "binance::BTC_USDT"
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, [full_symbol], resample_1min
        )
        expected_columns = ["close"]
        self._test_filter_columns4(im_client, full_symbol, expected_columns)

    # ////////////////////////////////////////////////////////////////////////

    @pytest.mark.requires_ck_infra
    def test_get_start_ts_for_symbol1(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbol = "binance::BTC_USDT"
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, [full_symbol], resample_1min
        )
        # Compare the expected values.
        expected_start_timestamp = pd.Timestamp("2021-12-30 00:00:00+00:00")
        self._test_get_start_ts_for_symbol1(
            im_client, full_symbol, expected_start_timestamp
        )

    @pytest.mark.requires_ck_infra
    def test_get_end_ts_for_symbol1(self) -> None:
        # Generate Parquet test data and initialize client.
        full_symbol = "binance::BTC_USDT"
        resample_1min = True
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example1(
            self, [full_symbol], resample_1min
        )
        # Compare the expected values.
        expected_end_timestamp = pd.Timestamp("2022-01-01 23:59:00+00:00")
        self._test_get_end_ts_for_symbol1(
            im_client, full_symbol, expected_end_timestamp
        )

    # ////////////////////////////////////////////////////////////////////////

    def test_get_universe1(self) -> None:
        # Init client for testing.
        resample_1min = True
        vendor = "mock"
        universe_version = "small"
        test_dir = "dummy"
        partition_mode = "by_year_month"
        infer_exachange_id = False
        im_client = imvcdchpce.MockHistoricalByTileClient(
            vendor,
            universe_version,
            test_dir,
            partition_mode,
            infer_exachange_id,
            resample_1min=resample_1min,
        )
        # Compare the expected values.
        expected_length = 2
        expected_first_elements = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        expected_last_elements = expected_first_elements
        self._test_get_universe1(
            im_client,
            expected_length,
            expected_first_elements,
            expected_last_elements,
        )


# #############################################################################
# TestHistoricalPqByTileClient2
# #############################################################################


@pytest.mark.slow
class TestHistoricalPqByTileClient2(icdc.ImClientTestCase):
    """
    Test that Parquet intervals are correctly filtered (corner cases).
    """

    def test_only_start_date1(self) -> None:
        """
        Interval has only start timestamp.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 2976
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-11-01 00:00:00+00:00, 2022-01-01 23:00:00+00:00]
        columns=full_symbol,close
        shape=(2976, 2)
                                         full_symbol   close
        timestamp
        2021-11-01 00:00:00+00:00  binance::BTC_USDT  16080
        2021-11-01 00:00:00+00:00   kucoin::FIL_USDT  16080
        2021-11-01 01:00:00+00:00  binance::BTC_USDT  16081
        ...
        2022-01-01 22:00:00+00:00   kucoin::FIL_USDT  17566
        2022-01-01 23:00:00+00:00  binance::BTC_USDT  17567
        2022-01-01 23:00:00+00:00   kucoin::FIL_USDT  17567"""
        start_timestamp = pd.Timestamp("2021-11-01 00:00:00+00:00")
        self._test_read_data3(
            im_client,
            full_symbols,
            start_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("6 seconds.")
    def test_only_end_date1(self) -> None:
        """
        Interval has only end timestamp.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 17570
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2020-01-01 00:00:00+00:00, 2021-01-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(17570, 2)
                                         full_symbol  close
        timestamp
        2020-01-01 00:00:00+00:00  binance::BTC_USDT      0
        2020-01-01 00:00:00+00:00   kucoin::FIL_USDT      0
        2020-01-01 01:00:00+00:00  binance::BTC_USDT      1
        ...
        2020-12-31 23:00:00+00:00   kucoin::FIL_USDT  8783
        2021-01-01 00:00:00+00:00  binance::BTC_USDT  8784
        2021-01-01 00:00:00+00:00   kucoin::FIL_USDT  8784"""
        end_timestamp = pd.Timestamp("2021-01-01 00:00:00+00:00")
        self._test_read_data4(
            im_client,
            full_symbols,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_one_month1(self) -> None:
        """
        Interval of 1 month length capturing data for 1 month strictly.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 1488
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-08-01 00:00:00+00:00, 2021-08-31 23:00:00+00:00]
        columns=full_symbol,close
        shape=(1488, 2)
                                         full_symbol   close
        timestamp
        2021-08-01 00:00:00+00:00  binance::BTC_USDT  13872
        2021-08-01 00:00:00+00:00   kucoin::FIL_USDT  13872
        2021-08-01 01:00:00+00:00  binance::BTC_USDT  13873
        ...
        2021-08-31 22:00:00+00:00   kucoin::FIL_USDT  14614
        2021-08-31 23:00:00+00:00  binance::BTC_USDT  14615
        2021-08-31 23:00:00+00:00   kucoin::FIL_USDT  14615"""
        start_timestamp = pd.Timestamp("2021-08-01 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2021-08-31 23:59:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_one_month2(self) -> None:
        """
        Interval of 1 month length capturing data for 2 month.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 1490
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2020-12-15 00:00:00+00:00, 2021-01-15 00:00:00+00:00]
        columns=full_symbol,close
        shape=(1490, 2)
                                         full_symbol   close
        timestamp
        2020-12-15 00:00:00+00:00  binance::BTC_USDT  8376
        2020-12-15 00:00:00+00:00   kucoin::FIL_USDT  8376
        2020-12-15 01:00:00+00:00  binance::BTC_USDT  8377
        ...
        2021-01-14 23:00:00+00:00   kucoin::FIL_USDT  9119
        2021-01-15 00:00:00+00:00  binance::BTC_USDT  9120
        2021-01-15 00:00:00+00:00   kucoin::FIL_USDT  9120"""
        start_timestamp = pd.Timestamp("2020-12-15 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2021-01-15 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_multiple_months1(self) -> None:
        """
        Interval of multiple month length capturing data for 1 year.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 4418
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-08-01 00:00:00+00:00, 2021-11-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(4418, 2)
                                         full_symbol   close
        timestamp
        2021-08-01 00:00:00+00:00  binance::BTC_USDT  13872
        2021-08-01 00:00:00+00:00   kucoin::FIL_USDT  13872
        2021-08-01 01:00:00+00:00  binance::BTC_USDT  13873
        ...
        2021-10-31 23:00:00+00:00   kucoin::FIL_USDT  16079
        2021-11-01 00:00:00+00:00  binance::BTC_USDT  16080
        2021-11-01 00:00:00+00:00   kucoin::FIL_USDT  16080"""
        start_timestamp = pd.Timestamp("2021-08-01 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2021-11-01 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("6 seconds.")
    def test_multiple_months2(self) -> None:
        """
        Interval of multiple month length capturing data for 2 years.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 7250
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2020-10-01 00:00:00+00:00, 2021-03-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(7250, 2)
                                         full_symbol   close
        timestamp
        2020-10-01 00:00:00+00:00  binance::BTC_USDT  6576
        2020-10-01 00:00:00+00:00   kucoin::FIL_USDT  6576
        2020-10-01 01:00:00+00:00  binance::BTC_USDT  6577
        ...
        2021-02-28 23:00:00+00:00   kucoin::FIL_USDT  10199
        2021-03-01 00:00:00+00:00  binance::BTC_USDT  10200
        2021-03-01 00:00:00+00:00   kucoin::FIL_USDT  10200"""
        start_timestamp = pd.Timestamp("2020-10-01 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2021-03-01 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("6 seconds.")
    def test_multiple_months3(self) -> None:
        """
        Interval of multiple month length capturing data for more than 2 years.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 19010
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2020-12-01 00:00:00+00:00, 2022-01-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(19010, 2)
                                         full_symbol   close
        timestamp
        2020-12-01 00:00:00+00:00  binance::BTC_USDT  8040
        2020-12-01 00:00:00+00:00   kucoin::FIL_USDT  8040
        2020-12-01 01:00:00+00:00  binance::BTC_USDT  8041
        ...
        2021-12-31 23:00:00+00:00   kucoin::FIL_USDT  17543
        2022-01-01 00:00:00+00:00  binance::BTC_USDT  17544
        2022-01-01 00:00:00+00:00   kucoin::FIL_USDT  17544"""
        start_timestamp = pd.Timestamp("2020-12-01 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2022-01-01 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_new_year1(self) -> None:
        """
        Interval of the last minute of a year and the first of the next one.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 2
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2022-01-01 00:00:00+00:00, 2022-01-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(2, 2)
                                         full_symbol    close
        timestamp
        2022-01-01 00:00:00+00:00  binance::BTC_USDT  17544
        2022-01-01 00:00:00+00:00   kucoin::FIL_USDT  17544"""
        start_timestamp = pd.Timestamp("2021-12-31 23:59:00+00:00")
        end_timestamp = pd.Timestamp("2022-01-01 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_equal_dates1(self) -> None:
        """
        Interval with equal timestamp boundaries.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example2(
            self, full_symbols
        )
        # Compare the expected values.
        expected_length = 2
        expected_column_names = ["close", "full_symbol"]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        }
        expected_signature = r"""# df=
        index=[2021-08-01 00:00:00+00:00, 2021-08-01 00:00:00+00:00]
        columns=full_symbol,close
        shape=(2, 2)
                                         full_symbol   close
        timestamp
        2021-08-01 00:00:00+00:00  binance::BTC_USDT  13872
        2021-08-01 00:00:00+00:00   kucoin::FIL_USDT  13872"""
        start_timestamp = pd.Timestamp("2021-08-01 00:00:00+00:00")
        end_timestamp = pd.Timestamp("2021-08-01 00:00:00+00:00")
        self._test_read_data5(
            im_client,
            full_symbols,
            start_timestamp,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )


# #############################################################################
# TestHistoricalPqByTileClient3
# #############################################################################


class TestHistoricalPqByTileClient3(icdc.ImClientTestCase):
    """
    Test that randomly generated Parquet intervals are correctly filtered.
    """

    @staticmethod
    def generate_random_time_interval(
        left_boundary: pd.Timestamp, right_boundary: pd.Timestamp, seed_: int
    ) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """
        Generate a timestamp interval between specified timestamp boundaries.

        Timestamps are generated in "[`left_boundary`: `right_boundary`)" interval.

        :param left_boundary: left boundary for generated timestamp interval
        :param right_boundary: right boundary for generated timestamp interval
        :param seed_: seed value
        :return: two consequtive timestamps that belong to the specified interval
        """
        # TODO(gp): Consider using random intervals based on system clock and
        #  print the `seed_` for reproducibility.
        # Set seed value and log it so that we can reproduce errors.
        _LOG.info("Seed value ='%s'", seed_)
        random.seed(seed_)
        # Convert boundaries to epochs.
        left_boundary_epoch = hdateti.convert_timestamp_to_unix_epoch(
            left_boundary, unit="h"
        )
        right_boundary_epoch = hdateti.convert_timestamp_to_unix_epoch(
            right_boundary, unit="h"
        )
        # Generate 2 random consequtive epochs in specified boundaries.
        # TODO(Dan): Consider using a simpler solution.
        #  https://stackoverflow.com/questions/50165501/generate-random-list-of-timestamps-in-python.
        # Integers are subtracted from right boundary since test data is
        # generated with open right boundary while `randint` works and
        # client reads data with closed right boundary.
        start_ts_epoch = random.randint(
            left_boundary_epoch, right_boundary_epoch - 2
        )
        end_ts_epoch = random.randint(start_ts_epoch, right_boundary_epoch - 1)
        # Convert generated epochs to timestamps.
        start_ts = hdateti.convert_unix_epoch_to_timestamp(
            start_ts_epoch, unit="h"
        )
        end_ts = hdateti.convert_unix_epoch_to_timestamp(end_ts_epoch, unit="h")
        return start_ts, end_ts

    @pytest.mark.superslow("~36 seconds.")
    def test_read_data_random1(self) -> None:
        """
        Timestamp intervals are randomly generated and tested N times.
        """
        # Generate Parquet test data and initialize client.
        full_symbols = ["binance::BTC_USDT", "kucoin::FIL_USDT"]
        start_date = "2018-12-30"
        end_date = "2022-01-02"
        resample_1min = False
        im_client = imvcdchpce.get_MockHistoricalByTileClient_example3(
            self, full_symbols, start_date, end_date, resample_1min
        )
        # Run tests.
        for seed_ in range(100):
            # Generate random timestamp interval and read data.
            left_boundary = pd.Timestamp(start_date)
            right_boundary = pd.Timestamp(end_date)
            start_ts, end_ts = self.generate_random_time_interval(
                left_boundary, right_boundary, seed_
            )
            columns = None
            filter_data_mode = "assert"
            data = im_client.read_data(
                full_symbols, start_ts, end_ts, columns, filter_data_mode
            )
            # Compare the expected values.
            self._check_output(data, full_symbols, start_ts, end_ts)

    def _check_output(
        self,
        actual_df: pd.DataFrame,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> None:
        """
        Check output for correctness.
        """
        expected_length = int(
            ((end_ts - start_ts).total_seconds() / (60 * 60) + 1)
            * len(full_symbols)
        )
        self.assert_equal(str(actual_df.shape[0]), str(expected_length))
        self.assert_equal(str(actual_df.index[0]), str(start_ts))
        self.assert_equal(str(actual_df.index[-1]), str(end_ts))
