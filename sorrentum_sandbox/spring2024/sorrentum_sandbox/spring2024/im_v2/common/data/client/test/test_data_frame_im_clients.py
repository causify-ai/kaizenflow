from typing import List

import pandas as pd

import core.finance as cofinanc
import im_v2.common.data.client.data_frame_im_clients as imvcdcdfimc
import im_v2.common.data.client.data_frame_im_clients_example as imvcdcdfimce
import im_v2.common.data.client.im_client_test_case as imvcdcimctc
import im_v2.common.universe as ivcu

# #############################################################################
# TestDataFrameImClient1
# #############################################################################


class TestDataFrameImClient1(imvcdcimctc.ImClientTestCase):
    @staticmethod
    def get_expected_column_names() -> List[str]:
        """
        Return a list of expected column names.
        """
        expected_column_names = [
            "full_symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "feature1",
        ]
        return expected_column_names

    @staticmethod
    def get_universe() -> List[str]:
        vendor = "mock1"
        mode = "trade"
        universe = ivcu.get_vendor_universe(
            vendor, mode, version="v1", as_full_symbol=True
        )
        return universe

    def get_ImClient(self) -> imvcdcdfimc.DataFrameImClient:
        universe = self.get_universe()
        df = cofinanc.get_MarketData_df6(universe)
        im_client = imvcdcdfimce.get_DataFrameImClient_example1(df)
        return im_client

    def get_duplicated_data(self) -> pd.DataFrame:
        """
        Return a duplicated data for the test.
        """
        universe = self.get_universe()
        df1 = cofinanc.get_MarketData_df6(universe)
        df2 = pd.DataFrame(df1[:20])
        df_dups = pd.concat([df1, df2])
        df_dups["knowledge_timestamp"] = pd.date_range(
            start="2000-02-01 12:15:00+00:00", periods=340, freq="T"
        )
        return df_dups

    def test_read_data1(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 160
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {"full_symbol": ["binance::BTC_USDT"]}
        expected_signature = r"""# df=
        index=[2000-01-01 14:31:00+00:00, 2000-01-01 17:10:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1
        shape=(160, 7)
                                         full_symbol  open  high  low  close  volume  feature1
        timestamp
        2000-01-01 14:31:00+00:00  binance::BTC_USDT   100   101   99  101.0       0       1.0
        2000-01-01 14:32:00+00:00  binance::BTC_USDT   100   101   99  101.0       1       1.0
        2000-01-01 14:33:00+00:00  binance::BTC_USDT   100   101   99  101.0       2       1.0
        ...
        2000-01-01 17:08:00+00:00  binance::BTC_USDT   100   101   99  100.0     157      -1.0
        2000-01-01 17:09:00+00:00  binance::BTC_USDT   100   101   99  100.0     158      -1.0
        2000-01-01 17:10:00+00:00  binance::BTC_USDT   100   101   99  100.0     159      -1.0"""
        # Run test.
        full_symbol = "binance::BTC_USDT"
        self._test_read_data1(
            im_client,
            full_symbol,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_read_data2(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 320
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        expected_signature = r"""# df=
        index=[2000-01-01 14:31:00+00:00, 2000-01-01 17:10:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1
        shape=(320, 7)
                                         full_symbol  open  high  low  close  volume  feature1
        timestamp
        2000-01-01 14:31:00+00:00  binance::ADA_USDT   100   101   99  101.0       0       1.0
        2000-01-01 14:31:00+00:00  binance::BTC_USDT   100   101   99  101.0       0       1.0
        2000-01-01 14:32:00+00:00  binance::ADA_USDT   100   101   99  101.0       1       1.0
        ...
        2000-01-01 17:09:00+00:00  binance::BTC_USDT   100   101   99  100.0     158      -1.0
        2000-01-01 17:10:00+00:00  binance::ADA_USDT   100   101   99  100.0     159      -1.0
        2000-01-01 17:10:00+00:00  binance::BTC_USDT   100   101   99  100.0     159      -1.0"""
        # Run test.
        full_symbols = ["binance::ADA_USDT", "binance::BTC_USDT"]
        self._test_read_data2(
            im_client,
            full_symbols,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_read_data3(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 314
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        expected_signature = r"""# df=
        index=[2000-01-01 14:34:00+00:00, 2000-01-01 17:10:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1
        shape=(314, 7)
                                         full_symbol  open  high  low  close  volume  feature1
        timestamp
        2000-01-01 14:34:00+00:00  binance::ADA_USDT   100   101   99  101.0       3       1.0
        2000-01-01 14:34:00+00:00  binance::BTC_USDT   100   101   99  101.0       3       1.0
        2000-01-01 14:35:00+00:00  binance::ADA_USDT   100   101   99  101.0       4       1.0
        ...
        2000-01-01 17:09:00+00:00  binance::BTC_USDT   100   101   99  100.0     158      -1.0
        2000-01-01 17:10:00+00:00  binance::ADA_USDT   100   101   99  100.0     159      -1.0
        2000-01-01 17:10:00+00:00  binance::BTC_USDT   100   101   99  100.0     159      -1.0"""
        # Run test.
        full_symbols = ["binance::ADA_USDT", "binance::BTC_USDT"]
        start_timestamp = pd.Timestamp("2000-01-01 14:34:00+00:00")
        self._test_read_data3(
            im_client,
            full_symbols,
            start_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_read_data4(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 16
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        expected_signature = r"""# df=
        index=[2000-01-01 14:31:00+00:00, 2000-01-01 14:38:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1
        shape=(16, 7)
                                         full_symbol  open  high  low  close  volume  feature1
        timestamp
        2000-01-01 14:31:00+00:00  binance::ADA_USDT   100   101   99  101.0       0       1.0
        2000-01-01 14:31:00+00:00  binance::BTC_USDT   100   101   99  101.0       0       1.0
        2000-01-01 14:32:00+00:00  binance::ADA_USDT   100   101   99  101.0       1       1.0
        ...
        2000-01-01 14:37:00+00:00  binance::BTC_USDT   100   101   99  100.0       6      -1.0
        2000-01-01 14:38:00+00:00  binance::ADA_USDT   100   101   99  100.0       7      -1.0
        2000-01-01 14:38:00+00:00  binance::BTC_USDT   100   101   99  100.0       7      -1.0"""
        # Run test.
        full_symbols = ["binance::ADA_USDT", "binance::BTC_USDT"]
        end_timestamp = pd.Timestamp("2000-01-01 14:38:00+00:00")
        self._test_read_data4(
            im_client,
            full_symbols,
            end_timestamp,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test_read_data5(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 10
        expected_column_names = self.get_expected_column_names()
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        expected_signature = r"""# df=
        index=[2000-01-01 14:34:00+00:00, 2000-01-01 14:38:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1
        shape=(10, 7)
                                         full_symbol  open  high  low  close  volume  feature1
        timestamp
        2000-01-01 14:34:00+00:00  binance::ADA_USDT   100   101   99  101.0       3       1.0
        2000-01-01 14:34:00+00:00  binance::BTC_USDT   100   101   99  101.0       3       1.0
        2000-01-01 14:35:00+00:00  binance::ADA_USDT   100   101   99  101.0       4       1.0
        ...
        2000-01-01 14:37:00+00:00  binance::BTC_USDT   100   101   99  100.0       6      -1.0
        2000-01-01 14:38:00+00:00  binance::ADA_USDT   100   101   99  100.0       7      -1.0
        2000-01-01 14:38:00+00:00  binance::BTC_USDT   100   101   99  100.0       7      -1.0"""
        # Run test.
        full_symbols = ["binance::ADA_USDT", "binance::BTC_USDT"]
        start_timestamp = pd.Timestamp("2000-01-01 14:34:00+00:00")
        end_timestamp = pd.Timestamp("2000-01-01 14:38:00+00:00")
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

    # TODO(Grisha): consider making a separate test case of it.
    def test_read_data5_dups(self) -> None:
        df = self.get_duplicated_data()
        im_client = imvcdcdfimce.get_DataFrameImClient_example1(df)
        # Set expected values.
        expected_length = 10
        expected_column_names = self.get_expected_column_names()
        expected_column_names.append("knowledge_timestamp")
        expected_column_unique_values = {
            "full_symbol": ["binance::ADA_USDT", "binance::BTC_USDT"]
        }
        expected_signature = r"""# df=
        index=[2000-01-01 14:34:00+00:00, 2000-01-01 14:38:00+00:00]
        columns=full_symbol,open,high,low,close,volume,feature1,knowledge_timestamp
        shape=(10, 8)
                                 full_symbol  open  high  low  close  volume  feature1       knowledge_timestamp
        timestamp
        2000-01-01 14:34:00+00:00  binance::ADA_USDT   100   101   99  101.0       3       1.0 2000-02-01 17:41:00+00:00
        2000-01-01 14:34:00+00:00  binance::BTC_USDT   100   101   99  101.0       3       1.0 2000-02-01 17:42:00+00:00
        2000-01-01 14:35:00+00:00  binance::ADA_USDT   100   101   99  101.0       4       1.0 2000-02-01 17:43:00+00:00
        ...
        2000-01-01 14:37:00+00:00  binance::BTC_USDT   100   101   99  100.0       6      -1.0 2000-02-01 17:48:00+00:00
        2000-01-01 14:38:00+00:00  binance::ADA_USDT   100   101   99  100.0       7      -1.0 2000-02-01 17:49:00+00:00
        2000-01-01 14:38:00+00:00  binance::BTC_USDT   100   101   99  100.0       7      -1.0 2000-02-01 17:50:00+00:00
        """
        # Run test.
        full_symbols = ["binance::ADA_USDT", "binance::BTC_USDT"]
        start_timestamp = pd.Timestamp("2000-01-01 14:34:00+00:00")
        end_timestamp = pd.Timestamp("2000-01-01 14:38:00+00:00")
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

    def test_read_data6(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Run test.
        full_symbols = "unsupported_exchange::unsupported_currency"
        self._test_read_data6(im_client, full_symbols)

    # Note that `test_read_data7()` is not implemented since data that is
    # generated for these tests should alternate every 5 rows and does not
    # contain any data gaps. Thus, resampling cannot be tested properly.

    # ////////////////////////////////////////////////////////////////////////

    def test_get_start_ts_for_symbol1(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        full_symbol = "binance::BTC_USDT"
        # Set expected values.
        expected_start_ts = pd.Timestamp("2000-01-01 14:31:00+00:00")
        # Run test.
        self._test_get_start_ts_for_symbol1(
            im_client,
            full_symbol,
            expected_start_ts,
        )

    def test_get_end_ts_for_symbol1(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        full_symbol = "binance::BTC_USDT"
        # Set expected values.
        expected_end_ts = pd.Timestamp("2000-01-01 17:10:00+00:00")
        # Run test.
        self._test_get_end_ts_for_symbol1(
            im_client,
            full_symbol,
            expected_end_ts,
        )

    # ////////////////////////////////////////////////////////////////////////

    def test_get_universe1(self) -> None:
        # Initialize client.
        im_client = self.get_ImClient()
        # Set expected values.
        expected_length = 2
        expected_first_elements = [
            "binance::ADA_USDT",
            "binance::BTC_USDT",
        ]
        # Universe for the test data contains only 2 full symbols so expected
        # first and last elements of the universe should be equal.
        expected_last_elements = expected_first_elements
        # Run test.
        self._test_get_universe1(
            im_client,
            expected_length,
            expected_first_elements,
            expected_last_elements,
        )
