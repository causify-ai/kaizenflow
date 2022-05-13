import datetime
import io
import logging
import os
import uuid
from typing import Any

import numpy as np
import pandas as pd

import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

_AWS_PROFILE = "am"


class Test_dassert_is_unique1(hunitest.TestCase):
    def get_df1(self) -> pd.DataFrame:
        """
        Return a df without duplicated index.
        """
        num_rows = 5
        idx = [
            pd.Timestamp("2000-01-01 9:00") + pd.Timedelta(minutes=i)
            for i in range(num_rows)
        ]
        values = [[i] for i in range(len(idx))]
        df = pd.DataFrame(values, index=idx)
        _LOG.debug("df=\n%s", df)
        #
        act = hpandas.df_to_str(df)
        exp = r"""
                             0
        2000-01-01 09:00:00  0
        2000-01-01 09:01:00  1
        2000-01-01 09:02:00  2
        2000-01-01 09:03:00  3
        2000-01-01 09:04:00  4"""
        self.assert_equal(act, exp, fuzzy_match=True)
        return df

    def test_dassert_is_unique1(self) -> None:
        df = self.get_df1()
        hpandas.dassert_unique_index(df)

    def get_df2(self) -> pd.DataFrame:
        """
        Return a df with duplicated index.
        """
        num_rows = 4
        idx = [
            pd.Timestamp("2000-01-01 9:00") + pd.Timedelta(minutes=i)
            for i in range(num_rows)
        ]
        idx.append(idx[0])
        values = [[i] for i in range(len(idx))]
        df = pd.DataFrame(values, index=idx)
        _LOG.debug("df=\n%s", df)
        #
        act = hpandas.df_to_str(df)
        exp = r"""
                             0
        2000-01-01 09:00:00  0
        2000-01-01 09:01:00  1
        2000-01-01 09:02:00  2
        2000-01-01 09:03:00  3
        2000-01-01 09:00:00  4"""
        self.assert_equal(act, exp, fuzzy_match=True)
        return df

    def test_dassert_is_unique2(self) -> None:
        df = self.get_df2()
        with self.assertRaises(AssertionError) as cm:
            hpandas.dassert_unique_index(df)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        cond=False
        Duplicated rows are:
                             0
        2000-01-01 09:00:00  0
        2000-01-01 09:00:00  4
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_to_series1(hunitest.TestCase):
    def helper(self, n: int, exp: str) -> None:
        vals = list(range(n))
        df = pd.DataFrame([vals], columns=[f"a{i}" for i in vals])
        df = df.T
        _LOG.debug("df=\n%s", df)
        srs = hpandas.to_series(df)
        _LOG.debug("srs=\n%s", srs)
        act = str(srs)
        self.assert_equal(act, exp, dedent=True, fuzzy_match=True)

    def test1(self) -> None:
        n = 0
        exp = r"""
        Series([], dtype: float64)
        """
        self.helper(n, exp)

    def test2(self) -> None:
        n = 1
        exp = r"""
        a0    0
        dtype: int64"""
        self.helper(n, exp)

    def test3(self) -> None:
        n = 5
        exp = r"""
        a0    0
        a1    1
        a2    2
        a3    3
        a4    4
        Name: 0, dtype: int64"""
        self.helper(n, exp)


# #############################################################################


class Test_trim_df1(hunitest.TestCase):
    def get_df(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        """
        Return a df where the CSV txt is read verbatim without inferring dates.

        The `start_time` column is thus a str.
        """

        txt = """
        ,start_time,egid,close
        4,2022-01-04 21:38:00.000000,13684,1146.48
        8,2022-01-04 21:38:00.000000,17085,179.45
        14,2022-01-04 21:37:00.000000,13684,1146.26
        18,2022-01-04 21:37:00.000000,17085,179.42
        24,2022-01-04 21:36:00.000000,13684,1146.0
        27,2022-01-04 21:36:00.000000,17085,179.46
        34,2022-01-04 21:35:00.000000,13684,1146.0
        38,2022-01-04 21:35:00.000000,17085,179.42
        40,2022-01-04 21:34:00.000000,17085,179.42
        44,2022-01-04 21:34:00.000000,13684,1146.0
        """
        txt = hprint.dedent(txt)
        df = pd.read_csv(io.StringIO(txt), *args, index_col=0, **kwargs)
        return df

    def test_types1(self) -> None:
        """
        Check the types of a df coming from `read_csv()`.

        The timestamps in `start_time` are left as strings.
        """
        df = self.get_df()
        #
        act = hpandas.df_to_str(
            df, print_dtypes=True, print_shape_info=True, tag="df"
        )
        exp = r"""# df=
        index=[4, 44]
        columns=start_time,egid,close
        shape=(10, 3)
        * type=
             col_name    dtype         num_unique        num_nans                  first_elem         type(first_elem)
        0       index    int64  10 / 10 = 100.00%  0 / 10 = 0.00%                           4    <class 'numpy.int64'>
        1  start_time   object    5 / 10 = 50.00%  0 / 10 = 0.00%  2022-01-04 21:38:00.000000            <class 'str'>
        2        egid    int64    2 / 10 = 20.00%  0 / 10 = 0.00%                       13684    <class 'numpy.int64'>
        3       close  float64    6 / 10 = 60.00%  0 / 10 = 0.00%                     1146.48  <class 'numpy.float64'>
                            start_time   egid    close
        4   2022-01-04 21:38:00.000000  13684  1146.48
        8   2022-01-04 21:38:00.000000  17085   179.45
        14  2022-01-04 21:37:00.000000  13684  1146.26
        ...
        38  2022-01-04 21:35:00.000000  17085   179.42
        40  2022-01-04 21:34:00.000000  17085   179.42
        44  2022-01-04 21:34:00.000000  13684  1146.00"""
        self.assert_equal(act, exp, fuzzy_match=True)

    def get_df_with_parse_dates(self) -> pd.DataFrame:
        """
        Read the CSV parsing `start_time` as timestamps.

        The inferred type is a nasty `datetime64` which is not as well-
        behaved as our beloved `pd.Timestamp`.
        """
        df = self.get_df(parse_dates=["start_time"])
        return df

    def test_types2(self) -> None:
        """
        Check the types of a df coming from `read_csv()` forcing parsing some
        values as dates.
        """
        df = self.get_df_with_parse_dates()
        # Check.
        act = hpandas.df_to_str(
            df, print_dtypes=True, print_shape_info=True, tag="df"
        )
        exp = r"""# df=
        index=[4, 44]
        columns=start_time,egid,close
        shape=(10, 3)
        * type=
             col_name           dtype         num_unique        num_nans                     first_elem            type(first_elem)
        0       index           int64  10 / 10 = 100.00%  0 / 10 = 0.00%                              4       <class 'numpy.int64'>
        1  start_time  datetime64[ns]    5 / 10 = 50.00%  0 / 10 = 0.00%  2022-01-04T21:38:00.000000000  <class 'numpy.datetime64'>
        2        egid           int64    2 / 10 = 20.00%  0 / 10 = 0.00%                          13684       <class 'numpy.int64'>
        3       close         float64    6 / 10 = 60.00%  0 / 10 = 0.00%                        1146.48     <class 'numpy.float64'>
                    start_time   egid    close
        4  2022-01-04 21:38:00  13684  1146.48
        8  2022-01-04 21:38:00  17085   179.45
        14 2022-01-04 21:37:00  13684  1146.26
        ...
        38 2022-01-04 21:35:00  17085   179.42
        40 2022-01-04 21:34:00  17085   179.42
        44 2022-01-04 21:34:00  13684  1146.00"""
        self.assert_equal(act, exp, fuzzy_match=True)

    def get_df_with_tz_timestamp(self) -> pd.DataFrame:
        """
        Force the column parsed as `datetime64` into a tz-aware object.

        The resulting object is a `datetime64[ns, tz]`.
        """
        df = self.get_df_with_parse_dates()
        # Apply the tz.
        col_name = "start_time"
        df[col_name] = (
            df[col_name].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
        )
        df[col_name] = pd.to_datetime(df[col_name])
        return df

    def test_types3(self) -> None:
        """
        Check the types of a df coming from `read_csv()` after conversion to
        tz-aware objects.
        """
        df = self.get_df_with_tz_timestamp()
        # Check.
        act = hpandas.df_to_str(
            df, print_dtypes=True, print_shape_info=True, tag="df"
        )
        exp = r"""# df=
        index=[4, 44]
        columns=start_time,egid,close
        shape=(10, 3)
        * type=
             col_name                             dtype         num_unique        num_nans                     first_elem            type(first_elem)
        0       index                             int64  10 / 10 = 100.00%  0 / 10 = 0.00%                              4       <class 'numpy.int64'>
        1  start_time  datetime64[ns, America/New_York]    5 / 10 = 50.00%  0 / 10 = 0.00%  2022-01-04T21:38:00.000000000  <class 'numpy.datetime64'>
        2        egid                             int64    2 / 10 = 20.00%  0 / 10 = 0.00%                          13684       <class 'numpy.int64'>
        3       close                           float64    6 / 10 = 60.00%  0 / 10 = 0.00%                        1146.48     <class 'numpy.float64'>
                          start_time   egid    close
        4  2022-01-04 16:38:00-05:00  13684  1146.48
        8  2022-01-04 16:38:00-05:00  17085   179.45
        14 2022-01-04 16:37:00-05:00  13684  1146.26
        ...
        38 2022-01-04 16:35:00-05:00  17085   179.42
        40 2022-01-04 16:34:00-05:00  17085   179.42
        44 2022-01-04 16:34:00-05:00  13684  1146.00"""
        self.assert_equal(act, exp, fuzzy_match=True)

    # //////////////////////////////////////////////////////////////////////////////

    def test_trim_df1(self) -> None:
        """
        In general one can't filter a df with columns represented as `str`
        using `pd.Timestamp` (either tz-aware or tz-naive).

        Pandas helps us when filtering the index doing some conversion
        for us. When it's a column, we have to handle it ourselves:
        `trim_df` does that by converting the columns in `pd.Timestamp`.
        """
        df = self.get_df()
        # Run.
        ts_col_name = "start_time"
        start_ts = pd.Timestamp("2022-01-04 21:35:00")
        end_ts = pd.Timestamp("2022-01-04 21:38:00")
        left_close = True
        right_close = True
        df_trim = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        # Check.
        act = hpandas.df_to_str(
            df_trim, print_dtypes=True, print_shape_info=True, tag="df_trim"
        )
        exp = r"""# df_trim=
        index=[4, 38]
        columns=start_time,egid,close
        shape=(8, 3)
        * type=
             col_name    dtype       num_unique       num_nans                  first_elem         type(first_elem)
        0       index    int64  8 / 8 = 100.00%  0 / 8 = 0.00%                           4    <class 'numpy.int64'>
        1  start_time   object   4 / 8 = 50.00%  0 / 8 = 0.00%  2022-01-04 21:38:00.000000            <class 'str'>
        2        egid    int64   2 / 8 = 25.00%  0 / 8 = 0.00%                       13684    <class 'numpy.int64'>
        3       close  float64   6 / 8 = 75.00%  0 / 8 = 0.00%                     1146.48  <class 'numpy.float64'>
                            start_time   egid    close
        4   2022-01-04 21:38:00.000000  13684  1146.48
        8   2022-01-04 21:38:00.000000  17085   179.45
        14  2022-01-04 21:37:00.000000  13684  1146.26
        ...
        27  2022-01-04 21:36:00.000000  17085   179.46
        34  2022-01-04 21:35:00.000000  13684  1146.00
        38  2022-01-04 21:35:00.000000  17085   179.42"""
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_trim_df2(self) -> None:
        """
        Trim a df with a column that is `datetime64` without tz using a
        `pd.Timestamp` without tz.

        This operation is valid.
        """
        df = self.get_df_with_parse_dates()
        # Run.
        ts_col_name = "start_time"
        start_ts = pd.Timestamp("2022-01-04 21:35:00")
        end_ts = pd.Timestamp("2022-01-04 21:38:00")
        left_close = True
        right_close = True
        df_trim = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        # Check.
        act = hpandas.df_to_str(
            df_trim, print_dtypes=True, print_shape_info=True, tag="df_trim"
        )
        exp = r"""# df_trim=
        index=[4, 38]
        columns=start_time,egid,close
        shape=(8, 3)
        * type=
             col_name           dtype       num_unique       num_nans                     first_elem            type(first_elem)
        0       index           int64  8 / 8 = 100.00%  0 / 8 = 0.00%                              4       <class 'numpy.int64'>
        1  start_time  datetime64[ns]   4 / 8 = 50.00%  0 / 8 = 0.00%  2022-01-04T21:38:00.000000000  <class 'numpy.datetime64'>
        2        egid           int64   2 / 8 = 25.00%  0 / 8 = 0.00%                          13684       <class 'numpy.int64'>
        3       close         float64   6 / 8 = 75.00%  0 / 8 = 0.00%                        1146.48     <class 'numpy.float64'>
                    start_time   egid    close
        4  2022-01-04 21:38:00  13684  1146.48
        8  2022-01-04 21:38:00  17085   179.45
        14 2022-01-04 21:37:00  13684  1146.26
        ...
        27 2022-01-04 21:36:00  17085   179.46
        34 2022-01-04 21:35:00  13684  1146.00
        38 2022-01-04 21:35:00  17085   179.42"""
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_trim_df3(self) -> None:
        """
        Trim a df with a column that is `datetime64` with tz vs a `pd.Timestamp
        with tz.

        This operation is valid.
        """
        df = self.get_df_with_tz_timestamp()
        # Run.
        ts_col_name = "start_time"
        start_ts = pd.Timestamp("2022-01-04 21:35:00", tz="UTC")
        end_ts = pd.Timestamp("2022-01-04 21:38:00", tz="UTC")
        left_close = True
        right_close = True
        df_trim = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        # Check.
        act = hpandas.df_to_str(
            df_trim, print_dtypes=True, print_shape_info=True, tag="df_trim"
        )
        exp = r"""# df_trim=
        index=[4, 38]
        columns=start_time,egid,close
        shape=(8, 3)
        * type=
             col_name                             dtype       num_unique       num_nans                     first_elem            type(first_elem)
        0       index                             int64  8 / 8 = 100.00%  0 / 8 = 0.00%                              4       <class 'numpy.int64'>
        1  start_time  datetime64[ns, America/New_York]   4 / 8 = 50.00%  0 / 8 = 0.00%  2022-01-04T21:38:00.000000000  <class 'numpy.datetime64'>
        2        egid                             int64   2 / 8 = 25.00%  0 / 8 = 0.00%                          13684       <class 'numpy.int64'>
        3       close                           float64   6 / 8 = 75.00%  0 / 8 = 0.00%                        1146.48     <class 'numpy.float64'>
                          start_time   egid    close
        4  2022-01-04 16:38:00-05:00  13684  1146.48
        8  2022-01-04 16:38:00-05:00  17085   179.45
        14 2022-01-04 16:37:00-05:00  13684  1146.26
        ...
        27 2022-01-04 16:36:00-05:00  17085   179.46
        34 2022-01-04 16:35:00-05:00  13684  1146.00
        38 2022-01-04 16:35:00-05:00  17085   179.42"""
        self.assert_equal(act, exp, fuzzy_match=True)

    # pylint: disable=line-too-long
    def test_trim_df4(self) -> None:
        """
        Trim a df with a column that is `datetime64` with tz vs a `pd.Timestamp
        without tz.

        This operation is invalid and we expect an assertion.
        """
        df = self.get_df_with_tz_timestamp()
        # Run.
        ts_col_name = "start_time"
        start_ts = pd.Timestamp("2022-01-04 21:35:00")
        end_ts = pd.Timestamp("2022-01-04 21:38:00")
        left_close = True
        right_close = True
        with self.assertRaises(AssertionError) as cm:
            hpandas.trim_df(
                df, ts_col_name, start_ts, end_ts, left_close, right_close
            )
        # Check.
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        'True'
        ==
        'False'
        datetime1='2022-01-04 16:38:00-05:00' and datetime2='2022-01-04 21:35:00' are not compatible"""
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class TestDfToStr(hunitest.TestCase):
    @staticmethod
    def get_test_data() -> pd.DataFrame:
        test_data = {
            "dummy_value_1": [1, 2, 3],
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [0, 0, 0],
        }
        df = pd.DataFrame(data=test_data)
        return df

    def test_df_to_str1(self) -> None:
        """
        Test common call to `df_to_str` with basic df.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(df)
        expected = r"""
            dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str2(self) -> None:
        """
        Test common call to `df_to_str` with tag.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(df, tag="df")
        expected = r"""# df=
           dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str3(self) -> None:
        """
        Test common call to `df_to_str` with print_shape_info.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(df, print_shape_info=True)
        expected = r"""
        index=[0, 2]
        columns=dummy_value_1,dummy_value_2,dummy_value_3
        shape=(3, 3)
           dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str4(self) -> None:
        """
        Test common call to `df_to_str` with print_dtypes.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(df, print_dtypes=True)
        expected = r"""
        * type=
                col_name   dtype       num_unique       num_nans first_elem       type(first_elem)
        0          index   int64  3 / 3 = 100.00%  0 / 3 = 0.00%          0  <class 'numpy.int64'>
        1  dummy_value_1   int64  3 / 3 = 100.00%  0 / 3 = 0.00%          1  <class 'numpy.int64'>
        2  dummy_value_2  object  3 / 3 = 100.00%  0 / 3 = 0.00%          A          <class 'str'>
        3  dummy_value_3   int64   1 / 3 = 33.33%  0 / 3 = 0.00%          0  <class 'numpy.int64'>
           dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str5(self) -> None:
        """
        Test common call to `df_to_str` with multiple args.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(
            df, print_shape_info=True, print_dtypes=True, tag="df"
        )
        expected = r"""
        # df=
        index=[0, 2]
        columns=dummy_value_1,dummy_value_2,dummy_value_3
        shape=(3, 3)
        * type=
                col_name   dtype       num_unique       num_nans first_elem       type(first_elem)
        0          index   int64  3 / 3 = 100.00%  0 / 3 = 0.00%          0  <class 'numpy.int64'>
        1  dummy_value_1   int64  3 / 3 = 100.00%  0 / 3 = 0.00%          1  <class 'numpy.int64'>
        2  dummy_value_2  object  3 / 3 = 100.00%  0 / 3 = 0.00%          A          <class 'str'>
        3  dummy_value_3   int64   1 / 3 = 33.33%  0 / 3 = 0.00%          0  <class 'numpy.int64'>
           dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str6(self) -> None:
        """
        Test common call to `df_to_str` with `pd.Series`.
        """
        df = self.get_test_data()
        actual = hpandas.df_to_str(df["dummy_value_2"])
        expected = r"""
            dummy_value_2
        0             A
        1             B
        2             C
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_df_to_str7(self) -> None:
        """
        Test common call to `df_to_str` with `pd.Index`.
        """
        df = self.get_test_data()
        index = df.index
        index.name = "index_name"
        actual = hpandas.df_to_str(index)
        expected = r"""
        index_name
        0  0
        1  1
        2  2
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestDataframeToJson(hunitest.TestCase):
    def test_dataframe_to_json(self) -> None:
        """
        Verify correctness of dataframe to JSON transformation.
        """
        # Initialize a dataframe.
        test_dataframe = pd.DataFrame(
            {
                "col_1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                "col_2": [1, 2, 3, 4, 5, 6, 7],
            }
        )
        # Convert dataframe to JSON.
        output_str = hpandas.convert_df_to_json_string(
            test_dataframe, n_head=3, n_tail=3
        )
        self.check_string(output_str)

    def test_dataframe_to_json_uuid(self) -> None:
        """
        Verify correctness of UUID-containing dataframe transformation.
        """
        # Initialize a dataframe.
        test_dataframe = pd.DataFrame(
            {
                "col_1": [
                    uuid.UUID("421470c7-7797-4a94-b584-eb83ff2de88a"),
                    uuid.UUID("22cde381-1782-43dc-8c7a-8712cbdf5ee1"),
                ],
                "col_2": [1, 2],
            }
        )
        # Convert dataframe to JSON.
        output_str = hpandas.convert_df_to_json_string(
            test_dataframe, n_head=None, n_tail=None
        )
        self.check_string(output_str)

    def test_dataframe_to_json_timestamp(self) -> None:
        """
        Verify correctness of transformation of a dataframe with Timestamps.
        """
        # Initialize a dataframe.
        test_dataframe = pd.DataFrame(
            {
                "col_1": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-05-12")],
                "col_2": [1.0, 2.0],
            }
        )
        # Convert dataframe to JSON.
        output_str = hpandas.convert_df_to_json_string(
            test_dataframe, n_head=None, n_tail=None
        )
        self.check_string(output_str)

    def test_dataframe_to_json_datetime(self) -> None:
        """
        Verify correctness of transformation of a dataframe with datetime.
        """
        # Initialize a dataframe.
        test_dataframe = pd.DataFrame(
            {
                "col_1": [
                    datetime.datetime(2020, 1, 1),
                    datetime.datetime(2020, 5, 12),
                ],
                "col_2": [1.0, 2.0],
            }
        )
        # Convert dataframe to JSON.
        output_str = hpandas.convert_df_to_json_string(
            test_dataframe, n_head=None, n_tail=None
        )
        self.check_string(output_str)


# #############################################################################


class TestFindGapsInDataframes(hunitest.TestCase):
    def test_find_gaps_in_dataframes(self) -> None:
        """
        Verify that gaps are caught.
        """
        # Prepare inputs.
        test_data = pd.DataFrame(
            data={
                "dummy_value_1": [1, 2, 3],
                "dummy_value_2": ["A", "B", "C"],
                "dummy_value_3": [0, 0, 0],
            }
        )
        # Run.
        missing_data = hpandas.find_gaps_in_dataframes(
            test_data.head(2), test_data.tail(2)
        )
        # Check output.
        actual = pd.concat(missing_data)
        actual = hpandas.df_to_str(actual)
        expected = r"""   dummy_value_1 dummy_value_2  dummy_value_3
        2              3             C              0
        0              1             A              0"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestCompareDataframeRows(hunitest.TestCase):
    def get_test_data(self) -> pd.DataFrame:
        test_data = {
            "dummy_value_1": [0, 1, 3, 2, 0],
            "dummy_value_2": ["0", "A", "C", "B", "D"],
            "dummy_value_3": [0, 0, 0, 0, 0],
        }
        df = pd.DataFrame(data=test_data)
        df.index.name = "test"
        return df

    def test_compare_dataframe_rows1(self) -> None:
        """
        Verify that differences are caught and displayed properly.
        """
        # Prepare inputs.
        test_data = self.get_test_data()
        edited_test_data = test_data.copy()[1:-1]
        edited_test_data.loc[1, "dummy_value_2"] = "W"
        edited_test_data.loc[2, "dummy_value_2"] = "Q"
        edited_test_data.loc[2, "dummy_value_3"] = "1"
        # Run.
        data_difference = hpandas.compare_dataframe_rows(
            test_data, edited_test_data
        )
        # Check output.
        actual = hpandas.df_to_str(data_difference)
        expected = r"""  dummy_value_2       dummy_value_3       test
                   self other          self other
        0             W     A          <NA>  <NA>    1
        1             Q     C             1     0    2"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_compare_dataframe_rows2(self) -> None:
        """
        Verify that differences are caught and displayed properly without
        original index.
        """
        # Prepare inputs.
        test_data = self.get_test_data()
        test_data.index.name = None
        edited_test_data = test_data.copy()[1:-1]
        edited_test_data.loc[1, "dummy_value_2"] = "W"
        edited_test_data.loc[2, "dummy_value_2"] = "Q"
        edited_test_data.loc[2, "dummy_value_3"] = "1"
        # Run.
        data_difference = hpandas.compare_dataframe_rows(
            test_data, edited_test_data
        )
        # Check output.
        actual = hpandas.df_to_str(data_difference)
        expected = r"""  dummy_value_2       dummy_value_3
                   self other          self other
        0             W     A           NaN   NaN
        1             Q     C             1   0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestReadDataFromS3(hunitest.TestCase):
    def test_read_csv1(self) -> None:
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        file_name = os.path.join(
            hs3.get_s3_bucket_path(_AWS_PROFILE),
            "data/kibot/all_stocks_1min/RIMG.csv.gz",
        )
        hs3.dassert_path_exists(file_name, s3fs)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        hpandas.read_csv_to_df(stream, **kwargs)

    def test_read_parquet1(self) -> None:
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        file_name = os.path.join(
            hs3.get_s3_bucket_path(_AWS_PROFILE),
            "data/kibot/pq/sp_500_1min/AAPL.pq",
        )
        hs3.dassert_path_exists(file_name, s3fs)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        hpandas.read_parquet_to_df(stream, **kwargs)


class TestSubsetDf1(hunitest.TestCase):
    def test1(self) -> None:
        # Generate some random data.
        np.random.seed(42)
        df = pd.DataFrame(
            np.random.randint(0, 100, size=(20, 4)), columns=list("ABCD")
        )
        # Subset.
        df2 = hpandas.subset_df(df, nrows=5, seed=43)
        # Check.
        actual = hpandas.df_to_str(df2)
        expected = r"""
           A   B   C   D
        0  51  92  14  71
        1  60  20  82  86
        3  23   2  21  52
        ...
        17  80  35  49   3
        18   1   5  53   3
        19  53  92  62  17
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


class TestDropNa(hunitest.TestCase):
    def test_dropna1(self) -> None:
        """
        Test if all types of NaNs are dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [np.nan, 1, 3, 2, 0],
            "dummy_value_2": ["0", "A", "B", None, "D"],
            "dummy_value_3": [0, 0, pd.NA, 0, 0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.dropna(test_df, drop_infs=False)
        # Prepare expected result.
        expected = {
            "dummy_value_1": [1, 0],
            "dummy_value_2": ["A", "D"],
            "dummy_value_3": [0, 0],
        }
        # Set the dtype of numeral columns to float to match the dataframe after NA dropping.
        expected = pd.DataFrame(data=expected).astype(
            {"dummy_value_1": "float64", "dummy_value_3": "object"}
        )
        # Set the index of the rows that remained.
        expected = expected.set_index(pd.Index([1, 4]))
        # Check.
        hunitest.compare_df(actual, expected)

    def test_dropna2(self) -> None:
        """
        Test if infs are dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [-np.inf, 1, 3, 2, 0],
            "dummy_value_2": ["0", "A", "B", "C", "D"],
            "dummy_value_3": [0, 0, np.inf, 0, 0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.dropna(test_df, drop_infs=True)
        # Prepare expected result.
        expected = {
            "dummy_value_1": [1, 2, 0],
            "dummy_value_2": ["A", "C", "D"],
            "dummy_value_3": [0, 0, 0],
        }
        # Set the dtype of numeral columns to float to match the dataframe after NA dropping.
        expected = pd.DataFrame(data=expected).astype(
            {"dummy_value_1": "float64", "dummy_value_3": "float64"}
        )
        # Set the index of the rows that remained.
        expected = expected.set_index(pd.Index([1, 3, 4]))
        # Check.
        hunitest.compare_df(actual, expected)


class TestDropAxisWithAllNans(hunitest.TestCase):
    def test_drop_rows1(self) -> None:
        """
        Test if row full of nans is dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [np.nan, 2, 3],
            "dummy_value_2": [pd.NA, "B", "C"],  # type: ignore
            "dummy_value_3": [None, 1.0, 1.0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.drop_axis_with_all_nans(test_df, drop_rows=True)
        # Prepare expected result.
        expected = {
            "dummy_value_1": [2, 3],
            "dummy_value_2": ["B", "C"],
            "dummy_value_3": [1.0, 1.0],
        }
        # Set the dtype of numeral columns to float to match the dataframe after NA dropping.
        expected = pd.DataFrame(data=expected).astype(
            {"dummy_value_1": "float64"}
        )
        # Set the index of the rows that remained.
        expected = expected.set_index(pd.Index([1, 2]))
        # Check.
        hunitest.compare_df(actual, expected)

    def test_drop_rows2(self) -> None:
        """
        Test if non fully nan row is not dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [np.nan, 2, 3],
            "dummy_value_2": ["A", "B", "C"],  # type: ignore
            "dummy_value_3": [None, 1.0, 1.0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.drop_axis_with_all_nans(test_df, drop_rows=True)
        # Prepare expected result.
        expected = {
            "dummy_value_1": [np.nan, 2, 3],
            "dummy_value_2": ["A", "B", "C"],  # type: ignore
            "dummy_value_3": [None, 1.0, 1.0],
        }
        # Set the dtype of numeral columns to float to match the dataframe after NA dropping.
        expected = pd.DataFrame(data=expected).astype(
            {"dummy_value_1": "float64"}
        )
        # Set the index of the rows that remained.
        expected = expected.set_index(pd.Index([0, 1, 2]))
        # Check.
        hunitest.compare_df(actual, expected)

    def test_drop_columns1(self) -> None:
        """
        Test if column full of nans is dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [np.nan, pd.NA, None],
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [1.0, 1.0, 1.0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.drop_axis_with_all_nans(test_df, drop_columns=True)
        # Prepare expected result.
        expected = {
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [1.0, 1.0, 1.0],
        }
        expected = pd.DataFrame(data=expected)
        # Check.
        hunitest.compare_df(actual, expected)

    def test_drop_columns2(self) -> None:
        """
        Test if column that is not full of nans is not dropped.
        """
        # Prepare actual result.
        test_data = {
            "dummy_value_1": [np.nan, 2, None],
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [1.0, 1.0, 1.0],
        }
        test_df = pd.DataFrame(data=test_data)
        # Drop NA.
        actual = hpandas.drop_axis_with_all_nans(test_df, drop_columns=True)
        # Prepare expected result.
        expected = {
            "dummy_value_1": [np.nan, 2, None],
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [1.0, 1.0, 1.0],
        }
        expected = pd.DataFrame(data=expected)
        # Check.
        hunitest.compare_df(actual, expected)


class TestDropDuplicates(hunitest.TestCase):
    """
    Test that duplicates are dropped correctly.
    """

    @staticmethod
    def get_test_data() -> pd.DataFrame:
        test_data = [
            (1, "A", 3.2),
            (1, "A", 3.2),
            (10, "B", 3.2),
            (8, "A", 3.2),
            (4, "B", 8.2),
            (10, "B", 3.2),
        ]
        index = [
            "dummy_value1",
            "dummy_value3",
            "dummy_value2",
            "dummy_value1",
            "dummy_value1",
            "dummy_value2",
        ]
        columns = ["int", "letter", "float"]
        df = pd.DataFrame(data=test_data, index=index, columns=columns)
        return df

    def test_drop_duplicates1(self) -> None:
        """
        - use_index = True
        - subset is not None
        """
        # Prepare test data.
        df = self.get_test_data()
        use_index = True
        subset = ["float"]
        no_duplicates_df = hpandas.drop_duplicates(df, use_index, subset=subset)
        no_duplicates_df = hpandas.df_to_str(no_duplicates_df)
        # Prepare expected result.
        expected_signature = r"""
                      int letter  float
        dummy_value1    1      A    3.2
        dummy_value3    1      A    3.2
        dummy_value2   10      B    3.2
        dummy_value1    4      B    8.2
        """
        # Check.
        self.assert_equal(no_duplicates_df, expected_signature, fuzzy_match=True)

    def test_drop_duplicates2(self) -> None:
        """
        - use_index = True
        - subset = None
        """
        # Prepare test data.
        df = self.get_test_data()
        use_index = True
        no_duplicates_df = hpandas.drop_duplicates(df, use_index)
        no_duplicates_df = hpandas.df_to_str(no_duplicates_df)
        # Prepare expected result.
        expected_signature = r"""
                      int letter  float
        dummy_value1    1      A    3.2
        dummy_value3    1      A    3.2
        dummy_value2   10      B    3.2
        dummy_value1    8      A    3.2
        dummy_value1    4      B    8.2
        """
        # Check.
        self.assert_equal(no_duplicates_df, expected_signature, fuzzy_match=True)

    def test_drop_duplicates3(self) -> None:
        """
        - use_index = False
        - subset = None
        """
        # Prepare test data.
        df = self.get_test_data()
        use_index = False
        no_duplicates_df = hpandas.drop_duplicates(df, use_index)
        no_duplicates_df = hpandas.df_to_str(no_duplicates_df)
        # Prepare expected result.
        expected_signature = r"""
                      int letter  float
        dummy_value1    1      A    3.2
        dummy_value2   10      B    3.2
        dummy_value1    8      A    3.2
        dummy_value1    4      B    8.2
        """
        # Check.
        self.assert_equal(no_duplicates_df, expected_signature, fuzzy_match=True)

    def test_drop_duplicates4(self) -> None:
        """
        - use_index = False
        - subset is not None
        """
        # Prepare test data.
        df = self.get_test_data()
        use_index = False
        subset = ["letter", "float"]
        no_duplicates_df = hpandas.drop_duplicates(df, use_index, subset)
        no_duplicates_df = hpandas.df_to_str(no_duplicates_df)
        # Prepare expected result.
        expected_signature = r"""
                      int letter  float
        dummy_value1    1      A    3.2
        dummy_value2   10      B    3.2
        dummy_value1    4      B    8.2
        """
        # Check.
        self.assert_equal(no_duplicates_df, expected_signature, fuzzy_match=True)
