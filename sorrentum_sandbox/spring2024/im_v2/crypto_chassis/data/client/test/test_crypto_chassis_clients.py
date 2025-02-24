import pandas as pd
import pytest

import helpers.henv as henv
import im_v2.common.data.client as icdc
import im_v2.crypto_chassis.data.client.crypto_chassis_clients_example as imvccdcccce


@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestCryptoChassisHistoricalPqByTileClient1(icdc.ImClientTestCase):
    @pytest.mark.slow("Slow via GH, fast on the server")
    def test1(self) -> None:
        """
        `dataset = bid_ask`
        `contract_type = futures`
        `tag = ""`
        """
        universe_version = "v2"
        dataset = "bid_ask"
        contract_type = "futures"
        data_snapshot = "20220620"
        client = imvccdcccce.get_CryptoChassisHistoricalPqByTileClient_example1(
            universe_version, dataset, contract_type, data_snapshot
        )
        full_symbols = ["binance::BTC_USDT", "binance::DOGE_USDT"]
        start_ts = pd.Timestamp("2022-05-15 13:00:00+00:00")
        end_ts = pd.Timestamp("2022-05-15 16:00:00+00:00")
        expected_signature = r"""# df=
        index=[2022-05-15 13:00:00+00:00, 2022-05-15 16:00:00+00:00]
        columns=full_symbol,bid_price,bid_size,ask_price,ask_size
        shape=(362, 5)
                                          full_symbol     bid_price     bid_size     ask_price    ask_size
        timestamp
        2022-05-15 13:00:00+00:00   binance::BTC_USDT  30274.410812       94.184  30276.087000      52.984
        2022-05-15 13:00:00+00:00  binance::DOGE_USDT      0.089351  1056883.000      0.089372  783002.000
        2022-05-15 13:01:00+00:00   binance::BTC_USDT  30263.589387       94.028  30271.038506      48.787
        ...
        2022-05-15 15:59:00+00:00  binance::DOGE_USDT      0.088676  1944119.000      0.088708  1063193.000
        2022-05-15 16:00:00+00:00   binance::BTC_USDT  30005.735776       70.693  30010.941933       66.659
        2022-05-15 16:00:00+00:00  binance::DOGE_USDT      0.088676   961916.000      0.088743  1415354.000
        """
        expected_length = 362
        expected_column_names = None
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "binance::DOGE_USDT"]
        }
        self._test_read_data5(
            client,
            full_symbols,
            start_ts,
            end_ts,
            expected_signature=expected_signature,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
        )

    @pytest.mark.slow("Slow via GH, fast on the server")
    def test2(self) -> None:
        """
        `dataset = ohlcv`
        `contract_type = spot`
        """
        universe_version = "v2"
        dataset = "ohlcv"
        contract_type = "spot"
        data_snapshot = "20220530"
        client = imvccdcccce.get_CryptoChassisHistoricalPqByTileClient_example1(
            universe_version, dataset, contract_type, data_snapshot
        )
        full_symbols = ["binance::BTC_USDT", "binance::DOGE_USDT"]
        start_ts = pd.Timestamp("2022-05-15 13:00:00+00:00")
        end_ts = pd.Timestamp("2022-05-15 13:15:00+00:00")
        expected_signature = r"""# df=
        index=[2022-05-15 13:00:00+00:00, 2022-05-15 13:15:00+00:00]
        columns=full_symbol,open,high,low,close,volume,vwap,number_of_trades,twap,knowledge_timestamp
        shape=(32, 10)
                                          full_symbol        open        high         low       close        volume          vwap  number_of_trades          twap              knowledge_timestamp
        timestamp
        2022-05-15 13:00:00+00:00   binance::BTC_USDT  30309.9900  30315.9100  30280.0000  30280.9500      45.13335  30291.409100               607  30291.172400 2022-05-31 14:38:23.953697+00:00
        2022-05-15 13:00:00+00:00  binance::DOGE_USDT      0.0895      0.0895      0.0894      0.0894  606842.00000      0.089435                49      0.089469 2022-05-31 14:38:29.472387+00:00
        2022-05-15 13:01:00+00:00   binance::BTC_USDT  30280.9500  30299.5700  30263.2800  30263.3100      39.45772  30278.419700               577  30278.335000 2022-05-31 14:38:23.953697+00:00
        ...
        2022-05-15 13:14:00+00:00  binance::DOGE_USDT      0.0895      0.0897      0.0894      0.0896  233260.00000      0.089547                30      0.089507 2022-05-31 14:38:29.472387+00:00
        2022-05-15 13:15:00+00:00   binance::BTC_USDT  30363.5000  30400.0000  30324.2300  30387.2600      62.71008  30370.925000              1364  30374.435700 2022-05-31 14:38:23.953697+00:00
        2022-05-15 13:15:00+00:00  binance::DOGE_USDT      0.0897      0.0898      0.0895      0.0898  460666.00000      0.089629                23      0.089626 2022-05-31 14:38:29.472387+00:00
        """
        expected_length = 32
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "binance::DOGE_USDT"]
        }
        expected_column_names = None
        self._test_read_data5(
            client,
            full_symbols,
            start_ts,
            end_ts,
            expected_signature=expected_signature,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
        )


@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestCryptoChassisHistoricalPqByTileClient2(icdc.ImClientTestCase):
    @pytest.mark.slow("Slow via GH, fast on the server")
    def test1(self) -> None:
        """
        `dataset = bid_ask`
        `contract_type = futures`
        `tag = resampled_1min`
        """
        universe_version = "v2"
        resample_1min = True
        contract_type = "futures"
        tag = "resampled_1min"
        client = imvccdcccce.get_CryptoChassisHistoricalPqByTileClient_example2(
            universe_version,
            resample_1min,
            contract_type,
            tag,
        )
        full_symbols = ["binance::BTC_USDT", "binance::DOGE_USDT"]
        start_ts = pd.Timestamp("2022-11-05 13:00:00+00:00")
        end_ts = pd.Timestamp("2022-11-05 14:00:00+00:00")
        expected_signature = r"""# df=
        index=[2022-11-05 13:00:00+00:00, 2022-11-05 14:00:00+00:00]
        columns=full_symbol,bid_price,bid_size,ask_price,ask_size
        shape=(122, 5)
                                  full_symbol     bid_price     bid_size     ask_price     ask_size
        timestamp
        2022-11-05 13:00:00+00:00   binance::BTC_USDT  21295.193172     1056.388  21294.732442     1306.262
        2022-11-05 13:00:00+00:00  binance::DOGE_USDT      0.127876  2341262.000      0.127916  3669090.000
        2022-11-05 13:01:00+00:00   binance::BTC_USDT  21292.477087     1439.011  21289.924597     1084.776
        ...
        2022-11-05 13:59:00+00:00  binance::DOGE_USDT      0.127682  1841378.000      0.127619  2266535.000
        2022-11-05 14:00:00+00:00   binance::BTC_USDT  21262.852986     1275.421  21262.126973      492.722
        2022-11-05 14:00:00+00:00  binance::DOGE_USDT      0.127745  2805192.000      0.127770  2139891.000
        """
        expected_length = 122
        expected_column_names = None
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "binance::DOGE_USDT"]
        }
        self._test_read_data5(
            client,
            full_symbols,
            start_ts,
            end_ts,
            expected_signature=expected_signature,
            expected_length=expected_length,
            expected_column_names=expected_column_names,
            expected_column_unique_values=expected_column_unique_values,
        )
