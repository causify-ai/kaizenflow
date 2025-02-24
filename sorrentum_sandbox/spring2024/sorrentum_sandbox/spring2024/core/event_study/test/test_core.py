import collections
import logging

import numpy as np
import pandas as pd

import core.event_study as esf
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestBuildLocalTimeseries(hunitest.TestCase):
    def test_minutely1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "T"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        relative_grid_indices = list(range(-10, 10)) + [14]
        idx = pd.date_range(start_date, periods=n_periods, freq=freq)
        events = pd.DataFrame(data={"ind": 1}, index=idx)
        grid_idx = pd.date_range(
            start_date - pd.Timedelta(f"50{freq}"),
            freq=freq,
            periods=n_periods + 100,
        )
        grid_data = pd.DataFrame(np.random.randn(len(grid_idx)), index=grid_idx)
        info: collections.OrderedDict = collections.OrderedDict()
        local_ts = esf.build_local_timeseries(
            events, grid_data, relative_grid_indices, info=info
        )
        str_info = str(info).replace("None", f"'{freq}'")
        self.check_string(f"local_ts:\n{local_ts.to_string()}\ninfo:\n{str_info}")

    def test_daily1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "D"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        relative_grid_indices = list(range(-10, 10)) + [14]
        idx = pd.date_range(start_date, periods=n_periods, freq=freq)
        events = pd.DataFrame(data={"ind": 1}, index=idx)
        grid_idx = pd.date_range(
            start_date - pd.Timedelta(f"50{freq}"),
            freq=freq,
            periods=n_periods + 100,
        )
        grid_data = pd.DataFrame(np.random.randn(len(grid_idx)), index=grid_idx)
        info: collections.OrderedDict = collections.OrderedDict()
        local_ts = esf.build_local_timeseries(
            events, grid_data, relative_grid_indices, info=info
        )
        str_info = str(info).replace("None", f"'{freq}'")
        self.check_string(f"local_ts:\n{local_ts.to_string()}\ninfo:\n{str_info}")

    def test_daily_shift_freq1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "D"
        shift_freq = "2D"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        relative_grid_indices = list(range(-10, 10)) + [14]
        idx = pd.date_range(start_date, periods=n_periods, freq=freq)
        events = pd.DataFrame(data={"ind": 1}, index=idx)
        grid_idx = pd.date_range(
            start_date - pd.Timedelta(f"50{freq}"),
            freq=freq,
            periods=n_periods + 100,
        )
        grid_data = pd.DataFrame(np.random.randn(len(grid_idx)), index=grid_idx)
        info: collections.OrderedDict = collections.OrderedDict()
        local_ts = esf.build_local_timeseries(
            events, grid_data, relative_grid_indices, freq=shift_freq, info=info
        )
        str_info = str(info).replace("None", f"'{freq}'")
        self.check_string(f"local_ts:\n{local_ts.to_string()}\ninfo:\n{str_info}")

    def test_multiple_responses_daily1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "D"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        n_cols = 2
        relative_grid_indices = list(range(-10, 10)) + [14]
        idx = pd.date_range(start_date, periods=n_periods, freq=freq)
        events = pd.DataFrame(data={"ind": 1}, index=idx)
        grid_idx = pd.date_range(
            start_date - pd.Timedelta(f"50{freq}"),
            freq=freq,
            periods=n_periods + 100,
        )
        grid_data = pd.DataFrame(
            np.random.randn(len(grid_idx), n_cols), index=grid_idx
        )
        info: collections.OrderedDict = collections.OrderedDict()
        local_ts = esf.build_local_timeseries(
            events, grid_data, relative_grid_indices, info=info
        )
        str_info = str(info).replace("None", f"'{freq}'")
        self.check_string(f"local_ts:\n{local_ts.to_string()}\ninfo:\n{str_info}")


class TestUnwrapLocalTimeseries(hunitest.TestCase):
    def test_daily1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "D"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        relative_grid_indices = list(range(-10, 10)) + [14]
        timestamps = pd.date_range(start_date, periods=n_periods, freq=freq)
        idx = pd.MultiIndex.from_product([relative_grid_indices, timestamps])
        local_ts = pd.DataFrame(np.random.randn(len(idx)), index=idx)
        grid_data = pd.DataFrame(np.random.randn(n_periods), index=timestamps)
        unwrapped = esf.unwrap_local_timeseries(local_ts, grid_data)
        self.check_string(unwrapped.to_string())

    def test_minutely1(self) -> None:
        np.random.seed(42)
        n_periods = 10
        freq = "T"
        start_date = pd.Timestamp("2009-09-29 10:00:00")
        relative_grid_indices = list(range(-10, 10)) + [14]
        timestamps = pd.date_range(start_date, periods=n_periods, freq=freq)
        idx = pd.MultiIndex.from_product([relative_grid_indices, timestamps])
        local_ts = pd.DataFrame(np.random.randn(len(idx)), index=idx)
        grid_data = pd.DataFrame(np.random.randn(n_periods), index=timestamps)
        unwrapped = esf.unwrap_local_timeseries(local_ts, grid_data)
        self.check_string(unwrapped.to_string())
