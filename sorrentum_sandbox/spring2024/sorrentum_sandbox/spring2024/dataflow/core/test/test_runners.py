import logging

import pandas as pd

import dataflow.core.dag_builder_example as dtfcdabuex
import dataflow.core.dag_runner as dtfcodarun
import dataflow.core.visitors as dtfcorvisi
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################


class TestRollingFitPredictDagRunner1(hunitest.TestCase):
    @staticmethod
    def get_datetimes(
        predict_start_timestamp: pd.Timestamp,
        predict_end_timestamp: pd.Timestamp,
        retraining_freq: str,
        retraining_lookback: int,
    ) -> str:
        datetimes = (
            dtfcodarun.RollingFitPredictDagRunner.generate_retraining_datetimes(
                predict_start_timestamp,
                predict_end_timestamp,
                retraining_freq,
                retraining_lookback,
            )
        )
        datetimes_as_str = hpandas.df_to_str(datetimes)
        return datetimes_as_str

    def test1(self) -> None:
        predict_start_timestamp = pd.Timestamp("2010-01-04 09:00")
        predict_end_timestamp = pd.Timestamp("2010-01-06 16:00")
        retraining_freq = "1D"
        retraining_lookback = 1
        actual = self.get_datetimes(
            predict_start_timestamp,
            predict_end_timestamp,
            retraining_freq,
            retraining_lookback,
        )
        expected = r"""
   fit_start    fit_end predict_start predict_end
0 2010-01-03 2010-01-03    2010-01-04  2010-01-04
1 2010-01-04 2010-01-04    2010-01-05  2010-01-05
2 2010-01-05 2010-01-05    2010-01-06  2010-01-06
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        predict_start_timestamp = pd.Timestamp("2010-01-04 09:30")
        predict_end_timestamp = pd.Timestamp("2010-01-10 16:00")
        retraining_freq = "1W"
        retraining_lookback = 3
        actual = self.get_datetimes(
            predict_start_timestamp,
            predict_end_timestamp,
            retraining_freq,
            retraining_lookback,
        )
        expected = r"""
   fit_start    fit_end predict_start predict_end
0 2009-12-13 2010-01-02    2010-01-03  2010-01-09
1 2009-12-20 2010-01-09    2010-01-10  2010-01-16
"""

        self.assert_equal(actual, expected, fuzzy_match=True)

    def test3(self) -> None:
        predict_start_timestamp = pd.Timestamp("2010-02-01 09:30")
        predict_end_timestamp = pd.Timestamp("2010-02-26 16:00")
        retraining_freq = "1W"
        retraining_lookback = 4
        actual = self.get_datetimes(
            predict_start_timestamp,
            predict_end_timestamp,
            retraining_freq,
            retraining_lookback,
        )
        expected = r"""
   fit_start    fit_end predict_start predict_end
0 2010-01-03 2010-01-30    2010-01-31  2010-02-06
1 2010-01-10 2010-02-06    2010-02-07  2010-02-13
2 2010-01-17 2010-02-13    2010-02-14  2010-02-20
3 2010-01-24 2010-02-20    2010-02-21  2010-02-27
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestIncrementalDagRunner1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test the DagRunner using `ArmaReturnsBuilder`.
        """
        dag_builder = dtfcdabuex.ArmaReturnsBuilder()
        config = dag_builder.get_config_template()
        # Create DAG and generate fit state.
        dag = dag_builder.get_dag(config)
        nid = dag.get_unique_sink()
        dag.run_leq_node(nid, "fit")
        fit_state = dtfcorvisi.get_fit_state(dag)
        #
        dag_runner = dtfcodarun.IncrementalDagRunner(
            dag=dag,
            start_timestamp="2010-01-04 15:30",
            end_timestamp="2010-01-04 15:45",
            freq="5T",
            fit_state=fit_state,
        )
        result_bundles = list(dag_runner.predict())
        self.assertEqual(len(result_bundles), 4)
        # Check that dataframe results of `col` do not retroactively change
        # over successive prediction steps (which would suggest future
        # peeking).
        col = "vwap_ret_0_vol.shift_-2_hat"
        for rb_i, rb_i_next in zip(result_bundles[:-1], result_bundles[1:]):
            srs_i = rb_i.result_df[col]
            srs_i_next = rb_i_next.result_df[col]
            self.assertTrue(srs_i.compare(srs_i_next[:-1]).empty)
