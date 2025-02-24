import collections
import copy
import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import core.signal_processing as csigproc
import dataflow.core.nodes.test.helpers as cdnth
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hunit_test as hunitest
from dataflow.core.nodes.volatility_models import (
    MultiindexVolatilityModel,
    SingleColumnVolatilityModel,
    SmaModel,
    VolatilityModel,
    VolatilityModulator,
)

_LOG = logging.getLogger(__name__)


class TestSmaModel(hunitest.TestCase):
    def test1(self) -> None:
        # Load test data.
        data = self._get_data()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("data=\n%s", str(data))
        config = cconfig.Config.from_dict(
            {
                "col": ["vol_sq"],
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        # Specify config and create modeling node.
        node = SmaModel("sma", **config.to_dict())
        # Run `fit()` and get output dataframe.
        df_out = node.fit(data)["df_out"]
        # Package results.
        self._check_results(df_out)

    def test2(self) -> None:
        """
        Specify `tau` parameter.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": ["vol_sq"],
                "steps_ahead": 2,
                "tau": 8,
                "nan_mode": "drop",
            }
        )
        node = SmaModel("sma", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        self._check_results(df_out)

    def test3(self) -> None:
        """
        Specify `col_mode=='merge_all'`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": ["vol_sq"],
                "steps_ahead": 2,
                "col_mode": "merge_all",
                "nan_mode": "drop",
            }
        )
        node = SmaModel("sma", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        self._check_results(df_out)

    def test4(self) -> None:
        """
        Run `predict()` after `fit()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": ["vol_sq"],
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        node = SmaModel("sma", **config.to_dict())
        # Run `fit()`, then `predict()`.
        node.fit(data.loc["2000-01-01":"2000-02-10"])  # type: ignore[misc]
        df_out = node.predict(data.loc["2000-01-20":"2000-02-23"])["df_out"]  # type: ignore[misc]
        # Package results.
        self._check_results(df_out)

    def test5(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": ["vol_sq"],
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        fit_df = data.loc["2000-01-01":"2000-02-10"]  # type: ignore[misc]
        predict_df = data.loc["2000-01-01":"2000-02-23"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, SmaModel
        )
        self.assert_equal(actual, expected)

    @staticmethod
    def _get_data() -> pd.DataFrame:
        """
        Generate "random returns" in the form:
        ```
                       vol_sq
        2000-01-03   3.111881
        2000-01-04   1.425590
        2000-01-05   2.298345
        2000-01-06   8.544551
        ```
        """
        # Get ARMA random data with some correlation.
        arma_process = carsigen.ArmaProcess([0.45], [0])
        date_range_kwargs = {"start": "2000-01-01", "periods": 40, "freq": "B"}
        date_range = pd.date_range(**date_range_kwargs)
        realization = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs, seed=0
        )
        # Square the volatility.
        vol_sq = np.abs(realization) ** 2
        vol_sq.name = "vol_sq"
        # Assemble the data in a dataframe.
        df = pd.DataFrame(index=date_range, data=vol_sq)
        return df

    def _check_results(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Convert inputs to a string and check it against golden reference.
        """
        decimals = 3
        actual = hpandas.df_to_str(
            df.round(decimals), num_rows=None, precision=decimals
        )
        self.check_string(actual, fuzzy_match=True)


class TestSingleColumnVolatilityModel(hunitest.TestCase):
    @pytest.mark.skipif(
        not hserver.is_inside_ci(),
        reason="Different goldends locally and in the GH Actions",
    )
    def test1(self) -> None:
        """
        Perform a typical `fit()` call.
        """
        # Load test data.
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": "ret_0",
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = SingleColumnVolatilityModel("vol_model", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    def test2(self) -> None:
        """
        Perform a typical `predict()` call.
        """
        # Load test data.
        data = self._get_data()
        # Specify config and create modeling node.
        config = cconfig.Config.from_dict(
            {
                "col": "ret_0",
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = SingleColumnVolatilityModel("vol_model", **config.to_dict())
        node.fit(data.loc[:"2000-02-10"])  # type: ignore[misc]
        df_out = node.predict(data.loc[:"2000-02-23"])["df_out"]  # type: ignore[misc]
        info = collections.OrderedDict()
        info["fit"] = node.get_info("fit")
        info["predict"] = node.get_info("predict")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "col": "ret_0",
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        fit_df = data.loc["2000-01-01":"2000-02-10"]  # type: ignore[misc]
        predict_df = data.loc["2000-01-01":"2000-02-23"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, SingleColumnVolatilityModel
        )
        self.assert_equal(actual, expected)

    @staticmethod
    def _get_data() -> pd.DataFrame:
        """
        Generate "random returns".

        Use lag + noise as predictor.
        """
        arma_process = carsigen.ArmaProcess([0.45], [0])
        date_range_kwargs = {"start": "2000-01-01", "periods": 40, "freq": "B"}
        date_range = pd.date_range(**date_range_kwargs)
        realization = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs, seed=10
        )
        realization.name = "ret_0"
        df = pd.DataFrame(index=date_range, data=realization)
        return df

    @staticmethod
    def _package_results1(
        config: cconfig.Config,
        info: collections.OrderedDict,
        df_out: pd.DataFrame,
    ) -> str:
        act: List[str] = []
        act.append(hprint.frame("config"))
        act.append(str(config))
        act.append(hprint.frame("info"))
        act.append(str(cconfig.Config.from_dict(info)))
        act.append(hprint.frame("df_out"))
        act.append(hpandas.df_to_str(df_out.round(2), num_rows=None, precision=2))
        act = "\n".join(act)
        return act


class TestVolatilityModel(hunitest.TestCase):
    @pytest.mark.skip("See CmTask #2975.")
    def test01(self) -> None:
        """
        Perform a typical `fit()` call.
        """
        # Load test data.
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act)

    @pytest.mark.skip("See CmTask #2975.")
    def test02(self) -> None:
        """
        Check that the volatility adjustment can be inverted.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        vol_adj_df = node.fit(data)["df_out"]
        # Invert volatility adjustment.
        ret_0_vol_0_hat = vol_adj_df["ret_0_vol.shift_-2_hat"].shift(2)
        inverted_rets = (ret_0_vol_0_hat * vol_adj_df["ret_0_vol_adj"]).rename(
            "ret_0_inverted"
        )
        # Compare results.
        df_out = vol_adj_df.join(inverted_rets)
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act)

    def test03(self) -> None:
        """
        Perform a typical `predict()` call.
        """
        # Load test data.
        data = self._get_data()
        # Specify config and create modeling node.
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        node.fit(data.loc["2000-01-01":"2000-02-10"])  # type: ignore[misc]
        # TODO(Paul): Update the `predict()` interval.
        df_out = node.predict(data.loc["2000-01-20":"2000-02-23"])["df_out"]  # type: ignore[misc]
        # TODO(Paul): Propagate `fit()` and `predict()` info.
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    def test04(self) -> None:
        """
        Check that the `predict()` volatility adjustment can be inverted.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        node.fit(data.loc["2000-01-01":"2000-02-10"])  # type: ignore[misc]
        vol_adj_df = node.predict(data.loc["2000-01-20":"2000-02-23"])["df_out"]  # type: ignore[misc]
        # Invert volatility adjustment.
        ret_0_vol_0_hat = vol_adj_df["ret_0_vol.shift_-2_hat"].shift(2)
        inverted_rets = (ret_0_vol_0_hat * vol_adj_df["ret_0_vol_adj"]).rename(
            "ret_0_inverted"
        )
        # Compare results.
        df_out = vol_adj_df.join(inverted_rets)
        # TODO(Paul): Propagate `fit()` and `predict()` info.
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    @pytest.mark.skip("See CmTask #2975.")
    def test05(self) -> None:
        """
        Use "replace_all" column mode.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "col_mode": "replace_all",
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        #
        df_out = node.fit(data)["df_out"]
        info = node.get_info("fit")
        #
        act = self._package_results1(config, info, df_out)
        self.check_string(act)

    @pytest.mark.skip("See CmTask #2975.")
    def test06(self) -> None:
        """
        Use "replace_selected" column mode.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0"],
                "steps_ahead": 2,
                "col_mode": "replace_selected",
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        #
        df_out = node.fit(data)["df_out"]
        info = node.get_info("fit")
        #
        act = self._package_results1(config, info, df_out)
        self.check_string(act)

    @pytest.mark.skip("See CmTask #2975.")
    def test07(self) -> None:
        """
        Model volatility for multiple columns (independently).
        """
        # Load test data.
        data = self._get_data()
        # TODO(Paul): Rename this column.
        data["ret_0.shift_-2"] = data.ret_0 + np.random.normal(size=len(data))
        # Specify config and create modeling node.
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0", "ret_0.shift_-2"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node = VolatilityModel("vol_model", **config.to_dict())
        #
        df_out = node.fit(data)["df_out"]
        info = node.get_info("fit")
        # Package results.
        act = self._package_results1(config, info, df_out)
        self.check_string(act)

    @pytest.mark.skip("We no longer directly expose tau")
    def test08(self) -> None:
        """
        Ensure that explicit `tau` is used post-`fit()`.
        """
        # Load test data.
        data = self._get_data()
        data["ret_0.shift_-2"] = data.ret_0 + np.random.normal(size=len(data))
        # Specify config.
        config = cconfig.Config.from_dict(
            {
                "cols": ["ret_0", "ret_0.shift_-2"],
                "steps_ahead": 2,
                "nan_mode": "drop",
                "tau": 10,
            }
        )
        # Check if specified tau is used for all columns via learned taus property.
        node = VolatilityModel("vol_model", **config.to_dict())
        node.fit(data)
        hdbg.dassert_set_eq(node.taus.values(), [10])

    def test09(self) -> None:
        """
        Ensure equivalence of explicit and implicit column specification.
        """
        # Load test data.
        data = self._get_data()
        data["ret_0.shift_-2"] = data.ret_0 + np.random.normal(size=len(data))
        # Specify config with columns implicit.
        config1 = cconfig.Config.from_dict(
            {
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node1 = VolatilityModel("vol_model", **config1.to_dict())
        df_out1 = node1.fit(data)["df_out"]
        # Specify config with explicit column names.
        config2 = cconfig.Config.from_dict(
            {
                "cols": ["ret_0", "ret_0.shift_-2"],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        node2 = VolatilityModel("vol_model", **config2.to_dict())
        df_out2 = node2.fit(data)["df_out"]
        # TODO(Paul): Improve the string conversion.
        np.testing.assert_equal(
            df_out1.to_string(),
            df_out2.to_string(),
        )

    def test10(self) -> None:
        """
        Ensure that `int` columns are supported.
        """
        # Load test data.
        data = self._get_data()
        data[10] = data.ret_0 + np.random.normal(size=len(data))
        # Specify config.
        config = cconfig.Config.from_dict(
            {
                "cols": [10],
                "steps_ahead": 2,
                "nan_mode": "leave_unchanged",
            }
        )
        # Get output with integer column names.
        node = VolatilityModel("vol_model", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        self.check_string(df_out.to_string(), fuzzy_match=True)

    @pytest.mark.skip("See CmTask #2975.")
    def test11(self) -> None:
        """
        Learn and store model state.
        """
        data = self._get_data()
        config = cconfig.Config()
        config["cols"] = ["ret_0"]
        config["steps_ahead"] = 2
        config["nan_mode"] = "leave_unchanged"
        node = VolatilityModel("vol_model", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        # Package results.
        state = node.get_fit_state()
        act = self._package_results2(config, state, df_out)
        self.check_string(act)

    @pytest.mark.skip("See CmTask #2975.")
    def test12(self) -> None:
        """
        Initialize model from saved state.
        """
        data = self._get_data()
        config = cconfig.Config()
        config["cols"] = ["ret_0"]
        config["steps_ahead"] = 2
        config["nan_mode"] = "leave_unchanged"
        node = VolatilityModel("vol_model", **config.to_dict())
        node.fit(data)["df_out"]
        # Package results.
        state = node.get_fit_state()
        # Load state.
        node2 = VolatilityModel("vol_model", **config.to_dict())
        node2.set_fit_state(state)
        df_out = node2.predict(data)["df_out"]
        # Package results.
        act = self._package_results2(config, state, df_out)
        self.check_string(act)

    def test13(self) -> None:
        """
        Compare results of initializing from state with relearning.
        """
        data = self._get_data()
        config = cconfig.Config()
        config["cols"] = ["ret_0"]
        config["steps_ahead"] = 2
        config["nan_mode"] = "leave_unchanged"
        node_fit = VolatilityModel("vol_model", **config.to_dict())
        node_fit.fit(data)
        output_fit = node_fit.predict(data)["df_out"]
        node_predefined = VolatilityModel("vol_model", **config.to_dict())
        node_predefined.set_fit_state(node_fit.get_fit_state())
        output_predefined = node_predefined.predict(data)["df_out"]
        pd.testing.assert_frame_equal(output_fit, output_predefined)

    @staticmethod
    def _package_results1(
        config: cconfig.Config,
        info: collections.OrderedDict,
        df_out: pd.DataFrame,
    ) -> str:
        act: List[str] = []
        act.append(hprint.frame("config"))
        act.append(str(config))
        act.append(hprint.frame("info"))
        act.append(str(cconfig.Config.from_dict(info)))
        act.append(hprint.frame("df_out"))
        act.append(hpandas.df_to_str(df_out, num_rows=None))
        act = "\n".join(act)
        return act

    @staticmethod
    def _package_results2(
        config: cconfig.Config, state: Dict[str, Any], df_out: pd.DataFrame
    ) -> str:
        act: List[str] = []
        act.append(hprint.frame("config"))
        act.append(str(config))
        act.append(hprint.frame("state"))
        act.append(str(state))
        act.append(hprint.frame("df_out"))
        act.append(hpandas.df_to_str(df_out, num_rows=None))
        act = "\n".join(act)
        return act

    @staticmethod
    def _get_data() -> pd.DataFrame:
        """
        Generate "random returns".

        Use lag + noise as predictor.
        """
        arma_process = carsigen.ArmaProcess([0.45], [0])
        date_range_kwargs = {"start": "2000-01-01", "periods": 40, "freq": "B"}
        date_range = pd.date_range(**date_range_kwargs)
        realization = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs, seed=0
        )
        realization.name = "ret_0"
        df = pd.DataFrame(index=date_range, data=realization)
        return df


# TODO(ShaopengZ): numerical issue. (arm vs x86)
@pytest.mark.requires_ck_infra
class TestMultiindexVolatilityModel(hunitest.TestCase):
    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        """
        Perform a typical `fit()` call.
        """
        # Load test data.
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("ret_0",),
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        node = MultiindexVolatilityModel("vol_model", **config.to_dict())
        df_out = node.fit(data)["df_out"]
        method = "fit"
        info = node.get_info(method)
        # Package results.
        act = self._package_results1(method, config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    @pytest.mark.requires_ck_infra
    def test2(self) -> None:
        """
        Perform a typical `predict()` call.
        """
        # Load test data.
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("ret_0",),
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        node = MultiindexVolatilityModel("vol_model", **config.to_dict())
        node.fit(data.loc[:"2000-01-31"])["df_out"]  # type: ignore[misc]
        # Package results.
        df_out = node.predict(data)["df_out"]
        method = "predict"
        info = node.get_info(method)
        act = self._package_results1(method, config, info, df_out)
        self.check_string(act, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test `get_fit_state()` and `set_fit_state()`.
        """
        data = self._get_data()
        config = cconfig.Config.from_dict(
            {
                "in_col_group": ("ret_0",),
                "steps_ahead": 2,
                "nan_mode": "drop",
            }
        )
        fit_df = data.loc["2000-01-01":"2000-02-10"]  # type: ignore[misc]
        predict_df = data.loc["2000-01-01":"2000-02-23"]  # type: ignore[misc]
        expected, actual = cdnth.test_get_set_state(
            fit_df, predict_df, config, MultiindexVolatilityModel
        )
        self.assert_equal(actual, expected)

    @staticmethod
    def _package_results1(
        method: str,
        config: cconfig.Config,
        info: collections.OrderedDict,
        df_out: pd.DataFrame,
    ) -> str:
        # Round tau value: we got different results on different machines
        # due to Python floating point arithmetic.
        rounded_info = copy.deepcopy(info)
        precision = 6
        initial_tau0 = rounded_info["MN0"]["MN0"][
            "compute_smooth_moving_average"
        ][method]["tau"]
        rounded_tau0 = round(initial_tau0, precision)
        (
            rounded_info["MN0"]["MN0"]["compute_smooth_moving_average"][method][
                "tau"
            ]
        ) = rounded_tau0
        initial_tau1 = rounded_info["MN1"]["MN1"][
            "compute_smooth_moving_average"
        ][method]["tau"]
        rounded_tau1 = round(initial_tau1, precision)
        (
            rounded_info["MN1"]["MN1"]["compute_smooth_moving_average"][method][
                "tau"
            ]
        ) = rounded_tau1
        act: List[str] = []
        act.append(hprint.frame("config"))
        act.append(str(config))
        act.append(hprint.frame("info"))
        act.append(str(cconfig.Config.from_dict(rounded_info)))
        act.append(hprint.frame("df_out"))
        act.append(hpandas.df_to_str(df_out.round(2), num_rows=None, precision=2))
        act = "\n".join(act)
        return act

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


class TestVolatilityModulator(hunitest.TestCase):
    def test_modulate1(self) -> None:
        steps_ahead = 2
        df_in = self._get_signal_and_fwd_vol(steps_ahead)
        # Get mock returns prediction 1 step ahead indexed by knowledge time.
        y_hat = csigproc.compute_smooth_moving_average(df_in["ret_0"], 4).shift(
            -1
        )
        df_in["ret_1_hat"] = y_hat
        config = cconfig.Config.from_dict(
            {
                "signal_cols": ["ret_1_hat"],
                "volatility_col": "vol.shift_-2_hat",
                "signal_steps_ahead": 1,
                "volatility_steps_ahead": 2,
                "mode": "modulate",
            }
        )
        node = VolatilityModulator("modulate", **config.to_dict())
        df_out = node.fit(df_in)["df_out"]
        # Check results.
        self._check_results(config, df_in, df_out)

    def test_demodulate1(self) -> None:
        steps_ahead = 2
        df_in = self._get_signal_and_fwd_vol(steps_ahead)
        config = cconfig.Config.from_dict(
            {
                "signal_cols": ["ret_0"],
                "volatility_col": "vol.shift_-2_hat",
                "signal_steps_ahead": 0,
                "volatility_steps_ahead": 2,
                "mode": "demodulate",
            }
        )
        node = VolatilityModulator("demodulate", **config.to_dict())
        df_out = node.fit(df_in)["df_out"]
        # Check results.
        self._check_results(config, df_in, df_out)

    def test_col_mode1(self) -> None:
        steps_ahead = 2
        df_in = self._get_signal_and_fwd_vol(steps_ahead)
        config = cconfig.Config.from_dict(
            {
                "signal_cols": ["ret_0"],
                "volatility_col": "vol.shift_-2_hat",
                "signal_steps_ahead": 0,
                "volatility_steps_ahead": 2,
                "mode": "demodulate",
                "col_rename_func": lambda x: f"{x}_zscored",
                "col_mode": "merge_all",
            }
        )
        node = VolatilityModulator("demodulate", **config.to_dict())
        df_out = node.fit(df_in)["df_out"]
        # Check results.
        self._check_results(config, df_in, df_out)

    def test_col_mode2(self) -> None:
        steps_ahead = 2
        df_in = self._get_signal_and_fwd_vol(steps_ahead)
        config = cconfig.Config.from_dict(
            {
                "signal_cols": ["ret_0"],
                "volatility_col": "vol.shift_-2_hat",
                "signal_steps_ahead": 0,
                "volatility_steps_ahead": 2,
                "mode": "demodulate",
                "col_rename_func": lambda x: f"{x}_zscored",
                "col_mode": "replace_selected",
            }
        )
        node = VolatilityModulator("demodulate", **config.to_dict())
        df_out = node.fit(df_in)["df_out"]
        # Check results.
        self._check_results(config, df_in, df_out)

    @staticmethod
    def _get_signal_and_fwd_vol(
        steps_ahead: int,
    ) -> pd.DataFrame:
        arma_process = carsigen.ArmaProcess([0.45], [0])
        date_range_kwargs = {"start": "2010-01-01", "periods": 40, "freq": "B"}
        signal = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs, scale=0.1, seed=42
        )
        vol = csigproc.compute_smooth_moving_average(signal, 16)
        fwd_vol = vol.shift(steps_ahead)
        return pd.concat(
            [signal.rename("ret_0"), fwd_vol.rename("vol.shift_-2_hat")], axis=1
        )

    def _check_results(
        self, config: cconfig.Config, df_in: pd.DataFrame, df_out: pd.DataFrame
    ) -> None:
        act: List[str] = []
        act.append(hprint.frame("config"))
        act.append(str(config))
        act = "\n".join(act)
        self.check_string(act, fuzzy_match=True)
        self.check_dataframe(df_in, tag="df_in", err_threshold=0.01)
        self.check_dataframe(df_out, tag="df_out", err_threshold=0.01)
