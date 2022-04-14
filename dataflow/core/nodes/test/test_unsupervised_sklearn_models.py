import logging

import pandas as pd
import sklearn.decomposition as sdecom

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import dataflow.core.nodes.test.helpers as cdnth
import dataflow.core.nodes.unsupervised_sklearn_models as dtfcnuskmo
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestUnsupervisedSkLearnModel(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `fit()` call.
        """
        # Load test data.
        data = self._get_data()
        # Create sklearn config and modeling node.
        config = cconfig.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.UnsupervisedSkLearnModel("sklearn", **config.to_dict())
        # Fit model.
        df_out = node.fit(data)["df_out"]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.UnsupervisedSkLearnModel("sklearn", **config.to_dict())
        node.fit(data.loc["2000-01-03":"2000-01-31"])  # type: ignore[misc]
        # Predict.
        df_out = node.predict(data.loc["2000-02-01":"2000-02-25"])["df_out"]  # type: ignore[misc]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        fit_df = data.loc["2000-01-03":"2000-01-31"]  # type: ignore[misc]
        predict_df = data.loc["2000-02-01":"2000-02-25"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, dtfcnuskmo.UnsupervisedSkLearnModel
        )
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        return realization


class TestMultiindexUnsupervisedSkLearnModel(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `fit()` call.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("pca",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.MultiindexUnsupervisedSkLearnModel(
            "sklearn", **config.to_dict()
        )
        df_out = node.fit(data)["df_out"]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("pca",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.MultiindexUnsupervisedSkLearnModel(
            "sklearn", **config.to_dict()
        )
        node.fit(data.loc["2000-01-03":"2000-01-31"])  # type: ignore[misc]
        # Predict.
        df_out = node.predict(data.loc["2000-02-01":"2000-02-25"])["df_out"]  # type: ignore[misc]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("pca",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        fit_df = data.loc["2000-01-03":"2000-01-31"]  # type: ignore[misc]
        predict_df = data.loc["2000-02-01":"2000-02-25"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df,
            predict_df,
            config,
            dtfcnuskmo.MultiindexUnsupervisedSkLearnModel,
        )
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        realization = realization.rename(columns=lambda x: "MN" + str(x))
        volume = pd.DataFrame(
            index=realization.index, columns=realization.columns, data=100
        )
        data = pd.concat([realization, volume], axis=1, keys=["ret_0", "volume"])
        return data


class TestResidualizer(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `fit()` call.
        """
        # Load test data.
        data = self._get_data()
        # Load sklearn config and create modeling node.
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("residual",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        #
        df_out = node.fit(data)["df_out"]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        # Load test data.
        data = self._get_data()
        # Load sklearn config and create modeling node.
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("residual",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        node.fit(data.loc["2000-01-03":"2000-01-31"])  # type: ignore[misc]
        # Predict.
        df_out = node.predict(data.loc["2000-02-01":"2000-02-25"])["df_out"]  # type: ignore[misc]
        df_str = hunitest.convert_df_to_string(df_out.round(3), index=True)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.get_config_from_nested_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("residual",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        fit_df = data.loc["2000-01-03":"2000-01-31"]  # type: ignore[misc]
        predict_df = data.loc["2000-02-01":"2000-02-25"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, dtfcnuskmo.Residualizer
        )
        self.assert_equal(actual, expected)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        realization = realization.rename(columns=lambda x: "MN" + str(x))
        volume = pd.DataFrame(
            index=realization.index, columns=realization.columns, data=100
        )
        data = pd.concat([realization, volume], axis=1, keys=["ret_0", "volume"])
        return data
