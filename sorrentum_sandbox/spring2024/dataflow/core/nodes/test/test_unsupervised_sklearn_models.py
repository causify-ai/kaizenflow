import datetime
import logging

import numpy as np
import pandas as pd
import sklearn.decomposition as sdecom

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import core.finance as cofinanc
import dataflow.core.nodes.test.helpers as cdnth
import dataflow.core.nodes.transformers as dtfconotra
import dataflow.core.nodes.unsupervised_sklearn_models as dtfcnuskmo
import helpers.hpandas as hpandas
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
        config = cconfig.Config.from_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtfcnuskmo.UnsupervisedSkLearnModel("sklearn", **config.to_dict())
        # Fit model.
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
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
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
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
        config = cconfig.Config.from_dict(
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
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
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
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
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
        data = self.get_data()
        # Load sklearn config and create modeling node.
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        #
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Test `predict()` after `fit()`.
        """
        # Load test data.
        data = self.get_data()
        # Load sklearn config and create modeling node.
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        node.fit(data.loc["2000-01-03":"2000-01-31"])  # type: ignore[misc]
        # Predict.
        df_out = node.predict(data.loc["2000-02-01":"2000-02-25"])["df_out"]  # type: ignore[misc]
        df_str = hpandas.df_to_str(df_out.round(3), num_rows=None)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self.get_data()
        config = self.get_node_config()
        fit_df = data.loc["2000-01-03":"2000-01-31"]  # type: ignore[misc]
        predict_df = data.loc["2000-02-01":"2000-02-25"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, dtfcnuskmo.Residualizer
        )
        self.assert_equal(actual, expected)

    def get_data(self) -> pd.DataFrame:
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

    def get_node_config(self) -> pd.DataFrame:
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("ret_0",),
                "out_col_group": ("residual",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        return config


class TestResidualizer2(hunitest.TestCase):
    def test1(self) -> None:
        """
        Fit on ideal test data.
        """
        # Load test data.
        data = self.get_data()
        #
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        #
        pca_residual = df_out["pca_residual"]
        df_str = hpandas.df_to_str(pca_residual.round(5), num_rows=None)
        self.check_string(df_str)

    def test2(self) -> None:
        """
        Fit on test data with an all-NaN column.
        """
        # Load test data.
        data = self.get_data()
        data[("close.ret_0", 100)] = np.nan
        #
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        #
        pca_residual = df_out["pca_residual"]
        df_str = hpandas.df_to_str(pca_residual.round(5), num_rows=None)
        self.check_string(df_str)

    def test3(self) -> None:
        """
        Test `fit()` with all-NaN column, predict with no all-NaN columns.
        """
        # Load test data.
        data = self.get_data()
        data[("close.ret_0", 100)].loc[:"2021-01-04"] = np.nan  # type: ignore[misc]
        #
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        _ = node.fit(data.loc[:"2021-01-04"])["df_out"]  # type: ignore[misc]
        df_out = node.predict(data)["df_out"]
        #
        pca_residual = df_out["pca_residual"]
        df_str = hpandas.df_to_str(pca_residual.round(5), num_rows=None)
        self.check_string(df_str)

    def test4(self) -> None:
        """
        Test `fit()` with no all-NaN column, predict with all-NaN column.
        """
        # Load test data.
        data = self.get_data()
        data[("close.ret_0", 100)].loc["2021-01-04":] = np.nan  # type: ignore[misc]
        #
        config = self.get_node_config()
        node = dtfcnuskmo.Residualizer("sklearn", **config.to_dict())
        _ = node.fit(data.loc["2021-01-04":])["df_out"]  # type: ignore[misc]
        df_out = node.predict(data)["df_out"]
        #
        pca_residual = df_out["pca_residual"]
        df_str = hpandas.df_to_str(pca_residual.round(5), num_rows=None)
        self.check_string(df_str)

    def get_data(self) -> pd.DataFrame:
        """
        Generate random OHLCV bars.
        """
        start_datetime = pd.Timestamp("2021-01-03 09:30", tz="America/New_York")
        end_datetime = pd.Timestamp("2021-01-04 16:00", tz="America/New_York")
        asset_ids = [100, 200, 300, 400]
        bar_duration = "30T"
        bar_volatility_in_bps = 50
        bar_expected_count = 1000000
        last_price = 1000
        start_time = datetime.time(9, 31)
        end_time = datetime.time(16, 0)
        seed = 10
        bars = cofinanc.generate_random_ohlcv_bars(
            start_datetime,
            end_datetime,
            asset_ids,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            bar_expected_count=bar_expected_count,
            last_price=last_price,
            start_time=start_time,
            end_time=end_time,
            seed=seed,
        )
        data = bars.set_index("end_datetime").drop(
            columns=["start_datetime", "timestamp_db"]
        )
        data = data.pivot(columns="asset_id")
        #
        compute_ret_0_config = cconfig.Config.from_dict(
            {
                "in_col_groups": [("close",)],
                "out_col_group": (),
                "transformer_kwargs": {
                    "mode": "log_rets",
                },
                "col_mapping": {
                    "close": "close.ret_0",
                },
            }
        )
        compute_ret_0_node = dtfconotra.GroupedColDfToDfTransformer(
            "compute_ret_0",
            transformer_func=cofinanc.compute_ret_0,
            **compute_ret_0_config.to_dict(),
        )
        #
        data = compute_ret_0_node.fit(data)["df_out"]
        return data

    def get_node_config(self) -> pd.DataFrame:
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("close.ret_0",),
                "out_col_group": ("pca_residual",),
                "model_func": sdecom.PCA,
                "model_kwargs": {"n_components": 1},
                "nan_mode": "drop",
            }
        )
        return config
