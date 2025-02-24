import logging

import pandas as pd

import core.artificial_signal_generators as carsigen
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestArmaProcess(hunitest.TestCase):
    def test1(self) -> None:
        ar_params = [0.75, -0.25]
        ma_params = [0.65, 0.35]
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=10,
        )
        self.check_string(
            hpandas.df_to_str(
                realization, tag=realization.name, num_rows=None
            )
        )

    def test2(self) -> None:
        ar_params = [0.5]
        ma_params = [-0.5]
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        self.check_string(
            hpandas.df_to_str(
                realization, tag=realization.name, num_rows=None
            )
        )

    def test3(self) -> None:
        ar_params = []
        ma_params = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        self.check_string(
            hpandas.df_to_str(
                realization, tag=realization.name, num_rows=None
            )
        )


class TestMultivariateNormalProcess(hunitest.TestCase):
    def test1(self) -> None:
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        self.check_string(hpandas.df_to_str(realization, num_rows=None))

    def test2(self) -> None:
        mean = pd.Series([1, 2])
        cov = pd.DataFrame([[0.5, 0.2], [0.2, 0.3]])
        mn_process = carsigen.MultivariateNormalProcess(mean=mean, cov=cov)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        self.check_string(hpandas.df_to_str(realization, num_rows=None))


class Test_generate_arima_signal_and_response(hunitest.TestCase):
    def test1(self) -> None:
        srs = carsigen.generate_arima_signal_and_response(
            "2010-01-01", "D", 40, 1
        )
        self.check_string(hpandas.df_to_str(srs, num_rows=None))


if henv.has_module("gluonts"):
    import gluonts
    import mxnet

    import gluonts.dataset.artificial.recipe as gdar  # isort: skip # noqa: F401 # pylint: disable=unused-import

    class TestGenerateRecipeDataset(hunitest.TestCase):
        def test1(self) -> None:
            mxnet.random.seed(0, ctx="all")
            recipe = [
                (
                    "feat_dynamic_real",
                    gluonts.dataset.artificial.recipe.SmoothSeasonality(
                        period=288, phase=-72
                    ),
                ),
                (
                    "noise",
                    gluonts.dataset.artificial.recipe.RandomGaussian(
                        shape=[0], stddev=0.1
                    ),
                ),
                (
                    "target",
                    gluonts.dataset.artificial.recipe.Add(
                        inputs=["feat_dynamic_real", "noise"]
                    ),
                ),
                (
                    "feat_dynamic_real",
                    gluonts.dataset.artificial.recipe.RandomGaussian(
                        shape=(1, 0)
                    ),
                ),
                # What GluonTS does is find zeros in shape and replace them
                # with length.
            ]
            train_dataset = carsigen.generate_recipe_dataset(
                recipe, "D", pd.Timestamp("2010-01-01"), 100, 10, 1
            )
            train_str = str(list(train_dataset.train))
            test_str = str(list(train_dataset.test))
            self.check_string(
                f"{hprint.frame('train')}{train_str}\n"
                f"{hprint.frame('test')}{test_str}"
            )
