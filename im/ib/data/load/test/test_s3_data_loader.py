"""
Import as:

import im.ib.data.load.test.test_s3_data_loader as tsdloa
"""

import pandas as pd
import pytest

import helpers.unit_test as hut
import im.common.data.types as mcdtyp
import im.ib.data.load.ib_s3_data_loader as isdloa


@pytest.mark.skip(msg="See alphamatic/dev_tools#288")
class TestS3IbDataLoader1(hut.TestCase):
    """
    Test data loading correctness for Ib from S3.
    """

    def setUp(self) -> None:
        super().setUp()
        self._s3_data_loader = isdloa.IbS3DataLoader()

    def test_dtypes1(self) -> None:
        """
        Test column types of loaded dataframe.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Daily,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=1,
        )
        # Get columns types.
        types = data.dtypes.to_string()
        # Compare with expected.
        self.check_string(types, fuzzy_match=True)

    def test_read_data1(self) -> None:
        """
        Test correctness of minute ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Minutely,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hut.convert_df_to_string(data)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    def test_read_data2(self) -> None:
        """
        Test correctness of daily ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Daily,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=True,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hut.convert_df_to_string(data)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    def test_read_data3(self) -> None:
        """
        Test correctness of hourly ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Hourly,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hut.convert_df_to_string(data)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    def test_read_data_check_date_type(self) -> None:
        """
        Check date type of date field if frequency is daily.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Daily,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=True,
            nrows=10,
        )
        # Check if date columns is date type.
        self.assertIsInstance(data["date"][0], pd.Timestamp)

    def test_read_data_with_start_end_ts(self) -> None:
        """
        Test correctness of hourly ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=mcdtyp.AssetClass.Futures,
            frequency=mcdtyp.Frequency.Hourly,
            contract_type=mcdtyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            start_ts=pd.to_datetime("2021-03-04 22:00:00-05:00"),
            end_ts=pd.to_datetime("2021-03-05 05:00:00-05:00"),
        )
        # Transform dataframe to string.
        actual_string = hut.convert_df_to_string(data)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)
