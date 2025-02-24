import datetime
import logging
from typing import Tuple

import pandas as pd

import dataflow.core.utils as dtfcorutil
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_df_info_as_string(hunitest.TestCase):
    def test1(self) -> None:
        df = pd.DataFrame({"col_1": [1, 2], "col_2": [3, 4]})
        info = dtfcorutil.get_df_info_as_string(df, exclude_memory_usage=False)
        self.check_string(info)

    def test2(self) -> None:
        df = pd.DataFrame({"col_1": [1, 2], "col_2": [3, 4]})
        info = dtfcorutil.get_df_info_as_string(df)
        self.check_string(info)


class Test_get_DagBuilder_name_from_string(hunitest.TestCase):
    """
    Test that the function returns a correct DAG builder name.
    """

    def test1(self) -> None:
        dag_builder_ctor_as_str = (
            "dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder"
        )
        act = dtfcorutil.get_DagBuilder_name_from_string(dag_builder_ctor_as_str)
        exp = "C1b"
        self.assert_equal(act, exp)

    def test2(self) -> None:
        dag_builder_ctor_as_str = (
            "dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
        )
        act = dtfcorutil.get_DagBuilder_name_from_string(dag_builder_ctor_as_str)
        exp = "C3a"
        self.assert_equal(act, exp)

    def test3(self) -> None:
        dag_builder_ctor_as_str = (
            "dataflow_lemonade.pipelines.C5.C5b_pipeline.C5b_DagBuilder"
        )
        act = dtfcorutil.get_DagBuilder_name_from_string(dag_builder_ctor_as_str)
        exp = "C5b"
        self.assert_equal(act, exp)


class Test_convert_to_multiindex(hunitest.TestCase):
    @staticmethod
    def get_test_data_multiple_asset() -> Tuple[pd.DataFrame, pd.MultiIndex]:
        """
        Function that return dummy dataframe with multiple asset id and
        Multiindex.
        """
        data = {
            "id": [13684, 17085, 13684, 17085, 13684],
            "close": [None, None, None, None, None],
            "volume": [0, 0, 0, 0, 0],
        }
        index = pd.to_datetime(
            ["2022-01-04 09:01:00-05:00"] * 2
            + ["2022-01-04 09:02:00-05:00"] * 2
            + ["2022-01-04 09:03:00-05:00"]
        )
        df = pd.DataFrame(data, index=index)
        expected_df_columns = pd.MultiIndex.from_product(
            [["close", "volume"], [13684, 17085]], names=[None, "id"]
        )
        return df, expected_df_columns

    @staticmethod
    def get_test_data_single_asset() -> Tuple[pd.DataFrame, pd.MultiIndex]:
        """
        Function that return dummy dataframe with single asset id and
        Multiindex.
        """
        data = {
            "id": [13684, 13684, 13684],
            "close": [None, None, None],
            "volume": [0, 0, 0],
        }
        index = pd.to_datetime(
            [
                "2022-01-04 09:01:00-05:00",
                "2022-01-04 09:02:00-05:00",
                "2022-01-04 09:03:00-05:00",
            ]
        )
        df = pd.DataFrame(data, index=index)
        expected_df_columns = pd.MultiIndex.from_product(
            [["close", "volume"], [13684]], names=[None, "id"]
        )
        return df, expected_df_columns

    def assert_multiindex_columns_equal(
        self, expected_df_columns: pd.MultiIndex, actual_df: pd.DataFrame
    ) -> None:
        """
        Compare the list of columns of actual df and and expected df.
        """
        expected_df_columns = str(expected_df_columns.to_list())
        actual_df_columns = str(actual_df.columns.to_list())
        self.assert_equal(expected_df_columns, actual_df_columns)

    def test1(self) -> None:
        """
        Test that a function transforms the DataFrame correctly.
        """
        # Prepare input and expected output.
        df, expected_df_columns = self.get_test_data_multiple_asset()
        asset_id_col = "id"
        # Prepare the actual output by running function.
        actual_df = dtfcorutil.convert_to_multiindex(df, asset_id_col)
        # Compare the result.
        self.assert_multiindex_columns_equal(expected_df_columns, actual_df)

    def test2(self) -> None:
        """
        Test that a function handles a DataFrame with duplicate rows correctly.
        """
        # Prepare input and expected output.
        df, expected_df_columns = self.get_test_data_multiple_asset()
        asset_id_col = "id"
        df = pd.concat([df, df.head(1)])
        # Prepare the actual output by running function.
        actual_df = dtfcorutil.convert_to_multiindex(df, asset_id_col)
        # Compare the result.
        self.assert_multiindex_columns_equal(expected_df_columns, actual_df)

    def test3(self) -> None:
        """
        Test that a function handles an empty dataframe correctly.
        """
        # Creating empty data frame for input.
        df = pd.DataFrame(columns=["id", "close", "volume"])
        asset_id_col = "id"
        with self.assertRaises(AssertionError) as context:
            dtfcorutil.convert_to_multiindex(df, asset_id_col)
        actual_error_message = str(context.exception)
        expected_error_message = r"""
        ################################################################################
        * Failed assertion *
        1 <= 0
        ################################################################################
        """
        self.assert_equal(
            actual_error_message, expected_error_message, fuzzy_match=True
        )

    def test4(self) -> None:
        """
        Test that a function handles a DataFrame with only one asset correctly.
        """
        # Prepare input and expected output.
        df, expected_df_columns = self.get_test_data_single_asset()
        asset_id_col = "id"
        # Prepare the actual output by running function.
        actual_df = dtfcorutil.convert_to_multiindex(df, asset_id_col)
        # Compare the result.
        self.assert_multiindex_columns_equal(expected_df_columns, actual_df)

    def test5(self) -> None:
        """
        Test that a function handles the case where the asset_id_col doesn't
        exist.
        """
        # Prepare input and expected output.
        df = self.get_test_data_single_asset()
        asset_id_col = "nonexistent_column"
        with self.assertRaises(AssertionError) as context:
            dtfcorutil.convert_to_multiindex(df, asset_id_col)
        # Get the actual error message
        actual_error_message = str(context.exception)
        expected_error_message = r"""
        ################################################################################
        * Failed assertion *
        Instance of '(                              id close  volume
        2022-01-04 09:01:00-05:00  13684  None       0
        2022-01-04 09:02:00-05:00  13684  None       0
        2022-01-04 09:03:00-05:00  13684  None       0, MultiIndex([( 'close', 13684),
                                ('volume', 13684)],
                                                      names=[None, 'id']))' is '<class 'tuple'>' instead of '<class 'pandas.core.frame.DataFrame'>'
        ################################################################################
        """
        self.assert_equal(
            actual_error_message, expected_error_message, fuzzy_match=True
        )

    def test6(self) -> None:
        """
        Test that a function handles the case where there is no index in the
        dataframe.
        """
        # Prepare input and expected output.
        df, expected_df_columns = self.get_test_data_single_asset()
        asset_id_col = "id"
        df = df.reset_index(drop=True)
        # Prepare the actual output by running function.
        actual_df = dtfcorutil.convert_to_multiindex(df, asset_id_col)
        # Compare the result.
        self.assert_multiindex_columns_equal(expected_df_columns, actual_df)


class Test_find_min_max_timestamps_from_intervals(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check for the case when no intervals are provided.
        """
        intervals = None
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (None, None)
        self.assertEqual(actual, expected)

    def test2(self) -> None:
        """
        Check for a single interval where both endpoints are empty.
        """
        intervals = [(None, None)]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (None, None)
        self.assertEqual(actual, expected)

    def test3(self) -> None:
        """
        Check for a single interval with valid endpoints.
        """
        intervals = [
            (
                datetime.datetime(2022, 1, 1, 10, 0, 0),
                datetime.datetime(2022, 1, 1, 11, 0, 0),
            )
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (
            datetime.datetime(2022, 1, 1, 10, 0, 0),
            datetime.datetime(2022, 1, 1, 11, 0, 0),
        )
        self.assertEqual(actual, expected)

    def test4(self) -> None:
        """
        Check for a single interval where both endpoints are the same.
        """
        intervals = [
            (
                pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
                pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
            )
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (
            pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
            pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
        )
        self.assertEqual(actual, expected)

    def test5(self) -> None:
        """
        Check for multiple intervals with a mix of valid and empty endpoints.
        """
        intervals = [
            (pd.Timestamp(2022, 1, 1, 10, tz="UTC"), None),
            (None, pd.Timestamp(2022, 1, 1, 11, tz="UTC")),
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (None, None)
        self.assertEqual(actual, expected)

    def test6(self) -> None:
        """
        Check for multiple intervals with valid endpoints.
        """
        intervals = [
            (
                pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
                pd.Timestamp(2022, 1, 1, 11, tz="UTC"),
            ),
            (
                pd.Timestamp(2022, 1, 1, 6, tz="UTC"),
                pd.Timestamp(2022, 1, 1, 9, tz="UTC"),
            ),
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (
            pd.Timestamp(2022, 1, 1, 6, tz="UTC"),
            pd.Timestamp(2022, 1, 1, 11, tz="UTC"),
        )
        self.assertEqual(actual, expected)

    def test7(self) -> None:
        """
        Check for multiple intervals with valid endpoints of different time
        zones.
        """
        intervals = [
            (
                pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
                pd.Timestamp(2022, 1, 1, 11, tz="UTC"),
            ),
            (
                pd.Timestamp(2022, 1, 1, 10, tz="EST"),
                pd.Timestamp(2022, 1, 1, 11, tz="EST"),
            ),
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (
            pd.Timestamp(2022, 1, 1, 10, tz="UTC"),
            pd.Timestamp(2022, 1, 1, 11, tz="EST"),
        )
        self.assertEqual(actual, expected)

    def test8(self) -> None:
        """
        Check for an interval with different endpoint types.
        """
        intervals = [
            (
                datetime.datetime(
                    2022, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                ),
                pd.Timestamp(2022, 1, 1, 11, tz="UTC"),
            )
        ]
        actual = dtfcorutil.find_min_max_timestamps_from_intervals(intervals)
        expected = (
            datetime.datetime(2022, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
            pd.Timestamp(2022, 1, 1, 11, tz="UTC"),
        )
        self.assertEqual(actual, expected)
