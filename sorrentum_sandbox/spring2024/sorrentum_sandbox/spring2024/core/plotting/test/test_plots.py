import logging
import unittest

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import core.plotting.boxplot as cploboxp
import core.plotting.correlation as cplocorr
import core.plotting.misc_plotting as cplmiplo
import core.plotting.normality as cplonorm
import core.plotting.portfolio_binned_stats as cppobist
import core.plotting.visual_stationarity_test as cpvistte

_LOG = logging.getLogger(__name__)


class Test_plots(unittest.TestCase):
    """
    Run smoke tests for plotting functions.
    """

    @staticmethod
    def get_test_plot_df1() -> pd.DataFrame:
        """
        Generate a DataFrame with random values to test plotting functions.
        """
        data = {
            "Column1": np.random.rand(100),
            "Column2": np.random.rand(100),
            "Column3": np.random.rand(100),
            "Column4": np.random.rand(100),
        }
        df = pd.DataFrame(data)
        return df

    @staticmethod
    def get_test_plot_srs1() -> pd.Series:
        """
        Generate a test data with normal distribution series and timestamps.
        """
        rng = np.random.default_rng(seed=0)
        samples = rng.normal(size=100)
        index = pd.date_range(start="2023-01-31", periods=len(samples), freq="H")
        srs = pd.Series(samples, index=index, name="test values")
        return srs

    @staticmethod
    def get_plot_projection1() -> pd.DataFrame:
        """
        Generate a test DataFrame for `plot_projection()`.
        """
        data = [
            [1, 1, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ]
        index = pd.date_range(start="2023-01-01", periods=len(data), freq="D")
        df = pd.DataFrame(data, index=index)
        return df

    @staticmethod
    def get_plot_portfolio_binned_stats1() -> pd.DataFrame:
        """
        Generate a test DataFrame for `plot_portfolio_binned_stats()`.
        """
        index = pd.date_range("2000-01-01 14:35:00", periods=10, freq="5T")
        columns = pd.MultiIndex.from_tuples(
            [
                ("prediction", 1467591036),
                ("prediction", 3303714233),
                ("holdings_notional", 1467591036),
                ("holdings_notional", 3303714233),
                ("pnl", 1467591036),
                ("pnl", 3303714233),
            ],
            names=[None, "asset_id"],
        )
        data = np.random.rand(len(index), len(columns))
        df = pd.DataFrame(data, index=index, columns=columns)
        return df

    def test_plot_histograms_and_lagged_scatterplot1(self) -> None:
        """
        Smoke test for `plot_histograms_and_lagged_scatterplot()`.
        """
        # Set inputs.
        srs = Test_plots.get_test_plot_srs1()
        lag = 7
        # Plot.
        cpvistte.plot_histograms_and_lagged_scatterplot(
            srs, lag, figsize=(20, 10)
        )

    def test_plot_time_series_by_period1(self) -> None:
        """
        Smoke test for `plot_time_series_by_period()`.
        """
        test_series = self.get_test_plot_srs1()
        period = "day"
        cplmiplo.plot_time_series_by_period(test_series, period)

    def test_plot_time_series_by_period2(self) -> None:
        """
        Smoke test for `plot_time_series_by_period()`.
        """
        test_series = self.get_test_plot_srs1()
        period = "time"
        cplmiplo.plot_time_series_by_period(test_series, period)

    def test_plot_heatmap1(self) -> None:
        """
        Smoke test for `plot_heatmap()`
        """
        mode = "clustermap"
        corr_df = self.get_test_plot_df1()
        cplocorr.plot_heatmap(corr_df, mode, figsize=(20, 10))

    def test_plot_effective_correlation_rank1(self) -> None:
        """
        Smoke test for `plot_effective_correlation_rank()`.

        - `q_values = None`
        """
        test_df = self.get_test_plot_df1()
        cplocorr.plot_effective_correlation_rank(test_df)

    def test_plot_effective_correlation_rank2(self) -> None:
        """
        Smoke test for `plot_effective_correlation_rank()`.

        - `q_values` is a list of values"
        """
        num_q_values = 5
        q_values = np.random.uniform(1, 10, num_q_values).tolist()
        test_df = self.get_test_plot_df1()
        cplocorr.plot_effective_correlation_rank(test_df, q_values)

    def test_plot_timeseries_distribution1(self) -> None:
        """
        Smoke test for 'plot_timeseries_distribution()'.
        """
        srs = self.get_test_plot_srs1()
        datetime_types = ["hour"]
        cplmiplo.plot_timeseries_distribution(srs, datetime_types)

    def test_plot_timeseries_distribution2(self) -> None:
        """
        Smoke test for 'plot_timeseries_distribution()'.
        """
        srs = self.get_test_plot_srs1()
        datetime_types = ["hour", "month"]
        cplmiplo.plot_timeseries_distribution(srs, datetime_types)

    def test_plot_spectrum1(self) -> None:
        """
        Smoke test for `plot_spectrum()`.

        - `axes = None`
        """
        test_df = self.get_test_plot_df1()
        cplmiplo.plot_spectrum(test_df)

    def test_plot_spectrum2(self) -> None:
        """
        Smoke test for `plot_spectrum()`.

        - `axes` is a list of Matplotlib axes
        """
        test_df = self.get_test_plot_df1()
        _, axes = plt.subplots(2, 2, figsize=(20, 10))
        axes_flat = axes.flatten()
        cplmiplo.plot_spectrum(signal=test_df, axes=axes_flat)

    def test_plot_cols1(self) -> None:
        """
        Smoke test for `plot_cols()`.
        """
        test_df = self.get_test_plot_df1()
        cplmiplo.plot_cols(test_df)

    def test_plot_autocorrelation1(self) -> None:
        """
        Smoke test for `plot_autocorrelation()`.
        """
        test_df = self.get_test_plot_df1()
        cplmiplo.plot_autocorrelation(test_df)

    def test_plot_projection1(self) -> None:
        """
        Smoke test for `plot_projection()`.
        """
        test_df = self.get_plot_projection1()
        special_values = [0]
        cplmiplo.plot_projection(test_df, special_values=special_values)

    def test_plot_projection2(self) -> None:
        """
        Smoke test for `plot_projection()`.

        - `mode = "scatter"`
        - `ax` is used for plotting
        """
        # Set input values with some empty values.
        test_df = self.get_plot_projection1()
        test_df = test_df.replace({0: None})
        # Set params.
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        mode = "scatter"
        # Run.
        cplmiplo.plot_projection(test_df, mode=mode, ax=ax)

    def test_plot_boxplot1(self) -> None:
        """
        Smoke test for `plot_boxplot()`.

        - `grouping = "by_row"`
        - `ylabel` is an empty string
        """
        test_df = self.get_test_plot_df1()
        cploboxp.plot_boxplot(test_df)

    def test_plot_boxplot2(self) -> None:
        """
        Smoke test for `plot_boxplot()`.

        - `grouping = "by_col"`
        - `ylabel` is a non-empty string
        """
        test_df = self.get_test_plot_df1()
        grouping = "by_col"
        ylabel = "Test Label"
        cploboxp.plot_boxplot(test_df, grouping=grouping, ylabel=ylabel)

    def test_plot_qq1(self) -> None:
        """
        Smoke test for `plot_qq()`.
        """
        test_series = self.get_test_plot_srs1()
        cplonorm.plot_qq(test_series)

    def test_plot_qq2(self) -> None:
        """
        Smoke test for `plot_qq()`.

        - Input series contains NaN values
        - `nan_mode = "drop"`
        - Axes are passed
        """
        test_series = self.get_test_plot_srs1()
        test_series[20:50] = np.nan
        _, axes = plt.subplots(1, 1, figsize=(10, 10))
        dist = "norm"
        nan_mode = "drop"
        cplonorm.plot_qq(test_series, ax=axes, dist=dist, nan_mode=nan_mode)

    def test_plot_portfolio_binned_stats1(self) -> None:
        """
        Smoke test for `plot_portfolio_binned_stats()`.

        Input is a DataFrame with 2 MultiIndex column levels.
        """
        test_df = self.get_plot_portfolio_binned_stats1()
        proportion_of_data_per_bin = 0.2
        normalize_prediction_col_values = True
        y_scale = 4
        cppobist.plot_portfolio_binned_stats(
            test_df,
            proportion_of_data_per_bin,
            normalize_prediction_col_values=normalize_prediction_col_values,
            y_scale=y_scale,
        )

    def test_plot_portfolio_binned_stats2(self) -> None:
        """
        Smoke test for `plot_portfolio_binned_stats()`.

        Input is a dict of 2 DataFrames with 2 MultiIndex column levels.
        """
        test_df = self.get_plot_portfolio_binned_stats1()
        test_dict = {
            "df1": test_df,
            "df2": test_df * 2,
        }
        proportion_of_data_per_bin = 0.2
        cppobist.plot_portfolio_binned_stats(test_df, proportion_of_data_per_bin)
