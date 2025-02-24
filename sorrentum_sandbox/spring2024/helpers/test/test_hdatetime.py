import datetime
import logging

import pandas as pd
import pytz

import helpers.hdatetime as hdateti
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################

_STR_TS_NAIVE = "2021-01-04 09:30:00"
_STR_TS_UTC = "2021-01-04 09:30:00-00:00"
_STR_TS_ET = "2021-01-04 09:30:00-05:00"

_PD_TS_NAIVE = pd.Timestamp("2021-01-04 09:30:00")
_PD_TS_UTC = pd.Timestamp("2021-01-04 09:30:00-00:00", tz="UTC")
_PD_TS_ET = pd.Timestamp("2021-01-04 09:30:00-05:00", tz="America/New_York")

_DT_DT_NAIVE = datetime.datetime(2021, 1, 4, 9, 30, 0)
_DT_DT_UTC = pytz.timezone("UTC").localize(_DT_DT_NAIVE)
_DT_DT_ET = pytz.timezone("America/New_York").localize(_DT_DT_NAIVE)


# #############################################################################
# Test_dassert_is_datetime1
# #############################################################################


class Test_dassert_is_datetime1(hunitest.TestCase):
    def test_is_datetime1(self) -> None:
        """
        Test valid datetime objects.
        """
        objs = [
            _STR_TS_NAIVE,
            _STR_TS_UTC,
            _STR_TS_ET,
            _PD_TS_NAIVE,
            _PD_TS_UTC,
            _PD_TS_ET,
            _DT_DT_NAIVE,
            _DT_DT_UTC,
            _DT_DT_ET,
        ]
        for obj in objs:
            _LOG.debug("obj='%s', type='%s'", str(obj), str(type(obj)))
            hdateti.dassert_is_datetime(obj)

    def test_is_datetime_fail1(self) -> None:
        """
        Test invalid datetime objects.
        """
        objs = [0, 0.0]
        for obj in objs:
            _LOG.debug("obj='%s', type='%s'", str(obj), str(type(obj)))
            with self.assertRaises(AssertionError):
                hdateti.dassert_is_datetime(obj)

    def test_is_strict_datetime1(self) -> None:
        """
        Test valid datetime objects.
        """
        objs = [
            _PD_TS_NAIVE,
            _PD_TS_UTC,
            _PD_TS_ET,
            _DT_DT_NAIVE,
            _DT_DT_UTC,
            _DT_DT_ET,
        ]
        for obj in objs:
            _LOG.debug("obj='%s', type='%s'", str(obj), str(type(obj)))
            hdateti.dassert_is_strict_datetime(obj)

    def test_is_strict_datetime_fail1(self) -> None:
        """
        Test invalid datetime objects.
        """
        objs = [0, _STR_TS_NAIVE, _STR_TS_UTC, _STR_TS_ET, "hello"]
        for obj in objs:
            _LOG.debug("obj='%s', type='%s'", str(obj), str(type(obj)))
            with self.assertRaises(AssertionError):
                hdateti.dassert_is_strict_datetime(obj)


# #############################################################################
# Test_dassert_tz1
# #############################################################################


class Test_dassert_tz1(hunitest.TestCase):
    def test_datetime_conversions(self) -> None:
        # Get a tz-naive datetime.
        dt = datetime.datetime(2020, 1, 5, 9, 30, 0)
        hdateti.dassert_is_tz_naive(dt)
        # Localize it to UTC.
        dt_utc = pytz.timezone("UTC").localize(dt)
        hdateti.dassert_has_tz(dt_utc)
        hdateti.dassert_has_UTC_tz(dt_utc)
        # Convert to ET.
        dt_et = dt_utc.astimezone(pytz.timezone("US/Eastern"))
        hdateti.dassert_has_tz(dt_et)
        hdateti.dassert_has_ET_tz(dt_et)
        # Convert it back to UTC.
        dt_utc2 = dt_et.astimezone(pytz.timezone("UTC"))
        hdateti.dassert_has_tz(dt_utc2)
        hdateti.dassert_has_UTC_tz(dt_utc2)
        self.assertEqual(dt_utc, dt_utc2)
        # Make it naive.
        dt2 = dt_utc2.replace(tzinfo=None)
        hdateti.dassert_is_tz_naive(dt2)
        self.assertEqual(dt, dt2)

    def test_dassert_is_datetime1(self) -> None:
        for obj in [
            _STR_TS_NAIVE,
            _STR_TS_UTC,
            _STR_TS_ET,
            _PD_TS_NAIVE,
            _PD_TS_UTC,
            _PD_TS_ET,
            _DT_DT_NAIVE,
            _DT_DT_UTC,
            _DT_DT_ET,
        ]:
            hdateti.dassert_is_datetime(obj)

    def test_dassert_is_datetime_assert1(self) -> None:
        datetime_ = 5
        with self.assertRaises(AssertionError) as cm:
            hdateti.dassert_is_datetime(datetime_)
        act = str(cm.exception)
        # pylint: disable=line-too-long
        exp = r"""
        * Failed assertion *
        Instance of '5' is '<class 'int'>' instead of '(<class 'str'>, <class 'pandas._libs.tslibs.timestamps.Timestamp'>, <class 'datetime.datetime'>)'
        datetime_='5' of type '<class 'int'>' is not a DateTimeType
        """
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_to_datetime1(self) -> None:
        """
        Apply `to_datetime` to a naive datetime.
        """
        for obj in [
            _STR_TS_NAIVE,
            _PD_TS_NAIVE,
            _DT_DT_NAIVE,
        ]:
            _LOG.debug("obj='%s' type='%s'", obj, type(obj))
            act = hdateti.to_datetime(obj)
            exp = _DT_DT_NAIVE
            self.assertEqual(act, exp)
            # Check the tz info.
            hdateti.dassert_is_tz_naive(act)
            with self.assertRaises(AssertionError):
                hdateti.dassert_has_tz(act)
                hdateti.dassert_has_UTC_tz(act)
                hdateti.dassert_has_ET_tz(act)

    def test_to_datetime2(self) -> None:
        """
        Apply `to_datetime` to a UTC datetime.
        """
        for obj in [
            _STR_TS_UTC,
            _PD_TS_UTC,
            _DT_DT_UTC,
        ]:
            _LOG.debug("obj='%s' type='%s'", obj, type(obj))
            act = hdateti.to_datetime(obj)
            exp = _DT_DT_UTC
            self.assertEqual(act, exp)
            # Check the tz info.
            hdateti.dassert_has_tz(act)
            hdateti.dassert_has_UTC_tz(act)
            with self.assertRaises(AssertionError):
                hdateti.dassert_is_tz_naive(act)
                hdateti.dassert_has_ET_tz(act)

    def test_to_datetime3(self) -> None:
        """
        Apply `to_datetime` to an ET datetime.
        """
        for obj in [
            _STR_TS_ET,
            _PD_TS_ET,
            _DT_DT_ET,
        ]:
            _LOG.debug("obj='%s' type='%s'", obj, type(obj))
            act = hdateti.to_datetime(obj)
            exp = _DT_DT_ET
            self.assertEqual(str(act), str(exp))


# #############################################################################
# Test_dassert_tz_compatible1
# #############################################################################


class Test_dassert_tz_compatible1(hunitest.TestCase):
    def test_dassert_compatible_timestamp1(self) -> None:
        """
        Both datetimes are naive.
        """
        for datetime1 in [_PD_TS_NAIVE, _DT_DT_NAIVE]:
            for datetime2 in [_PD_TS_NAIVE, _DT_DT_NAIVE]:
                hdateti.dassert_tz_compatible(datetime1, datetime2)

    def test_dassert_compatible_timestamp2(self) -> None:
        """
        Both datetimes have tz info.
        """
        for datetime1 in [_PD_TS_UTC, _PD_TS_ET]:
            for datetime2 in [_DT_DT_UTC, _DT_DT_ET]:
                hdateti.dassert_tz_compatible(datetime1, datetime2)

    def test_dassert_compatible_timestamp_assert1(self) -> None:
        """
        Test a single not compatible pair of datetimes and check the raised
        exception.
        """
        with self.assertRaises(AssertionError) as cm:
            hdateti.dassert_tz_compatible(_PD_TS_NAIVE, _DT_DT_UTC)
        act = str(cm.exception)
        # pylint: disable=line-too-long
        exp = """
        * Failed assertion *
        'False'
        ==
        'True'
        datetime1='2021-01-04 09:30:00' and datetime2='2021-01-04 09:30:00+00:00' are not compatible
        """
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_dassert_compatible_timestamp_assert2(self) -> None:
        """
        Test a pairs of non-compatible datetimes making sure the assertion is
        raised.
        """
        for datetime1 in [_PD_TS_NAIVE, _DT_DT_NAIVE, _PD_TS_NAIVE, _DT_DT_NAIVE]:
            for datetime2 in [_PD_TS_UTC, _PD_TS_ET, _DT_DT_UTC, _DT_DT_ET]:
                with self.assertRaises(AssertionError):
                    hdateti.dassert_tz_compatible(datetime1, datetime2)


# #############################################################################
# Test_dassert_have_same_tz1
# #############################################################################


class Test_dassert_have_same_tz1(hunitest.TestCase):
    """
    Test an assertion that checks that timezones are equal for input
    timestamps.
    """

    def test1(self) -> None:
        """
        Timezones are equal.
        """
        hdateti.dassert_have_same_tz(_DT_DT_ET, _PD_TS_ET)

    def test2(self) -> None:
        """
        Both timestamps are tz-naive.
        """
        hdateti.dassert_have_same_tz(_PD_TS_NAIVE, _DT_DT_NAIVE)

    def test3(self) -> None:
        """
        Different timezones.
        """
        with self.assertRaises(AssertionError) as cm:
            hdateti.dassert_have_same_tz(_DT_DT_ET, _DT_DT_UTC)
        act = str(cm.exception)
        # pylint: disable=line-too-long
        exp = """
        * Failed assertion *
        'America/New_York'
        ==
        'UTC'
        datetime1=2021-01-04 09:30:00-05:00 (datetime1.tzinfo=America/New_York) datetime2=2021-01-04 09:30:00+00:00 (datetime2.tzinfo=UTC)
        """
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test4(self) -> None:
        """
        Same timezone but different DST mode (i.e. EST vs EDT).
        """
        ts_est = pd.Timestamp("2023-03-12 01:55:00-05:00", tz="America/New_York")
        ts_edt = pd.Timestamp("2023-03-12 03:00:00-04:00", tz="America/New_York")
        hdateti.dassert_have_same_tz(ts_est, ts_edt)


# #############################################################################
# Test_get_current_time1
# #############################################################################


class Test_get_current_time1(hunitest.TestCase):
    def test_get_current_time_UTC(self) -> None:
        tz = "UTC"
        dt = hdateti.get_current_time(tz)
        _LOG.debug("tz=%s -> dt=%s", tz, dt)
        hdateti.dassert_has_UTC_tz(dt)

    def test_get_current_time_ET(self) -> None:
        tz = "ET"
        dt = hdateti.get_current_time(tz)
        _LOG.debug("tz=%s -> dt=%s", tz, dt)
        hdateti.dassert_has_ET_tz(dt)

    def test_get_current_time_naive_UTC(self) -> None:
        tz = "naive_UTC"
        dt = hdateti.get_current_time(tz)
        _LOG.debug("tz=%s -> dt=%s", tz, dt)
        hdateti.dassert_is_tz_naive(dt)

    def test_get_current_time_naive_ET(self) -> None:
        tz = "naive_ET"
        dt = hdateti.get_current_time(tz)
        _LOG.debug("tz=%s -> dt=%s", tz, dt)
        hdateti.dassert_is_tz_naive(dt)


# #############################################################################
# Test_to_generalized_datetime
# #############################################################################


class Test_to_generalized_datetime(hunitest.TestCase):
    def test_srs1(self) -> None:
        srs = pd.Series(["2010-01-01", "2010-01-02"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-02")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_index1(self) -> None:
        idx = pd.Index(["2010-01-01", "2010-01-02"])
        actual = hdateti.to_generalized_datetime(idx)
        expected = pd.Index(
            [pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-02")]
        )
        pd.testing.assert_index_equal(actual, expected)

    def test_daily1(self) -> None:
        srs = pd.Series(["1 Jan 2010", "2 Jan 2010"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-02")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_weekly1(self) -> None:
        srs = pd.Series(["2021-W14", "2021-W15"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2021-04-10"), pd.Timestamp("2021-04-17")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_semiannual1(self) -> None:
        srs = pd.Series(["2021-S1", "2021-S2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2021-06-30"), pd.Timestamp("2021-12-31")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_semiannual2(self) -> None:
        srs = pd.Series(["2021/S1", "2021/S2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2021-06-30"), pd.Timestamp("2021-12-31")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_bimonthly1(self) -> None:
        srs = pd.Series(["2021-B1", "2021-B2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2021-01-01"), pd.Timestamp("2021-03-01")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_monthly1(self) -> None:
        srs = pd.Series(["2020-M1", "2020-M2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_monthly2(self) -> None:
        srs = pd.Series(["2020M01", "2020M02"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_monthly3(self) -> None:
        srs = pd.Series(["2020-01", "2020-02"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_monthly4(self) -> None:
        srs = pd.Series(["2020 Jan", "2020 Feb"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_monthly5(self) -> None:
        srs = pd.Series(["January 2020", "February 2020"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_quarterly1(self) -> None:
        srs = pd.Series(["2020-Q1", "2020-Q2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-03-31"), pd.Timestamp("2020-06-30")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_quarterly2(self) -> None:
        srs = pd.Series(["2020Q1", "2020Q2"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-03-31"), pd.Timestamp("2020-06-30")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_quarterly3(self) -> None:
        srs = pd.Series(["Q1 2020", "Q2 2020"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2020-03-31"), pd.Timestamp("2020-06-30")]
        )
        pd.testing.assert_series_equal(actual, expected)

    def test_annual1(self) -> None:
        srs = pd.Series(["2021", "2022"])
        actual = hdateti.to_generalized_datetime(srs)
        expected = pd.Series(
            [pd.Timestamp("2021-12-31"), pd.Timestamp("2022-12-31")]
        )
        pd.testing.assert_series_equal(actual, expected)


# #############################################################################
# Test_find_bar_timestamp1
# #############################################################################


class Test_find_bar_timestamp1(hunitest.TestCase):
    """
    Use mode="round".
    """

    def helper1(self, current_timestamp: pd.Timestamp) -> None:
        bar_duration_in_secs = 15 * 60
        max_distance_in_secs = 10
        act = hdateti.find_bar_timestamp(
            current_timestamp,
            bar_duration_in_secs,
            max_distance_in_secs=max_distance_in_secs,
        )
        exp = pd.Timestamp("2021-09-09T08:00:00", tz="UTC")
        self.assert_equal(str(act), str(exp))

    def test1(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T08:00:00", tz="UTC")
        self.helper1(current_timestamp)

    def test2(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T08:00:05", tz="UTC")
        self.helper1(current_timestamp)

    def test3(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T07:59:55", tz="UTC")
        self.helper1(current_timestamp)

    def test4(self) -> None:
        current_timestamp = pd.Timestamp(
            "2021-09-09 08:01:59.500000+0000", tz="UTC"
        )
        bar_duration_in_secs = 1
        #
        act = hdateti.find_bar_timestamp(
            current_timestamp, bar_duration_in_secs, mode="round"
        )
        exp = pd.Timestamp("2021-09-09T08:02:00+0000", tz="UTC")
        self.assert_equal(str(act), str(exp))

    # ///////////////////////////////////////////////////////////////////////////

    def test5(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T07:59:20", tz="UTC")
        with self.assertRaises(AssertionError) as cm:
            self.helper1(current_timestamp)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        40 <= 10
        current_timestamp=2021-09-09 07:59:20+00:00 is too distant from bar_timestamp=2021-09-09 08:00:00+00:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test6(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T08:10:20", tz="UTC")
        with self.assertRaises(AssertionError) as cm:
            self.helper1(current_timestamp)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        280 <= 10
        current_timestamp=2021-09-09 08:10:20+00:00 is too distant from bar_timestamp=2021-09-09 08:15:00+00:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)


class Test_find_bar_timestamp2(hunitest.TestCase):
    """
    Use mode="floor".
    """

    def test1(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T07:59:55", tz="UTC")
        bar_duration_in_secs = 15 * 60
        #
        act = hdateti.find_bar_timestamp(
            current_timestamp, bar_duration_in_secs, mode="floor"
        )
        exp = pd.Timestamp("2021-09-09T07:45:00", tz="UTC")
        self.assert_equal(str(act), str(exp))

    def test2(self) -> None:
        current_timestamp = pd.Timestamp("2021-09-09T08:01:55", tz="UTC")
        bar_duration_in_secs = 15 * 60
        #
        act = hdateti.find_bar_timestamp(
            current_timestamp, bar_duration_in_secs, mode="floor"
        )
        exp = pd.Timestamp("2021-09-09T08:00:00", tz="UTC")
        self.assert_equal(str(act), str(exp))

    def test3(self) -> None:
        current_timestamp = pd.Timestamp(
            "2021-09-09 08:01:59.500000+0000", tz="UTC"
        )
        bar_duration_in_secs = 1
        #
        act = hdateti.find_bar_timestamp(
            current_timestamp, bar_duration_in_secs, mode="floor"
        )
        exp = pd.Timestamp("2021-09-09T08:01:59+0000", tz="UTC")
        self.assert_equal(str(act), str(exp))


# #############################################################################
# Test_convert_seconds_to_minutes
# #############################################################################


class Test_convert_seconds_to_minutes(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check that conversion is implemented correcty.
        """
        num_secs = 300
        act = hdateti.convert_seconds_to_minutes(num_secs)
        exp = int(num_secs / 60)
        self.assertEqual(act, exp)

    def test2(self) -> None:
        """
        Check that an error is raised when input is not an integer number of
        minutes.
        """
        num_secs = 10
        with self.assertRaises(AssertionError) as cm:
            hdateti.convert_seconds_to_minutes(num_secs)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        '10'
        ==
        '0'
        num_secs=10 is not an integer number of minutes
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_convert_unix_epoch_to_timestamp
# #############################################################################


class Test_convert_unix_epoch_to_timestamp(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test with default parameter values.
        """
        epoch = 1631145600000
        actual = hdateti.convert_unix_epoch_to_timestamp(epoch=epoch)
        expected = pd.Timestamp("2021-09-09T00:00:00", tz="UTC")
        self.assert_equal(str(actual), str(expected))

    def test2(self) -> None:
        """
        Test with specified unit.
        """
        epoch = 1631145600
        unit = "s"
        actual = hdateti.convert_unix_epoch_to_timestamp(epoch=epoch, unit=unit)
        expected = pd.Timestamp("2021-09-09T00:00:00", tz="UTC")
        self.assert_equal(str(actual), str(expected))

    def test3(self) -> None:
        """
        Test with specified timezone.
        """
        epoch = 1631145600000
        tz = "US/Pacific"
        actual = hdateti.convert_unix_epoch_to_timestamp(epoch=epoch, tz=tz)
        expected = pd.Timestamp("2021-09-08T17:00:00", tz="US/Pacific")
        self.assert_equal(str(actual), str(expected))


# #############################################################################
# Test_convert_timestamp_to_unix_epoch
# #############################################################################


class Test_convert_timestamp_to_unix_epoch(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test with default parameter values.
        """
        timestamp = pd.Timestamp("2021-09-09")
        actual = hdateti.convert_timestamp_to_unix_epoch(timestamp=timestamp)
        expected = 1631145600000
        self.assert_equal(str(actual), str(expected))

    def test2(self) -> None:
        """
        Test with specified unit.
        """
        timestamp = pd.Timestamp("2021-09-09")
        unit = "s"
        actual = hdateti.convert_timestamp_to_unix_epoch(
            timestamp=timestamp, unit=unit
        )
        expected = 1631145600
        self.assert_equal(str(actual), str(expected))

    def test3(self) -> None:
        """
        Test for a timestamp with specified timezone.
        """
        timestamp = pd.Timestamp("2021-09-08T17:00:00", tz="US/Pacific")
        actual = hdateti.convert_timestamp_to_unix_epoch(timestamp=timestamp)
        expected = 1631145600000
        self.assert_equal(str(actual), str(expected))


class Test_str_to_timestamp1(hunitest.TestCase):
    """
    Test if string representation of datetime is converted correctly.
    """

    def test1(self) -> None:
        """
        - `datetime_str` has a valid format
        - `datetime_format` has a valid pattern for `datetime_str`
        """
        datetime_str = "20230728_150513"
        timezone_info = "US/Eastern"
        datetime_format = "%Y%m%d_%H%M%S"
        actual = hdateti.str_to_timestamp(
            datetime_str, timezone_info, datetime_format=datetime_format
        )
        expected = pd.Timestamp("2023-07-28 15:05:13-0400", tz="US/Eastern")
        self.assertEqual(actual, expected)

    def test2(self) -> None:
        """
        - `datetime_str` has a valid format
        - `datetime_format` has an valid pattern for `datetime_str`
        - `timezone_info` is UTC
        """
        datetime_str = "20230728_150513"
        timezone_info = "UTC"
        format = "%Y%m%d_%H%M%S"
        actual = hdateti.str_to_timestamp(
            datetime_str, timezone_info, datetime_format=format
        )
        expected = pd.Timestamp("2023-07-28 15:05:13+0000", tz="UTC")
        self.assertEqual(actual, expected)

    def test3(self) -> None:
        """
        - `datetime_str` has a valid format
        - `datetime_format` has an invalid pattern for `datetime_str`
        """
        datetime_str = "28-07-2023 15:05:13"
        timezone_info = "US/Eastern"
        datetime_format = "%Y%m%d_%H%M%S"
        # The datetime format does not match the string representation of datetime.
        with self.assertRaises(ValueError) as err:
            hdateti.str_to_timestamp(
                datetime_str, timezone_info, datetime_format=datetime_format
            )
        actual = str(err.exception)
        self.check_string(actual)

    def test4(self) -> None:
        """
        - `datetime_str` has an invalid format
        - `datetime_format` is not defined
        """
        datetime_str = "qwe28abc07-201234"
        timezone_info = "US/Eastern"
        # Invalid datetime, should raise a ValueError.
        with self.assertRaises(ValueError) as err:
            hdateti.str_to_timestamp(datetime_str, timezone_info)
        actual = str(err.exception)
        self.check_string(actual)


# #############################################################################
# Test_dassert_str_is_date
# #############################################################################


class Test_dassert_str_is_date(hunitest.TestCase):
    """
    Test that the function checks a string representation of date correctly.
    """

    def test1(self) -> None:
        """
        - date has a valid format
        """
        date_str = "20221101"
        hdateti.dassert_str_is_date(date_str)

    def test2(self) -> None:
        """
        - date has an invalid format
        """
        date = "2022-11-01"
        with self.assertRaises(ValueError) as err:
            hdateti.dassert_str_is_date(date)
        actual = str(err.exception)
        self.check_string(actual)
