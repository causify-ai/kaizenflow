"""
Import as:

import im.ib.data.load.test.test_s3_data_loader as tsdloa
"""
import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import im.common.data.types as imcodatyp
import im.ib.data.load.ib_s3_data_loader as iidlisdlo


@pytest.mark.requires_aws
@pytest.mark.requires_ck_infra
class TestS3IbDataLoader1(hunitest.TestCase):
    """
    Test data loading correctness for Ib from S3.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield

    def set_up_test(self) -> None:
        self._s3_data_loader = iidlisdlo.IbS3DataLoader()

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_dtypes1(self) -> None:
        """
        Test column types of loaded dataframe.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Daily,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=1,
        )
        # Get columns types.
        types = data.dtypes.to_string()
        # Compare with expected.
        self.check_string(types, fuzzy_match=True)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_read_data1(self) -> None:
        """
        Test correctness of minute ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Minutely,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hpandas.df_to_str(data, num_rows=None)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_read_data2(self) -> None:
        """
        Test correctness of daily ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Daily,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=True,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hpandas.df_to_str(data, num_rows=None)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_read_data3(self) -> None:
        """
        Test correctness of hourly ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Hourly,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            nrows=10,
        )
        # Transform dataframe to string.
        actual_string = hpandas.df_to_str(data, num_rows=None)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_read_data_check_date_type(self) -> None:
        """
        Check date type of date field if frequency is daily.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Daily,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=True,
            nrows=10,
        )
        # Check if date columns is date type.
        self.assertIsInstance(data["date"][0], pd.Timestamp)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_read_data_with_start_end_ts(self) -> None:
        """
        Test correctness of hourly ES data loading.
        """
        # Load data.
        data = self._s3_data_loader.read_data(
            exchange="GLOBEX",
            symbol="ES",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Hourly,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            unadjusted=None,
            start_ts=pd.to_datetime("2021-03-04 22:00:00-05:00"),
            end_ts=pd.to_datetime("2021-03-05 05:00:00-05:00"),
        )
        # Transform dataframe to string.
        actual_string = hpandas.df_to_str(data, num_rows=None)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)
