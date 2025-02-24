import logging
from typing import Iterable

import pytest

import helpers.henv as henv


if henv.has_module("gluonts"):
    import gluonts
    import mxnet
    import numpy as np
    import pandas as pd

    import core.artificial_signal_generators as carsigen
    import core.backtest as cobackte
    import core.data_adapters as cdatadap
    import helpers.hprint as hprint
    import helpers.hunit_test as hunitest

    # TODO(*): gluon needs these imports to work properly.
    import gluonts.model.deepar as gmd  # isort: skip # noqa: F401 # pylint: disable=unused-import
    import gluonts.model.predictor as gmp  # isort: skip # noqa: F401 # pylint: disable=unused-import
    import gluonts.trainer as gt  # isort: skip # noqa: F401 # pylint: disable=unused-import

    _LOG = logging.getLogger(__name__)

    class TestGeneratePredictions(hunitest.TestCase):
        @pytest.mark.skip("Disabled because of PTask2440")
        def test1(self) -> None:
            """
            Generate y from a shift of an ARIMA series.
            """
            mxnet.random.seed(0, ctx="all")
            num_x_vars = 1
            df = TestGeneratePredictions._generate_input_data(
                num_x_vars=num_x_vars, base_random_state=42
            )
            x_vars = ["x0"]
            y_vars = ["y"]
            train_ts = cdatadap.transform_to_gluon(df, x_vars, y_vars, "T")
            #
            trainer = gluonts.trainer.Trainer(epochs=1)
            prediction_length = 3
            estimator = gluonts.model.deepar.DeepAREstimator(
                prediction_length=prediction_length,
                trainer=trainer,
                freq="T",
                use_feat_dynamic_real=True,
            )
            predictor = estimator.train(train_ts)
            #
            test_df = TestGeneratePredictions._generate_input_data(
                num_x_vars=num_x_vars, base_random_state=0
            )
            yhat, y = cobackte.generate_predictions(
                predictor=predictor,
                df=test_df,
                y_vars=y_vars,
                prediction_length=prediction_length,
                num_samples=4,
                x_vars=x_vars,
            )
            merged = y.merge(yhat, left_index=True, right_index=True)
            str_output = (
                f"{hprint.frame('df')}\n{test_df.to_string()}\n\n"
                f"{hprint.frame('y/yhat')}\n{merged.to_string()}"
            )
            self.check_string(str_output)

        @pytest.mark.skip("Disabled because of PTask2440")
        def test2(self) -> None:
            """
            Generate y from a shift of a linear combination of ARIMA series.
            """
            mxnet.random.seed(0, ctx="all")
            num_x_vars = 2
            df = TestGeneratePredictions._generate_input_data(
                num_x_vars=num_x_vars, base_random_state=42
            )
            x_vars = ["x0", "x1"]
            y_vars = ["y"]
            train_ts = cdatadap.transform_to_gluon(df, x_vars, y_vars, "T")
            #
            trainer = gluonts.trainer.Trainer(epochs=1)
            prediction_length = 3
            estimator = gluonts.model.deepar.DeepAREstimator(
                prediction_length=prediction_length,
                trainer=trainer,
                freq="T",
                use_feat_dynamic_real=True,
            )
            predictor = estimator.train(train_ts)
            #
            test_df = TestGeneratePredictions._generate_input_data(
                num_x_vars=num_x_vars, base_random_state=0
            )
            yhat, y = cobackte.generate_predictions(
                predictor=predictor,
                df=test_df,
                y_vars=y_vars,
                prediction_length=prediction_length,
                num_samples=4,
                x_vars=x_vars,
            )
            merged = y.merge(yhat, left_index=True, right_index=True)
            str_output = (
                f"{hprint.frame('df')}\n{test_df.to_string()}\n\n"
                f"{hprint.frame('y/yhat')}\n{merged.to_string()}"
            )
            self.check_string(str_output)

        @pytest.mark.skip("Disabled because of PTask2440")
        def test3(self) -> None:
            """
            Generate y from a shift of an ARIMA series.

            Ignore x.
            """
            mxnet.random.seed(0, ctx="all")
            df = TestGeneratePredictions._generate_input_data(
                num_x_vars=1, base_random_state=42
            )
            y_vars = ["y"]
            df = df[["y"]]
            train_ts = cdatadap.transform_to_gluon(df, None, y_vars, "T")
            #
            trainer = gluonts.trainer.Trainer(epochs=1)
            prediction_length = 3
            estimator = gluonts.model.deepar.DeepAREstimator(
                prediction_length=prediction_length,
                trainer=trainer,
                freq="T",
            )
            predictor = estimator.train(train_ts)
            #
            test_df = TestGeneratePredictions._generate_input_data(
                num_x_vars=1, base_random_state=0
            )
            test_df = test_df[["y"]]
            yhat, y = cobackte.generate_predictions(
                predictor=predictor,
                df=test_df,
                y_vars=y_vars,
                prediction_length=prediction_length,
                num_samples=4,
            )
            merged = y.merge(yhat, left_index=True, right_index=True)
            str_output = (
                f"{hprint.frame('df')}\n{test_df.to_string()}\n\n"
                f"{hprint.frame('y/yhat')}\n{merged.to_string()}"
            )
            self.check_string(str_output)

        @pytest.mark.slow
        @pytest.mark.skip("Disabled because of PTask2440")
        def test4(self) -> None:
            """
            Generate y using `m4_hourly` Gluon dataset.

            No `x_vars`.
            """
            mxnet.random.seed(0, ctx="all")
            train_length = 500
            test_length = 100
            train_df, test_df = carsigen.get_gluon_dataset(
                dataset_name="m4_hourly",
                train_length=train_length,
                test_length=test_length,
            )
            x_vars = None
            y_vars = ["y"]
            freq = train_df.index.freq.freqstr
            train_ts = cdatadap.transform_to_gluon(train_df, x_vars, y_vars, freq)
            #
            trainer = gluonts.trainer.Trainer(epochs=1)
            prediction_length = 5
            estimator = gluonts.model.deepar.DeepAREstimator(
                prediction_length=prediction_length,
                trainer=trainer,
                freq=freq,
                use_feat_dynamic_real=False,
            )
            predictor = estimator.train(train_ts)
            #
            yhat, y = cobackte.generate_predictions(
                predictor=predictor,
                df=test_df,
                y_vars=y_vars,
                prediction_length=prediction_length,
                num_samples=4,
                x_vars=None,
            )
            merged = y.merge(yhat, left_index=True, right_index=True)
            str_output = (
                f"{hprint.frame('df')}\n{test_df.to_string()}\n\n"
                f"{hprint.frame('y/yhat')}\n{merged.to_string()}"
            )
            self.check_string(str_output)

        @staticmethod
        def _generate_test_series(
            random_state: int = 42,
            n_periods: int = 20,
            ar: Iterable[float] = np.array([0.462, -0.288]),
            ma: Iterable[float] = np.array([0.01]),
        ) -> np.array:
            return carsigen._generate_arima_sample(
                random_state=random_state, n_periods=n_periods, ar=ar, ma=ma
            )

        @staticmethod
        def _generate_input_data(
            num_x_vars: int,
            n_periods: int = 20,
            base_random_state: int = 0,
            shift: int = 1,
        ) -> pd.DataFrame:
            return carsigen.generate_arima_signal_and_response(
                "2010-01-01",
                "T",
                n_periods,
                num_x_vars,
                base_random_state=base_random_state,
                shift=shift,
            )
