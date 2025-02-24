import logging
import pytest
from typing import Any, Dict

import pandas as pd

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import im_v2.ig.data.client.ig_historical_pq_by_date_taq_bar_client as imvidcihpbdtbc

_LOG = logging.getLogger(__name__)


# TODO(gp): Use ImClientTestCase.
@pytest.mark.requires_aws 
@pytest.mark.requires_ck_infra
class TestIgHistoricalPqByDateTaqBarClient1(hunitest.TestCase):
    def read_data_helper(self, *args: Any, **kwargs: Dict[str, Any]) -> None:
        # Execute.
        vendor = "ig"
        resample_1min = False
        root_dir = "s3://cryptokaizen-unit-test/alphamatic-data/unit_test/ig_parquet"
        aws_profile = "ck"
        full_symbol_col_name = "igid"
        im_client = imvidcihpbdtbc.IgHistoricalPqByDateTaqBarClient(
            vendor, resample_1min, root_dir, aws_profile, full_symbol_col_name
        )
        actual = im_client.read_data(*args, **kwargs)
        # Check the output values.
        actual_string = hpandas.df_to_str(actual, print_shape_info=True, tag="df")
        _LOG.debug("actual_string=%s", actual_string)
        self.check_string(actual_string, fuzzy_match=True)

    @pytest.mark.requires_aws 
    @pytest.mark.requires_ck_infra
    def test_read_data1(self) -> None:
        """
        - Read data for one symbol
        - With normalization
        """
        full_symbols = ["17085"]
        start_ts = pd.Timestamp("2019-01-07 9:00:00-05:00")
        end_ts = pd.Timestamp("2019-01-07 16:00:00-05:00")
        columns = ["timestamp_db", "ticker", "igid", "close"]
        filter_data_mode = "assert"
        # Execute.
        self.read_data_helper(
            full_symbols,
            start_ts,
            end_ts,
            columns,
            filter_data_mode,
        )

    @pytest.mark.requires_aws 
    @pytest.mark.requires_ck_infra
    def test_read_data2(self) -> None:
        """
        - Read data for two symbols
        - With normalization
        """
        full_symbols = ["17085", "13684"]
        start_ts = pd.Timestamp("2019-01-07 9:00:00-05:00")
        end_ts = pd.Timestamp("2019-01-08 16:00:00-05:00")
        columns = ["timestamp_db", "ticker", "igid", "close", "open"]
        filter_data_mode = "assert"
        # Execute.
        self.read_data_helper(
            full_symbols,
            start_ts,
            end_ts,
            columns,
            filter_data_mode,
        )
