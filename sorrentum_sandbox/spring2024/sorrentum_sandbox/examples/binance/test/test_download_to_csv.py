import argparse
import unittest.mock as umock
from typing import Any, List

import pandas as pd

import helpers.hunit_test as hunitest
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.examples.binance.download_to_csv as ssesbdtcs


def _fake_binance_response() -> List[List[Any]]:
    """
    Build fake records as a Binance response.
    """
    return [
        [
            # Open time.
            1499040000000,
            # Open.
            "0.01634790",
            # High.
            "0.80000000",
            # Low.
            "0.01575800",
            # Close.
            "0.01577100",
            # Volume.
            "148976.11427815",
            # Close time.
            1499644799999,
            # Quote asset volume.
            "2434.19055334",
            # Number of trades.
            308,
            # Taker buy base asset volume.
            "1756.87402397",
            # Taker buy quote asset volume.
            "28.46694368",
            # Ignore.
            "17928899.62484339",
        ]
        for _ in range(100)
    ]


class TestDownloadToCsv(hunitest.TestCase):
    def test_parser(self) -> None:
        """
        Test arg parser for predefined args in the script.
        """
        parser = ssesbdtcs._parse()
        cmd = []
        cmd.extend(["--start_timestamp", "2022-10-20 10:00:00-04:00"])
        cmd.extend(["--end_timestamp", "2022-10-21 15:30:00-04:00"])
        cmd.extend(["--target_dir", "binance_data"])
        args = parser.parse_args(cmd)
        actual = vars(args)
        expected = {
            "start_timestamp": "2022-10-20 10:00:00-04:00",
            "end_timestamp": "2022-10-21 15:30:00-04:00",
            "target_dir": "binance_data",
            "use_global_api": False,
            "log_level": "INFO",
        }
        self.assertDictEqual(actual, expected)

    @umock.patch.object(ssesbdtcs.CsvDataFrameSaver, "save")
    def test_main(self, mock_save) -> None:
        """
        Test that calling the script returns the expected data.
        """
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        kwargs = {
            "start_timestamp": "2022-10-20 10:00:00-04:00",
            "end_timestamp": "2022-10-20 11:00:00-04:00",
            "target_dir": "binance_data",
            "use_global_api": False,
            "log_level": "INFO",
        }
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        # Run.
        mock_downloaded_data = ssacodow.RawData(
            pd.DataFrame(_fake_binance_response())
        )
        with umock.patch.object(
            ssesbdtcs.ssesbido.OhlcvRestApiDownloader,
            "download",
            return_value=mock_downloaded_data,
        ) as mock_download:
            ssesbdtcs._main(mock_argument_parser)
            # Check the output.
            mock_download.assert_called_with(
                pd.Timestamp(kwargs["start_timestamp"]),
                pd.Timestamp(kwargs["end_timestamp"]),
            )
            mock_save.assert_called_with(mock_downloaded_data)
