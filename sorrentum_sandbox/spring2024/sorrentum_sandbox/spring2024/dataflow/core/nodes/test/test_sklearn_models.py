import logging

import numpy as np
import pandas as pd
import sklearn.linear_model as slmode

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import dataflow.core.nodes.sklearn_models as dtfcnoskmo
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestContinuousSkLearnModel(hunitest.TestCase):
    def test1(self) -> None:
        # Load test data.
        data = self._get_data(1)
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
                "col_mode": "merge_all",
            }
        )
        # Load sklearn config and create modeling node.
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test2(self) -> None:
        data = self._get_data(2)
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "model_kwargs": {
                    "alpha": 0.5,
                },
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test `slmode.Lasso` model.

        `Lasso` returns a one-dimensional array for a two-dimensional
        input.
        """
        data = self._get_data(1)
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.Lasso,
            **config.to_dict(),
        )
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test4(self) -> None:
        data = self._get_data(1)
        data_fit = data.loc[:"2010-01-01 00:29:00"]  # type: ignore[misc]
        data_predict = data.loc["2010-01-01 00:30:00":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
                "col_mode": "merge_all",
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test5(self) -> None:
        data = self._get_data(2)
        data_fit = data.loc[:"2010-01-01 00:29:00"]  # type: ignore[misc]
        data_predict = data.loc["2010-01-01 00:30:00":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test6(self) -> None:
        """
        Use `sample_weight_col` in `fit()`.
        """
        data = self._get_data(2)
        data["weights"] = range(0, data.shape[0])
        data_fit = data.loc[:"2010-01-01 00:29:00"]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "sample_weight_col": ["weights"],
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.LinearRegression,
            **config.to_dict(),
        )
        df_out = node.fit(data_fit)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test7(self) -> None:
        """
        Use `sample_weight_col` in `predict()`.
        """
        data = self._get_data(2)
        data["weights"] = range(0, data.shape[0])
        data_fit = data.loc[:"2010-01-01 00:29:00"]  # type: ignore[misc]
        data_predict = data.loc["2010-01-01 00:30:00":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "sample_weight_col": ["weights"],
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.LinearRegression,
            **config.to_dict(),
        )
        _ = node.fit(data_fit)["df_out"]
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test8(self) -> None:
        """
        Use `sample_weight_col` in `predict()`.
        """
        data = self._get_data(2)
        data["weights"] = range(0, data.shape[0])
        data["weights"].loc["2010-01-01 00:31:00":] = np.nan  # type: ignore[misc]
        data_fit = data.loc[:"2010-01-01 00:29:00"]  # type: ignore[misc]
        data_predict = data.loc["2010-01-01 00:30:00":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "x_vars": ["x"],
                "y_vars": ["y"],
                "steps_ahead": 2,
                "sample_weight_col": ["weights"],
                "nan_mode": "drop",
            }
        )
        node = dtfcnoskmo.ContinuousSkLearnModel(
            "sklearn",
            model_func=slmode.LinearRegression,
            **config.to_dict(),
        )
        _ = node.fit(data_fit)["df_out"]
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def _get_data(self, lag: int) -> pd.DataFrame:
        """
        Generate "random returns".

        Use lag + noise as predictor.
        """
        num_periods = 50
        total_steps = num_periods + lag + 1
        rets = carsigen.get_gaussian_walk(0, 0.2, total_steps, seed=10).diff()
        noise = carsigen.get_gaussian_walk(0, 0.02, total_steps, seed=1).diff()
        pred = rets.shift(-lag).loc[1:num_periods] + noise.loc[1:num_periods]
        resp = rets.loc[1:num_periods]
        idx = pd.date_range("2010-01-01", periods=num_periods, freq="T")
        df = pd.DataFrame.from_dict({"x": pred, "y": resp}).set_index(idx)
        return df


class TestMultiindexSkLearnModel(hunitest.TestCase):
    def test1(self) -> None:
        # Load test data.
        data = self._get_data()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("ret_0",),
                ],
                "out_col_group": (),
                "x_vars": ["ret_0"],
                "y_vars": ["ret_0"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        # Load sklearn config and create modeling node.
        node = dtfcnoskmo.MultiindexSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test2(self) -> None:
        data = self._get_data()
        data_fit = data.loc[:"2000-01-31"]  # type: ignore[misc]
        data_predict = data.loc["2000-01-31":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("ret_0",),
                ],
                "out_col_group": (),
                "x_vars": ["ret_0"],
                "y_vars": ["ret_0"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        node = dtfcnoskmo.MultiindexSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=2, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        realization = realization.rename(columns=lambda x: "MN" + str(x))
        volume = pd.DataFrame(
            index=realization.index, columns=realization.columns, data=100
        )
        data = pd.concat([realization, volume], axis=1, keys=["ret_0", "volume"])
        return data


class TestMultiindexPooledSkLearnModel(hunitest.TestCase):
    def test1(self) -> None:
        # Load test data.
        data = self._get_data()
        # Generate node config.
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("ret_0",),
                ],
                "out_col_group": (),
                "x_vars": ["ret_0"],
                "y_vars": ["ret_0"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        # Load sklearn config and create modeling node.
        node = dtfcnoskmo.MultiindexPooledSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        #
        df_out = node.fit(data)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def test2(self) -> None:
        data = self._get_data()
        data_fit = data.loc[:"2000-01-31"]  # type: ignore[misc]
        data_predict = data.loc["2000-01-31":]  # type: ignore[misc]
        config = cconfig.Config.from_dict(
            {
                "in_col_groups": [
                    ("ret_0",),
                ],
                "out_col_group": (),
                "x_vars": ["ret_0"],
                "y_vars": ["ret_0"],
                "steps_ahead": 1,
                "model_kwargs": {
                    "alpha": 0.5,
                },
            }
        )
        node = dtfcnoskmo.MultiindexPooledSkLearnModel(
            "sklearn",
            model_func=slmode.Ridge,
            **config.to_dict(),
        )
        node.fit(data_fit)
        df_out = node.predict(data_predict)["df_out"]
        df_str = hpandas.df_to_str(
            df_out.round(3), num_rows=None, precision=3
        )
        self.check_string(df_str, fuzzy_match=True)

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=2, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        realization = realization.rename(columns=lambda x: "MN" + str(x))
        volume = pd.DataFrame(
            index=realization.index, columns=realization.columns, data=100
        )
        data = pd.concat([realization, volume], axis=1, keys=["ret_0", "volume"])
        return data
