import argparse
import os
from typing import Any, Dict, Tuple

import pytest

import helpers.hgit as hgit
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import im_v2.common.data.transform.transform_pq_by_date_to_by_asset as imvcdttpbdtba
import im_v2.common.test as imvct


@pytest.mark.skip(
    reason="TODO(gp): Need to update this tests after transform v1.3."
    "See CmampTask7538 for details."
)
class TestPqByDateToByAsset1(hunitest.TestCase):
    def generate_test_data(self, verbose: bool) -> Tuple[str, str]:
        """
        Generate test data in form of daily Parquet files.
        """
        start_date = "2021-12-30"
        end_date = "2022-01-01"
        assets = ["A", "B", "C"]
        asset_col_name = "ticker"
        test_dir = self.get_scratch_space()
        by_date_dir = os.path.join(test_dir, "by_date")
        kwargs = {}
        if verbose:
            kwargs["output_type"] = "verbose_open"
            kwargs["reset_index"] = True
        imvct.generate_parquet_files(
            start_date, end_date, assets, asset_col_name, by_date_dir, **kwargs
        )
        return test_dir, by_date_dir

    def check_directory_structure_with_file_contents(
        self, by_date_dir: str, by_asset_dir: str
    ) -> None:
        """
        Generate directory and file structure together with file contents in
        form of string. String is compared with previously generated .txt file
        for any differences.

        :param by_date_dir: daily PQ files before conversion
        :param by_asset_dir: daily PQ files after conversion in by asset
            format
        """
        include_file_content = True
        by_date_signature = hunitest.get_dir_signature(
            by_date_dir, include_file_content
        )
        actual = []
        actual.append("# by_date=")
        actual.append(by_date_signature)
        by_asset_signature = hunitest.get_dir_signature(
            by_asset_dir, include_file_content
        )
        actual.append("# by_asset=")
        actual.append(by_asset_signature)
        actual = "\n".join(actual)
        self.check_string(actual, purify_text=True)

    def test_command_line(self) -> None:
        """
        Test command line with specific arguments and comparing its output with
        predefined directory structure and file contents.

        Command is run against test data that was generated in verbose
        mode meaning it is more realistic than generic data that is
        generated in non-verbose mode.
        """
        verbose = True
        self._test_command_line(verbose)

    def test_function_call1(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments and comparing function output with predefined directory
        structure and file contents.

        Function is run against simple test data in non-verbose mode.
        """
        verbose = False
        self._test_function_call(verbose)

    def test_function_call2(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments and comparing function output with predefined directory
        structure and file contents.

        Function is run against test data that was generated in verbose
        mode meaning it is more realistic than generic data that is
        generated in non-verbose mode.
        """
        verbose = True
        self._test_function_call(verbose)

    def test_process_chunk(self) -> None:
        """
        Test function that is used for parallel execution which is generating
        outputs depending on how many files/data is provided with.

        Test data for the function is generated in verbose mode.
        """
        verbose = True
        self._test_joblib_task(verbose, {})

    def _test_command_line(self, verbose: bool) -> None:
        """
        Generate daily data for 3 days in a by-date format and then convert it
        to by-asset.
        """
        test_dir, by_date_dir = self.generate_test_data(verbose)
        # Build command line to convert the data.
        cmd = []
        file_path = os.path.join(
            hgit.get_amp_abs_path(),
            "im_v2/common/data/transform/transform_pq_by_date_to_by_asset.py",
        )
        cmd.append(file_path)
        cmd.append(f"--src_dir {by_date_dir}")
        by_asset_dir = os.path.join(test_dir, "by_asset")
        cmd.append(f"--dst_dir {by_asset_dir}")
        cmd.append("--num_threads 1")
        if verbose:
            cmd.append("--asset_col_name ticker")
        cmd = " ".join(cmd)
        hsystem.system(cmd)
        self.check_directory_structure_with_file_contents(
            by_date_dir, by_asset_dir
        )

    def _test_function_call(self, verbose: bool) -> None:
        """
        Tests directly _run function for coverage increase.

        Flow is same as in _test_daily_data.
        """
        # Prepare inputs.
        test_dir, by_date_dir = self.generate_test_data(verbose)
        by_asset_dir = os.path.join(test_dir, "by_asset")
        kwargs = {
            "src_dir": by_date_dir,
            "dst_dir": by_asset_dir,
            "asset_col_name": "asset",
            # parallelization args
            "num_threads": "1",
            "dry_run": True,
            "no_incremental": True,
            "skip_on_error": True,
            "num_attempts": 1,
        }
        if verbose:
            kwargs.update({"asset_col_name": "ticker"})
        # Run.
        args = argparse.Namespace(**kwargs)
        imvcdttpbdtba._run(args)
        # Check output.
        self.check_directory_structure_with_file_contents(
            by_date_dir, by_asset_dir
        )

    def _test_joblib_task(
        self, verbose: bool, config_update: Dict[str, Any]
    ) -> None:
        """
        Tests directly _save_chunk function that is used as joblib task.

        Because it is run as a separate process it is not caught by
        coverage.
        """
        # Prepare inputs.
        test_dir, by_date_dir = self.generate_test_data(verbose)
        by_asset_dir = os.path.join(test_dir, "by_asset")
        config = {
            "dst_dir": by_asset_dir,
            "parquet_file_names": [
                f"{test_dir}/by_date/date=20211230/data.parquet",
                f"{test_dir}/by_date/date=20211231/data.parquet",
                f"{test_dir}/by_date/date=20220101/data.parquet",
            ],
            "asset_col_name": "asset",
        }
        if verbose:
            config.update({"asset_col_name": "ticker"})
        if config_update:
            config.update(config_update)
        # Run.
        imvcdttpbdtba._process_chunk(**config)
        # Check output.
        self.check_directory_structure_with_file_contents(
            by_date_dir, by_asset_dir
        )
