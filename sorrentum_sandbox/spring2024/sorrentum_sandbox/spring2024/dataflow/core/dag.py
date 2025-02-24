"""
Import as:

import dataflow.core.dag as dtfcordag
"""

import itertools
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import networkx as networ
import pandas as pd
from tqdm.autonotebook import tqdm

import dataflow.core.node as dtfcornode
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hlist as hlist
import helpers.hlogging as hloggin
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.htimer as htimer
import helpers.hwall_clock_time as hwacltim

_LOG = logging.getLogger(__name__)


DagOutput = Dict[dtfcornode.NodeId, dtfcornode.NodeOutput]


# TODO(gp): Consider calling it `Dag` given our convention of snake case
#  abbreviations in the code (but not in comments).
class DAG(hobject.PrintableMixin):
    """
    Class for creating and executing a DAG of `Node`s.

    This class:
    - builds a DAG in terms of adding and connecting nodes
    - queries a DAG in terms of nodes, sources, and sinks
    - manages node execution and storage of outputs within executed nodes
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        mode: Optional[str] = None,
        get_wall_clock_time: Optional[hdateti.GetWallClockTime] = None,
    ) -> None:
        """
        Create a DAG.

        :param name: optional str identifier of the DAG
        :param mode: determine how to handle an attempt to add a node that already
            belongs to the DAG:
            - "strict": asserts
            - "loose": deletes old node (also removes edges) and adds new node. This
              is useful for interactive notebooks and debugging
        :param get_wall_clock_time: the function that returns the wall clock
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("name mode"))
        self._nx_dag = networ.DiGraph()
        # Store the DAG name.
        if name is not None:
            hdbg.dassert_isinstance(name, str)
        self._name = name
        # Store mode.
        mode = mode or "strict"
        hdbg.dassert_in(mode, ["strict", "loose"], "Unsupported mode requested")
        self._mode = mode
        # If no function is passed we use the actual machine wall-clock time.
        if get_wall_clock_time is None:
            event_loop = None
            get_wall_clock_time = lambda: hdateti.get_current_time(
                tz="ET", event_loop=event_loop
            )
        hdbg.dassert_isinstance(get_wall_clock_time, Callable)
        self._get_wall_clock_time = get_wall_clock_time
        # Set debug parameters so no debugging info is dumped by default.
        self._save_node_io = ""
        self._save_node_df_out_stats = False
        self._profile_execution = False
        self._dst_dir: Optional[str] = None
        self.set_debug_mode(
            self._save_node_io,
            self._save_node_df_out_stats,
            self._profile_execution,
            self._dst_dir,
        )
        # Disable freeing nodes.
        self.force_free_nodes = False

    def __repr__(self) -> str:
        """
        Return a detailed representation for debugging.

        E.g.,
        ```
        name=None
        mode=strict
        json=
          {
              "directed": true,
              ...
              "nodes": [
                  {
                      "id": "n1",
                      "stage": "Node"
                  }
              ]
          }
        ```
        """
        txt = []
        # Get the representation for the class.
        txt.append(super().__repr__())
        # Add more details.
        res = []
        res.append("nodes=" + str(self.nx_dag.nodes(data=True)))
        res.append("edges=" + str(self.nx_dag.edges(data=True)))
        res.append("json=\n" + self._to_json())
        res = "\n".join(res)
        num_spaces = 2
        txt.append(hprint.indent(res, num_spaces=num_spaces))
        # Assemble return value.
        txt = "\n".join(txt)
        return txt

    def set_debug_mode(
        self,
        save_node_io: str,
        save_node_df_out_stats: bool,
        profile_execution: bool,
        dst_dir: Optional[str],
    ) -> None:
        """
        Set the debug parameters.

        Sometimes it's difficult to pass these parameters (e.g., through a
        `DagBuilder`) so we allow to set them after construction.

        :param save_node_io: store the values at the interface of the nodes
            into a directory `dst_dir`. Disclaimer: the amount of data generate can
            be huge
            - ``: save no information
            - `df_as_csv`: save the full content of the node interface, using CSV for
              dataframes
            - `df_as_parquet`: like `df_as_csv` but using Parquet for dataframes
        :param save_node_df_out_stats: save high level information about the output DataFrame, e.g.,
            dtype info, shape info, memory usage, nans info
        :param profile_execution: if not `None`, store information about the
            execution of the nodes
        :param dst_dir: directory to save node interface and execution profiling info
        """
        hdbg.dassert_in(
            save_node_io,
            ("", "stats", "df_as_csv", "df_as_pq", "df_as_csv_and_pq"),
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "save_node_io save_node_df_out_stats profile_execution dst_dir"
                )
            )
        self._save_node_io = save_node_io
        # To process the profiling info in a human consumable form:
        # ```
        # ls -tr -1 tmp.dag_profile/*after* | xargs -n 1 -i sh -c 'echo; echo; echo "# {}"; cat {}'
        # ```
        self._save_node_df_out_stats = save_node_df_out_stats
        self._profile_execution = profile_execution
        self._dst_dir = dst_dir
        if self._dst_dir:
            hio.create_dir(self._dst_dir, incremental=False)
        if any(
            [
                self._save_node_io,
                self._save_node_df_out_stats,
                self._profile_execution,
            ]
        ):
            _LOG.warning(
                "Setting up debug mode: %s",
                hprint.to_str(
                    "save_node_io save_node_df_out_stats profile_execution dst_dir"
                ),
            )
            hdbg.dassert_is_not(
                dst_dir, None, "Need to specify a directory to save the data"
            )

    # /////////////////////////////////////////////////////////////////////////////
    # Accessor.
    # /////////////////////////////////////////////////////////////////////////////

    @property
    def nx_dag(self) -> networ.DiGraph:
        return self._nx_dag

    # TODO(*): Should we force to always have a name? So mypy can perform more
    #  checks.
    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def mode(self) -> str:
        return self._mode

    # /////////////////////////////////////////////////////////////////////////////
    # Build DAG.
    # /////////////////////////////////////////////////////////////////////////////

    def add_node(self, node: dtfcornode.Node) -> None:
        """
        Add `node` to the DAG.

        Rely upon the unique nid for identifying the node.
        """
        # In principle, `_Node` could be supported; however, to do so,
        # the `run` methods below would need to be suitably modified.
        hdbg.dassert_issubclass(
            node, dtfcornode.Node, "Only DAGs of class `Node` are supported"
        )
        # NetworkX requires that nodes be hashable and uses hashes for
        # identifying nodes. Because our `Node`s are objects whose hashes can
        # change as operations are performed, we use the `Node.nid` as the
        # NetworkX node and the `Node` instance as a `node attribute`, which we
        # identify internally with the keyword `stage`.
        #
        # Note that this usage requires that `nid`'s be unique within a given
        # DAG.
        if self.mode == "strict":
            hdbg.dassert(
                not self._nx_dag.has_node(node.nid),
                "A node with nid=%s already belongs to the DAG",
                node.nid,
            )
        elif self.mode == "loose":
            # If a node with the same id already belongs to the DAG:
            #   - Remove the node and all of its successors, and their incident
            #     edges
            #   - Add the new node to the graph.
            # This is useful for notebook research flows, e.g., rerunning
            # blocks that build the DAG incrementally.
            if self._nx_dag.has_node(node.nid):
                _LOG.warning(
                    "Node `%s` is already in DAG. Removing existing node, "
                    "successors, and all incident edges of such nodes",
                    node.nid,
                )
                # Remove node successors.
                for nid in networ.descendants(self._nx_dag, node.nid):
                    _LOG.warning("Removing nid=%s", nid)
                    self.remove_node(nid)
                # Remove node.
                _LOG.warning("Removing nid=%s", node.nid)
                self.remove_node(node.nid)
        else:
            hdbg.dfatal("Invalid mode='%s'", self.mode)
        # Add node.
        self._nx_dag.add_node(node.nid, stage=node)

    def get_node(self, nid: dtfcornode.NodeId) -> dtfcornode.Node:
        """
        Implement a convenience node accessor.

        :param nid: unique node id
        """
        hdbg.dassert_isinstance(nid, dtfcornode.NodeId)
        hdbg.dassert(self._nx_dag.has_node(nid), "Node `%s` is not in DAG", nid)
        return self._nx_dag.nodes[nid]["stage"]

    def remove_node(self, nid: dtfcornode.NodeId) -> None:
        """
        Remove node from DAG and clear any connected edges.
        """
        hdbg.dassert_isinstance(nid, dtfcornode.NodeId)
        hdbg.dassert(self._nx_dag.has_node(nid), "Node `%s` is not in DAG", nid)
        self._nx_dag.remove_node(nid)

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

        If this is called multiple times on the same nid's but with
        different output/input pairs, the additional input/output pairs
        are simply added to the existing edge (the previous ones are not
        overwritten).

        :param parent: tuple of the form (nid, output) or nid if it has
            a single output
        :param child: tuple of the form (nid, input) or just nid if it
            has a single input
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
        hdbg.dassert_isinstance(parent_nid, dtfcornode.NodeId)
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
        hdbg.dassert_isinstance(child_nid, dtfcornode.NodeId)
        hdbg.dassert_in(child_in, self.get_node(child_nid).input_names)
        # Ensure that `child_in` is not already hooked up to an output.
        for nid in self._nx_dag.predecessors(child_nid):
            hdbg.dassert_not_in(
                child_in,
                self._nx_dag.get_edge_data(nid, child_nid),
                "`%s` already receiving input from node %s",
                child_in,
                nid,
            )
        # Add the edge along with an `edge attribute` indicating the parent
        # output to connect to the child input.
        kwargs = {child_in: parent_out}
        self._nx_dag.add_edge(parent_nid, child_nid, **kwargs)
        # If adding the edge causes the DAG property to be violated, remove the
        # edge and raise an error.
        if not networ.is_directed_acyclic_graph(self._nx_dag):
            self._nx_dag.remove_edge(parent_nid, child_nid)
            hdbg.dfatal(
                f"Creating edge {parent_nid} -> {child_nid} introduces a cycle!"
            )

    def compose(self, dag: "DAG") -> None:
        """
        Add `dag` to self.

        Node sets of `self` and `dag` must be disjoint. The composition
        is the union of nodes and edges of `self` and `dag`.
        """
        hdbg.dassert_isinstance(dag, DAG)
        if self.mode == "loose":
            # The "loose" mode is for idempotent operations in a notebook.
            # If this is needed, we could implement it by
            # - ensuring all nodes of `dag` belong to `self`
            # - removing the intersection of nodes the ancestors of those nodes
            raise NotImplementedError
        elif self.mode == "strict":
            my_nodes = set(self._nx_dag.nodes)
            their_nodes = set(dag._nx_dag.nodes)
            hdbg.dassert(not my_nodes.intersection(their_nodes))
            composition = networ.compose(self._nx_dag, dag._nx_dag)
            hdbg.dassert(networ.is_directed_acyclic_graph(composition))
            self._nx_dag = composition
        else:
            hdbg.dfatal("Invalid mode='%s'", self.mode)

    # /////////////////////////////////////////////////////////////////////////////
    # Query DAG.
    # /////////////////////////////////////////////////////////////////////////////

    def get_sources(self) -> List[dtfcornode.NodeId]:
        """
        :return: list of nid's of source nodes
        """
        sources = []
        for nid in networ.topological_sort(self._nx_dag):
            if not any(True for _ in self._nx_dag.predecessors(nid)):
                sources.append(nid)
        return sources

    def get_sinks(self) -> List[dtfcornode.NodeId]:
        """
        :return: list of nid's of sink nodes
        """
        sinks = []
        for nid in networ.topological_sort(self._nx_dag):
            if not any(True for _ in self._nx_dag.successors(nid)):
                sinks.append(nid)
        return sinks

    def get_unique_source(self) -> dtfcornode.NodeId:
        """
        Return the only source node, asserting if there is more than one.
        """
        sources = self.get_sources()
        hdbg.dassert_eq(
            len(sources),
            1,
            "There is more than one sink node %s in DAG",
            str(sources),
        )
        return sources[0]

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

    def has_single_source(self) -> bool:
        sources = self.get_sources()
        if len(sources) == 1:
            return True
        return False

    def insert_at_head(self, obj: Union[dtfcornode.Node, "DAG"]) -> None:
        """
        Connect a node or single-sink DAG to the head (root) of the DAG.

        Asserts if the DAG has more than one source.
        """
        sources = self.get_sources()
        hdbg.dassert_lte(len(sources), 1)
        if isinstance(obj, dtfcornode.Node):
            self.add_node(obj)
            sink_nid = obj.nid
        elif isinstance(obj, DAG):
            sink_nid = obj.get_unique_sink()
            self.compose(obj)
        else:
            raise ValueError("Unsupported type(obj)=%s", type(obj))
        if sources:
            source_nid = sources[0]
            self.connect(sink_nid, source_nid)

    def has_single_sink(self) -> bool:
        sinks = self.get_sinks()
        if len(sinks) == 1:
            return True
        return False

    def append_to_tail(self, obj: Union[dtfcornode.Node, "DAG"]) -> None:
        """
        Connect a node or single-source DAG to the tail (leaf) of the DAG.

        Asserts if the DAG has more thank one sink.
        """
        sinks = self.get_sinks()
        hdbg.dassert_lte(len(sinks), 1)
        if isinstance(obj, dtfcornode.Node):
            self.add_node(obj)
            source_nid = obj.nid
        elif isinstance(obj, DAG):
            source_nid = obj.get_unique_source()
            self.compose(obj)
        else:
            raise ValueError("Unsupported type(obj)=%s", type(obj))
        if sinks:
            sink_nid = sinks[0]
            self.connect(sink_nid, source_nid)

    # /////////////////////////////////////////////////////////////////////////////
    # Execute DAG.
    # /////////////////////////////////////////////////////////////////////////////

    def run_dag(self, method: dtfcornode.Method) -> DagOutput:
        """
        Execute entire DAG.

        :param method: method of class `Node` (or subclass) to be executed for
            the entire DAG
        :return: dict keyed by sink node nid with values from node's
            `get_outputs(method)`
        """
        sinks = self.get_sinks()
        for id_, nid in enumerate(networ.topological_sort(self._nx_dag)):
            self._run_node(id_, nid, method)
        return {sink: self.get_node(sink).get_outputs(method) for sink in sinks}

    def run_leq_node(
        self,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        progress_bar: bool = True,
    ) -> dtfcornode.NodeOutput:
        """
        Execute DAG up to (and including) Node `nid` and return output.

        "leq" in the method name refers to the partial ordering on the vertices.
        This method runs a node if and only if there is a directed path from the
        node to `nid`. Nodes are run according to a topological sort.

        :param nid: desired terminal node for execution
        :param method: `Node` subclass method to be executed
        :return: the mapping from output name to corresponding value (i.e., the
            result of node `nid`'s `get_outputs(method)`
        """
        hdbg.dassert_isinstance(nid, dtfcornode.NodeId)
        hdbg.dassert_isinstance(method, dtfcornode.Method)
        ancestors = filter(
            lambda x: x in networ.ancestors(self._nx_dag, nid),
            networ.topological_sort(self._nx_dag),
        )
        # The `ancestors` filter only returns nodes strictly less than `nid`,
        # and so we need to add `nid` back.
        nids = itertools.chain(ancestors, [nid])
        # Execute all the ancestors of `nid`.
        if progress_bar:
            nids = tqdm(list(nids), desc="run_leq_node")
        for id_, pred_nid in enumerate(nids):
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Executing node '%s'", pred_nid)
            self._run_node(id_, pred_nid, method)
        # Retrieve the output the node.
        node = self.get_node(nid)
        node_output = node.get_outputs(method)
        return node_output

    # /////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////////

    def _to_json(self) -> str:
        # Get internal networkx representation of the DAG.
        graph: networ.classes.digraph.DiGraph = self.nx_dag
        node_link_data = networ.readwrite.json_graph.node_link_data(graph)
        # Remove stages names from `node_link_data` dictionary since they refer to
        # `Node` objects, which are not JSON serializable.
        # E.g., `node_link_data` looks like:
        #   {'directed': True,
        #    'graph': {},
        #    'links': [],
        #    'multigraph': False,
        #    'nodes': [{'id': 'n1',
        #               'stage': <dataflow.core.Node object at 0x...>}]}
        node_link_data = node_link_data.copy()
        for data in node_link_data["nodes"]:
            data["stage"] = data["stage"].__class__.__name__
        # Print as JSON.
        json_node_link_data = json.dumps(node_link_data, indent=4, sort_keys=True)
        return json_node_link_data

    def _write_prof_stats_to_dst_dir(
        self,
        topological_id: int,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        output_name: str,
        *,
        extra_txt: str = "",
    ) -> None:
        """
        Write information about the system (e.g., time and memory) before
        running a node.

        The file has a format like:
        ```
        {dst_dir}/
           node_io.stats/
               {method}.{topological_id}.{nid}.{output_name}.{machine_timestamp}.txt
        ```
        E.g.,
        ```
            system_log_dir/20220808/dag/
                node_io.prof/
                    predict.0.read_data.df_out.20220808_161500.txt
        ```

        :param topological_id, nid, method: information about the node and its method
            to run
        :param output_name: the tag to add to the file (e.g., `df_out`)
        """
        txt = []
        # We use the machine timestamp here since this is information about the
        # actual run and not the simulation.
        curr_timestamp = hwacltim.get_machine_wall_clock_time(as_str=True)
        txt.append(f"timestamp={curr_timestamp}")
        memory_as_str = str(hloggin.get_memory_usage_as_str(process=None))
        txt.append("memory=%s" % memory_as_str)
        if extra_txt:
            txt.append(extra_txt)
        txt = "\n".join(txt)
        # Report the information on the screen.
        _LOG.info(
            "\n%s\n%s",
            hprint.frame(
                "%s: method '%s' for node topological_id=%s nid='%s'"
                % (output_name, method, topological_id, nid)
            ),
            txt,
        )
        # Save information to file.
        # E.g., system_log_dir/20220808/dag/
        #   node_io.prof/
        #   predict.0.read_data.df_out.20220808_161500.txt
        dst_dir = cast(str, self._dst_dir)
        bar_timestamp = hwacltim.get_current_bar_timestamp(as_str=True)
        filename = (
            f"{method}.{topological_id}.{nid}.{output_name}.{bar_timestamp}.txt"
        )
        file_name = os.path.join(dst_dir, "node_io.prof", filename)
        hio.to_file(file_name, txt)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Saved log file '%s'", file_name)

    def _write_node_interface_to_dst_dir(
        self,
        topological_id: int,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        output_name: str,
        obj: Any,
    ) -> None:
        """
        Write information about the system (e.g., time and memory) before
        running a node.

        The file has a format like:
        ```
        {dst_dir}/
           node_io.stats/
               {method}.{topo_id}.{nid}.{output_name}.{bar_timestamp}.[csv|parquet]
        ```
        E.g.,
        ```
            system_log_dir/20220808/dag/
                node_io.data/
                    predict.0.read_data.df_out.20220808_161500.csv
        ```

        :param: similar to `_write_prof_stats_to_dst_dir()`
        """
        dst_dir = cast(str, self._dst_dir)
        bar_timestamp = hwacltim.get_current_bar_timestamp(as_str=True)
        wall_clock_time = self._get_wall_clock_time()
        wall_clock_time_str = wall_clock_time.strftime("%Y%m%d_%H%M%S")
        basename = f"{method}.{topological_id}.{nid}.{output_name}.{bar_timestamp}.{wall_clock_time_str}"
        file_name = os.path.join(dst_dir, "node_io.data", basename)
        #
        if isinstance(obj, pd.Series):
            obj = pd.DataFrame(obj)
        if isinstance(obj, pd.DataFrame):
            df = obj
            if self._save_node_df_out_stats:
                # Save high level description about the df.
                _LOG.debug("Saving node df out stats...")
                txt = hpandas.df_to_str(
                    df,
                    print_dtypes=True,
                    print_shape_info=True,
                    print_memory_usage=True,
                    print_nan_info=True,
                )
                hio.to_file(file_name + ".txt", txt)
            # Save content of the df.
            if self._save_node_io == "df_as_csv":
                csv_file_name = f"{file_name}.csv.gz"
                df.to_csv(csv_file_name, compression="gzip")
            elif self._save_node_io == "df_as_pq":
                parquet_file_name = f"{file_name}.parquet"
                hparque.to_parquet(df, parquet_file_name)
            elif self._save_node_io == "df_as_csv_and_pq":
                csv_file_name = f"{file_name}.csv.gz"
                df.to_csv(csv_file_name, compression="gzip")
                parquet_file_name = f"{file_name}.parquet"
                hparque.to_parquet(df, parquet_file_name)
            else:
                raise ValueError(f"Invalid save_node_io='{self._save_node_io}'")
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Saved log dir in '%s'", file_name)
        else:
            _LOG.warning(
                "Can't save node input / output of type '%s': %s",
                str(type(obj)),
                obj,
            )

    def _run_node(
        self,
        topological_id: int,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
    ) -> None:
        """
        Run the requested `method` on a single node.

        This method DOES NOT run (or re-run) ancestors of `nid`.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "\n%s",
                hprint.frame(
                    "Executing method '%s' for node topological_id=%s nid='%s' ..."
                    % (method, topological_id, nid)
                ),
            )
        # Save system info before execution of the node.
        if self._profile_execution:
            file_tag = "before_execution"
            self._write_prof_stats_to_dst_dir(
                topological_id, nid, method, file_tag
            )
            run_node_dtimer = htimer.dtimer_start(logging.DEBUG, "run_node")
            run_node_dmemory = htimer.dmemory_start(logging.DEBUG, "run_node")
        # Retrieve the arguments needed to execute the `method` on the node.
        kwargs = {}
        for pred_nid in self._nx_dag.predecessors(nid):
            kvs = self._nx_dag.edges[[pred_nid, nid]]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("pred_nid=%s, nid=%s", pred_nid, nid)
            pred_node = self.get_node(pred_nid)
            for input_name, value in kvs.items():
                # Retrieve output from store.
                kwargs[input_name] = pred_node.get_output(method, value)
                if self.force_free_nodes:
                    _LOG.warning(
                        "Forcing deallocation of pred_node=%s", pred_node
                    )
                    # TODO(gp): We should move this after using the data deallocating
                    # all the nodes whose output has been used. For linear pipelines,
                    # this check is not needed.
                    pred_node.free()
            # TODO(gp): Save info for inputs, if needed.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("kwargs are %s", kwargs)
        # Execute `node.method()`.
        with htimer.TimedScope(logging.DEBUG, "node_execution") as ts:
            node = self.get_node(nid)
            try:
                output = getattr(node, method)(**kwargs)
            except AttributeError as e:
                raise AttributeError(
                    f"An exception occurred in node '{nid}'\n{str(e)}"
                ) from e
        # Update the node.
        for output_name in node.output_names:
            value = output[output_name]
            node._store_output(  # pylint: disable=protected-access
                method, output_name, value
            )
            if self._save_node_io:
                # Save info for the output of the node.
                self._write_node_interface_to_dst_dir(
                    topological_id, nid, method, output_name, value
                )
        # Save system info after execution the node.
        if self._profile_execution:
            file_tag = "after_execution"
            txt = []
            txt.append(ts.get_result())
            txt.append(htimer.dtimer_stop(run_node_dtimer)[0])
            txt.append(htimer.dmemory_stop(run_node_dmemory))
            txt = "\n".join(txt)
            self._write_prof_stats_to_dst_dir(
                topological_id,
                nid,
                method,
                file_tag,
                extra_txt=txt,
            )


# TODO(Grisha): consider creating a class `DagStatsComputer` and moving the
# function (together with `DAG._write_prof_stats_to_dst_dir()`) there.
def load_prof_stats_from_dst_dir(
    dst_dir: str,
    topological_id: int,
    nid: str,
    method: str,
    output_name: str,
    bar_timestamp_as_str: str,
) -> str:
    """
    Load information about the system (e.g., time and memory) before or after
    running a node.

    This function is mirroring `DAG._write_prof_stats_to_dst_dir()`.

    Output example:
    ```
    timestamp=20230221_080022
    memory=rss=0.468GB vms=2.953GB mem_pct=2%
    node_execution done (5.036 s)
    run_node done (11.573 s)
    run_node done: start=(0.439GB 2.933GB 1%) end=(0.468GB 2.953GB 2%) diff=(0.029GB 0.020GB 0%)
    ```

    :param dst_dir: dir that contains the DAG output
    :param topological_id, nid, method: information about the node and its method
    :param output_name: the tag to add to the file (e.g., `after_execution`)
    :param bar_timestamp_as_str: bar timestamp to load the information for
    :return: text with information about the system
    """
    # E.g., `predict.8.process_forecasts.before_execution.20230221_030500.txt`.
    file_name = f"{method}.{topological_id}.{nid}.{output_name}.{bar_timestamp_as_str}.txt"
    file_path = os.path.join(dst_dir, "node_io.prof", file_name)
    txt = hio.from_file(file_path)
    return txt


# TODO(Grisha): consider creating a class `DagStatsComputer` and moving the
# function there.
def load_node_df_out_stats_from_dst_dir(
    dst_dir: str,
    topological_id: int,
    nid: str,
    method: str,
    bar_timestamp_as_str: str,
) -> str:
    """
    Load statistics about a node's results df.

    The statistics includes:
        - df memory consumption
        - df size
        - nan statistics
        - df data types

    :param dst_dir: dir that contains the DAG output
    :param topological_id, nid, method: information about the node and its method
    :param bar_timestamp_as_str: bar timestamp to load the information for
    :return: text with a node's results df statistics
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str(
                "dst_dir topological_id nid method bar_timestamp_as_str"
            )
        )
    node_data_dir = os.path.join(dst_dir, "node_io.data")
    hdbg.dassert_dir_exists(node_data_dir)
    # Do include the `wall_clock_timestamp_as_str` to simplify the interface, rather
    # just search for a file using the pattern.
    # E.g., `predict.8.process_forecasts.df_out.20230221_030500_20230221_030542.txt`.
    file_name_pattern = (
        f"{method}.{topological_id}.{nid}.df_out.{bar_timestamp_as_str}.*.txt"
    )
    cmd = f"find '{node_data_dir}' -name {file_name_pattern}"
    # TODO(Grisha): check that there is exactly one file.
    _, file_name = hsystem.system_to_string(cmd)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("file_name"))
    file_path = os.path.join(node_data_dir, file_name)
    txt = hio.from_file(file_path)
    return txt
