import logging

import numpy as np

import core.config as cconfig
import dataflow.core.dag as dtfcordag
import dataflow.core.dag_builder_example as dtfcdabuex
import dataflow.core.dag_runner as dtfcodarun
import dataflow.core.nodes.sources as dtfconosou
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################


# TODO(gp): Factor out the common code in a _TestPipelineBuilder.
class TestArmaReturnsBuilder(hunitest.TestCase):
    """
    Test the `ArmaReturnsBuilder` pipeline.
    """

    def test1(self) -> None:
        dag_builder = dtfcdabuex.ArmaReturnsBuilder()
        config = dag_builder.get_config_template()
        dag = dag_builder.get_dag(config)
        #
        dag_runner = dtfcodarun.FitPredictDagRunner(dag)
        result_bundle = dag_runner.fit()
        #
        df_out = result_bundle.result_df
        str_output = (
            f"{hprint.frame('config')}\n{config}\n"
            f"{hprint.frame('df_out')}\n{hpandas.df_to_str(df_out, num_rows=None)}\n"
        )
        self.check_string(str_output, fuzzy_match=True)

    def test_str1(self) -> None:
        dag_builder = dtfcdabuex.ArmaReturnsBuilder()
        act = str(dag_builder)
        self.check_string(act)


class TestMvnReturnsBuilder(hunitest.TestCase):
    """
    Test the `MvnReturnsBuilder` pipeline.
    """

    def test1(self) -> None:
        dag_builder = dtfcdabuex.MvnReturns_DagBuilder()
        #
        overriding_config = cconfig.Config()
        overriding_config["load_prices"] = cconfig.Config.from_dict(
            {
                "frequency": "T",
                "start_date": "2010-01-04 09:30:00",
                "end_date": "2010-01-14 16:05:00",
                "dim": 4,
                "target_volatility": 0.25,
                "seed": 247,
            }
        )
        node = dtfconosou.MultivariateNormalDataSource
        nodes_to_insert = [("load_prices", node)]
        #
        config = dag_builder.get_config_template()
        dag = dag_builder.get_dag(config)
        # TODO(Paul): Clean up these calls.
        hdbg.dassert_eq(len(nodes_to_insert), 1)
        stage, node_ctor = nodes_to_insert[0]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("stage node_ctor"))
        head_nid = dag_builder._get_nid(stage)  # pylint: disable=protected-access
        node = node_ctor(
            head_nid,
            **overriding_config[head_nid],
        )
        dtfcordag.DAG.insert_at_head(dag, node)
        #
        dag_runner = dtfcodarun.FitPredictDagRunner(dag)
        result_bundle = dag_runner.fit()
        #
        df_out = result_bundle.result_df
        expected_cols = [
            ("close.ret_0", "MN0"),
            ("close.ret_0", "MN1"),
            ("close.ret_0", "MN2"),
            ("close.ret_0", "MN3"),
            ("twap.ret_0", "MN0"),
            ("twap.ret_0", "MN1"),
            ("twap.ret_0", "MN2"),
            ("twap.ret_0", "MN3"),
            ("vwap.ret_0", "MN0"),
            ("vwap.ret_0", "MN1"),
            ("vwap.ret_0", "MN2"),
            ("vwap.ret_0", "MN3"),
            ("close", "MN0"),
            ("close", "MN1"),
            ("close", "MN2"),
            ("close", "MN3"),
            ("twap", "MN0"),
            ("twap", "MN1"),
            ("twap", "MN2"),
            ("twap", "MN3"),
            ("volume", "MN0"),
            ("volume", "MN1"),
            ("volume", "MN2"),
            ("volume", "MN3"),
            ("vwap", "MN0"),
            ("vwap", "MN1"),
            ("vwap", "MN2"),
            ("vwap", "MN3"),
        ]
        np.testing.assert_equal(df_out.columns.to_list(), expected_cols)
        np.testing.assert_equal(df_out.shape, (2960, 28))
        np.testing.assert_equal(df_out.dropna(how="all").shape, (702, 28))

    def test_str1(self) -> None:
        dag_builder = dtfcdabuex.MvnReturns_DagBuilder()
        act = str(dag_builder)
        self.check_string(act)
