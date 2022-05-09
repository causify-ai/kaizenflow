import argparse
import unittest.mock as umock

import pytest

import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hsql as hsql
import helpers.hgit as hgit
import im_v2.ccxt.data.extract.download_realtime_for_one_exchange as imvcdedrfoe
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.db.db_utils as imvcddbut


@pytest.mark.skipif(
    not hgit.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available")
class TestDownloadRealtimeForOneExchange1(
    hmoto.S3Mock_TestCase, imvcddbut.TestImDbHelper
):
    # Secret needed for getting realtime data.
    binance_secret = None

    def setUp(self) -> None:
        # Getting necessary secret before boto3 is mocked.
        if self.binance_secret is None:
            import helpers.hsecrets as hsecret

            self.binance_secret = hsecret.get_secret("binance")
        super().setUp()
        # Initialize database.
        ccxt_ohlcv_table_query = imvccdbut.get_ccxt_ohlcv_create_table_query()
        hsql.execute_query(self.connection, ccxt_ohlcv_table_query)

    def tearDown(self) -> None:
        super().tearDown()
        # Drop table used in tests.
        ccxt_ohlcv_drop_query = "DROP TABLE IF EXISTS ccxt_ohlcv;"
        hsql.execute_query(self.connection, ccxt_ohlcv_drop_query)

    @pytest.mark.slow
    @umock.patch.object(
        imvcdedrfoe.imvcdeexcl.hdateti, "get_current_timestamp_as_string"
    )
    @umock.patch.object(imvcdedrfoe.imvcdeexut.hdateti, "get_current_time")
    @umock.patch.object(imvcdedrfoe.imvcdeexcl.hsecret, "get_secret")
    def test_function_call1(
        self,
        mock_get_secret: umock.MagicMock,
        mock_get_current_time: umock.MagicMock,
        mock_get_current_timestamp_as_string: umock.MagicMock,
    ) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments and checking saved content in database.

        Run without saving to s3.
        """
        mock_get_secret.return_value = self.binance_secret
        mock_get_current_time.return_value = "2021-11-10 00:00:01.000000+00:00"
        mock_get_current_timestamp_as_string.return_value = "20211110-000001"
        use_s3 = False
        self._test_function_call(use_s3)
        # Check number of calls and args for current time.
        self.assertEqual(mock_get_current_time.call_count, 18)
        self.assertEqual(mock_get_current_time.call_args.args, ("UTC",))
        self.assertEqual(mock_get_current_timestamp_as_string.call_count, 0)
        self.assertEqual(mock_get_current_timestamp_as_string.call_args, None)

    @pytest.mark.slow
    @umock.patch.object(
        imvcdedrfoe.imvcdeexcl.hdateti, "get_current_timestamp_as_string"
    )
    @umock.patch.object(imvcdedrfoe.imvcdeexut.hdateti, "get_current_time")
    @umock.patch.object(imvcdedrfoe.imvcdeexcl.hsecret, "get_secret")
    def test_function_call2(
        self,
        mock_get_secret: umock.MagicMock,
        mock_get_current_time: umock.MagicMock,
        mock_get_current_timestamp_as_string: umock.MagicMock,
    ) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments and checking saved content in database.

        Run and save to s3.
        """
        mock_get_secret.return_value = self.binance_secret
        mock_get_current_time.return_value = "2021-11-10 00:00:01.000000+00:00"
        mock_get_current_timestamp_as_string.return_value = "20211110-000001"
        use_s3 = True
        self._test_function_call(use_s3)
        # Check number of calls and args for current time.
        self.assertEqual(mock_get_current_time.call_count, 18)
        self.assertEqual(mock_get_current_time.call_args.args, ("UTC",))
        self.assertEqual(mock_get_current_timestamp_as_string.call_count, 9)
        self.assertEqual(
            mock_get_current_timestamp_as_string.call_args.args, ("UTC",)
        )
        # Check csv files on s3.
        csv_meta_list = self.moto_client.list_objects(Bucket=self.bucket_name)[
            "Contents"
        ]
        csv_files = sorted([csv_meta["Key"] for csv_meta in csv_meta_list])
        expected = [
            "binance/ADA_USDT_20211110-000001.csv",
            "binance/AVAX_USDT_20211110-000001.csv",
            "binance/BNB_USDT_20211110-000001.csv",
            "binance/BTC_USDT_20211110-000001.csv",
            "binance/DOGE_USDT_20211110-000001.csv",
            "binance/EOS_USDT_20211110-000001.csv",
            "binance/ETH_USDT_20211110-000001.csv",
            "binance/LINK_USDT_20211110-000001.csv",
            "binance/SOL_USDT_20211110-000001.csv",
        ]
        self.assertListEqual(csv_files, expected)

    def test_parser(self) -> None:
        """
        Test arg parser for predefined args in the script.

        Mostly for coverage and to detect argument changes.
        """
        parser = imvcdedrfoe._parse()
        cmd = []
        cmd.extend(["--start_timestamp", "20211110-101100"])
        cmd.extend(["--end_timestamp", "20211110-101200"])
        cmd.extend(["--exchange_id", "binance"])
        cmd.extend(["--universe", "v3"])
        cmd.extend(["--db_stage", "dev"])
        cmd.extend(["--db_table", "ccxt_ohlcv"])
        cmd.extend(["--aws_profile", "ck"])
        cmd.extend(["--s3_path", "s3://cryptokaizen-data/realtime/"])
        args = parser.parse_args(cmd)
        actual = vars(args)
        expected = {
            "start_timestamp": "20211110-101100",
            "end_timestamp": "20211110-101200",
            "exchange_id": "binance",
            "universe": "v3",
            "db_stage": "dev",
            "db_table": "ccxt_ohlcv",
            "incremental": False,
            "log_level": "INFO",
            "aws_profile": "ck",
            "s3_path": "s3://cryptokaizen-data/realtime/",
        }
        self.assertDictEqual(actual, expected)

    def _test_function_call(self, use_s3: bool) -> None:
        """
        Test directly _run function for coverage increase.
        """
        # Prepare inputs.
        kwargs = {
            "start_timestamp": "20211110-101100",
            "end_timestamp": "20211110-101200",
            "exchange_id": "binance",
            "universe": "v3",
            "db_stage": "local",
            "db_table": "ccxt_ohlcv",
            "incremental": False,
            "log_level": "INFO",
            "aws_profile": None,
            "s3_path": None,
        }
        if use_s3:
            # Update kwargs.
            kwargs.update(
                {"aws_profile": "ck", "s3_path": f"s3://{self.bucket_name}/"}
            )
        # Run.
        args = argparse.Namespace(**kwargs)
        # TODO(Nikola): Port test to different location, CMTask #1426.
        imvcdedrfoe.imvcdeexut.download_realtime_for_one_exchange(
            args, imvcdedrfoe.imvcdeexcl.CcxtExchange
        )
        # Get saved data in db.
        select_all_query = "SELECT * FROM ccxt_ohlcv;"
        actual_df = hsql.execute_query_to_df(self.connection, select_all_query)
        # Check data output.
        actual = hpandas.df_to_str(actual_df, num_rows=5000)
        # pylint: disable=line-too-long
        expected = r"""        id      timestamp     open     high      low    close    volume currency_pair exchange_id end_download_timestamp knowledge_timestamp
        0        1  1636539060000    2.227    2.228    2.225    2.225  71884.50      ADA_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        1        2  1636539120000    2.226    2.228    2.225    2.227  64687.00      ADA_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        2        3  1636539180000    2.228    2.232    2.227    2.230  59076.30      ADA_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        3        4  1636539240000    2.230    2.233    2.230    2.231  58236.20      ADA_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        4        5  1636539300000    2.232    2.232    2.228    2.232  62120.70      ADA_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        ...    ...            ...      ...      ...      ...      ...       ...           ...         ...                    ...                 ...
        4495  4496  1636568760000  240.930  241.090  240.850  240.990    507.21      SOL_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        4496  4497  1636568820000  240.990  241.010  240.800  241.010    623.65      SOL_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        4497  4498  1636568880000  241.010  241.420  241.010  241.300    705.84      SOL_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        4498  4499  1636568940000  241.300  241.680  241.240  241.660    864.55      SOL_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01
        4499  4500  1636569000000  241.660  241.670  241.410  241.430    762.90      SOL_USDT     binance    2021-11-10 00:00:01 2021-11-10 00:00:01

        [4500 rows x 11 columns]"""
        self.assert_equal(actual, expected, fuzzy_match=True)
