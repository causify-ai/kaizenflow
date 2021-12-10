"""
Import as:

import dataflow.core.dag as dtfcordag
"""
import itertools
import logging
from typing import Dict, List, Optional, Tuple, Union

import networkx as networ
from tqdm.autonotebook import tqdm

import dataflow.core.node as dtfcornode
import helpers.dbg as hdbg
import helpers.list as hlist
import helpers.printing as hprint

_LOG = logging.getLogger(__name__)

# #############################################################################
# Class for creating and executing a DAG of nodes.
# #############################################################################


DagOutput = Dict[dtfcornode.NodeId, dtfcornode.NodeOutput]


class DAG:
    """
    Class for building DAGs using Nodes.

    The DAG manages node execution and storage of outputs (within
    executed nodes).
    """

    # TODO(gp): -> name: str to simplify the interface
    def __init__(
        self, name: Optional[str] = None, mode: Optional[str] = None
    ) -> None:
        """
        Create a DAG.

        :param name: optional str identifier
        :param mode: determines how to handle an attempt to add a node that already
            belongs to the DAG:
            - "strict": asserts
            - "loose": deletes old node (also removes edges) and adds new node. This
              is useful for interactive notebooks and debugging.
        """
        self._dag = networ.DiGraph()
        #
        if name is not None:
            hdbg.dassert_isinstance(name, str)
        self._name = name
        #
        if mode is None:
            mode = "strict"
        hdbg.dassert_in(
            mode, ["strict", "loose"], "Unsupported mode %s requested!", mode
        )
        self._mode = mode

    # TODO(gp): A bit confusing since other classes have `dag / get_dag` method that
    #  returns a DAG. Also the code does `dag.dag`. Maybe -> `nx_dag()` to say that
    #  we are extracting the networkx data structures.
    @property
    def dag(self) -> networ.DiGraph:
        return self._dag

    # TODO(*): Should we force to always have a name? So mypy can perform more
    #  checks.
    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def mode(self) -> str:
        return self._mode

    def add_node(self, node: dtfcornode.Node) -> None:
        """
        Add `node` to the DAG.

        Rely upon the unique nid for identifying the node.
        """
        # In principle, `NodeInterface` could be supported; however, to do so,
        # the `run` methods below would need to be suitably modified.
        hdbg.dassert_issubclass(
            node, dtfcornode.Node, "Only DAGs of class `Node` are supported!"
        )
        # NetworkX requires that nodes be hashable and uses hashes for
        # identifying nodes. Because our Nodes are objects whose hashes can
        # change as operations are performed, we use the `Node.nid` as the
        # NetworkX node and the `Node` instance as a `node attribute`, which we
        # identifying internally with the keyword `stage`.
        #
        # Note that this usage requires that nid's be unique within a given
        # DAG.
        if self.mode == "strict":
            hdbg.dassert(
                not self._dag.has_node(node.nid),
                "A node with nid=%s already belongs to the DAG!",
                node.nid,
            )
        elif self.mode == "loose":
            # If a node with the same id already belongs to the DAG:
            #   - Remove the node and all of its successors (and their incident
            #     edges)
            #   - Add the new node to the graph.
            # This is useful for notebook research flows, e.g., rerunning
            # blocks that build the DAG incrementally.
            if self._dag.has_node(node.nid):
                _LOG.warning(
                    "Node `%s` is already in DAG. Removing existing node, "
                    "successors, and all incident edges of such nodes. ",
                    node.nid,
                )
                # Remove node successors.
                for nid in networ.descendants(self._dag, node.nid):
                    _LOG.warning("Removing nid=%s", nid)
                    self.remove_node(nid)
                # Remove node.
                _LOG.warning("Removing nid=%s", node.nid)
                self.remove_node(node.nid)
        else:
            hdbg.dfatal("Invalid mode='%s'", self.mode)
        # Add node.
        self._dag.add_node(node.nid, stage=node)

    def get_node(self, nid: dtfcornode.NodeId) -> dtfcornode.Node:
        """
        Implement a convenience node accessor.

        :param nid: unique node id
        """
        hdbg.dassert_isinstance(nid, dtfcornode.NodeId)
        hdbg.dassert(self._dag.has_node(nid), "Node `%s` is not in DAG!", nid)
        return self._dag.nodes[nid]["stage"]  # type: ignore

    def remove_node(self, nid: dtfcornode.NodeId) -> None:
        """
        Remove node from DAG and clear any connected edges.
        """
        hdbg.dassert(self._dag.has_node(nid), "Node `%s` is not in DAG!", nid)
        self._dag.remove_node(nid)

    def connect(
        self,
        parent: Union[
            Tuple[dtfcornode.NodeId, dtfcornode.NodeId], dtfcornode.NodeId
        ],
        child: Union[
            Tuple[dtfcornode.NodeId, dtfcornode.NodeId], dtfcornode.NodeId
        ],
    ) -> None:
        """
        Add a directed edge from parent node output to child node input.

        Raise if the requested edge is invalid or forms a cycle.

        If this is called multiple times on the same nid's but with different
        output/input pairs, the additional input/output pairs are simply added
        to the existing edge (the previous ones are not overwritten).

        :param parent: tuple of the form (nid, output) or nid if it has a single
            output
        :param child: tuple of the form (nid, input) or just nid if it has a single
            input
        """
        # Automatically infer output name when the parent has only one output.
        # Ensure that parent node belongs to DAG (through `get_node` call).
        if isinstance(parent, tuple):
            parent_nid, parent_out = parent
        else:
            parent_nid = parent
            parent_out = hlist.assert_single_element_and_return(
                self.get_node(parent_nid).output_names
            )
        hdbg.dassert_in(parent_out, self.get_node(parent_nid).output_names)
        # Automatically infer input name when the child has only one input.
        # Ensure that child node belongs to DAG (through `get_node` call).
        if isinstance(child, tuple):
            child_nid, child_in = child
        else:
            child_nid = child
            child_in = hlist.assert_single_element_and_return(
                self.get_node(child_nid).input_names
            )
        hdbg.dassert_in(child_in, self.get_node(child_nid).input_names)
        # Ensure that `child_in` is not already hooked up to an output.
        for nid in self._dag.predecessors(child_nid):
            hdbg.dassert_not_in(
                child_in,
                self._dag.get_edge_data(nid, child_nid),
                "`%s` already receiving input from node %s",
                child_in,
                nid,
            )
        # Add the edge along with an `edge attribute` indicating the parent
        # output to connect to the child input.
        kwargs = {child_in: parent_out}
        self._dag.add_edge(parent_nid, child_nid, **kwargs)
        # If adding the edge causes the DAG property to be violated, remove the
        # edge and raise an error.
        if not networ.is_directed_acyclic_graph(self._dag):
            self._dag.remove_edge(parent_nid, child_nid)
            hdbg.dfatal(
                f"Creating edge {parent_nid} -> {child_nid} introduces a cycle!"
            )

    def get_sources(self) -> List[dtfcornode.NodeId]:
        """
        :return: list of nid's of source nodes
        """
        sources = []
        for nid in networ.topological_sort(self._dag):
            if not any(True for _ in self._dag.predecessors(nid)):
                sources.append(nid)
        return sources

    def get_sinks(self) -> List[dtfcornode.NodeId]:
        """
        :return: list of nid's of sink nodes
        """
        sinks = []
        for nid in networ.topological_sort(self._dag):
            if not any(True for _ in self._dag.successors(nid)):
                sinks.append(nid)
        return sinks

    def get_unique_sink(self) -> dtfcornode.NodeId:
        """
        Return the only sink node, asserting if there is more than one.
        """
        sinks = self.get_sinks()
        hdbg.dassert_eq(
            len(sinks),
            1,
            "There is more than one sink node %s in DAG",
            str(sinks),
        )
        return sinks[0]

    def run_dag(self, method: dtfcornode.Method) -> DagOutput:
        """
        Execute entire DAG.

        :param method: method of class `Node` (or subclass) to be executed for
            the entire DAG
        :return: dict keyed by sink node nid with values from node's
            `get_outputs(method)`
        """
        sinks = self.get_sinks()
        for nid in networ.topological_sort(self._dag):
            self._run_node(nid, method)
        return {sink: self.get_node(sink).get_outputs(method) for sink in sinks}

    def run_leq_node(
        self,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        progress_bar: bool = True,
    ) -> dtfcornode.NodeOutput:
        """
        Execute DAG up to (and including) Node `nid` and returns output.

        "leq" refers to the partial ordering on the vertices. This method
        runs a node if and only if there is a directed path from the node to
        `nid`. Nodes are run according to a topological sort.

        :param nid: desired terminal node for execution
        :param method: `Node` subclass method to be executed
        :return: result of node nid's `get_outputs(method)`, i.e., mapping from
            output name to corresponding value
        """
        ancestors = filter(
            lambda x: x in networ.ancestors(self._dag, nid),
            networ.topological_sort(self._dag),
        )
        # The `ancestors` filter only returns nodes strictly less than `nid`,
        # and so we need to add `nid` back.
        nids = itertools.chain(ancestors, [nid])
        if progress_bar:
            nids = tqdm(list(nids), desc="run_leq_node")
        for n in nids:
            _LOG.debug("Executing node '%s'", n)
            self._run_node(n, method)
        node = self.get_node(nid)
        return node.get_outputs(method)

    def _run_node(
        self, nid: dtfcornode.NodeId, method: dtfcornode.Method
    ) -> None:
        """
        Run a single node.

        This method DOES NOT run (or re-run) ancestors of `nid`.
        """
        _LOG.debug(
            "\n%s",
            hprint.frame(
                "Node nid=`%s` executing method `%s`..." % (nid, method)
            ),
        )
        kwargs = {}
        for pre in self._dag.predecessors(nid):
            kvs = self._dag.edges[[pre, nid]]
            pre_node = self.get_node(pre)
            for k, v in kvs.items():
                # Retrieve output from store.
                kwargs[k] = pre_node.get_output(method, v)
        _LOG.debug("kwargs are %s", kwargs)
        node = self.get_node(nid)
        try:
            output = getattr(node, method)(**kwargs)
        except AttributeError as e:
            raise AttributeError(
                f"An exception occurred in node '{nid}'.\n{str(e)}"
            ) from e
        for out in node.output_names:
            node._store_output(  # pylint: disable=protected-access
                method, out, output[out]
            )
