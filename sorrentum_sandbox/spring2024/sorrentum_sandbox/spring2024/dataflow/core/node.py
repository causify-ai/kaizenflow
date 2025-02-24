"""
Import as:

import dataflow.core.node as dtfcornode
"""
import abc
import logging
from typing import Any, Dict, List, Optional

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Core node classes
# #############################################################################

# We use a string to represent a node's unique identifier. This type helps
# improve the interface and make the code more readable (e.g., `Dict[NodeId, ...]`
# instead of `Dict[str, ...]`).
NodeId = str


class _Node(abc.ABC):
    """
    Abstract node class for creating DAGs of functions.

    This class provides:
    - a unique identifier (`nid`) for building graphs of nodes. The `nid` is also
      useful for config purposes.
    - some convenient introspection (input/output names) accessors
    """

    # TODO(gp): Are inputs / output without names useful? If not we can simplify the
    #   interface.
    # TODO(gp): inputs -> input_names, outputs -> output_names
    def __init__(
        self,
        nid: NodeId,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
    ) -> None:
        """
        Constructor.

        :param nid: node identifier. Should be unique in a graph.
        :param inputs: list-like string names of `input_names`. `None` for no names.
        :param outputs: list-like string names of `output_names`. `None` for no names.
        """
        hdbg.dassert_isinstance(nid, NodeId)
        hdbg.dassert(nid, "Empty string chosen for unique nid!")
        self._nid = nid
        self._input_names = self._init_validation_helper(inputs)
        self._output_names = self._init_validation_helper(outputs)

    @property
    def nid(self) -> NodeId:
        return self._nid

    @property
    def input_names(self) -> List[str]:
        return self._input_names

    @property
    def output_names(self) -> List[str]:
        return self._output_names

    # TODO(gp): Consider using the more common approach with `_check_validity()`.
    @staticmethod
    def _init_validation_helper(items: Optional[List[str]]) -> List[str]:
        """
        Ensure that items are valid and returns the validated items.
        """
        if items is None:
            return []
        # Make sure the items are all non-empty strings.
        for item in items:
            hdbg.dassert_isinstance(item, str)
            hdbg.dassert_ne(item, "")
        hdbg.dassert_no_duplicates(items)
        return items


# #############################################################################


# Name of a Node's method, e.g., `fit` or `predict`.
Method = str

# Mapping between the name of an output of a node and the corresponding stored value.
NodeOutput = Dict[str, Any]


# TODO(gp): Should we merge this with _Node? There is lots of class
#  hierarchy (_Node -> Node -> FitPredictNode) that doesn't seem really
#  used / useful any more.
class Node(_Node):
    """
    A node class that stores and retrieves its output values on a per-method
    basis. (e.g., "fit" or "predict")

    E.g., for each method (e.g., "fit" and "predict") returns a value
    for each output.
    """

    # TODO(gp): inputs -> input_names, outputs -> output_names
    def __init__(
        self,
        # TODO(gp): Use *args, **args since the interface is the same.
        nid: NodeId,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
    ) -> None:
        """
        Implement the same interface as `_Node`.
        """
        super().__init__(nid, inputs, outputs)
        # Dictionary method name -> output node name -> output.
        self._output_vals: Dict[Method, NodeOutput] = {}

    def get_output(self, method: Method, output_name: str) -> Any:
        """
        Return the value of output `name` for the requested `method`.
        """
        hdbg.dassert_in(
            method,
            self._output_vals.keys(),
            "%s of node %s has no output!",
            method,
            self.nid,
        )
        hdbg.dassert_in(
            output_name,
            self.output_names,
            "%s is not an output of node %s!",
            output_name,
            self.nid,
        )
        return self._output_vals[method][output_name]

    def get_outputs(self, method: Method) -> NodeOutput:
        """
        Return all the output values for the requested `method`.

        E.g., for a method "fit" it returns, "df_out" -> pd.DataFrame
        """
        hdbg.dassert_in(method, self._output_vals.keys())
        return self._output_vals[method]

    def free(self, *, only_warning: bool = True) -> None:
        """
        Deallocate all the data stored inside the node.

        Note that this should be called only after the node is not
        needed anymore.

        :param only_warning=True: raise an assertion or a warning if
        the memory is not actually reported as deallocated.
        """
        # Minimize the dependencies by importing locally since this is a method
        # called rarely, for now.
        import gc

        import helpers.hintrospection as hintros
        import helpers.hlogging as hloggin

        txt: List = []

        def _log(msg: str) -> None:
            txt.append(msg)
            # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug("%s", msg)
            _LOG.info("%s", msg)

        # Report the status before.
        rss_mem_before_in_gb = hloggin.get_memory_usage(process=None)[0]
        memory_as_str = str(hloggin.get_memory_usage_as_str(process=None))
        msg = "nid='%s', before free: memory=%s" % (self._nid, memory_as_str)
        _log(msg)
        # Traverse the data structure accumulating used memory.
        rss_used_mem_in_gb = 0.0
        for method, node_output in self._output_vals.items():
            for name in node_output:
                obj = node_output[name]
                used_mem_tmp = obj.memory_usage(deep=True).sum()
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug(
                        "Removing %s:%s -> type=%s, mem=%s refs=%s",
                        method,
                        name,
                        type(obj),
                        hintros.format_size(used_mem_tmp),
                        gc.get_referrers(obj),
                    )
                rss_used_mem_in_gb += used_mem_tmp / (1024**3)
        # Remove all the outstanding references to the objects.
        del obj
        del self._output_vals
        # Force garbage collection.
        gc.collect()
        # Recreate an empty data structure for the next DAG execution.
        self._output_vals: Dict[Method, NodeOutput] = {}  # type: ignore[no-redef]
        #
        rss_mem_after_in_gb = hloggin.get_memory_usage(process=None)[0]
        memory_as_str = str(hloggin.get_memory_usage_as_str(process=None))
        msg = "nid='%s', after free: memory=%s" % (self._nid, memory_as_str)
        _log(msg)
        # We should have deallocated at least 90 of the used memory by the node.
        rss_mem_diff_in_gb = rss_mem_before_in_gb - rss_mem_after_in_gb
        hdbg.dassert_lte(0, rss_used_mem_in_gb)
        msg = (
            "nid='%s' successfully deallocated releasing %.1f GB out of %.1f GB"
            % (self._nid, rss_mem_diff_in_gb, rss_used_mem_in_gb)
        )
        _log(msg)
        # txt_msg = "\n".join(txt)
        # hdbg.dassert_lte(
        #     0.9 * rss_used_mem_in_gb,
        #     rss_mem_diff_in_gb,
        #     msg=txt_msg,
        #     only_warning=only_warning,
        # )

    def _store_output(self, method: Method, output_name: str, value: Any) -> None:
        """
        Store the output for `name` and the specific `method`.
        """
        hdbg.dassert_in(
            output_name,
            self.output_names,
            "%s is not an output of node %s!",
            output_name,
            self.nid,
        )
        # Create a dictionary of values for `method` if it doesn't exist.
        if method not in self._output_vals:
            self._output_vals[method] = {}
        # Assign the requested value.
        self._output_vals[method][output_name] = value
