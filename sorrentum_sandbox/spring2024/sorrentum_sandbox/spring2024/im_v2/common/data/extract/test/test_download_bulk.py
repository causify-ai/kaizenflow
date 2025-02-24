import argparse
import os
import unittest.mock as umock
from typing import List

import pandas as pd
import pytest

import data_schema.dataset_schema_utils as dsdascut
import helpers.hmoto as hmoto
import helpers.hs3 as hs3
import im_v2.common.data.extract.download_bulk as imvcdedobu
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.universe as ivcu


@pytest.mark.requires_ck_infra
@pytest.mark.requires_aws
@pytest.mark.skip(
    reason="Modify the test to not have an API call",
)
class TestDownloadBulk(hmoto.S3Mock_TestCase):
    @umock.patch.object(imvcdeexut.hdateti, "get_current_time")
    def call_download_bulk(
        self,
        vendor: str,
        data_type: str,
        expected_list: List[str],
        mock_get_current_time: umock.MagicMock,
    ) -> None:
        """
        Directly call function for increased coverage.
        """
        mock_get_current_time.return_value = pd.Timestamp(
            "2022-02-08 10:12:00.000000+00:00"
        )
        # Prepare inputs.
        kwargs = {
            "start_timestamp": "2021-12-31 23:00:00",
            "end_timestamp": "2021-12-31 23:01:00",
            "exchange_id": "binance",
            "vendor": vendor,
            "data_type": data_type,
            "download_mode": "periodic_daily",
            "downloading_entity": "manual",
            "action_tag": "downloaded_all",
            "contract_type": "spot",
            "aws_profile": self.mock_aws_profile,
            "s3_path": f"s3://{self.bucket_name}/",
            "data_format": "parquet",
            "assert_on_missing_data": True,
            "universe": "v1",
            "log_level": "INFO",
        }
        if vendor == "crypto_chassis":
            kwargs["universe_part"] = 1
        args = argparse.Namespace(**kwargs)
        with umock.patch.object(
            ivcu, "get_vendor_universe", return_value={"binance": ["BTC_USDT"]}
        ):
            imvcdedobu._run(args)

        # Prepare common `hs3.listdir` params.
        s3_bucket = f"s3://{self.bucket_name}"
        pattern = "*.parquet"
        only_files = True
        use_relative_paths = True
        # Check parquet files on s3.
        parquet_path_list = hs3.listdir(
            s3_bucket,
            pattern,
            only_files,
            use_relative_paths,
            aws_profile=self.mock_aws_profile,
        )
        parquet_path_list.sort()
        parquet_path_list = [
            # Remove uuid names.
            "/".join(path.split("/")[:-1])
            for path in parquet_path_list
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

    @pytest.mark.slow("12 seconds")
    def test1(
        self,
    ) -> None:
        expected_list = [
            "currency_pair=BTC_USDT/year=2021/month=12/day=31",
        ]
        self.call_download_bulk("ccxt", "trades", expected_list)

    @pytest.mark.slow("12 seconds")
    def test2(
        self,
    ) -> None:
        expected_list = [
            "currency_pair=BTC_USDT/year=2021/month=12",
        ]
        self.call_download_bulk("ccxt", "ohlcv", expected_list)

    @pytest.mark.slow("12 seconds")
    def test4(
        self,
    ) -> None:
        expected_list = [
            "currency_pair=BTC_USDT/year=2021/month=12/day=31",
        ]
        self.call_download_bulk("binance", "trades", expected_list)
