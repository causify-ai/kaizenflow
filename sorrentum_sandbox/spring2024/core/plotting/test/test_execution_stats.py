import logging
import unittest.mock as umock

import pandas as pd

import core.plotting.execution_stats as cplexsta
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_plot_adj_fill_ecdfs(hunitest.TestCase):
    """
    Run tests for plotting `plot_adj_fill_ecdfs` function.
    """

    @umock.patch("logging.Logger.info")
    def test_plot_adj_fill_ecdfs1(self, mock_log_info) -> None:
        """
        Test with empty dataframe.
        """
        df = pd.DataFrame()
        # Plot the ECDFs.
        cplexsta._plot_adj_fill_ecdfs_single_df(df, 1, 10)
        # Check the log message.
        mock_log_info.assert_called_with("No trades found for wave id=%d", 1)

    @umock.patch("logging.Logger.info")
    def test_plot_execution_stat2(self, mock_log_info) -> None:
        """
        Test for the case where all trades for wave_id were conducted
        immediately.

        Case when the index is 0.0.
        """
        df = pd.DataFrame(
            {1467591036: [0.11], 1464553467: [0.053]},
            index=pd.Index([0.0], name="secs_to_fill"),
        )
        # Plot the ECDFs.
        cplexsta._plot_adj_fill_ecdfs_single_df(df, 1, 10)
        # Check the log message.
        mock_log_info.assert_called_with(
            "All trades for wave_id=%d were conducted immediately (with rounding)",
            1,
        )

    @umock.patch("logging.Logger.info")
    def test_plot_execution_stat3(self, mock_log_info) -> None:
        """
        Test for the case where all trades for wave_id were conducted
        immediately.

        Case when the index is non-zero and the number of columns is 1.
        """
        df = pd.DataFrame(
            {1467591036: [0.11]}, index=pd.Index([7.719], name="secs_to_fill")
        )
        # Plot the ECDFs.
        cplexsta._plot_adj_fill_ecdfs_single_df(df, 1, 10)
        # Check the log message.
        mock_log_info.assert_called_with(
            "All trades for wave_id=%d were conducted immediately (with rounding)",
            1,
        )

    def test_plot_execution_stat4(self) -> None:
        """
        Test for the case where the DataFrame has a non-zero index value and
        more than one column.
        """
        df = pd.DataFrame(
            {1467591036: [0.11], 1464553467: [0.053]},
            index=pd.Index([7.719], name="secs_to_fill"),
        )
        # Check.
        with self.assertRaises(AssertionError):
            cplexsta._plot_adj_fill_ecdfs_single_df(df, 1, 10)
