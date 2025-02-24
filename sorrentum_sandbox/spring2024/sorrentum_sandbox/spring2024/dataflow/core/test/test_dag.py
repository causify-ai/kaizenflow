import logging
import os

import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import dataflow.core.visualization as dtfcorvisu
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# _TestDataflowHelper
# #############################################################################


class _TestDataflowHelper(hunitest.TestCase):
    def _check(self, dag: dtfcordag.DAG) -> None:
        """
        Compute and freeze with `check_string` the signature of a graph.
        """
        act = []
        #
        act.append(hprint.frame("# str"))
        act.append(str(dag))
        #
        act.append(hprint.frame("# repr"))
        act.append(repr(dag))
        #
        act = "\n".join(act)
        self.check_string(act, purify_text=True)
        # Make sure the DAG can be drawn into a file.
        dir_name = self.get_scratch_space()
        file_name = os.path.join(dir_name, "graph.png")
        dtfcorvisu.draw_to_file(dag, file_name)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Saved plot to %s", file_name)


# #############################################################################
# Test_dataflow_core_DAG1
# #############################################################################


class Test_dataflow_core_DAG1(_TestDataflowHelper):
    def test_add_nodes1(self) -> None:
        """
        Create a node and add it to a DAG.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag.add_node(n1)
        self._check(dag)

    def test_add_nodes2(self) -> None:
        """
        Demonstrate "strict" and "loose" behavior on repeated add_node().
        """
        dag_strict = dtfcordag.DAG(mode="strict")
        m1 = dtfcornode.Node("m1")
        dag_strict.add_node(m1)
        # Assert when adding a node that already exists.
        with self.assertRaises(AssertionError):
            dag_strict.add_node(m1)
        #
        dag_loose = dtfcordag.DAG(mode="loose")
        n1 = dtfcornode.Node("n1")
        # Add the same node twice.
        dag_loose.add_node(n1)
        dag_loose.add_node(n1)
        self._check(dag_loose)

    def test_add_nodes3(self) -> None:
        """
        Demonstrate "strict" and "loose" behavior on repeated add_node().

        Same as `test_add_nodes2()` but creating another node.
        """
        dag_strict = dtfcordag.DAG(mode="strict")
        m1 = dtfcornode.Node("m1")
        dag_strict.add_node(m1)
        m1_prime = dtfcornode.Node("m1")
        with self.assertRaises(AssertionError):
            dag_strict.add_node(m1_prime)
        #
        dag_loose = dtfcordag.DAG(mode="loose")
        n1 = dtfcornode.Node("n1")
        dag_loose.add_node(n1)
        n1_prime = dtfcornode.Node("n1")
        dag_loose.add_node(n1_prime)
        self._check(dag_loose)

    def test_add_nodes4(self) -> None:
        """
        Add multiple nodes to a DAG.
        """
        dag = dtfcordag.DAG()
        for name in ["n1", "n2", "n3", "n4"]:
            dag.add_node(dtfcornode.Node(name, inputs=["in1"], outputs=["out1"]))
        self._check(dag)

    def test_add_nodes5(self) -> None:
        """
        Re-adding a node clears node, successors, and edges in `loose` mode.
        """
        dag = dtfcordag.DAG(mode="loose")
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        n3 = dtfcornode.Node("n3", inputs=["in1"])
        dag.add_node(n3)
        dag.connect("n2", "n3")
        dag.add_node(n1)
        self._check(dag)


# #############################################################################
# Test_dataflow_core_DAG2
# #############################################################################


class Test_dataflow_core_DAG2(_TestDataflowHelper):
    def test_connect_nodes1(self) -> None:
        """
        Simplest case of connecting two nodes.
        """
        dag = self._get_two_nodes()
        dag.connect(("n1", "out1"), ("n2", "in1"))
        self._check(dag)

    def test_connect_nodes2(self) -> None:
        """
        Simplest case, but inferred input/output names.
        """
        dag = self._get_two_nodes()
        dag.connect("n1", "n2")
        self._check(dag)

    def test_connect_nodes3(self) -> None:
        """
        Ensure input/output names are valid.
        """
        dag = self._get_two_nodes()
        with self.assertRaises(AssertionError) as cm:
            dag.connect(("n2", "out1"), ("n1", "in1"))
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        'out1' in '[]'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_connect_nodes4(self) -> None:
        """
        Forbid creating cycles in DAG.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", inputs=["in1"], outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1"])
        dag.add_node(n2)
        # n1 -> n2
        dag.connect(("n1", "out1"), ("n2", "in1"))
        # n2 -> n1 creates a cycle.
        with self.assertRaises(AssertionError) as cm:
            dag.connect(("n2", "out1"), ("n1", "in1"))
        act = str(cm.exception)
        exp = """
        Creating edge n2 -> n1 introduces a cycle!
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_connect_nodes5(self) -> None:
        """
        Forbid creating cycles in DAG (inferred input/output names).
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", inputs=["in1"], outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        with self.assertRaises(AssertionError) as cm:
            dag.connect("n2", "n1")
        act = str(cm.exception)
        exp = r"""
        Creating edge n2 -> n1 introduces a cycle!
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_connect_nodes6(self) -> None:
        """
        A nontrivial, multi-input/output example.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1", "out2"])
        dag.add_node(n2)
        n3 = dtfcornode.Node("n3", inputs=["in1"], outputs=["out1"])
        dag.add_node(n3)
        n4 = dtfcornode.Node("n4", inputs=["in1"], outputs=["out1"])
        dag.add_node(n4)
        n5 = dtfcornode.Node("n5", inputs=["in1", "in2"], outputs=["out1"])
        dag.add_node(n5)
        dag.connect("n1", ("n2", "in1"))
        dag.connect(("n2", "out1"), "n3")
        dag.connect(("n2", "out2"), "n4")
        dag.connect("n3", ("n5", "in1"))
        dag.connect("n4", ("n5", "in2"))
        self._check(dag)

    def test_connect_nodes7(self) -> None:
        """
        Forbid connecting a node that doesn't belong to the DAG.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        with self.assertRaises(AssertionError) as cm:
            dag.connect("n2", "n1")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        cond=False
        Node `n2` is not in DAG
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_connect_nodes8(self) -> None:
        """
        Ensure at most one output connects to any input.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1", "out2"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.add_node(n2)
        dag.connect(("n1", "out1"), "n2")
        with self.assertRaises(AssertionError) as cm:
            dag.connect(("n1", "out2"), "n2")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        'in1' not in '{'in1': 'out1'}'
        `in1` already receiving input from node n1
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_connect_nodes9(self) -> None:
        """
        Allow multi-attribute edges if each input has at most one source.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1", "in2"])
        dag.add_node(n2)
        dag.connect("n1", ("n2", "in1"))
        dag.connect("n1", ("n2", "in2"))
        self._check(dag)

    def test_connect_nodes10(self) -> None:
        """
        Demonstrate adding edges is not idempotent.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        with self.assertRaises(AssertionError) as cm:
            dag.connect("n1", "n2")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        'in1' not in '{'in1': 'out1'}'
        `in1` already receiving input from node n1
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    @staticmethod
    def _get_two_nodes() -> dtfcordag.DAG:
        """
        Return a DAG with two unconnected nodes.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.add_node(n2)
        return dag


# #############################################################################
# Test_dataflow_core_DAG3
# #############################################################################


class Test_dataflow_core_DAG3(_TestDataflowHelper):
    def test_sources_sinks1(self) -> None:
        """
        Check sources and sinks of a single node linear DAG.
        """
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag.add_node(n1)
        #
        self.assertEqual(dag.get_sources(), ["n1"])
        self.assertEqual(dag.get_sinks(), ["n1"])

    def test_sources_sinks2(self) -> None:
        """
        Check sources and sinks of a two node linear DAG.
        """
        # Build a DAG n1 -> n2
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        # Check.
        self.assertEqual(dag.get_sources(), ["n1"])
        self.assertEqual(dag.get_sinks(), ["n2"])

    def test_sources_sinks3(self) -> None:
        dag = dtfcordag.DAG()
        src1 = dtfcornode.Node("src1", outputs=["out1"])
        dag.add_node(src1)
        src2 = dtfcornode.Node("src2", outputs=["out1"])
        dag.add_node(src2)
        m1 = dtfcornode.Node("m1", inputs=["in1", "in2"], outputs=["out1"])
        dag.add_node(m1)
        dag.connect("src1", ("m1", "in1"))
        dag.connect("src2", ("m1", "in2"))
        snk1 = dtfcornode.Node("snk1", inputs=["in1"])
        dag.add_node(snk1)
        dag.connect("m1", "snk1")
        snk2 = dtfcornode.Node("snk2", inputs=["in1"])
        dag.add_node(snk2)
        dag.connect("m1", "snk2")
        #
        sources = dag.get_sources()
        sources.sort()
        self.assertListEqual(sources, ["src1", "src2"])
        #
        sinks = dag.get_sinks()
        sinks.sort()
        self.assertListEqual(sinks, ["snk1", "snk2"])


# #############################################################################
# Test_dataflow_core_DAG4
# #############################################################################


class Test_dataflow_core_DAG4(_TestDataflowHelper):
    def test_insert_at_head1(self) -> None:
        """
        Insert a node at head on an empty DAG.
        """
        # Create an empty DAG.
        dag = dtfcordag.DAG()
        # Insert a new node at head.
        n1 = dtfcornode.Node("n1")
        dag.insert_at_head(n1)
        self._check(dag)

    def test_insert_at_head2(self) -> None:
        """
        Insert a node at head on a nonempty DAG.
        """
        # Create a single-node DAG.
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", inputs=["in1"])
        dag.add_node(n1)
        # Insert a new node at head.
        n2 = dtfcornode.Node("n2", outputs=["out1"])
        dag.insert_at_head(n2)
        self._check(dag)

    def test_insert_at_head3(self) -> None:
        """
        Insert a node at head on a multinode DAG.
        """
        # Create a multinode DAG.
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", inputs=["in1"], outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        # Insert a new node at head.
        n3 = dtfcornode.Node("n3", outputs=["out1"])
        dag.insert_at_head(n3)
        self._check(dag)

    def test_insert_at_head4(self) -> None:
        """
        Insert a DAG at head on a multinode DAG.
        """
        # Create a multinode DAG.
        dag1 = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", inputs=["in1"], outputs=["out1"])
        dag1.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag1.add_node(n2)
        dag1.connect("n1", "n2")
        # Create a second multinode DAG.
        dag2 = dtfcordag.DAG()
        n3 = dtfcornode.Node("n3", outputs=["out1"])
        dag2.add_node(n3)
        n4 = dtfcornode.Node("n4", inputs=["in1"], outputs=["out1"])
        dag2.add_node(n4)
        dag2.connect("n3", "n4")
        # Insert `dag2` at head of `dag1`.
        dag1.insert_at_head(dag2)
        self._check(dag1)

    def test_append_to_tail1(self) -> None:
        """
        Append a node to tail on an empty DAG.
        """
        # Create an empty DAG.
        dag = dtfcordag.DAG()
        # Append a new node to tail.
        n1 = dtfcornode.Node("n1")
        dag.append_to_tail(n1)
        self._check(dag)

    def test_append_to_tail2(self) -> None:
        """
        Append a node to tail on a nonempty DAG.
        """
        # Create a single-node DAG.
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        # Append a new node to tail.
        n2 = dtfcornode.Node("n2", inputs=["in1"])
        dag.append_to_tail(n2)
        self._check(dag)

    def test_append_to_tail3(self) -> None:
        """
        Append a node to tail on a multinode DAG.
        """
        # Create a multinode DAG.
        dag = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1"])
        dag.add_node(n2)
        dag.connect("n1", "n2")
        # Append a new node to tail.
        n3 = dtfcornode.Node("n3", inputs=["in1"])
        dag.append_to_tail(n3)
        self._check(dag)

    def test_append_to_tail4(self) -> None:
        """
        Append a DAG to tail on a multinode DAG.
        """
        # Create a multinode DAG.
        dag1 = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1", outputs=["out1"])
        dag1.add_node(n1)
        n2 = dtfcornode.Node("n2", inputs=["in1"], outputs=["out1"])
        dag1.add_node(n2)
        dag1.connect("n1", "n2")
        # Create a second multinode DAG.
        dag2 = dtfcordag.DAG()
        n3 = dtfcornode.Node("n3", inputs=["in1"], outputs=["out1"])
        dag2.add_node(n3)
        n4 = dtfcornode.Node("n4", inputs=["in1"])
        dag2.add_node(n4)
        dag2.connect("n3", "n4")
        # Append `dag2` to tail of `dag1`.
        dag1.append_to_tail(dag2)
        self._check(dag1)


# #############################################################################
# Test_dataflow_core_DAG5
# #############################################################################


class Test_dataflow_core_DAG5(_TestDataflowHelper):
    def test_compose_empty_with_empty(self) -> None:
        dag1 = dtfcordag.DAG()
        dag2 = dtfcordag.DAG()
        dag1.compose(dag2)
        self._check(dag1)

    def test_compose_empty_with_nonempty(self) -> None:
        dag1 = dtfcordag.DAG()
        #
        dag2 = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag2.add_node(n1)
        #
        dag1.compose(dag2)
        self._check(dag1)

    def test_compose_nonempty_with_empty(self) -> None:
        dag1 = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag1.add_node(n1)
        #
        dag2 = dtfcordag.DAG()
        #
        dag1.compose(dag2)
        self._check(dag1)

    def test_compose_nonempty_with_nonempty(self) -> None:
        dag1 = dtfcordag.DAG()
        n1 = dtfcornode.Node("n1")
        dag1.add_node(n1)
        #
        dag2 = dtfcordag.DAG()
        n2 = dtfcornode.Node("n2")
        dag2.add_node(n2)
        #
        dag1.compose(dag2)
        self._check(dag1)
