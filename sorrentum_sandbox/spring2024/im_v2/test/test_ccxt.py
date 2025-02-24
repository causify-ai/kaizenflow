import argparse
import asyncio
import os
import unittest.mock as umock
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import pytest

import data_schema.dataset_schema_utils as dsdascut
import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hs3 as hs3
import helpers.hsql as hsql
import helpers.hunit_test as hunitest
import im_v2.ccxt.data.extract.download_exchange_data_to_db_periodically as imvcdededtdp
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.data.extract.download_bulk as imvcdedobu
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe as ivcu


@pytest.mark.requires_ck_infra
@pytest.mark.requires_aws
@pytest.mark.skip(
    reason="Modify the test to not have an API call",
)
class TestDownloadBulk(hmoto.S3Mock_TestCase):
    """
    Test REST API for CCXT for ohlcv, bid_ask and trades.

    - Call rest api of CCXT.
    - save data to S3.
    - load data from S3 and verify.
    """

    @umock.patch.object(imvcdeexut.hdateti, "get_current_time")
    def call_download_bulk(
        self,
        vendor: str,
        data_type: str,
        contract_type: str,
        exchange_id: str,
        currency_pairs: List[str],
        expected_list: List[str],
        expected_data: str,
        mock_get_current_time: umock.MagicMock,
    ) -> None:
        """
        Directly call function for increased coverage.
        """
        mock_get_current_time.return_value = pd.Timestamp(
            "2023-02-08 10:12:00.000000+00:00"
        )
        # Prepare inputs.
        kwargs = {
            "start_timestamp": "2023-12-31 23:00:00",
            "end_timestamp": "2023-12-31 23:01:00",
            "exchange_id": exchange_id,
            "vendor": vendor,
            "data_type": data_type,
            "download_mode": "periodic_daily",
            "downloading_entity": "manual",
            "action_tag": "downloaded_all",
            "contract_type": contract_type,
            "aws_profile": self.mock_aws_profile,
            "s3_path": f"s3://{self.bucket_name}/",
            "data_format": "parquet",
            "assert_on_missing_data": True,
            "universe": "v7.6",
            "pq_save_mode": "append",
            "log_level": "INFO",
        }
        if vendor == "crypto_chassis":
            kwargs["universe_part"] = 1
        args = argparse.Namespace(**kwargs)
        with umock.patch.object(
            ivcu, "get_vendor_universe", return_value={exchange_id: currency_pairs}
        ):
            imvcdedobu._run(args)

        self.s3fs_ = hs3.get_s3fs(self.mock_aws_profile)
        # Prepare common `hs3.listdir` params.
        s3_bucket = f"s3://{self.bucket_name}"
        pattern = "*.parquet"
        only_files = True
        use_relative_paths = True
        # Check parquet files on s3.
        full_parquet_path_list = hs3.listdir(
            s3_bucket,
            pattern,
            only_files,
            use_relative_paths,
            aws_profile=self.mock_aws_profile,
        )
        full_parquet_path_list.sort()
        parquet_path_list = [
            # Remove uuid names.
            "/".join(path.split("/")[:-1])
            for path in full_parquet_path_list
        ]
        # Add kwargs required to build s3 path.
        kwargs["asset_type"] = kwargs["contract_type"]
        kwargs["version"] = "v1_0_0"
        s3_path_common = dsdascut.build_s3_dataset_path_from_args(
            s3_bucket, kwargs
        )
        expected_list = [
            os.path.join(s3_path_common, val) for val in expected_list
        ]
        parquet_path_list = [
            os.path.join(s3_bucket, val) for val in parquet_path_list
        ]
        self.assertListEqual(parquet_path_list, expected_list)
        # Check data.
        # import pdb;pdb.set_trace()
        parquet_data_path = os.path.join(s3_bucket, full_parquet_path_list[0])
        actual_df = hparque.from_parquet(
            parquet_data_path, aws_profile=self.s3fs_
        )
        actual = hpandas.df_to_str(actual_df)
        self.assert_equal(actual, expected_data, fuzzy_match=True)

    @pytest.mark.slow("12 seconds")
    def test1(
        self,
    ) -> None:
        """
        Test REST API for binance futures with data type trades.
        """
        vendor = "ccxt"
        data_type = "trades"
        contract_type = "futures"
        exchange_id = "binance"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12/day=31",
        ]
        expected_data = r"""
                                      timestamp         symbol  side    price  amount exchange_id       knowledge_timestamp
        timestamp                                                                                                                  
        2023-12-31 23:00:00.064000+00:00  1704063600064  BTC/USDT:USDT  sell  42294.8   0.005     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:00.104000+00:00  1704063600104  BTC/USDT:USDT   buy  42294.9   0.140     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:00.127000+00:00  1704063600127  BTC/USDT:USDT  sell  42294.8   0.084     binance 2023-02-08 10:12:00+00:00
        ...
        2023-12-31 23:00:59.683000+00:00  1704063659683  BTC/USDT:USDT   buy  42314.0   0.005     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:59.812000+00:00  1704063659812  BTC/USDT:USDT  sell  42313.9   0.200     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:59.922000+00:00  1704063659922  BTC/USDT:USDT   buy  42314.0   1.104     binance 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test2(
        self,
    ) -> None:
        """
        Test REST API for binance futures with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "futures"
        exchange_id = "binance"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12",
        ]
        expected_data = r"""
                               timestamp     open     high      low    close    volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                   
        2023-12-31 23:00:00+00:00  1704063600000  42294.8  42326.7  42211.0  42314.0  1095.062     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42314.0  42332.3  42276.0  42283.5   440.441     binance 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test3(
        self,
    ) -> None:
        """
        Test REST API for binance spot with data type trades.
        """
        vendor = "ccxt"
        data_type = "trades"
        contract_type = "spot"
        exchange_id = "binance"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12/day=31",
        ]
        expected_data = r"""
                                      timestamp    symbol  side     price   amount exchange_id       knowledge_timestamp
        timestamp                                                                                                               
        2023-12-31 23:00:00+00:00         1704063600000  BTC/USDT   buy  42257.89  0.00041     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:00.005000+00:00  1704063600005  BTC/USDT  sell  42257.88  0.00078     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:00.006000+00:00  1704063600006  BTC/USDT   buy  42257.89  0.00071     binance 2023-02-08 10:12:00+00:00
        ...
        2023-12-31 23:00:59.994000+00:00  1704063659994  BTC/USDT  buy  42277.25  0.00176     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:59.995000+00:00  1704063659995  BTC/USDT  buy  42277.25  0.00165     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:59.997000+00:00  1704063659997  BTC/USDT  buy  42277.25  0.00170     binance 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test4(
        self,
    ) -> None:
        """
        Test REST API for binance spot with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "spot"
        exchange_id = "binance"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12",
        ]
        expected_data = r"""
                               timestamp      open     high       low     close     volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                       
        2023-12-31 23:00:00+00:00  1704063600000  42257.89  42291.1  42196.61  42277.25  114.76075     binance 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42277.25  42296.6  42241.10  42252.14   45.96533     binance 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )
    
    @pytest.mark.slow("12 seconds")
    def test5(
        self,
    ) -> None:
        """
        Test REST API for cryptocom futures with data type trades.
        """
        vendor = "ccxt"
        data_type = "trades"
        contract_type = "futures"
        exchange_id = "cryptocom"
        currency_pairs = ["BTC_USD"]
        expected_list = [
            "currency_pair=BTC_USD/year=2023/month=12/day=31",
        ]
        expected_data = r"""
                                      timestamp       symbol side    price  amount exchange_id       knowledge_timestamp
        timestamp                                                                                                               
        2023-12-31 23:00:39.410000+00:00  1704063639410  BTC/USD:USD  buy  42242.9  0.1000   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:39.410000+00:00  1704063639410  BTC/USD:USD  buy  42243.5  0.0148   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:39.466000+00:00  1704063639466  BTC/USD:USD  buy  42245.3  0.0500   cryptocom 2023-02-08 10:12:00+00:00
        ...
        2023-12-31 23:00:55.454000+00:00  1704063655454  BTC/USD:USD  sell  42268.3  0.0059   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:55.889000+00:00  1704063655889  BTC/USD:USD   buy  42267.0  0.0028   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:57.683000+00:00  1704063657683  BTC/USD:USD   buy  42279.3  0.0150   cryptocom 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test6(
        self,
    ) -> None:
        """
        Test REST API for cryptocom futures with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "futures"
        exchange_id = "cryptocom"
        currency_pairs = ["BTC_USD"]
        expected_list = [
            "currency_pair=BTC_USD/year=2023/month=12",
        ]
        expected_data = r"""
                               timestamp     open     high      low    close   volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                  
        2023-12-31 23:00:00+00:00  1704063600000  42265.2  42301.0  42179.3  42279.3  17.7506   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42290.5  42302.8  42238.7  42250.3  20.2185   cryptocom 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test7(
        self,
    ) -> None:
        """
        Test REST API for cryptocom spot with data type trades.
        """
        vendor = "ccxt"
        data_type = "trades"
        contract_type = "spot"
        exchange_id = "cryptocom"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12/day=31",
        ]
        expected_data = r"""
                                      timestamp    symbol side     price   amount exchange_id       knowledge_timestamp
        timestamp                                                                                                              
        2023-12-31 23:00:30.726000+00:00  1704063630726  BTC/USDT  buy  42262.43  0.00989   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:30.726000+00:00  1704063630726  BTC/USDT  buy  42262.43  0.00989   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:30.726000+00:00  1704063630726  BTC/USDT  buy  42262.43  0.00989   cryptocom 2023-02-08 10:12:00+00:00
        ...
        2023-12-31 23:00:53.530000+00:00  1704063653530  BTC/USDT  sell  42256.65  0.02062   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:53.531000+00:00  1704063653531  BTC/USDT  sell  42256.65  0.00387   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:55.890000+00:00  1704063655890  BTC/USDT   buy  42263.52  0.00279   cryptocom 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test8(
        self,
    ) -> None:
        """
        Test REST API for cryptocom spot with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "spot"
        exchange_id = "cryptocom"
        currency_pairs = ["BTC_USD"]
        expected_list = [
            "currency_pair=BTC_USD/year=2023/month=12",
        ]
        expected_data = r"""
                               timestamp      open      high       low     close    volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                       
        2023-12-31 23:00:00+00:00  1704063600000  42253.92  42288.70  42182.38  42273.67  13.84140   cryptocom 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42278.54  42291.86  42227.93  42241.13   9.71717   cryptocom 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test9(
        self,
    ) -> None:
        """
        Test REST API for okx futures with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "futures"
        exchange_id = "okx"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12",
        ]
        expected_data = r"""
                                    timestamp     open     high      low    close  volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                 
        2023-12-31 23:00:00+00:00  1704063600000  42274.6  42309.0  42205.4  42294.5  386.24         okx 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42294.5  42314.3  42254.0  42266.2   98.98         okx 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test10(
        self,
    ) -> None:
        """
        Test REST API for okx spot with data type ohlcv.
        """
        vendor = "ccxt"
        data_type = "ohlcv"
        contract_type = "spot"
        exchange_id = "okx"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12",
        ]
        expected_data = r"""
                                    timestamp     open     high      low    close     volume exchange_id       knowledge_timestamp
        timestamp                                                                                                                    
        2023-12-31 23:00:00+00:00  1704063600000  42261.9  42295.9  42183.7  42281.4  41.971951         okx 2023-02-08 10:12:00+00:00
        2023-12-31 23:01:00+00:00  1704063660000  42281.5  42303.6  42244.6  42253.0  12.088122         okx 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

    @pytest.mark.slow("12 seconds")
    def test11(
        self,
    ) -> None:
        """
        Test REST API for kraken spot with data type trades.
        """
        vendor = "ccxt"
        data_type = "trades"
        contract_type = "spot"
        exchange_id = "kraken"
        currency_pairs = ["BTC_USDT"]
        expected_list = [
            "currency_pair=BTC_USDT/year=2023/month=12/day=31",
        ]
        expected_data = r"""
                                      timestamp    symbol side    price    amount exchange_id       knowledge_timestamp
        timestamp                                                                                                              
        2023-12-31 23:00:02.408000+00:00  1704063602408  BTC/USDT  buy  42268.7  0.000100      kraken 2023-02-08 10:12:00+00:00
        2023-12-31 23:00:34.167000+00:00  1704063634167  BTC/USDT  buy  42265.6  0.001501      kraken 2023-02-08 10:12:00+00:00
        """
        self.call_download_bulk(
            vendor,
            data_type,
            contract_type,
            exchange_id,
            currency_pairs,
            expected_list,
            expected_data
        )

@pytest.mark.skip(
    "Cannot be run from the US due to 451 error API error. Run manually."
)
class TestDownloadRealtimeForOneExchangePeriodically3(
    imvcddbut.TestImDbHelper, hunitest.TestCase
):
    """
    Test Websocket API for CCXT for bid_ask futures and spot.

    - Call rest api of CCXT.
    - save data to RDS.
    - load data from RDS and verify.
    """

    db_connection_patch = umock.patch.object(
        imvcdeexut.imvcddbut.DbConnectionManager, "get_connection"
    )

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def set_up_test(self) -> None:
        # Run before each test.
        # Add an isolated events loop.
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.mock_get_connection = self.db_connection_patch.start()
        self.mock_get_connection.return_value = self.connection
        yield
        # Run after each test.
        self.db_connection_patch.stop()
        self.loop.close()
    
    def call_download_realtime_for_one_exchange_periodically(
        self,
        contract_type: str,
        exchange_id: str,
        currency_pairs: List[str],
        db_table: str,
        db_query: str,
        expected_data: int,
    ) -> None:
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Amount of downloads depends on the start time and stop time.
        current_time = datetime.now()
        start_time = current_time + timedelta(minutes=0, seconds=8)
        stop_time = current_time + timedelta(minutes=0, seconds=10)
        kwargs = {
            "data_type": "bid_ask",
            "exchange_id": exchange_id,
            "universe": "v7.4",
            "db_stage": "test",
            "contract_type": contract_type,
            "vendor": "ccxt",
            "db_table": db_table,
            "aws_profile": "ck",
            "start_time": f"{start_time}",
            "stop_time": f"{stop_time}",
            "method": "websocket",
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_200ms",
            "data_format": "postgres",
            "log_level": "INFO",
            "websocket_data_buffer_size": 0,
            "db_saving_mode": "on_buffer_full",
            "bid_ask_depth": 10,
        }
        # Create argparser.
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        create_db_query = db_query
        # Create the database.
        cursor = self.connection.cursor()
        cursor.execute(create_db_query)
        # Run.
        with umock.patch.object(
            imvcdeexut.ivcu,
            "get_vendor_universe",
            return_value={exchange_id: currency_pairs},
        ):
            # Mock waiting time to speed up test.
            imvcdededtdp.imvcdeexut.WEBSOCKET_CONFIG["bid_ask"][
                "sleep_between_iter_in_ms"
            ] = 1000
            imvcdededtdp._main(mock_argument_parser)
            # Get downloaded data.
            get_data_query = f"SELECT * FROM {db_table} where exchange_id='{exchange_id}';"
            data = hsql.execute_query_to_df(self.connection, get_data_query)
        self.assertEqual(len(data), expected_data)

    @pytest.mark.slow("~10 seconds.")
    def test1(self) -> None:
        """
        Test Websocket API for binance futures.
        """
        contract_type = "futures"
        exchange_id = "binance"
        currency_pairs = ["ETH_USDT"]
        db_table = "ccxt_bid_ask_futures_raw"
        db_query = imvccdbut.get_ccxt_create_bid_ask_futures_raw_table_query()
        expected_data = 20
        self.call_download_realtime_for_one_exchange_periodically(
            contract_type,
            exchange_id,
            currency_pairs,
            db_table,
            db_query,
            expected_data,
        )
        

    @pytest.mark.slow("~10 seconds.")
    def test2(self) -> None:
        """
        Test Websocket API for binance spot.
        """
        contract_type = "spot"
        exchange_id = "binance"
        currency_pairs = ["ETH_USDT"]
        db_table = "ccxt_bid_ask_spot_raw"
        db_query = imvccdbut.get_ccxt_create_bid_ask_raw_table_query()
        expected_data = 20
        self.call_download_realtime_for_one_exchange_periodically(
            contract_type,
            exchange_id,
            currency_pairs,
            db_table,
            db_query,
            expected_data,
        )

    @pytest.mark.slow("~10 seconds.")
    def test3(self) -> None:
        """
        Test Websocket API for cryptocom futures.
        """
        contract_type = "futures"
        exchange_id = "cryptocom"
        currency_pairs = ["ETH_USD"]
        db_table = "ccxt_bid_ask_futures_raw"
        db_query = imvccdbut.get_ccxt_create_bid_ask_futures_raw_table_query()
        expected_data = 20
        self.call_download_realtime_for_one_exchange_periodically(
            contract_type,
            exchange_id,
            currency_pairs,
            db_table,
            db_query,
            expected_data,
        )
    
    @pytest.mark.slow("~10 seconds.")
    def test4(self) -> None:
        """
        Test Websocket API for okx futures.
        """
        contract_type = "futures"
        exchange_id = "okx"
        currency_pairs = ["ETH_USDT"]
        db_table = "ccxt_bid_ask_futures_raw"
        db_query = imvccdbut.get_ccxt_create_bid_ask_futures_raw_table_query()
        expected_data = 20
        self.call_download_realtime_for_one_exchange_periodically(
            contract_type,
            exchange_id,
            currency_pairs,
            db_table,
            db_query,
            expected_data,
        )
    
    @pytest.mark.slow("~10 seconds.")
    def test5(self) -> None:
        """
        Test Websocket API for Kraken spot.
        """
        contract_type = "spot"
        exchange_id = "kraken"
        currency_pairs = ["ETH_USDT"]
        db_table = "ccxt_bid_ask_spot_raw"
        db_query = imvccdbut.get_ccxt_create_bid_ask_raw_table_query()
        expected_data = 20
        self.call_download_realtime_for_one_exchange_periodically(
            contract_type,
            exchange_id,
            currency_pairs,
            db_table,
            db_query,
            expected_data,
        )