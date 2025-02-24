import logging
from typing import Tuple

import numpy as np
import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.correlation as dtfmodcorr
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def get_data(
    indices_equal: bool, columns_equal: bool
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    start_timestamp = pd.Timestamp("2020-01-01-09:30")
    df1_end_timestamp = pd.Timestamp("2022-09-28-10:30")
    if indices_equal:
        df2_end_timestamp = df1_end_timestamp
    else:
        df2_end_timestamp = pd.Timestamp("2022-09-28-10:35")
    #
    df1_cols = [100, 200]
    if columns_equal:
        df2_cols = df1_cols
    else:
        df2_cols = [100, 200, 300]
    # NOTE: The data is not invariant with respect to changes in the start/end
    #  times or the columns.
    df1 = cfidaexa.get_forecast_dataframe(
        start_timestamp,
        df1_end_timestamp,
        df1_cols,
        seed=1,
    )
    df2 = cfidaexa.get_forecast_dataframe(
        start_timestamp,
        df2_end_timestamp,
        df2_cols,
        seed=2,
    )
    return df1, df2


class Test_compute_correlations(hunitest.TestCase):
    def test_equal_axes(self) -> None:
        df1, df2 = get_data(True, True)
        corrs = dtfmodcorr.compute_correlations(df1, df2)
        precision = 4
        actual = hpandas.df_to_str(
            corrs.round(precision), num_rows=None, precision=precision
        )
        expected = r"""
     prediction  returns  volatility
100     -0.0011   0.0016      0.0097
200      0.0013  -0.0031      0.0018
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_unequal_indices_failure(self) -> None:
        with self.assertRaises(AssertionError):
            df1, df2 = get_data(False, True)
            _ = dtfmodcorr.compute_correlations(
                df1,
                df2,
            )

    def test_unequal_indices(self) -> None:
        df1, df2 = get_data(False, True)
        corrs = dtfmodcorr.compute_correlations(
            df1,
            df2,
            allow_unequal_indices=True,
        )
        precision = 4
        actual = hpandas.df_to_str(
            corrs.round(precision), num_rows=None, precision=precision
        )
        expected = r"""
     prediction  returns  volatility
100     -0.0044   0.0016      0.0097
200     -0.0015   0.0002      0.0057
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_unequal_columns_failure(self) -> None:
        df1, df2 = get_data(True, False)
        with self.assertRaises(AssertionError):
            _ = dtfmodcorr.compute_correlations(df1, df2)

    def test_unequal_columns(self) -> None:
        df1, df2 = get_data(True, False)
        corrs = dtfmodcorr.compute_correlations(
            df1,
            df2,
            allow_unequal_columns=True,
        )
        precision = 4
        actual = hpandas.df_to_str(
            corrs.round(precision), num_rows=None, precision=precision
        )
        expected = r"""
     prediction  returns  volatility
100     -0.0011   0.0016      0.0097
200      0.0013  -0.0031      0.0018
300         NaN      NaN         NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_remove_outliers(hunitest.TestCase):
    def get_df1(self) -> None:
        nums = np.array(
            [
                [-1.53580211, -0.88311838, -0.9268523],
                [0.09501515, 1.12366058, 0.80002804],
                [1.08125789, -0.20406254, -0.08120811],
                [0.33397661, 1.04270523, 1.59740044],
                [-0.4743577, -0.50033428, 0.09625748],
                [0.8941359, 1.19616695, -1.09999985],
                [-1.40818938, -0.42240908, -0.2632948],
                [-0.79188331, 2.1047349, 0.23452866],
                [-0.3200597, -0.53649986, -0.62987924],
                [0.32623263, 1.08249829, -0.81985613],
                [3.10699222, 0.14783941, 1.32086867],
                [1.03414825, 0.01248009, -0.82187353],
                [1.10943433, -0.54393293, 0.13566491],
                [-0.14998328, -2.40109159, 0.83874707],
                [0.80136256, -0.16536185, -0.41269046],
                [-0.37734219, -0.42609142, 2.12198585],
                [1.05515186, 1.59208727, -0.23878072],
                [-0.61766738, 1.53046652, -1.17789303],
                [1.07962295, -0.22866981, -0.52123512],
                [1.88383153, 2.15388803, -1.40128023],
                [-1.60486466, -1.2914935, -2.20470003],
                [-0.6113645, -0.53856561, 0.08046906],
                [0.38195559, -0.18929166, -1.61712474],
                [-0.11033695, 0.74294306, -0.08442939],
                [1.43922872, -1.46676904, 0.5632592],
                [-0.18302709, 0.72735447, -1.07294376],
                [0.5699014, -0.04598221, -2.03213193],
                [-0.04296407, -0.8878259, -0.72056154],
                [0.89140669, -1.53084954, -0.75036537],
                [0.55553088, -0.48892993, 0.76471976],
            ]
        )
        dates = (
            pd.date_range(end=pd.Timestamp("2022-05-05"), periods=30)
            .to_pydatetime()
            .tolist()
        )
        df = pd.DataFrame(nums, columns=["a", "b", "c"], index=dates)
        return df

    def get_df2(self) -> None:
        nums = np.array(
            [
                [0.95688092, -1.61211317, -0.49511472],
                [-1.18345345, -0.1784506, -2.15030254],
                [1.22679103, 2.41914244, 0.32424152],
                [0.84301801, 0.66286444, -0.11545963],
                [-0.33896853, -1.70096013, 1.87300553],
                [-0.50184827, -0.13878928, -0.18330645],
                [-0.07431446, -0.24753453, -0.84070791],
                [1.58537025, -1.2839932, -0.40655959],
                [-0.63102528, 1.01691436, -2.38013045],
                [0.07074936, 0.18946245, -0.47350746],
                [-0.80159395, 0.69250321, 0.98042399],
                [1.39437048, 0.93380013, 1.4213013],
                [0.91551884, 0.48759975, 0.03499219],
                [0.92336526, -0.86663111, -0.44961433],
                [1.17915856, 0.23447891, -1.05031986],
                [0.23184606, 0.79154335, 1.31570492],
                [0.79327324, -0.37828518, 1.14849524],
                [-0.15511277, -0.43720107, -1.3445319],
                [0.93769945, -0.93531101, 1.38676881],
                [-1.96857404, 0.39211937, 0.4067497],
                [1.17083631, 1.23111748, -0.09562158],
                [-0.00376395, 2.22474077, 0.14293839],
                [-1.96050123, -1.58404481, -2.32508485],
                [-0.55190869, -0.19300038, 1.57041683],
                [0.03164568, -0.29209098, -0.29495549],
                [0.84602043, 1.13781165, -1.0538485],
                [-1.32579285, 0.76399403, 0.64146817],
                [-0.37745564, 1.31407114, 0.62208967],
                [-0.39312642, 0.80881361, 0.43797826],
                [0.99352325, 1.35195131, 1.24468165],
            ]
        )
        dates = (
            pd.date_range(end=pd.Timestamp("2022-05-05"), periods=30)
            .to_pydatetime()
            .tolist()
        )
        df = pd.DataFrame(nums, columns=["a", "b", "c"], index=dates)
        return df

    def test1(self) -> None:
        """
        Given the initial DataFrame with 30 rows make sure that the function
        removes outliers.
        """
        df = self.get_df1()
        outlier_kwargs = {
            "outlier_columns": ["a", "b"],
            "outlier_quantiles": (0.05, 0.95),
        }
        df_modified = dtfmodcorr.remove_outliers(df, **outlier_kwargs)
        expected_length = 20
        expected_column_names = ["a", "b", "c"]
        expected_column_unique_values = None
        expected_signature = r"""# df=
        index=[2022-04-06 00:00:00, 2022-05-05 00:00:00]
        columns=a,b,c
        shape=(20, 3)
                        a         b         c
        2022-04-06 -1.535802 -0.883118 -0.926852
        2022-04-09  0.333977  1.042705  1.597400
        2022-04-10 -0.474358 -0.500334  0.096257
        ...
        2022-05-02  0.569901 -0.045982 -2.032132
        2022-05-03 -0.042964 -0.887826 -0.720562
        2022-05-05  0.555531 -0.488930  0.764720
        """
        self.check_df_output(
            df_modified,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )

    def test2(self) -> None:
        """
        Check that `remove_outliers()` works correctly inside
        `compute_correlations()`
        """
        df1 = self.get_df1()
        df2 = self.get_df2()
        outlier_kwargs = {
            "outlier_columns": ["a", "b"],
            "outlier_quantiles": (0.1, 0.9),
        }
        trim_outliers = True
        allow_unequal_indices = True
        corrs = dtfmodcorr.compute_correlations(
            df1,
            df2,
            trim_outliers=trim_outliers,
            outlier_kwargs=outlier_kwargs,
            allow_unequal_indices=allow_unequal_indices,
        )
        expected_length = 3
        expected_column_names = ["correlation"]
        expected_column_unique_values = None
        expected_signature = r"""# df=
        index=[a, c]
        columns=correlation
        shape=(3, 1)
        correlation
        a     0.317994
        b     0.230572
        c     0.498841
        """
        self.check_df_output(
            corrs,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            expected_signature,
        )
