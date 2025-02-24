import os
from typing import List

import pandas as pd
import pytest

import helpers.hio as hio
import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hs3 as hs3
import im_v2.common.data.transform.convert_csv_to_pq as imvcdtcctp


class TestCsvToPq(hmoto.S3Mock_TestCase):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test2()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test2(self) -> None:
        self.set_up_test()
        # Initialize the mock s3 path of CSV and Parquet output.
        self.csv_dir_path = f"s3://{self.bucket_name}/csv_dir"
        self.pq_dir_path = f"s3://{self.bucket_name}/pq_dir"
        self.s3fs_ = hs3.get_s3fs(self.mock_aws_profile)

    def generate_example_csv_files(self) -> List[pd.DataFrame]:
        """
        Create CSV files in scratch directory.
        """
        d1 = {
            "timestamp": [1638646800000, 1638646860000, 1638646960000],
            "open": [49317.68, 49330.63, 49320.31],
            "high": [49346.95, 49400.98, 49500.75],
            "volume": [23.13681, 61.99752, 79.92761],
            "low": [49315.45, 49322.78, 49325.23],
            "close": [49330.63, 49325.23, 49328.23],
            "end_download_timestamp": [
                "2021-12-07 13:01:20.183463+00:00",
                "2021-12-07 13:01:20.183463+00:00",
                "2021-12-07 13:01:20.183463+00:00",
            ],
            "exchange_id": ["binance", "binance", "binance"],
            "currency_pair": ["BTC_USDT", "ETH_USDT", "BTC_USDT"],
            "year": [2021, 2021, 2021],
            "month": [12, 12, 12],
        }
        d2 = {
            "timestamp": [1638656800000, 1638676860000, 1638656960000],
            "open": [49318.68, 49331.63, 49321.31],
            "high": [49446.95, 49500.98, 49600.75],
            "volume": [24.13681, 62.99752, 80.92761],
            "low": [49325.45, 49323.78, 49326.23],
            "close": [49340.63, 49335.23, 49428.23],
            "end_download_timestamp": [
                "2021-12-07 13:01:20.183463+00:00",
                "2021-12-07 13:01:20.183463+00:00",
                "2021-12-07 13:01:20.183463+00:00",
            ],
            "exchange_id": ["binance", "binance", "binance"],
            "currency_pair": ["BTC_USDT", "ETH_USDT", "BTC_USDT"],
            "year": [2021, 2021, 2021],
            "month": [12, 12, 12],
        }
        df1 = pd.DataFrame(data=d1)
        df2 = pd.DataFrame(data=d2)
        return [df1, df2]

    def test_csv_to_pq_script1(self) -> None:
        """
        Convert single csv file from single dir to Parquet.
        """
        # Generate dummy csv.
        df, _ = self.generate_example_csv_files()
        # Save the input data to mock s3.
        file_path = os.path.join(self.csv_dir_path, "test1.csv")
        df.to_csv(file_path, index=False)
        # Run script with arg parser.
        self._run_csv_to_pq_script(
            self.csv_dir_path, self.pq_dir_path, aws_profile=self.s3fs_
        )
        self._test_csv_to_pq_script(df, aws_profile=self.s3fs_)

    def test_csv_to_pq_script2(self) -> None:
        """
        Convert multiple csv files from single dir to Parquet.
        """
        # Generate dummy csv.
        df1, df2 = self.generate_example_csv_files()
        # Save the input data to mock s3.
        file_path1 = os.path.join(self.csv_dir_path, "test1.csv")
        file_path2 = os.path.join(self.csv_dir_path, "test2.csv")
        df1.to_csv(file_path1, index=False)
        df2.to_csv(file_path2, index=False)
        df = pd.concat([df1, df2])
        # Run script with arg parser.
        self._run_csv_to_pq_script(
            self.csv_dir_path, self.pq_dir_path, aws_profile=self.s3fs_
        )
        self._test_csv_to_pq_script(df, aws_profile=self.s3fs_)

    def test_csv_to_pq_script3(self) -> None:
        """
        Convert single csv file from multiple dir to Parquet.
        """
        # Generate dummy csv.
        df_list = self.generate_example_csv_files()
        # Save the input data to mock s3.
        for i, df in enumerate(df_list):
            csv_dir_path = f"s3://{self.bucket_name}/csv_dir{i}"
            file_path = os.path.join(csv_dir_path, "test1.csv")
            df.to_csv(file_path, index=False)
            # Run script with arg parser.
            self._run_csv_to_pq_script(
                csv_dir_path, self.pq_dir_path, aws_profile=self.s3fs_
            )
        df = pd.concat(df_list)
        self._test_csv_to_pq_script(df, aws_profile=self.s3fs_)

    def test_csv_to_pq_script4(self) -> None:
        """
        Convert single csv file from single dir to Parquet in local filesystem.
        """
        self._create_local_scratch_space()
        # Generate dummy csv.
        df, _ = self.generate_example_csv_files()
        # Save the input data to mock s3.
        file_path = os.path.join(self.csv_dir_path, "test1.csv")
        df.to_csv(file_path, index=False)
        # Run script with arg parser.
        self._run_csv_to_pq_script(
            self.csv_dir_path, self.pq_dir_path, aws_profile=None
        )
        self._test_csv_to_pq_script(df, aws_profile=None)

    def test_csv_to_pq_script5(self) -> None:
        """
        Convert multiple csv files from single dir to Parquet in local filesystem.
        """
        self._create_local_scratch_space()
        # Generate dummy csv.
        df1, df2 = self.generate_example_csv_files()
        # Save the input data to mock s3.
        file_path1 = os.path.join(self.csv_dir_path, "test1.csv")
        file_path2 = os.path.join(self.csv_dir_path, "test2.csv")
        df1.to_csv(file_path1, index=False)
        df2.to_csv(file_path2, index=False)
        df = pd.concat([df1, df2])
        # Run script with arg parser.
        self._run_csv_to_pq_script(
            self.csv_dir_path, self.pq_dir_path, aws_profile=None
        )
        self._test_csv_to_pq_script(df, aws_profile=None)

    def test_csv_to_pq_script6(self) -> None:
        """
        Convert single csv file from multiple dir to Parquet in local filesystem.
        """
        self._create_local_scratch_space()
        # Generate dummy csv.
        df_list = self.generate_example_csv_files()
        # Save the input data to mock s3.
        for i, df in enumerate(df_list):
            csv_dir_path = f"{self.scratch_dir}/csv_dir{i}"
            hio.create_dir(csv_dir_path, incremental=False)
            file_path = os.path.join(csv_dir_path, "test1.csv")
            df.to_csv(file_path, index=False)
            # Run script with arg parser.
            self._run_csv_to_pq_script(
                csv_dir_path, self.pq_dir_path, aws_profile=None
            )
        df = pd.concat(df_list)
        self._test_csv_to_pq_script(df, aws_profile=None)

    def _create_local_scratch_space(self) -> None:
        """
        Create temprorary folder in local filesystem for csv and Parquet.
        """
        self.scratch_dir = self.get_scratch_space()
        self.csv_dir_path = os.path.join(self.scratch_dir, "csv_dir")
        hio.create_dir(self.csv_dir_path, incremental=False)
        self.pq_dir_path = os.path.join(self.scratch_dir, "pq_dir")
        hio.create_dir(self.pq_dir_path, incremental=False)

    def _test_csv_to_pq_script(
        self,
        df: pd.DataFrame,
        *,
        aws_profile: hs3.AwsProfile,
    ) -> None:
        """
        Load the saved Parquet data to verify the correctness.

        :param df: pandas dataframe from csv files which was converted
            to Parquet
        """
        # Load the saved data to verify.
        actual_df = hparque.from_parquet(
            self.pq_dir_path, aws_profile=aws_profile
        )
        actual_df = actual_df.reset_index(drop=True)
        # allign column and rows of actual df.
        actual_df = actual_df[df.columns]
        actual_df = actual_df.sort_values(by=["timestamp", "currency_pair"])
        actual_df = actual_df.reset_index(drop=True)
        # allign column and rows of expected df.
        df = df.sort_values(by=["timestamp", "currency_pair"])
        df = df.reset_index(drop=True)
        # convert df to string.
        actual = hpandas.df_to_str(actual_df)
        expected = hpandas.df_to_str(df)
        # Check results.
        self.assert_equal(expected, actual, fuzzy_match=True)

    def _run_csv_to_pq_script(
        self,
        csv_dir_path: str,
        pq_dir_path: str,
        *,
        aws_profile: hs3.AwsProfile,
    ) -> None:
        """
        Run cvs_to_pq script using argument parser.

        :param csv_dir_path: dir path where csv files are present
        :param pq_dir_path: dir path where pq files will be dumped
        """
        # Parse the command line.
        parser = imvcdtcctp._parse()
        args = parser.parse_args(
            [
                "--src_dir",
                f"{csv_dir_path}",
                "--dst_dir",
                f"{pq_dir_path}",
                "--datetime_col",
                "timestamp",
                "--asset_col",
                "currency_pair",
                "--aws_profile",
                "ck",
            ]
        )
        # Run the script.
        imvcdtcctp._run(args, aws_profile=aws_profile)
