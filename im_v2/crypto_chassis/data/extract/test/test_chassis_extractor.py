import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import im_v2.crypto_chassis.data.extract.extractor as imvccdexex


class TestCryptoChassisExtractor1(hunitest.TestCase):
    def test_initialize_class(self) -> None:
        """
        Smoke test that the class is being initialized correctly.
        """
        _ = imvccdexex.CryptoChassisExtractor()

    def test_download_market_depth_data1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-01-09T23:59:00", tz="UTC")
        exchange_id = "binance"
        currency_pair = "btc/usdt"
        data_type = "market_depth"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_market_depth(
            exchange_id, currency_pair, start_timestamp, end_timestamp, data_type
        )
        # Verify dataframe length.
        self.assertEqual(86007, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686400, first_date)
        self.assertEqual(1641772799, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)

    def test_download_market_depth_data_futures1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-01-09T23:59:00", tz="UTC")
        exchange_id = "binance"
        currency_pair = "btc/usdt"
        data_type = "market_depth-futures"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_market_depth(
            exchange_id, currency_pair, start_timestamp, end_timestamp, data_type
        )
        # Verify dataframe length.
        self.assertEqual(86369, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686400, first_date)
        self.assertEqual(1641772799, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)

    def test_download_market_depth_invalid_input1(self) -> None:
        """
        Run with invalid start timestamp.
        """
        exchange = "binance"
        currency_pair = "btc/usdt"
        start_timestamp = "invalid"
        end_timestamp = pd.Timestamp("2022-01-09T23:59:00", tz="UTC")
        data_type = "market_depth"
        expected = """
* Failed assertion *
Instance of 'invalid' is '<class 'str'>' instead of '<class 'pandas._libs.tslibs.timestamps.Timestamp'>'
"""
        client = imvccdexex.CryptoChassisExtractor()
        with self.assertRaises(AssertionError) as cm:
            client._download_market_depth(
                exchange, currency_pair, start_timestamp, end_timestamp, data_type
            )
        # Check output for error.
        actual = str(cm.exception)
        self.assertIn(expected, actual)

    def test_download_market_depth_invalid_input2(self) -> None:
        """
        Run with invalid exchange name.
        """
        exchange = "bibance"
        currency_pair = "btc/usdt"
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-01-09T23:59:00", tz="UTC")
        data_type = "market_depth"
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_market_depth(
            exchange, currency_pair, start_timestamp, end_timestamp, data_type
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)

    def test_download_market_depth_invalid_input3(self) -> None:
        """
        Run with invalid currency pair.
        """
        exchange = "binance"
        currency_pair = "btc/busdt"
        # End is before start -> invalid.
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-01-09T23:59:00", tz="UTC")
        data_type = "market_depth"
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_market_depth(
            exchange, currency_pair, start_timestamp, end_timestamp, data_type
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)

    @pytest.mark.skip(reason="CmTask1997 'Too many request errors'.")
    @pytest.mark.slow("10 seconds.")
    def test_download_ohlcv1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-03-09T00:00:00", tz="UTC")
        exchange = "binance"
        currency_pair = "btc/usdt"
        data_type = "ohlcv"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_ohlcv(
            exchange,
            currency_pair,
            start_timestamp,
            end_timestamp,
            data_type
        )
        # Verify dataframe length.
        self.assertEqual(84961, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686400, first_date)
        self.assertEqual(1646784000, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)
    
    @pytest.mark.skip(reason="CmTask1997 'Too many request errors'.")
    @pytest.mark.slow("10 seconds.")
    def test_download_ohlcv_futures1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-03-09T00:00:00", tz="UTC")
        exchange = "binance"
        currency_pair = "btc/usdt"
        data_type = "ohlcv-futures"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_ohlcv(
            exchange,
            currency_pair,
            start_timestamp,
            end_timestamp,
            data_type
        )
        # Verify dataframe length.
        self.assertEqual(84961, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686400, first_date)
        self.assertEqual(1646784000, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)

    @pytest.mark.skip(reason="CmTask1997 'Too many request errors'.")
    def test_download_ohlcv_invalid_input1(self) -> None:
        """
        Run with invalid exchange name.
        """
        exchange = "bibance"
        currency_pair = "btc/usdt"
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-03-09T00:00:00", tz="UTC")
        data_type = "ohlcv"
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_ohlcv(
            exchange,
            currency_pair,
            start_timestamp,
            end_timestamp,
            data_type
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)

    @pytest.mark.skip(reason="CmTask1997 'Too many request errors'.")
    def test_download_ohlcv_invalid_input2(self) -> None:
        """
        Run with invalid currency pair.
        """
        exchange = "binance"
        currency_pair = "btc/busdt"
        # End is before start -> invalid.
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        end_timestamp = pd.Timestamp("2022-03-09T00:00:00", tz="UTC")
        data_type = "ohlcv"
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_ohlcv(
            exchange,
            currency_pair,
            start_timestamp,
            end_timestamp,
            data_type
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)

    def test_download_ohlcv_invalid_input3(self) -> None:
        """
        Run with invalid start timestamp.
        """
        exchange = "binance"
        currency_pair = "btc/usdt"
        start_timestamp = "invalid"
        end_timestamp = "invalid"
        data_type = "ohlcv"
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        expected = """
* Failed assertion *
Instance of 'invalid' is '<class 'str'>' instead of '<class 'pandas._libs.tslibs.timestamps.Timestamp'>'
"""
        with self.assertRaises(AssertionError) as cm:
            client._download_ohlcv(
                exchange,
                currency_pair,
                start_timestamp,
                end_timestamp,
                data_type
            )
        # Check output for error.
        actual = str(cm.exception)
        self.assertIn(expected, actual)

    def test_download_trade1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        exchange = "coinbase"
        currency_pair = "btc/usdt"
        data_type = "trade"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_trades(
            exchange, currency_pair, data_type, start_timestamp=start_timestamp
        )
        # Verify dataframe length.
        self.assertEqual(12396, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686404, first_date)
        self.assertEqual(1641772751, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)

    def test_download_trade_futures1(
        self,
    ) -> None:
        """
        Test download for historical data.
        """
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        exchange = "binance"
        currency_pair = "btc/usdt"
        data_type = "trade-futures"
        client = imvccdexex.CryptoChassisExtractor()
        actual = client._download_trades(
            exchange, currency_pair, data_type, start_timestamp=start_timestamp
        )
        # Verify dataframe length.
        self.assertEqual(1265597, actual.shape[0])
        # Verify corner datetime if output is not empty.
        first_date = int(actual["timestamp"].iloc[0])
        last_date = int(actual["timestamp"].iloc[-1])
        self.assertEqual(1641686402, first_date)
        self.assertEqual(1641772799, last_date)
        # Check the output values.
        actual = actual.reset_index(drop=True)
        actual = hpandas.convert_df_to_json_string(actual)
        self.check_string(actual)

    def test_download_trade_invalid_input1(self) -> None:
        """
        Run with invalid start timestamp.
        """
        exchange = "binance"
        currency_pair = "btc/usdt"
        start_timestamp = "invalid"
        data_type = "trades"
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        expected = """
* Failed assertion *
Instance of 'invalid' is '<class 'str'>' instead of '<class 'pandas._libs.tslibs.timestamps.Timestamp'>'
"""
        with self.assertRaises(AssertionError) as cm:
            client._download_trades(
                exchange, currency_pair, data_type, start_timestamp=start_timestamp
            )
        # Check output for error.
        actual = str(cm.exception)
        self.assertIn(expected, actual)

    def test_download_trade_invalid_input2(self) -> None:
        """
        Run with invalid exchange name.
        """
        exchange = "bibance"
        currency_pair = "btc/usdt"
        data_type = "trades"
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_trades(
            exchange, currency_pair, data_type, start_timestamp=start_timestamp
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)

    def test_download_trade_invalid_input3(self) -> None:
        """
        Run with invalid currency pair.
        """
        exchange = "binance"
        currency_pair = "btc/busdt"
        data_type = "trades"
        # End is before start -> invalid.
        start_timestamp = pd.Timestamp("2022-01-09T00:00:00", tz="UTC")
        # Empty Dataframe is expected.
        expected = hpandas.convert_df_to_json_string(pd.DataFrame())
        client = imvccdexex.CryptoChassisExtractor()
        df = client._download_trades(
            exchange, currency_pair, data_type, start_timestamp=start_timestamp
        )
        actual = hpandas.convert_df_to_json_string(df)
        self.assert_equal(expected, actual, fuzzy_match=True)
