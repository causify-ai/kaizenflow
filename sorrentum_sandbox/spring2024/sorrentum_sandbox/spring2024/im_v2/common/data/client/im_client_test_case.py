"""
Import as:

import im_v2.common.data.client.im_client_test_case as imvcdcimctc
"""

from typing import Any, List

import pandas as pd

import helpers.hunit_test as hunitest
import helpers.hunit_test_utils as hunteuti
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

# #############################################################################
# ImClientTestCase
# #############################################################################


# Inherit from `Obj_to_str_TestCase` to also exercise `__str()__` and `__repr()__`.
class ImClientTestCase(hunitest.TestCase, hunteuti.Obj_to_str_TestCase):
    """
    Help test classes for classes derived from `ImClient` by implementing
    template test methods for the interface methods in any `ImClient`.
    """

    # TODO(gp): To enforce that all methods are called we could add corresponding
    #  abstract methods to the test methods.

    # TODO(gp): not sure this adds value over using a list as in _test_read_data2.
    # TODO(gp): to keep things more maintanable we should find better meaningful names
    #  rather than 1, 2, ...
    def _test_read_data1(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for one full symbol
        - start_ts = end_ts = None
        - resample_1min = True
        """
        full_symbols = [full_symbol]
        start_ts = None
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    def _test_read_data2(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for two or more full symbols
        - start_ts = end_ts = None
        - resample_1min = True
        """
        start_ts = None
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    def _test_read_data3(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: pd.Timestamp,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for two or more symbols
        - specified start_ts
        - end_ts = None
        - resample_1min = True
        """
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    def _test_read_data4(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        end_ts: pd.Timestamp,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for two or more symbols
        - start_ts = None
        - specified end_ts
        - resample_1min = True
        """
        start_ts = None
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    def _test_read_data5(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for two or more symbols
        - specified start_ts and end_ts
        - resample_1min = True
        """
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    def _test_read_data6(
        self, im_client: icdc.ImClient, full_symbol: ivcu.FullSymbol
    ) -> None:
        """
        Test:
        - error is raised when an unsupported full symbol is provided
        - start_ts = end_ts = None
        - resample_1min = True
        """
        full_symbols = [full_symbol]
        start_ts = None
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        # TODO(gp): We should raise a more specific assertion and / or
        #  check part of the exception as a string.
        with self.assertRaises(AssertionError):
            im_client.read_data(
                full_symbols, start_ts, end_ts, columns, filter_data_mode
            )

    def _test_read_data7(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Test:
        - reading data for two or more full symbols
        - reading not resampled data
        - start_ts = end_ts = None
        - resample_1min = False
        """
        start_ts = None
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        self.check_df_output(actual_df, *args, **kwargs)

    # ////////////////////////////////////////////////////////////////////////

    def _test_filter_columns1(
        self,
        im_client: icdc.ImClient,
        full_symbols: List[ivcu.FullSymbol],
        columns: List[str],
    ) -> None:
        """
        Test that columns have been filtered correctly:

        - requested columns = received columns
        """
        start_ts = None
        end_ts = None
        filter_data_mode = "assert"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        actual_columns = actual_df.columns.tolist()
        self.assert_equal(str(actual_columns), str(columns))

    def _test_filter_columns2(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        columns: List[str],
    ) -> None:
        """
        Test that error is raised when requested columns != received columns:

        - `filter_data_mode` = "assert"
        """
        full_symbols = [full_symbol]
        start_ts = None
        end_ts = None
        filter_data_mode = "assert"
        with self.assertRaises(AssertionError):
            im_client.read_data(
                full_symbols, start_ts, end_ts, columns, filter_data_mode
            )

    def _test_filter_columns3(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        columns: List[str],
    ) -> None:
        """
        Test that error is raised when requested columns != received columns:

        - full symbol column is not requested but is still returned
        - `filter_data_mode` = "assert"
        """
        full_symbols = [full_symbol]
        start_ts = None
        end_ts = None
        filter_data_mode = "assert"
        with self.assertRaises(AssertionError):
            im_client.read_data(
                full_symbols, start_ts, end_ts, columns, filter_data_mode
            )

    def _test_filter_columns4(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        columns: List[str],
    ) -> None:
        """
        Test that columns have been filtered correctly:

        - full symbol column is not requested and trimmed under the hood
        - `filter_data_mode` = "warn_and_trim"
        """
        full_symbols = [full_symbol]
        start_ts = None
        end_ts = None
        filter_data_mode = "warn_and_trim"
        actual_df = im_client.read_data(
            full_symbols, start_ts, end_ts, columns, filter_data_mode
        )
        # Check output.
        actual_columns = actual_df.columns.tolist()
        self.assert_equal(str(actual_columns), str(columns))

    # ////////////////////////////////////////////////////////////////////////

    def _test_get_start_ts_for_symbol1(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        expected_start_ts: pd.Timestamp,
    ) -> None:
        """
        Test that the earliest timestamp available is computed correctly.
        """
        actual_start_ts = im_client.get_start_ts_for_symbol(full_symbol)
        self.assertEqual(actual_start_ts, expected_start_ts)

    def _test_get_end_ts_for_symbol1(
        self,
        im_client: icdc.ImClient,
        full_symbol: ivcu.FullSymbol,
        expected_end_ts: pd.Timestamp,
    ) -> None:
        """
        Test that the latest timestamp available is computed correctly.
        """
        actual_end_ts = im_client.get_end_ts_for_symbol(full_symbol)
        # TODO(Grisha): use `assertGreater` when start downloading more data.
        self.assertEqual(actual_end_ts, expected_end_ts)

    # ////////////////////////////////////////////////////////////////////////

    def _test_get_universe1(
        self,
        # TODO(Grisha): pass vendor when we start testing `CDD`.
        im_client: icdc.ImClient,
        expected_length: int,
        expected_first_elements: List[ivcu.FullSymbol],
        expected_last_elements: List[ivcu.FullSymbol],
    ) -> None:
        """
        Test that universe is computed correctly.
        """
        # TODO(gp): We might want to sort actual and expected universe for
        #  stability.
        universe = im_client.get_universe()
        actual_length = len(universe)
        actual_first_elements = universe[:3]
        actual_last_elements = universe[-3:]
        self.assertEqual(actual_length, expected_length)
        self.assertEqual(actual_first_elements, expected_first_elements)
        self.assertEqual(actual_last_elements, expected_last_elements)

    # TODO(Grisha): @Dan move to `ImClientMetadataTestCase`.
    def _test_get_metadata1(
        self, im_client: icdc.ImClient, *args: Any, **kwargs: Any
    ) -> None:
        """
        Test that metadata is computed correctly.
        """
        actual_df = im_client.get_metadata()
        self.check_df_output(actual_df, *args, **kwargs)
