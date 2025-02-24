import argparse
import unittest.mock as umock

import pytest

import helpers.henv as henv
import helpers.hunit_test as hunitest
import im_v2.common.data.extract.download_bulk as imvcdedobu
import im_v2.common.data.extract.extract_utils as imvcdeexut


@pytest.mark.skip("CryptoChassis is a deprecated data source")
class TestDownloadHistoricalData1(hunitest.TestCase):
    def test_parser(self) -> None:
        """
        Test arg parser for predefined args in the script.

        Mostly for coverage and to detect argument changes.
        """
        parser = imvcdedobu._parse()
        cmd = []
        cmd.extend(["--download_mode", "periodic_daily"])
        cmd.extend(["--downloading_entity", "manual"])
        cmd.extend(["--action_tag", "downloaded_1min"])
        cmd.extend(["--data_type", "ohlcv"])
        cmd.extend(["--vendor", "crypto_chassis"])
        cmd.extend(["--start_timestamp", "2022-02-08"])
        cmd.extend(["--end_timestamp", "2022-02-09"])
        cmd.extend(["--exchange_id", "binance"])
        cmd.extend(["--contract_type", "spot"])
        cmd.extend(["--universe", "v3"])
        cmd.extend(["--aws_profile", "ck"])
        cmd.extend(["--s3_path", "s3://cryptokaizen-data-test/"])
        cmd.extend(["--data_format", "parquet"])
        cmd.extend(["--universe_part", "1"])
        args = parser.parse_args(cmd)
        actual = vars(args)
        expected = {
            "download_mode": "periodic_daily",
            "downloading_entity": "manual",
            "action_tag": "downloaded_1min",
            "data_type": "ohlcv",
            "vendor": "crypto_chassis",
            "start_timestamp": "2022-02-08",
            "end_timestamp": "2022-02-09",
            "exchange_id": "binance",
            "contract_type": "spot",
            "universe": "v3",
            "aws_profile": "ck",
            "s3_path": "s3://cryptokaizen-data-test/",
            "log_level": "INFO",
            "data_format": "parquet",
            "bid_ask_depth": 10,
            "universe_part": 1,
            "assert_on_missing_data": False,
            "dst_dir": None,
            "pq_save_mode": "append",
        }
        self.assertDictEqual(actual, expected)

    @umock.patch.object(
        imvcdedobu.imvccdexex,
        "CryptoChassisExtractor",
        autospec=True,
        spec_set=True,
    )
    @umock.patch.object(imvcdeexut, "download_historical_data")
    def test_main(
        self,
        mock_download_historical: umock.MagicMock,
        chassis_extractor_mock: umock.MagicMock,
    ) -> None:
        """
        Smoke test to directly run `_main` function for coverage increase.
        """
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        kwargs = {
            "download_mode": "bulk",
            "downloading_entity": "manual",
            "action_tag": "downloaded_1min",
            "data_type": "ohlcv",
            "vendor": "crypto_chassis",
            "start_timestamp": "2021-12-31 23:00:00",
            "end_timestamp": "2022-01-01 01:00:00",
            "universe": "v1",
            "exchange_id": "binance",
            "contract_type": "spot",
            "data_format": "parquet",
            "log_level": "INFO",
            "s3_path": "s3://mock_bucket",
            "aws_profile": "ck",
            "universe_part": 1,
        }
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        # Run.
        imvcdedobu._main(mock_argument_parser)
        # Check call.
        self.assertEqual(len(mock_download_historical.call_args), 2)
        actual_args = mock_download_historical.call_args.args
        self.assertDictEqual(actual_args[0], {**kwargs, **{"unit": "s"}})
        # Verify that `CryptoChassisExtractor` instance is passed.
        self.assertEqual(
            actual_args[1]._extract_mock_name(), "CryptoChassisExtractor()"
        )
        # Verify that `CryptoChassisExtractor` instance creation is properly called.
        self.assertEqual(chassis_extractor_mock.call_count, 1)
        actual_args = tuple(chassis_extractor_mock.call_args)
        expected_args = (("spot",), {})
        self.assertEqual(actual_args, expected_args)
