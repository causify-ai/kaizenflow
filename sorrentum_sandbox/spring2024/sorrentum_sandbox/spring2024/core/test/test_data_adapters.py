import logging
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

import core.data_adapters as cdatadap
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

if henv.has_module("gluonts"):
    import gluonts
    import gluonts.dataset.artificial as gda

    import gluonts.dataset.common as gdc  # isort: skip # noqa: F401 # pylint: disable=unused-import

    # TODO(*): gluon needs this import to work properly.
    import gluonts.model.forecast as gmf  # isort: skip # noqa: F401 # pylint: disable=unused-import


_LOG = logging.getLogger(__name__)


class _TestAdapter:
    def __init__(self, n_rows: int = 100, n_cols: int = 5):
        self._frequency = "T"
        self._n_rows = n_rows
        self._n_cols = n_cols
        self._df = self._get_test_df()
        self._x_vars = self._df.columns[:-2].tolist()
        self._y_vars = self._df.columns[-2:].tolist()

    def _get_test_df(self) -> pd.DataFrame:
        np.random.seed(42)
        idx = pd.Series(
            pd.date_range(
                "2010-01-01 00:00", "2010-01-01 03:00", freq=self._frequency
            )
        ).sample(self._n_rows)
        df = pd.DataFrame(np.random.randn(self._n_rows, self._n_cols), index=idx)
        df.index.name = "timestamp"
        df.columns = [f"col_{j}" for j in range(0, self._n_cols)]
        df.sort_index(inplace=True)
        df = df.asfreq(self._frequency)
        return df


if henv.has_module("gluonts"):

    class TestCreateIterSingleIndex(hunitest.TestCase):
        def test1(self) -> None:
            ta = _TestAdapter()
            data_iter = cdatadap.iterate_target_features(
                ta._df, ta._x_vars, ta._y_vars, None
            )
            self.check_string(str(list(data_iter)))

        def test_shape1(self) -> None:
            ta = _TestAdapter()
            data_iter = cdatadap.iterate_target_features(
                ta._df, ta._x_vars, ta._y_vars, None
            )
            for data_dict in data_iter:
                target = data_dict[gluonts.dataset.field_names.FieldName.TARGET]
                start = data_dict[gluonts.dataset.field_names.FieldName.START]
                features = data_dict[
                    gluonts.dataset.field_names.FieldName.FEAT_DYNAMIC_REAL
                ]
                self.assertEqual(target.shape, (len(ta._y_vars), ta._df.shape[0]))
                self.assertEqual(
                    features.shape, (len(ta._x_vars), ta._df.shape[0])
                )
                self.assertIsInstance(start, pd.Timestamp)

        def test_truncate1(self) -> None:
            ta = _TestAdapter()
            data_iter = cdatadap.iterate_target_features(
                ta._df, ta._x_vars, ta._y_vars, y_truncate=10
            )
            self.check_string(str(list(data_iter)))

    class TestTransformToGluon(hunitest.TestCase):
        def test_transform(self) -> None:
            ta = _TestAdapter()
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, ta._x_vars, ta._y_vars, ta._frequency
            )
            self.check_string(str(list(gluon_ts)))

        def test_transform_local_ts(self) -> None:
            ta = _TestAdapter()
            local_ts = pd.concat([ta._df, ta._df + 1], keys=[0, 1])
            gluon_ts = cdatadap.transform_to_gluon(
                local_ts, ta._x_vars, ta._y_vars, ta._frequency
            )
            self.check_string(str(list(gluon_ts)))

        def test_transform_series_target(self) -> None:
            ta = _TestAdapter()
            y_vars = ta._y_vars[-1:]
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, ta._x_vars, y_vars, ta._frequency
            )
            self.check_string(str(list(gluon_ts)))

        def test_transform_none_x_vars(self) -> None:
            ta = _TestAdapter()
            y_vars = ta._y_vars[-1:]
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, None, y_vars, ta._frequency
            )
            self.check_string(str(list(gluon_ts)))

    class TestTransformFromGluon(hunitest.TestCase):
        @pytest.mark.skip("Disabled because of PTask2440")
        def test_transform(self) -> None:
            ta = _TestAdapter()
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, ta._x_vars, ta._y_vars, ta._frequency
            )
            df = cdatadap.transform_from_gluon(
                gluon_ts,
                ta._x_vars,
                ta._y_vars,
                index_name=ta._df.index.name,
            )
            self.check_string(df.to_string())

        @pytest.mark.skip("Disabled because of PTask2440")
        def test_transform_none_x_vars(self) -> None:
            ta = _TestAdapter()
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, None, ta._y_vars, ta._frequency
            )
            df = cdatadap.transform_from_gluon(
                gluon_ts,
                None,
                ta._y_vars,
                index_name=ta._df.index.name,
            )
            self.check_string(df.to_string())

        @pytest.mark.skip("Disabled because of PTask2440")
        def test_correctness(self) -> None:
            ta = _TestAdapter()
            gluon_ts = cdatadap.transform_to_gluon(
                ta._df, ta._x_vars, ta._y_vars, ta._frequency
            )
            inverted_df = cdatadap.transform_from_gluon(
                gluon_ts,
                ta._x_vars,
                ta._y_vars,
                index_name=ta._df.index.name,
            )
            inverted_df = inverted_df.astype(np.float64)
            pd.testing.assert_frame_equal(ta._df, inverted_df)

        @pytest.mark.skip("Disabled because of PTask2440")
        def test_correctness_local_ts(self) -> None:
            ta = _TestAdapter()
            local_ts = pd.concat([ta._df, ta._df + 1], keys=[0, 1])
            gluon_ts = cdatadap.transform_to_gluon(
                local_ts, ta._x_vars, ta._y_vars, ta._frequency
            )
            inverted_df = cdatadap.transform_from_gluon(
                gluon_ts,
                ta._x_vars,
                ta._y_vars,
                index_name=ta._df.index.name,
            )
            inverted_df = inverted_df.astype(np.float64)
            pd.testing.assert_frame_equal(local_ts, inverted_df)

        @pytest.mark.skip("Disabled because of PTask2440")
        def test_transform_artificial_ts(self) -> None:
            """
            Artificial time series below has one-dimensional target.
            """
            artificial_dataset = gda.ComplexSeasonalTimeSeries(
                num_series=1,
                prediction_length=21,
                freq_str="H",
                length_low=30,
                length_high=40,
                min_val=-10000,
                max_val=10000,
                is_integer=False,
                proportion_missing_values=0,
                is_noise=True,
                is_scale=True,
                percentage_unique_timestamps=1,
                is_out_of_bounds_date=True,
            )
            train_ts = gluonts.dataset.common.ListDataset(
                artificial_dataset.train, freq=artificial_dataset.metadata.freq
            )
            test_ts = gluonts.dataset.common.ListDataset(
                artificial_dataset.test, freq=artificial_dataset.metadata.freq
            )
            train_df = cdatadap.transform_from_gluon(
                train_ts, None, ["y"], index_name=None
            )
            test_df = cdatadap.transform_from_gluon(
                test_ts, None, ["y"], index_name=None
            )
            str_res = f"{hprint.frame('train')}{train_df}\n{hprint.frame('test')}{test_df}"
            self.check_string(str_res)

    class TestTransformFromGluonForecasts(hunitest.TestCase):
        def test_transform1(self) -> None:
            forecasts = TestTransformFromGluonForecasts._get_mock_forecasts()
            df = cdatadap.transform_from_gluon_forecasts(forecasts)
            self.check_string(df.to_string())

        @staticmethod
        def _get_mock_forecasts(
            n_traces: int = 3,
            n_offsets: int = 50,
            n_forecasts: int = 2,
            frequency: str = "T",
        ) -> List[gluonts.model.forecast.SampleForecast]:
            np.random.seed(42)
            all_samples = np.random.randn(n_traces, n_offsets, n_forecasts)
            start_dates = pd.date_range(
                pd.Timestamp("2010-01-01"), freq="D", periods=n_forecasts
            )
            forecasts = [
                gluonts.model.forecast.SampleForecast(
                    all_samples[:, :, i], start_date, frequency
                )
                for i, start_date in enumerate(start_dates)
            ]
            return forecasts


class TestTransformToSklean(hunitest.TestCase):
    def test_transform1(self) -> None:
        ta = _TestAdapter()
        df = ta._df.dropna()
        sklearn_input = cdatadap.transform_to_sklearn_old(
            df, ta._x_vars, ta._y_vars
        )
        self.check_string("x_vals:\n{}\ny_vals:\n{}".format(*sklearn_input))

    def test_transform_none_x_vars1(self) -> None:
        ta = _TestAdapter()
        df = ta._df.dropna()
        sklearn_input = cdatadap.transform_to_sklearn_old(df, None, ta._y_vars)
        self.check_string("x_vals:\n{}\ny_vals:\n{}".format(*sklearn_input))


class TestTransformFromSklean(hunitest.TestCase):
    def test_transform1(self) -> None:
        sklearn_data = TestTransformFromSklean._get_sklearn_data()
        transformed_df = cdatadap.transform_from_sklearn(*sklearn_data)
        self.check_string(transformed_df.to_string())

    @staticmethod
    def _get_sklearn_data() -> Tuple[pd.Index, pd.DataFrame, pd.DataFrame]:
        np.random.seed(42)
        ta = _TestAdapter()
        df = ta._df.dropna()
        idx = df.index
        x_vars = ta._x_vars
        x_vals = df[x_vars]
        return idx, x_vars, x_vals
