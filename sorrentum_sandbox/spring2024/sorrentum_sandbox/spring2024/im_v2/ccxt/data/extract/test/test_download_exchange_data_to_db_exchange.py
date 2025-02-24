import argparse
import unittest.mock as umock

import pytest

import helpers.henv as henv
import helpers.hunit_test as hunitest
import im_v2.ccxt.data.extract.download_exchange_data_to_db as imvcdededtd
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.data.extract.extract_utils as imvcdeexut


@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestDownloadRealtimeForOneExchange1(hunitest.TestCase):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test_parser(self) -> None:
        """
        Test arg parser for predefined args in the script.

        Mostly for coverage and to detect argument changes.
        """
        parser = imvcdededtd._parse()
        cmd = []
        cmd.extend(["--download_mode", "realtime"])
        cmd.extend(["--downloading_entity", "manual"])
        cmd.extend(["--action_tag", "downloaded_1min"])
        cmd.extend(["--vendor", "ccxt"])
        cmd.extend(["--start_timestamp", "20211110-101100"])
        cmd.extend(["--end_timestamp", "20211110-101200"])
        cmd.extend(["--exchange_id", "binance"])
        cmd.extend(["--contract_type", "spot"])
        cmd.extend(["--universe", "v3"])
        cmd.extend(["--db_stage", "dev"])
        cmd.extend(["--db_table", "ccxt_ohlcv_spot"])
        cmd.extend(["--aws_profile", "ck"])
        cmd.extend(["--data_type", "ohlcv"])
        cmd.extend(["--data_format", "postgres"])
        args = parser.parse_args(cmd)
        actual = vars(args)
        expected = {
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_1min",
            "vendor": "ccxt",
            "start_timestamp": "20211110-101100",
            "end_timestamp": "20211110-101200",
            "exchange_id": "binance",
            "contract_type": "spot",
            "universe": "v3",
            "universe_part": None,
            "db_stage": "dev",
            "db_table": "ccxt_ohlcv_spot",
            "log_level": "INFO",
            "aws_profile": "ck",
            "data_format": "postgres",
            "data_type": "ohlcv",
            "bid_ask_depth": 10,
            "s3_path": None,
            "dst_dir": None,
            "pq_save_mode": "append",
        }
        self.assertDictEqual(actual, expected)

    @pytest.mark.skip(
        "Cannot be run from the US due to 451 error API error. Run manually."
    )
    @umock.patch.object(imvcdeexut, "download_exchange_data_to_db")
    def test_main(self, mock_download_realtime: umock.MagicMock) -> None:
        """
        Smoke test to directly run `_main` function for coverage increase.
        """
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        kwargs = {
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_1min",
            "vendor": "ccxt",
            "start_timestamp": "20211110-101100",
            "end_timestamp": "20211110-101200",
            "exchange_id": "binance",
            "contract_type": "spot",
            "data_type": "ohlcv",
            "universe": "v3",
            "db_stage": "local",
            "db_table": "ccxt_ohlcv_spot",
            "log_level": "INFO",
            "aws_profile": "ck",
            "data_format": "postgres",
        }
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        # Run.
        imvcdededtd._main(mock_argument_parser)
        # Check call.
        self.assertEqual(len(mock_download_realtime.call_args), 2)
        self.assertEqual(mock_download_realtime.call_args.args[0], kwargs)
        self.assertEqual(
            type(mock_download_realtime.call_args.args[1]),
            imvcdexex.CcxtExtractor,
        )
