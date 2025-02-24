import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import im.common.data.types as imcodatyp
import im.kibot.data.load.kibot_s3_data_loader as ikdlksdlo


@pytest.mark.requires_aws
@pytest.mark.requires_ck_infra
@pytest.mark.skip(reason="Kibot Equity Reader not in use ref. #5582.")
class TestKibotS3DataLoader(hunitest.TestCase):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield

    def set_up_test(self) -> None:
        self._s3_data_loader = ikdlksdlo.KibotS3DataLoader()

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        df = self._s3_data_loader._read_data(
            symbol="XG",
            aws_profile="am",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Daily,
            contract_type=imcodatyp.ContractType.Continuous,
        )
        self.check_string(df.head(10).to_string())

    @pytest.mark.skip(reason="Not implemented yet")
    def test_read_data_with_start_end_ts(self) -> None:
        """
        Test correctness of hourly ES data loading.
        """
        # Load data.
        data = self._s3_data_loader._read_data(
            symbol="XG",
            asset_class=imcodatyp.AssetClass.Futures,
            frequency=imcodatyp.Frequency.Daily,
            contract_type=imcodatyp.ContractType.Continuous,
            start_ts=pd.to_datetime("1990-12-28 00:00:00"),
            end_ts=pd.to_datetime("1991-01-14 00:00:00"),
        )
        data.insert(0, "date", data.index)
        # Transform dataframe to string.
        actual_string = hpandas.df_to_str(data, num_rows=None)
        # Compare with expected.
        self.check_string(actual_string, fuzzy_match=True)
