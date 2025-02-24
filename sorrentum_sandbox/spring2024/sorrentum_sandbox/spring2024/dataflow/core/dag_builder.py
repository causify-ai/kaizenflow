"""
Import as:

import dataflow.core.dag_builder as dtfcodabui
"""
import abc
import logging
from typing import Any, Dict, List, Optional, cast

import pandas as pd

import core.config as cconfig
import dataflow.core.dag as dtfcordag
import dataflow.core.node as dtfcornode
import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


class DagBuilder(abc.ABC):
    """
    Abstract class for creating DAGs.

    Each DagBuilder is specific of a DAG.

    Concrete classes must specify:
    1) `get_config_template()`
       - It returns a `Config` object that represents the parameters used to build
         the DAG
       - The config can depend upon variables used in class initialization
       - A config can be incomplete, e.g., `cconfig.DUMMY` is used for required
         fields that must be defined before the config can be used to initialize
         a DAG
    2) methods that allow changing a config in multiple places in self-consistent
       way (e.g., setting weights, setting frequency)
    3) methods that return properties of the DAG to be built (e.g., number of
       needed days of history)
    4) `get_dag()`
       - It builds a DAG
       - Defines the DAG nodes and how they are connected to each other. The
         passed-in config object tells this function how to configure / initialize
         the various nodes
       - Once the DAG is built, we assume that the DagBuilder and the config that
         generated can be safely discarded
    """

    def __init__(self, nid_prefix: Optional[str] = None) -> None:
        """
        Constructor.

        :param nid_prefix: a namespace ending with "/" for graph node
            naming. This may be useful if the DAG built by the builder
            is either built upon an existing DAG or will be built upon
            subsequently.
        """
        # If no nid prefix is specified, make it an empty string to simplify
        # the implementation of helpers.
        self._nid_prefix = nid_prefix or ""
        # Make sure the nid_prefix ends with "/" (unless it is "").
        if self._nid_prefix and not self._nid_prefix.endswith("/"):
            _LOG.warning(
                "Appended '/' to nid_prefix '%s'. To avoid this warning, "
                "only pass nid prefixes ending in '/'.",
                self._nid_prefix,
            )
            self._nid_prefix += "/"

    # ////////////////////////////////////////////////////////////////////////////
    # Print.
    # ////////////////////////////////////////////////////////////////////////////

    def __str__(self) -> str:
        txt = []
        txt.append(f"nid_prefix={self._nid_prefix}")
        #
        txt = "\n".join(txt)
        return txt

    # ////////////////////////////////////////////////////////////////////////////
    # Get specific (derived) parameters.
    # ////////////////////////////////////////////////////////////////////////////

    @staticmethod
    @abc.abstractmethod
    def get_column_name(tag: str) -> str:
        """
        Return the name of the column corresponding to `tag`.
        """

    # ////////////////////////////////////////////////////////////////////////////
    # Properties.
    # ////////////////////////////////////////////////////////////////////////////

    @property
    def nid_prefix(self) -> str:
        return self._nid_prefix

    @property
    def methods(self) -> List[str]:
        """
        Methods supported by the DAG.
        """
        # TODO(gp): Consider make this an abstractmethod. This should be a property
        #  of the DAG and not of the builder.
        return ["fit", "predict"]

    def to_string(self) -> str:
        """
        Return a string with a (verbose) representation of the DagBuilder.
        """
        txt = []
        txt.append(f"nid_prefix={self._nid_prefix}")
        #
        txt.append("get_config_template=")
        config_template = self.get_config_template()
        config_as_str = str(config_template)
        txt.append(hprint.indent(config_as_str, 2))
        #
        txt.append("dag=")
        # We can't validate the DAG since we are not filling all the dummies in the
        # config template.
        validate = False
        dag = self.get_dag(config_template, validate=validate)
        dag_as_str = repr(dag)
        txt.append(hprint.indent(dag_as_str, 2))
        #
        txt = "\n".join(txt)
        return txt

    # ////////////////////////////////////////////////////////////////////////////
    # Get config template.
    # ////////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    def get_config_template(self) -> cconfig.Config:
        """
        Return a config template compatible with `self.get_dag()`.

        :return: a valid configuration for `self.get_dag`, possibly with some
            "dummy" required paths.
        """

    def get_column_names_dict(self, column_names: List[str]) -> Dict[str, str]:
        """
        Build a dictionary by a column tag as a key and a column name as a
        value.

        E.g.:
        {
            "price": "vwap",
            "prediction": "feature",
            ...
        }
        """
        hdbg.dassert_isinstance(column_names, list)
        hdbg.dassert_lte(1, len(column_names))
        column_names_dict = {}
        for name in column_names:
            column_names_dict[name] = self.get_column_name(name)
        return column_names_dict

    # TODO(gp): -> tighten types along the lines of `Dict[Column, ...]`.
    # TODO(gp): Is this needed?
    def get_column_to_tags_mapping(  # pylint: disable=useless-return
        self, config: cconfig.Config
    ) -> Optional[Dict[Any, List[str]]]:
        """
        Get a dictionary of result nid column names to semantic tags.

        :return: dictionary keyed by column names and with values that
            are lists of str tag names
        """
        _ = self, config
        return None

    def get_required_start_timestamp(
        self, config: cconfig.Config, end_timestamp: pd.Timestamp
    ) -> pd.Timestamp:
        """
        Return the start_timestamp needed to execute pipeline to get a result
        on 'end_timestamp'.
        """
        mark_key_as_used = True
        effective_days = self.get_required_lookback_in_effective_days(
            config, mark_key_as_used
        )
        # TODO(gp): We should a trading calendar to handle holidays and half days.
        #  For now we just consider business days as an approximation.
        return end_timestamp - pd.tseries.offsets.BDay(effective_days)

    @abc.abstractmethod
    def get_trading_period(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        Return the current trading period.

        :return: string representation of a time interval, e.g., "1T",
            "5T"
        """

    # TODO(Grisha): -> `get_required_lookback_duration()`.
    # TODO(Grisha): return `pd.Timedelta` instead of the number of days.
    @abc.abstractmethod
    def get_required_lookback_in_effective_days(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> int:
        """
        Return the number of days needed to execute pipeline at the frequency
        given by config.
        """

    # ////////////////////////////////////////////////////////////////////////////
    # Set specific (derived) parameters.
    # ////////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    def set_weights(
        self, config: cconfig.Config, weights: pd.Series
    ) -> cconfig.Config:
        """
        Return a modified copy of `config` using given feature `weights`.
        """

    @abc.abstractmethod
    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        Convert trading period to fast prod setup.
        """

    # ////////////////////////////////////////////////////////////////////////////
    # Build DAG.
    # ////////////////////////////////////////////////////////////////////////////

    def get_dag(
        self,
        config: cconfig.Config,
        *,
        mode: str = "strict",
        validate: bool = True,
    ) -> dtfcordag.DAG:
        """
        Build DAG given `config`.

        :param config: configures DAG. It is up to the client to guarantee
            compatibility. The result of `self.get_config_template()` should
            always be compatible following template completion.
        :param mode: as in `DAG` constructor
        :return: `dag` with all builder operations applied
        """
        dag = self._get_dag(config, mode=mode)
        if validate:
            self._validate_config_and_dag(config, dag)
        return dag

    def get_fully_built_dag(self) -> dtfcordag.DAG:
        """
        Return the DAG for a fully specified (i.e., not template) config.
        """
        config = self.get_config_template()
        dag = self.get_dag(config)
        return dag

    # ////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ////////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _validate_config_and_dag(
        config: cconfig.Config, dag: dtfcordag.DAG
    ) -> None:
        """
        Implement sanity-checks for the provided config and a DAG.

        - Raises if `config` has a DUMMY value
        - Raises if `config` has an entry for a node that is not in the DAG
        """
        hdbg.dassert(cconfig.check_no_dummy_values(config))
        for key in config.to_dict().keys():
            # This raises if the node does not exist.
            dag.get_node(key)

    @staticmethod
    def _append(
        dag: dtfcordag.DAG, tail_nid: Optional[str], node: dtfcornode.Node
    ) -> str:
        """
        Append `node` to the DAG after the node `tail_nid`.

        A typical use of this function is like:
        ```
        tail_nid = None
        tail_nid = dag.append(tail_nid, node_1)
        ...
        tail_nid = dag.append(tail_nid, node_n)
        _ = tail_nid
        ```

        :param tail_nid: the nid of the node to append to. If `None` add only
            without appending. This allows a pattern like:
        """
        # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug("dag before appending=\n%s", str(dag))
        dag.add_node(node)
        if tail_nid is not None:
            dag.connect(tail_nid, node.nid)
        # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug("dag after appending=\n%s", str(dag))
        nid = node.nid
        nid = cast(str, nid)
        return nid

    def _get_nid(self, stage_name: str) -> str:
        hdbg.dassert_isinstance(stage_name, str)
        nid = self._nid_prefix + stage_name
        return nid

    @abc.abstractmethod
    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcordag.DAG:
        """
        Implement the DAG.
        """
        ...
