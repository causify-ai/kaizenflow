import collections
import logging

import pandas as pd
import sklearn.linear_model as slm

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import dataflow.core as dtf
import dataflow.model.dataframe_modeler as dtfmodamod
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestDataFrameModeler(hunitest.TestCase):
    def test_dump_json1(self) -> None:
        df = pd.DataFrame(
            {"col0": [1, 2, 3], "col1": [4, 5, 6]},
            index=pd.date_range("2010-01-01", periods=3),
        )
        oos_start = pd.Timestamp("2010-01-01")
        info = collections.OrderedDict({"df_info": dtf.get_df_info_as_string(df)})
        df_modeler = dtfmodamod.DataFrameModeler(
            df, oos_start=oos_start, info=info
        )
        output = df_modeler.dump_json()
        self.check_string(output)

    def test_load_json1(self) -> None:
        """
        Test by dumping json and loading it again.
        """
        df = pd.DataFrame(
            {"col0": [1, 2, 3], "col1": [4, 5, 6]},
            index=pd.date_range("2010-01-01", periods=3),
        )
        oos_start = pd.Timestamp("2010-01-01")
        info = collections.OrderedDict({"df_info": dtf.get_df_info_as_string(df)})
        df_modeler = dtfmodamod.DataFrameModeler(
            df, oos_start=oos_start, info=info
        )
        json_str = df_modeler.dump_json()
        df_modeler_loaded = dtfmodamod.DataFrameModeler.load_json(json_str)
        pd.testing.assert_frame_equal(df_modeler.df, df_modeler_loaded.df)
        self.assertEqual(df_modeler.oos_start, df_modeler_loaded.oos_start)
        self.assertDictEqual(df_modeler.info, df_modeler_loaded.info)

    def test_load_json2(self) -> None:
        """
        Test by dumping json and loading it again with `oos_start=None`.
        """
        df = pd.DataFrame(
            {"col0": [1, 2, 3], "col1": [4, 5, 6]},
            index=pd.date_range("2010-01-01", periods=3),
        )
        oos_start = None
        info = collections.OrderedDict({"df_info": dtf.get_df_info_as_string(df)})
        df_modeler = dtfmodamod.DataFrameModeler(
            df, oos_start=oos_start, info=info
        )
        json_str = df_modeler.dump_json()
        df_modeler_loaded = dtfmodamod.DataFrameModeler.load_json(json_str)
        pd.testing.assert_frame_equal(df_modeler.df, df_modeler_loaded.df)
        self.assertEqual(df_modeler.oos_start, df_modeler_loaded.oos_start)
        self.assertDictEqual(df_modeler.info, df_modeler_loaded.info)

    def test_load_json3(self) -> None:
        """
        Test by dumping json and loading it again with `info=None`.
        """
        df = pd.DataFrame(
            {"col0": [1, 2, 3], "col1": [4, 5, 6]},
            index=pd.date_range("2010-01-01", periods=3),
        )
        oos_start = pd.Timestamp("2010-01-01")
        info = None
        df_modeler = dtfmodamod.DataFrameModeler(
            df, oos_start=oos_start, info=info
        )
        json_str = df_modeler.dump_json()
        df_modeler_loaded = dtfmodamod.DataFrameModeler.load_json(json_str)
        pd.testing.assert_frame_equal(df_modeler.df, df_modeler_loaded.df)
        self.assertEqual(df_modeler.oos_start, df_modeler_loaded.oos_start)
        self.assertEqual(df_modeler.info, df_modeler_loaded.info)

    def test_apply_sklearn_model_fit_with_oos(self) -> None:
        pred_lag = 2
        data = self._get_data(pred_lag)
        config = self._get_config(pred_lag)
        df_modeler = dtfmodamod.DataFrameModeler(df=data, oos_start="2010-03-01")
        node_class = dtf.ContinuousSkLearnModel
        output = df_modeler.apply_node(node_class, config.to_dict())
        output_df = output.df
        str_output = hpandas.df_to_str(
            output_df.round(3), num_rows=None, precision=3
        )
        self.check_string(str_output, fuzzy_match=True)

    def test_apply_sklearn_model_predict_with_oos(self) -> None:
        pred_lag = 2
        data = self._get_data(pred_lag)
        config = self._get_config(pred_lag)
        df_modeler = dtfmodamod.DataFrameModeler(df=data, oos_start="2010-03-01")
        node_class = dtf.ContinuousSkLearnModel
        output = df_modeler.apply_node(
            node_class, config.to_dict(), method="predict"
        )
        output_df = output.df
        str_output = hpandas.df_to_str(
            output_df.round(3), num_rows=None, precision=3
        )
        self.check_string(str_output, fuzzy_match=True)

    def test_apply_sklearn_model_fit_without_oos(self) -> None:
        pred_lag = 2
        data = self._get_data(pred_lag)
        config = self._get_config(pred_lag)
        df_modeler = dtfmodamod.DataFrameModeler(df=data)
        node_class = dtf.ContinuousSkLearnModel
        output = df_modeler.apply_node(node_class, config.to_dict())
        output_df = output.df
        str_output = hpandas.df_to_str(
            output_df.round(3), num_rows=None, precision=3
        )
        self.check_string(str_output, fuzzy_match=True)

    def test_apply_sklearn_model_predict_without_oos(self) -> None:
        pred_lag = 2
        data = self._get_data(pred_lag)
        config = self._get_config(pred_lag)
        df_modeler = dtfmodamod.DataFrameModeler(df=data)
        node_class = dtf.ContinuousSkLearnModel
        with self.assertRaises(AssertionError):
            df_modeler.apply_node(node_class, config.to_dict(), method="predict")

    def test_merge(self) -> None:
        df1 = pd.DataFrame(
            {"col0": [1, 2, 3], "col1": [4, 5, 6]},
            index=pd.date_range("2010-01-01", periods=3),
        )
        df2 = pd.DataFrame(
            {"col2": [7, 8, 9, 10, 11]},
            index=pd.date_range("2010-01-01", periods=5),
        )
        dfm = dtfmodamod.DataFrameModeler(df1, oos_start="2010-01-01")
        dfm = dfm.merge(dtfmodamod.DataFrameModeler(df2, oos_start="2010-01-02"))
        df = pd.merge(df1, df2, left_index=True, right_index=True)
        pd.testing.assert_frame_equal(dfm.df, df)
        self.assertEqual(dfm.oos_start, pd.Timestamp("2010-01-01"))
        str_output = hpandas.df_to_str(dfm.df, num_rows=None)
        self.check_string(str_output)

    def _get_config(self, steps_ahead: int) -> cconfig.Config:
        config = cconfig.Config()
        config["x_vars"] = ["x"]
        config["y_vars"] = ["y"]
        config["steps_ahead"] = steps_ahead
        config["model_func"] = slm.LinearRegression
        config["col_mode"] = "merge_all"
        return config

    def _get_data(self, lag: int) -> pd.DataFrame:
        """
        Generate "random returns".

        Use lag + noise as predictor.
        """
        num_periods = 100
        total_steps = num_periods + lag + 1
        rets = carsigen.get_gaussian_walk(0, 0.2, total_steps, seed=10).diff()
        noise = carsigen.get_gaussian_walk(0, 0.02, total_steps, seed=1).diff()
        pred = rets.shift(-lag).loc[1:num_periods] + noise.loc[1:num_periods]
        resp = rets.loc[1:num_periods]
        idx = pd.date_range("2010-01-01", periods=num_periods, freq="D")
        df = pd.DataFrame.from_dict({"x": pred, "y": resp}).set_index(idx)
        return df
