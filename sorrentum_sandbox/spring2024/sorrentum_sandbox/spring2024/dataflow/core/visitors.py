"""
Import as:

import dataflow.core.visitors as dtfcorvisi
"""

import collections
import copy
import logging
from typing import Any, Dict, List

import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# Mapping from node and method to some data.
# NodeInfo = MutableMapping[dtfcornode.NodeId, MutableMapping[dtfcornode.Method, Any]]
# NodeInfo = typing.OrderedDict[dtfcornode.NodeId, typing.OrderedDict[dtfcornode.Method, Any]]
NodeInfo = Dict[dtfcornode.NodeId, Dict[dtfcornode.Method, Any]]


# #############################################################################


def extract_info(
    dag: dtfcordag.DAG, methods: List[dtfcornode.Method]
) -> NodeInfo:
    """
    Extract node info from each DAG node.

    :param dag: dataflow DAG. Node info is populated upon running.
    :param methods: `Node` method infos to extract
    :return: nested `OrderedDict`
    """
    hdbg.dassert_isinstance(dag, dtfcordag.DAG)
    hdbg.dassert_isinstance(methods, list)
    info = collections.OrderedDict()
    graph = dag.nx_dag
    # Scan the nodes.
    for nid in graph.nodes():
        node_info = collections.OrderedDict()
        node = dag.get_node(nid)
        # Extract the info for each method.
        for method in methods:
            method_info = node.get_info(method)
            node_info[method] = copy.copy(method_info)
        # TODO(gp): Not sure about the double copy. Maybe a single deepcopy is
        # enough.
        info[nid] = copy.copy(node_info)
    return info  # type: ignore


# #############################################################################


NodeState = Dict[dtfcornode.NodeId, Dict[str, Any]]


# TODO(gp): We could save / load state also of DAGs with some stateless Node.
def get_fit_state(dag: dtfcordag.DAG) -> NodeState:
    """
    Obtain the node state learned during fit from DAG.

    :param dag: dataflow DAG consisting of `FitPredictNode`s
    :return: result of node `get_fit_state()` keyed by nid
    """
    hdbg.dassert_isinstance(dag, dtfcordag.DAG)
    fit_state = collections.OrderedDict()
    graph = dag.nx_dag
    # Scan the nodes.
    for nid in graph.nodes():
        node = dag.get_node(nid)
        # Save the info for the fit state.
        hdbg.dassert_isinstance(node, dtfconobas.FitPredictNode)
        node_fit_state = node.get_fit_state()
        fit_state[nid] = copy.copy(node_fit_state)
    return fit_state


def set_fit_state(dag: dtfcordag.DAG, fit_state: NodeState) -> None:
    """
    Initialize a DAG with pre-fit node state.

    :param dag: dataflow DAG consisting of `FitPredictNode`s
    :param fit_state: result of node `get_fit_state()` keyed by nid
    """
    hdbg.dassert_isinstance(dag, dtfcordag.DAG)
    hdbg.dassert_isinstance(fit_state, collections.OrderedDict)
    #
    graph = dag.nx_dag
    hdbg.dassert_eq(len(graph.nodes()), len(fit_state.keys()))
    # Scan the nodes.
    for nid in graph.nodes():
        node = dag.get_node(nid)
        # Set the info for the fit state.
        hdbg.dassert_isinstance(node, dtfconobas.FitPredictNode)
        hdbg.dassert_in(nid, fit_state.keys())
        node_fit_state = copy.copy(fit_state[nid])
        node.set_fit_state(node_fit_state)
