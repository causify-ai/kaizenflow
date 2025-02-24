import logging
import os

import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import dataflow.core.visualization as dtfcorvisu
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_dataflow_core_visualization1(hunitest.TestCase):
    def test_draw1(self) -> None:
        """
        Build a DAG and draw it in IPython.
        """
        dag = self._build_dag()
        _ = dtfcorvisu.draw(dag)

    def test_draw_to_file1(self) -> None:
        """
        Build a DAG, draw it, and save the result in a file.
        """
        dag = self._build_dag()
        # Save to file.
        dir_name = self.get_scratch_space()
        file_name = os.path.join(dir_name, "plot.png")
        dtfcorvisu.draw_to_file(dag, file_name)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("file_name=%s", file_name)
        # Check that the output file exists.
        self.assertTrue(os.path.exists(file_name))

    @staticmethod
    def _build_dag() -> dtfcordag.DAG:
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag.add_node(n1)
        return dag
