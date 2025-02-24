from typing import Any, Dict

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics as costatis
import core.timeseries_study as ctimstud
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest


class TestTimeSeriesDailyStudy(hunitest.TestCase):
    def test_usual_case(self) -> None:
        idx = pd.date_range("2018-12-31", "2019-01-31")
        vals = np.random.randn(len(idx))
        ts = pd.Series(vals, index=idx)
        tsds = ctimstud.TimeSeriesDailyStudy(ts)
        tsds.execute()


class TestTimeSeriesMinutelyStudy(hunitest.TestCase):
    def test_usual_case(self) -> None:
        idx = pd.date_range("2018-12-31", "2019-01-31", freq="5T")
        vals = np.random.randn(len(idx))
        ts = pd.Series(vals, index=idx)
        tsms = ctimstud.TimeSeriesMinutelyStudy(ts, freq_name="5 minutes")
        tsms.execute()


class TestMapDictToDataframeTest1(hunitest.TestCase):
    def test1(self) -> None:
        stat_funcs = {
            "norm_": costatis.apply_normality_test,
            "adf_": costatis.apply_adf_test,
            "kpss_": costatis.apply_kpss_test,
        }
        result_dict = self._get_dict_of_series(1)
        actual = ctimstud.map_dict_to_dataframe(
            dict_=result_dict, functions=stat_funcs
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        stat_funcs = {
            "norm_": costatis.apply_normality_test,
            "adf_": costatis.apply_adf_test,
            "kpss_": costatis.apply_kpss_test,
        }
        result_dict = self._get_dict_of_series(1)
        actual = ctimstud.map_dict_to_dataframe(
            dict_=result_dict,
            functions=stat_funcs,
            add_prefix=False,
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        stat_funcs = {
            "norm_": costatis.apply_normality_test,
            "adf_": costatis.apply_adf_test,
            "kpss_": costatis.apply_kpss_test,
        }
        result_dict = self._get_dict_of_series(1)
        actual = ctimstud.map_dict_to_dataframe(
            dict_=result_dict,
            functions=stat_funcs,
            progress_bar=False,
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series

    def _get_dict_of_series(self, seed: int) -> Dict[Any, pd.Series]:
        n_items = 15
        test_keys = ["test_key_" + str(x) for x in range(n_items)]
        result_dict = {key: self._get_series(seed) for key in test_keys}
        return result_dict
