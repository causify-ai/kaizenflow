"""
Import as:

import core.information_bars.test.test_bars as bttbar
"""

import os

import core.information_bars.bars as cinbabar
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

class TestBars(hunitest.TestCase):
    def test_get_tick_bars(self) -> None:
        """
        Test that tick bar creation works.
        """
        file_path = self._get_input_file_path()
        actual = cinbabar.get_tick_bars(file_path, threshold=10)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test_get_volume_bars(self) -> None:
        """
        Test that volume bar creation works.
        """
        file_path = self._get_input_file_path()
        actual = cinbabar.get_volume_bars(file_path, threshold=10)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test_get_dollar_bars(self) -> None:
        """
        Test that dollar bar creation works.
        """
        file_path = self._get_input_file_path()
        actual = cinbabar.get_dollar_bars(file_path, threshold=10)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def _get_input_file_path(self) -> str:
        """
        Get file path to input CSV file for a current test.

        :returns path to input file for this test
        """
        file_name = "input.csv"
        file_name = os.path.join(self.get_input_dir(), file_name)
        file_name = os.path.abspath(file_name)
        return file_name
