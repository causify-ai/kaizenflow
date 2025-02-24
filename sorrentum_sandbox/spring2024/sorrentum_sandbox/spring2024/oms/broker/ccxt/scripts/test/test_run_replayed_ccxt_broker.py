import argparse
import os
import unittest.mock as umock
from typing import Dict

import pytest

import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import oms.broker.ccxt.scripts.run_replayed_ccxt_broker as obcsrrcbr


class TestRunReplayedCcxtBroker1(hunitest.TestCase):
    """
    Replay the entire CCXT broker experiment with the help of
    `ReplayedCcxtExchange` and `ReplayedDataReadersystem`.
    """

    def get_test_data_dir(self) -> Dict:
        """
        Downloading test data in a scratch dir.
        """
        # Download test data from s3 to local .
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        s3_log_dir = os.path.join(s3_input_dir, "test_log")
        scratch_dir = self.get_scratch_space()
        aws_profile = "ck"
        hs3.copy_data_from_s3_to_local_dir(s3_log_dir, scratch_dir, aws_profile)
        return scratch_dir

    @pytest.mark.slow("11 seconds.")
    def test1(
        self,
    ) -> None:
        """
        Check proper replay of log data in sequential order same as the actual
        experiment.
        """
        # Prepare inputs.
        log_data_dir = self.get_test_data_dir()
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Assign args to call the function.
        scratch_dir = self.get_scratch_space()
        log_dir = os.path.join(scratch_dir, "mock", "test_log")
        kwargs = {
            "log_dir": log_dir,
            "universe": "v7.4",
            "secret_id": 4,
            "replayed_dir": log_data_dir,
            "log_level": "DEBUG",
        }
        mock_parse = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = mock_parse
        obcsrrcbr._main(mock_argument_parser)
