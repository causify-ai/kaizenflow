import datetime
import logging
import os
from typing import Any

import pandas as pd
import pytest

import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.htimer as htimer
import helpers.hunit_test as hunitest
import im_v2.ig.data.client.historical_bars as imvidchiba
import im_v2.ig.ig_utils as imvigigut

_LOG = logging.getLogger(__name__)

_ROOT_DATA_DIR = "s3://cryptokaizen-unit-test/alphamatic-data/unit_test/ig_parquet"
_AWS_PROFILE = "ck"

# Start date for mock data.
_IG_START_DATE = "2019-01-07"

# This data was generated with
# //lime/notebooks/vendors_lime/taq_bars/notebooks/LimeTask1_explore_IG_price_data.ipynb
#
# > aws s3 ls --profile am s3://alphamatic-data/unit_test/ig_parquet/
#                           PRE 20190107/
#                           PRE 20190108/


@pytest.mark.requires_aws
@pytest.mark.requires_ck_infra
class TestTaqBarsUtils1(hunitest.TestCase):

    def test_get_available_dates1(self) -> None:
        dates = imvidchiba.get_available_dates(_ROOT_DATA_DIR, _AWS_PROFILE)
        _LOG.debug("len(dates)=%s", len(dates))
        _LOG.debug("dates[:3]=%s", str(dates[:3]))
        # Perform some sanity checks.
        self.assertGreater(len(dates), 0)
        self.assertEqual(sorted(dates), dates)
        self.assertEqual(str(dates[0]), _IG_START_DATE)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_filter_dates1(self) -> None:
        start_date = "2019-01-07"
        end_date = "2019-01-08"
        dates = imvidchiba.get_available_dates(_ROOT_DATA_DIR, _AWS_PROFILE)
        filtered_dates = imvigigut.filter_dates(start_date, end_date, dates)
        # Check.
        self.assertEqual(sorted(filtered_dates), filtered_dates)
        self.assertEqual(str(min(filtered_dates)), start_date)
        self.assertEqual(str(max(filtered_dates)), end_date)
        self.assertEqual(len(filtered_dates), 2)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_filter_dates2(self) -> None:
        """
        Filter with [None, 2019-01-08].
        """
        start_date = None
        end_date = "2019-01-07"
        dates = imvidchiba.get_available_dates(_ROOT_DATA_DIR, _AWS_PROFILE)
        filtered_dates = imvigigut.filter_dates(start_date, end_date, dates)
        # Check.
        self.assertEqual(sorted(filtered_dates), filtered_dates)
        self.assertEqual(str(min(filtered_dates)), _IG_START_DATE)
        self.assertEqual(str(max(filtered_dates)), end_date)
        self.assertEqual(len(filtered_dates), 1)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_filter_dates3(self) -> None:
        """
        Filter with [_IG_START_DATE, None].
        """
        start_date = _IG_START_DATE
        end_date = None
        dates = imvidchiba.get_available_dates(_ROOT_DATA_DIR, _AWS_PROFILE)
        filtered_dates = imvigigut.filter_dates(start_date, end_date, dates)
        # Check.
        self.assertEqual(sorted(filtered_dates), filtered_dates)
        self.assertEqual(str(min(filtered_dates)), _IG_START_DATE)
        self.assertGreater(str(max(filtered_dates)), "2019-01-07")
        self.assertGreater(len(filtered_dates), 1)

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test_filter_dates4(self) -> None:
        """
        Check that filtering with [None, None] corresponds to no filtering.
        """
        start_date = None
        end_date = None
        dates = imvidchiba.get_available_dates(_ROOT_DATA_DIR, _AWS_PROFILE)
        filtered_dates = imvigigut.filter_dates(start_date, end_date, dates)
        # Check.
        self.assertEqual(sorted(filtered_dates), filtered_dates)
        self.assertEqual(filtered_dates, dates)


# #############################################################################

@pytest.mark.requires_ck_infra
class TestGetBarData1(hunitest.TestCase):
    def get_bar_data_helper(self, *args: Any, **kwargs: Any) -> None:
        df = imvidchiba.get_bar_data_for_dates(*args, **kwargs)
        asset_ids = args[0]
        asset_id_name = args[1]
        #
        act = []

        def _add_stats():
            df_as_str = hpandas.df_to_str(df)
            act_tmp = "## df_as_str=\n%s" % df_as_str
            _LOG.debug("%s", act_tmp)
            act.append(act_tmp)
            #
            stats = imvidchiba.compute_bar_data_stats(
                df, asset_ids, asset_id_name
            )
            act_tmp = "## stats=\n%s" % stats
            _LOG.debug("%s", act_tmp)
            act.append(act_tmp)

        #
        act.append("# With nans")
        _add_stats()
        # Drop nans.
        df = df.dropna()
        act.append("# Without nans")
        _add_stats()
        #
        act_result = "\n".join(act)
        self.check_string(act_result, fuzzy_match=True)
        return df

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        """
        Get data for one day and multiple assets.
        """
        # SPY: 10971
        # AAPL: 17085
        # BAC: 15224
        asset_ids = [10971, 17085, 15224]
        asset_id_name = "igid"
        dates = ["2019-01-07"]
        dates = list(map(imvigigut.convert_to_date, dates))
        columns = ["end_time", "close", "volume", "igid"]
        normalize = True
        tz_zone = "America/New_York"
        abort_on_error = True
        root_data_dir = _ROOT_DATA_DIR
        aws_profile = _AWS_PROFILE
        num_concurrent_requests = 10
        self.get_bar_data_helper(
            asset_ids,
            asset_id_name,
            dates,
            columns,
            normalize,
            tz_zone,
            abort_on_error,
            root_data_dir,
            aws_profile,
            num_concurrent_requests,
        )

    @pytest.mark.requires_aws
    @pytest.mark.requires_ck_infra
    def test2(self) -> None:
        """
        Get multiple days and check the format.
        """
        asset_ids = [17085, 15224]
        asset_id_name = "igid"
        dates = ["2019-01-07", "2019-01-08"]
        dates = list(map(imvigigut.convert_to_date, dates))
        columns = ["end_time", "close", "volume", "igid"]
        normalize = True
        tz_zone = "America/New_York"
        abort_on_error = True
        root_data_dir = _ROOT_DATA_DIR
        aws_profile = _AWS_PROFILE
        num_concurrent_requests = 10
        self.get_bar_data_helper(
            asset_ids,
            asset_id_name,
            dates,
            columns,
            normalize,
            tz_zone,
            abort_on_error,
            root_data_dir,
            aws_profile,
            num_concurrent_requests,
        )


# #############################################################################


@pytest.mark.requires_aws
@pytest.mark.requires_ck_infra
class Test_get_cached_bar_data_for_date_interval1(hunitest.TestCase):
    def test_tsla1(self) -> None:
        """
        Get the data the day before TSLA IPO: there should be no data.
        """
        asset_ids = [13684]
        asset_id_name = "igid"
        start_date = datetime.date(2019, 1, 7)
        end_date = datetime.date(2019, 1, 8)
        columns = ["end_time", "close", "volume", "igid"]
        root_data_dir = _ROOT_DATA_DIR
        aws_profile = _AWS_PROFILE
        df = imvidchiba.get_cached_bar_data_for_date_interval(
            asset_ids,
            asset_id_name,
            start_date,
            end_date,
            columns,
            root_data_dir,
            aws_profile,
        )
        stats_as_str = imvidchiba.compute_bar_data_stats(
            df, asset_ids, asset_id_name
        )
        _LOG.debug("stats_as_str=%s", stats_as_str)
        self.check_string(stats_as_str)


# #############################################################################


class Test_get_cached_bar_data_for_date_interval_perf1(hunitest.TestCase):
    @pytest.mark.slow("Takes around 1 minute")
    def test1(self) -> None:
        """
        Get data for multiple assets and multiple days.
        """
        use_reference = True
        if use_reference:
            asset_ids = [10971, 17085, 15224]
            start_date = datetime.date(2019, 1, 7)
            end_date = datetime.date(2019, 1, 8)
        else:
            asset_ids = [13684]
            start_date = datetime.date(2019, 1, 7)
            end_date = datetime.date(2019, 1, 7)
        asset_id_name = "igid"
        columns = ["end_time", "close", "volume", "igid"]
        root_data_dir = _ROOT_DATA_DIR
        aws_profile = _AWS_PROFILE
        # num_concurrent_requests = 1
        num_concurrent_requests = 10
        # num_concurrent_requests = 20
        with htimer.TimedScope(logging.INFO, "Run"):
            df = imvidchiba.get_cached_bar_data_for_date_interval(
                asset_ids,
                asset_id_name,
                start_date,
                end_date,
                columns,
                root_data_dir,
                aws_profile,
                num_concurrent_requests=num_concurrent_requests,
            )
        if use_reference:
            self.check_string(
                hpandas.df_to_str(df, num_rows=None)
            )  # , use_gzip=True)

    @pytest.mark.slow("Takes around 1 minute")
    def test2(self) -> None:
        """
        Get data for one assets and multiple days.
        """
        use_reference = True
        asset_ids = [13684]
        asset_id_name = "igid"
        if use_reference:
            start_date = datetime.date(2019, 1, 7)
            end_date = datetime.date(2019, 1, 8)
        else:
            start_date = datetime.date(2019, 1, 7)
            end_date = datetime.date(2019, 1, 7)
        columns = ["end_time", "close", "volume", "igid"]
        root_data_dir = _ROOT_DATA_DIR
        aws_profile = _AWS_PROFILE
        # num_concurrent_requests = 1
        num_concurrent_requests = 10
        # num_concurrent_requests = 20
        with htimer.TimedScope(logging.INFO, "Run"):
            df = imvidchiba.get_cached_bar_data_for_date_interval(
                asset_ids,
                asset_id_name,
                start_date,
                end_date,
                columns,
                root_data_dir,
                aws_profile,
                num_concurrent_requests=num_concurrent_requests,
            )
        if use_reference:
            self.check_string(
                hpandas.df_to_str(df, num_rows=None)
            )  # , use_gzip=True)


# #############################################################################


class TestTaqBarsUtils2(hunitest.TestCase):
    @pytest.mark.skip(reason="This is used to generate the frozen input")
    def test_generate_raw_ig_data(self) -> None:
        """
        Generate the frozen input data.
        """
        # Get the data.
        ig_date = "20190107"
        asset_ids = 17085
        columns = ["end_time", "close"]
        with htimer.TimedScope(logging.INFO, "Read S3 data"):
            df_taq_bars = imvidchiba.get_raw_historical_data(
                ig_date, asset_ids=[asset_ids], columns=columns
            )
        # Subset.
        df_taq_bars = hpandas.subset_df(df_taq_bars, nrows=200, seed=43)
        # Save the data.
        file_name = self._get_test_data_file_name()
        hio.create_enclosing_dir(file_name, incremental=True)
        df_taq_bars.to_csv(file_name)
        _LOG.info("Saved data to '%s'", file_name)
        # Read back and compare to make sure it works.
        df_taq_bars2 = self._get_frozen_input()
        self.assert_equal(str(df_taq_bars), str(df_taq_bars2))
        hunitest.compare_df(df_taq_bars, df_taq_bars2)

    def test_convert_string_to_timestamp1(self) -> None:
        df = self._get_frozen_input()
        _LOG.debug("df=\n%s", str(df))
        # Transform.
        in_col_name = "end_time"
        out_col_name = "end_time"
        tz_zone = "America/New_York"
        df2 = imvidchiba._convert_string_to_timestamp(
            df, in_col_name, out_col_name, tz_zone
        )
        _LOG.debug("df2=\n%s", str(df2))
        # Check.
        act = hpandas.df_to_str(df, num_rows=None)
        self.check_string(act)

    def test_process_bar_data1(self) -> None:
        df = self._get_frozen_input()
        _LOG.debug("df=\n%s", str(df))
        # Transform.
        tz_zone = "America/New_York"
        df2 = imvidchiba.normalize_bar_data(df, tz_zone)
        _LOG.debug("df2=\n%s", str(df2))
        # Check.
        act = hpandas.df_to_str(df, num_rows=None)
        self.check_string(act)

    def _get_test_data_file_name(self) -> str:
        """
        Return the name of the file containing the data for testing this class.
        """
        dir_name = self.get_input_dir(use_only_test_class=True)
        file_name = os.path.join(dir_name, "data.csv")
        _LOG.debug("file_name=%s", file_name)
        return file_name

    def _get_frozen_input(self) -> pd.DataFrame:
        """
        Get the frozen input data.
        """
        file_name = self._get_test_data_file_name()
        df = pd.read_csv(file_name, index_col=0, parse_dates=True)
        return df


# #############################################################################


# TODO(gp): Add unit test for all the functions.
