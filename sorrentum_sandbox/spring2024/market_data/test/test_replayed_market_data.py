import logging
from typing import Any, Callable, Tuple, Union

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import helpers.hwall_clock_time as hwacltim
import market_data.market_data_example as mdmadaex
import market_data.replayed_market_data as mdremada

_LOG = logging.getLogger(__name__)


# TODO(gp): Factor out this test in a ReplayedMarketData_TestCase
def _check_get_data(
    self_: Any,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
    func: Callable,
    expected_df_as_str: str,
) -> mdremada.ReplayedMarketData:
    """
    - Build `ReplayedTimePriceInterval`
    - Execute the function `get_data*` in `func`
    - Check actual output against expected.
    """
    with hasynci.solipsism_context() as event_loop:
        # Build ReplayedTimePriceInterval.
        start_datetime = pd.Timestamp("2000-01-01 09:30:00-05:00")
        end_datetime = pd.Timestamp("2000-01-01 10:29:00-05:00")
        asset_ids = [1000]
        (market_data, _,) = mdmadaex.get_ReplayedTimeMarketData_example2(
            event_loop,
            start_datetime,
            end_datetime,
            replayed_delay_in_mins_or_timestamp,
            asset_ids,
        )
        # Execute function under test.
        actual_df = func(market_data)
    # Check.
    actual_df = actual_df[sorted(actual_df.columns)]
    actual_df_as_str = hpandas.df_to_str(
        actual_df, print_shape_info=True, tag="df"
    )
    _LOG.info("-> %s", actual_df_as_str)
    self_.assert_equal(
        actual_df_as_str,
        expected_df_as_str,
        dedent=True,
        fuzzy_match=True,
    )
    return market_data


class TestReplayedMarketData1(hunitest.TestCase):
    def check_last_end_time(
        self,
        market_data: mdremada.ReplayedMarketData,
        expected_last_end_time: pd.Timestamp,
        expected_is_online: bool,
    ) -> None:
        """
        Check output of `get_last_end_time()` and `is_online()`.
        """
        #
        last_end_time = market_data.get_last_end_time()
        _LOG.info("-> last_end_time=%s", last_end_time)
        self.assertEqual(last_end_time, expected_last_end_time)
        #
        is_online = market_data.is_online()
        _LOG.info("-> is_online=%s", is_online)
        self.assertEqual(is_online, expected_is_online)

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_data1(self) -> None:
        """
        - Set the current time to 9:35
        - Get the last 5 mins of data
        - The returned data should be in [9:30, 9:35]
        """
        replayed_delay_in_mins_or_timestamp = 5
        #
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 09:35:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(5, 4)
                                   asset_id     last_price             start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000    999.874540   2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000    1000.325254  2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000    1000.557248  2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        2000-01-01 09:34:00-05:00      1000    1000.655907  2000-01-01 09:33:00-05:00 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00      1000    1000.311925  2000-01-01 09:34:00-05:00 2000-01-01 09:35:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:35:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data2(self) -> None:
        """
        - Set the current time to 9:35
        - Get the last 1 min of data
        - The returned data should be at 9:35
        """
        replayed_delay_in_mins_or_timestamp = 5
        #
        timedelta = pd.Timedelta("1T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:35:00-05:00, 2000-01-01 09:35:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(1, 4)
                                   asset_id   last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:35:00-05:00      1000  1000.311925 2000-01-01 09:34:00-05:00 2000-01-01 09:35:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:35:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data3(self) -> None:
        """
        - Set the current time to 9:50
        - Get the last 10 mins of data
        - The returned data should be in [9:40, 9:50]
        """
        replayed_delay_in_mins_or_timestamp = 20
        #
        timedelta = pd.Timedelta("10T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:41:00-05:00, 2000-01-01 09:50:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(10, 4)
                                   asset_id   last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:41:00-05:00      1000   999.721952 2000-01-01 09:40:00-05:00 2000-01-01 09:41:00-05:00
        2000-01-01 09:42:00-05:00      1000  1000.191862 2000-01-01 09:41:00-05:00 2000-01-01 09:42:00-05:00
        2000-01-01 09:43:00-05:00      1000  1000.524304 2000-01-01 09:42:00-05:00 2000-01-01 09:43:00-05:00
        ...
        2000-01-01 09:48:00-05:00      1000  999.430872 2000-01-01 09:47:00-05:00 2000-01-01 09:48:00-05:00
        2000-01-01 09:49:00-05:00      1000  999.362817 2000-01-01 09:48:00-05:00 2000-01-01 09:49:00-05:00
        2000-01-01 09:50:00-05:00      1000  999.154046 2000-01-01 09:49:00-05:00 2000-01-01 09:50:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:50:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data4(self) -> None:
        """
        - Set the current time to 10:00
        - Get data for the last day
        - The returned data should be in [9:30, 10:00]
        """
        replayed_delay_in_mins_or_timestamp = 30
        #
        timedelta = pd.Timedelta("1D")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 10:00:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(30, 4)
                                   asset_id   last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000   999.874540 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000  1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000  1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        ...
        2000-01-01 09:58:00-05:00      1000  998.519053 2000-01-01 09:57:00-05:00 2000-01-01 09:58:00-05:00
        2000-01-01 09:59:00-05:00      1000  998.611468 2000-01-01 09:58:00-05:00 2000-01-01 09:59:00-05:00
        2000-01-01 10:00:00-05:00      1000  998.157918 2000-01-01 09:59:00-05:00 2000-01-01 10:00:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 10:00:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data5(self) -> None:
        """
        - Set the current time to 10:00
        - Get all data using 365 days for specified period
        - The returned data should be in [9:30, 10:00]
        """
        replayed_delay_in_mins_or_timestamp = 30
        #
        timedelta = pd.Timedelta("365T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 10:00:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(30, 4)
                                   asset_id   last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000   999.874540 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000  1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000  1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        ...
        2000-01-01 09:58:00-05:00      1000  998.519053 2000-01-01 09:57:00-05:00 2000-01-01 09:58:00-05:00
        2000-01-01 09:59:00-05:00      1000  998.611468 2000-01-01 09:58:00-05:00 2000-01-01 09:59:00-05:00
        2000-01-01 10:00:00-05:00      1000  998.157918 2000-01-01 09:59:00-05:00 2000-01-01 10:00:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 10:00:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    # //////////////////////////////////////////////////////////////////////////////

    def test_get_data_for_minute_0(self) -> None:
        """
        The replayed time starts at the same time of the data to represent the
        first minute of trading.
        """
        replayed_delay_in_mins_or_timestamp = 0
        #
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # Check.
        expected_df_as_str = """
        # df=
        Empty DataFrame
        Columns: [asset_id, last_price, start_datetime, timestamp_db]
        Index: []"""
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = None
        expected_is_online = False
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data_for_minute_1(self) -> None:
        """
        The replayed time starts one minute after the data to represent the
        first minute of trading.
        """
        replayed_delay_in_mins_or_timestamp = 1
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 09:31:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(1, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000   999.87454 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:31:00-0500")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data_for_minute_3(self) -> None:
        """
        The replayed time starts 3 minutes after the opening of the trading
        day.
        """
        replayed_delay_in_mins_or_timestamp = 3
        #
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # Check.
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 09:33:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(3, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000    999.874540  2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000    1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000    1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:33:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data_for_minute_6(self) -> None:
        """
        The replayed time starts 6 minutes after the opening of the trading
        day.
        """
        replayed_delay_in_mins_or_timestamp = 6
        #
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # Check.
        # pylint: disable=line-too-long
        expected_df_as_str = """# df=
        index=[2000-01-01 09:32:00-05:00, 2000-01-01 09:36:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(5, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:32:00-05:00      1000    1000.325254  2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000    1000.557248  2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        2000-01-01 09:34:00-05:00      1000    1000.655907  2000-01-01 09:33:00-05:00 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00      1000    1000.311925  2000-01-01 09:34:00-05:00 2000-01-01 09:35:00-05:00
        2000-01-01 09:36:00-05:00      1000    999.967920   2000-01-01 09:35:00-05:00 2000-01-01 09:36:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 09:36:00-05:00")
        expected_is_online = True
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )

    def test_get_data_for_minute_63(self) -> None:
        """
        The replayed time starts 63 minutes after the opening of the trading
        day.
        """
        replayed_delay_in_mins_or_timestamp = 63
        #
        timedelta = pd.Timedelta("5T")
        func = lambda market_data: market_data.get_data_for_last_period(timedelta)
        # Check.
        # pylint: disable=line-too-long
        expected_df_as_str = """# df=
        index=[2000-01-01 10:29:00-05:00, 2000-01-01 10:30:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(2, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 10:29:00-05:00      1000   998.224716  2000-01-01 10:28:00-05:00 2000-01-01 10:29:00-05:00
        2000-01-01 10:30:00-05:00      1000   998.050046  2000-01-01 10:29:00-05:00 2000-01-01 10:30:00-05:00"""
        # pylint: enable=line-too-long
        market_data = _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )
        #
        expected_last_end_time = pd.Timestamp("2000-01-01 10:30:00-0500")
        expected_is_online = False
        self.check_last_end_time(
            market_data, expected_last_end_time, expected_is_online
        )


# #############################################################################


class TestReplayedMarketData2(hunitest.TestCase):

    # TODO(gp): Add same tests for the SQL version.
    def test_get_data_for_interval1(self) -> None:
        """
        - Start replaying time 5 minutes after the beginning of the day, i.e., the
          current time is 9:35.
        - Ask data for [9:30, 9:45]
        - The returned data is [9:30, 9:35]
        """
        # Start replaying time 5 minutes after the beginning of the day, so the
        # current time is 9:35.
        replayed_delay_in_mins_or_timestamp = 5
        # Ask data for 9:30 to 9:45.
        start_ts = pd.Timestamp("2000-01-01 09:30:00-05:00")
        end_ts = pd.Timestamp("2000-01-01 09:45:00-05:00")
        ts_col_name = "end_datetime"
        asset_ids = None
        func = lambda market_data: market_data.get_data_for_interval(
            start_ts, end_ts, ts_col_name, asset_ids
        )
        # pylint: disable=line-too-long
        expected_df_as_str = """
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 09:35:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(5, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000    999.874540  2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000    1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000    1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        2000-01-01 09:34:00-05:00      1000    1000.655907 2000-01-01 09:33:00-05:00 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00      1000    1000.311925 2000-01-01 09:34:00-05:00 2000-01-01 09:35:00-05:00"""
        # pylint: enable=line-too-long
        _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )

    def test_get_data_for_interval2(self) -> None:
        """
        - Current time is 9:45
        - Ask data in [9:35, 9:40]
        - The returned data is [9:30, 9:40]
        """
        replayed_delay_in_mins_or_timestamp = 15
        start_ts = pd.Timestamp("2000-01-01 09:35:00-05:00")
        end_ts = pd.Timestamp("2000-01-01 09:40:00-05:00")
        ts_col_name = "start_datetime"
        asset_ids = None
        func = lambda market_data: market_data.get_data_for_interval(
            start_ts, end_ts, ts_col_name, asset_ids
        )
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2000-01-01 09:36:00-05:00, 2000-01-01 09:40:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(5, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:36:00-05:00      1000   999.967920  2000-01-01 09:35:00-05:00 2000-01-01 09:36:00-05:00
        2000-01-01 09:37:00-05:00      1000   999.526004  2000-01-01 09:36:00-05:00 2000-01-01 09:37:00-05:00
        2000-01-01 09:38:00-05:00      1000   999.892180  2000-01-01 09:37:00-05:00 2000-01-01 09:38:00-05:00
        2000-01-01 09:39:00-05:00      1000   999.993295  2000-01-01 09:38:00-05:00 2000-01-01 09:39:00-05:00
        2000-01-01 09:40:00-05:00      1000   1000.201367 2000-01-01 09:39:00-05:00 2000-01-01 09:40:00-05:00"""
        # pylint: enable=line-too-long
        _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )

    def test_get_data_for_interval3(self) -> None:
        """
        - Current time is 9:35
        - Ask data in [9:00, 9:40)
        - The returned data is [9:30, 9:40)
        """
        replayed_delay_in_mins_or_timestamp = pd.Timestamp(
            "2000-01-01 09:35:00-05:00"
        )
        start_ts = pd.Timestamp("2000-01-01 09:30:00-05:00")
        end_ts = pd.Timestamp("2000-01-01 09:35:00-05:00")
        ts_col_name = "start_datetime"
        asset_ids = None
        func = lambda market_data: market_data.get_data_for_interval(
            start_ts, end_ts, ts_col_name, asset_ids
        )
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2000-01-01 09:31:00-05:00, 2000-01-01 09:35:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(5, 4)
                           asset_id   last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:31:00-05:00      1000   999.874540 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
        2000-01-01 09:32:00-05:00      1000  1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
        2000-01-01 09:33:00-05:00      1000  1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00
        2000-01-01 09:34:00-05:00      1000  1000.655907 2000-01-01 09:33:00-05:00 2000-01-01 09:34:00-05:00
        2000-01-01 09:35:00-05:00      1000  1000.311925 2000-01-01 09:34:00-05:00 2000-01-01 09:35:00-05:00
        """
        # pylint: enable=line-too-long
        _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )

    def test_get_data_at_timestamp1(self) -> None:
        """
        - Current time is 9:45
        - Ask data for 9:35
        - The returned data is for 9:35
        """
        replayed_delay_in_mins_or_timestamp = 15
        ts = pd.Timestamp("2000-01-01 09:35:00-05:00")
        ts_col_name = "start_datetime"
        asset_ids = None
        func = lambda market_data: market_data.get_data_at_timestamp(
            ts, ts_col_name, asset_ids
        )
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        index=[2000-01-01 09:36:00-05:00, 2000-01-01 09:36:00-05:00]
        columns=asset_id,last_price,start_datetime,timestamp_db
        shape=(1, 4)
                                   asset_id  last_price            start_datetime              timestamp_db
        end_datetime
        2000-01-01 09:36:00-05:00      1000   999.96792  2000-01-01 09:35:00-05:00 2000-01-01 09:36:00-05:00"""
        # pylint: enable=line-too-long
        _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )

    def test_get_data_at_timestamp2(self) -> None:
        """
        - Current time is 9:45
        - Ask data for 9:50
        - The return data is empty
        """
        replayed_delay_in_mins_or_timestamp = 15
        ts = pd.Timestamp("2000-01-01 09:50:00-05:00")
        ts_col_name = "start_datetime"
        asset_ids = None
        func = lambda market_data: market_data.get_data_at_timestamp(
            ts, ts_col_name, asset_ids
        )
        # pylint: disable=line-too-long
        expected_df_as_str = r"""
        # df=
        Empty DataFrame
        Columns: [asset_id, last_price, start_datetime, timestamp_db]
        Index: []"""
        # pylint: enable=line-too-long
        _check_get_data(
            self, replayed_delay_in_mins_or_timestamp, func, expected_df_as_str
        )


# #############################################################################


class TestReplayedMarketData3(hunitest.TestCase):
    """
    Test `ReplayedMarketData.is_last_bar_available()` using simulated time.
    """

    def test_get_last_end_time1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Build object.
            start_datetime = pd.Timestamp("2000-01-01 09:30:00-05:00")
            end_datetime = pd.Timestamp("2000-01-01 10:30:00-05:00")
            asset_ids = [1000]
            replayed_delay_in_mins_or_timestamp = 5
            delay_in_secs = 0
            (market_data, _,) = mdmadaex.get_ReplayedTimeMarketData_example2(
                event_loop,
                start_datetime,
                end_datetime,
                replayed_delay_in_mins_or_timestamp,
                asset_ids,
                delay_in_secs=delay_in_secs,
            )
            # Call method.
            last_end_time = market_data.get_last_end_time()
        # Check.
        _LOG.info("-> last_end_time=%s", last_end_time)
        self.assertEqual(last_end_time, pd.Timestamp("2000-01-01 09:35:00-05:00"))

    # #########################################################################

    def test_is_last_bar_available1(self) -> None:
        """
        Wait for the market to open.
        """
        replayed_delay_in_mins_or_timestamp = -2
        start_time, end_time, num_iter = self._run(
            replayed_delay_in_mins_or_timestamp
        )
        # Check.
        expected_start_time = pd.Timestamp("2000-01-01 09:28:00-05:00")
        self.assertEqual(start_time, expected_start_time)
        #
        expected_end_time = pd.Timestamp("2000-01-01 09:31:00-05:00")
        self.assertEqual(end_time, expected_end_time)
        #
        expected_num_iter = 6
        self.assertEqual(num_iter, expected_num_iter)

    def test_is_last_bar_available2(self) -> None:
        """
        The market is already opened.
        """
        replayed_delay_in_mins_or_timestamp = 5
        start_time, end_time, num_iter = self._run(
            replayed_delay_in_mins_or_timestamp
        )
        # Check.
        expected_start_time = pd.Timestamp("2000-01-01 09:35:00-05:00")
        self.assertEqual(start_time, expected_start_time)
        #
        expected_end_time = pd.Timestamp("2000-01-01 09:35:00-05:00")
        self.assertEqual(end_time, expected_end_time)
        #
        expected_num_iter = 0
        self.assertEqual(num_iter, expected_num_iter)

    def test_is_last_bar_available3(self) -> None:
        """
        The market is closed, so we expect a timeout.
        """
        replayed_delay_in_mins_or_timestamp = 63
        with self.assertRaises(TimeoutError):
            self._run(replayed_delay_in_mins_or_timestamp)

    def _run(
        self, replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp]
    ) -> Tuple[pd.Timestamp, pd.Timestamp, int]:
        """
        - Build a ReplayedMarketData
        - Run `is_last_bar_available()`
        """
        with hasynci.solipsism_context() as event_loop:
            # Build a ReplayedMarketData.
            start_datetime = pd.Timestamp("2000-01-01 09:30:00-05:00")
            end_datetime = pd.Timestamp("2000-01-01 10:30:00-05:00")
            asset_ids = [1000]
            delay_in_secs = 0
            sleep_in_secs = 30
            time_out_in_secs = 60 * 5
            (market_data, _,) = mdmadaex.get_ReplayedTimeMarketData_example2(
                event_loop,
                start_datetime,
                end_datetime,
                replayed_delay_in_mins_or_timestamp,
                asset_ids,
                delay_in_secs=delay_in_secs,
                sleep_in_secs=sleep_in_secs,
                time_out_in_secs=time_out_in_secs,
            )
            # Set the `current_bar_timestamp` that is needed inside
            # `wait_for_latest_data()`.
            current_timestamp = market_data.get_wall_clock_time()
            bar_duration_in_secs = 60 * 5
            hdateti.set_current_bar_timestamp(
                current_timestamp, bar_duration_in_secs
            )
            # Run the method.
            start_time, end_time, num_iter = hasynci.run(
                market_data.wait_for_latest_data(),
                event_loop=event_loop,
            )
        return start_time, end_time, num_iter


class TestReplayedMarketData4(hunitest.TestCase):
    """
    Test `ReplayedMarketData.is_last_bar_available()` using simulated time.
    """

    def test_is_last_bar_available1(self) -> None:
        """
        Wait for the market to open.
        """
        start_time, end_time, num_iter = self._run()
        # Check.
        expected_start_time = pd.Timestamp(
            "2000-01-03 09:31:00-05:00", tz="America/New_York"
        )
        self.assertEqual(start_time, expected_start_time)
        #
        expected_end_time = pd.Timestamp(
            "2000-01-03 09:31:30-05:00", tz="America/New_York"
        )
        self.assertEqual(end_time, expected_end_time)
        #
        expected_num_iter = 1
        self.assertEqual(num_iter, expected_num_iter)

    def _run(self) -> Tuple[pd.Timestamp, pd.Timestamp, int]:
        """
        - Build a ReplayedMarketData
        - Run `is_last_bar_available()`
        """
        with hasynci.solipsism_context() as event_loop:
            # Build a ReplayedMarketData.
            (market_data, _,) = mdmadaex.get_ReplayedTimeMarketData_example4(
                event_loop,
                # Replay data starting at `2000-01-03 09:32:00-05:00`.
                replayed_delay_in_mins_or_timestamp=1,
                start_datetime=pd.Timestamp(
                    "2000-01-03 09:31:00-05:00", tz="America/New_York"
                ),
                end_datetime=pd.Timestamp(
                    "2000-01-03 09:31:00-05:00", tz="America/New_York"
                ),
                asset_ids=[101, 202, 303],
            )
            # Set the `current_bar_timestamp` that is needed inside
            # `wait_for_latest_data()`.
            current_timestamp = market_data.get_wall_clock_time()
            bar_duration_in_secs = 60
            hdateti.set_current_bar_timestamp(
                current_timestamp, bar_duration_in_secs
            )
            # Run the method.
            start_time, end_time, num_iter = hasynci.run(
                market_data.wait_for_latest_data(),
                event_loop=event_loop,
            )
        return start_time, end_time, num_iter
