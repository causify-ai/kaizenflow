"""
Import as:

import dataflow.core.nodes.base as dtfconobas
"""

import abc
import collections
import copy
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import pandas as pd

import dataflow.core.node as dtfcornode
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# FitPredictNode
# #############################################################################


class FitPredictNode(dtfcornode.Node, abc.ABC):
    """
    Class with abstract sklearn-style `fit()` and `predict()` functions.

    The class contains an optional state that can be
    serialized/deserialized with `get_fit_state()` and
    `set_fit_state()`.

    Nodes may store a dictionary of information for each method
    following the method's invocation.
    """

    # Represent the output of a `FitPredictNode`, mapping an output name to a
    # dataframe.
    NodeOutput = Dict[str, pd.DataFrame]

    # Represent the state of a `Node`.
    NodeState = Dict[str, Any]

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
    ) -> None:
        # TODO(gp): Consider forcing to specify `inputs` and `outputs` so we can
        #  simplify interface and code.
        if inputs is None:
            inputs = ["df_in"]
        if outputs is None:
            outputs = ["df_out"]
        super().__init__(nid, inputs, outputs)
        self._info: collections.OrderedDict = collections.OrderedDict()

    # //////////////////////////////////////////////////////////////////////////
    # fit / predict.
    # //////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    def fit(self, df_in: pd.DataFrame) -> "FitPredictNode.NodeOutput":
        ...

    @abc.abstractmethod
    def predict(self, df_in: pd.DataFrame) -> "FitPredictNode.NodeOutput":
        ...

    def get_fit_state(self) -> "FitPredictNode.NodeState":
        _ = self
        return {}

    def set_fit_state(self, fit_state: "FitPredictNode.NodeState") -> None:
        _ = self, fit_state

    # //////////////////////////////////////////////////////////////////////////
    # Info.
    # //////////////////////////////////////////////////////////////////////////

    def get_info(
        self, method: dtfcornode.Method
    ) -> Optional[Union[str, collections.OrderedDict]]:
        """
        The returned `info` is not copied and the client should not modify it.
        """
        # TODO(Paul): Add a dassert_getattr function to use here and in core.
        hdbg.dassert_isinstance(method, str)
        hdbg.dassert(getattr(self, method))
        if method in self._info.keys():
            return self._info[method]
        # TODO(Paul): Maybe crash if there is no info.
        _LOG.warning("No info found for nid=%s, method=%s", self.nid, method)
        return None

    # TODO(gp): values -> info
    def _set_info(
        self, method: dtfcornode.Method, values: collections.OrderedDict
    ) -> None:
        """
        The passed `info` is copied internally.
        """
        hdbg.dassert_isinstance(method, str)
        hdbg.dassert(getattr(self, method))
        hdbg.dassert_isinstance(values, collections.OrderedDict)
        # Save the info in the node: we make a copy just to be safe.
        self._info[method] = copy.copy(values)


# #############################################################################
# DataSource
# #############################################################################


# TODO(gp):
#  In practice we are mixing two behaviors
#  1) allowing fit/predict through `set_fit_intervals` / `set_predict_intervals`
#  2) a mechanism in `fit`/`predict` to extract the desired data intervals
#  This node requires to have all the data stored in self.df so that `fit()` can
#   extract the subset to use.
#  Not all the nodes can / want to load all the data at once (e.g., nodes using
#  Parquet backend might want to read only the data that is needed for the
#  cross-validation).
class DataSource(FitPredictNode, abc.ABC):
    """
    A source node that generates train/test data from the passed data frame.

    Derived classes inject the data as a DataFrame in this class at construction
    time (e.g., from a passed DataFrame, reading from a file). This node implements
    the interface of `FitPredictNode` allowing to filter data for fitting and
    predicting based on intervals.

    Fit and predict intervals are interpreted as `[a, b]`.
    """

    def __init__(
        self, nid: dtfcornode.NodeId, outputs: Optional[List[str]] = None
    ) -> None:
        if outputs is None:
            outputs = ["df_out"]
        # TODO(gp): This seems a common function. We can factor it out in a
        #  `validate_string_list()`.
        # Do not allow any empty list, repetition, or empty strings.
        hdbg.dassert(outputs)
        hdbg.dassert_no_duplicates(outputs)
        for output in outputs:
            hdbg.dassert_ne(output, "")
        super().__init__(nid, inputs=[], outputs=outputs)
        # This data is initialized by the derived classes depending on their
        # semantics.
        self.df: Optional[pd.DataFrame] = None
        self._fit_intervals: Optional[dtfcorutil.Intervals] = None
        self._predict_intervals: Optional[dtfcorutil.Intervals] = None
        self._predict_idxs = None

    # //////////////////////////////////////////////////////////////////////////
    # fit / predict.
    # //////////////////////////////////////////////////////////////////////////

    def set_fit_intervals(
        self, intervals: Optional[dtfcorutil.Intervals]
    ) -> None:
        """
        Set the intervals to be used to generate data for the fit stage.

        :param intervals:
            - `None` means no filtering
            - a list of closed time intervals, e.g., `[[start1, end1], [start2, end2]]`.
              `None` boundary is interpreted as data start/end
            -
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("intervals=%s", intervals)
        if intervals is None:
            dtfcorutil.dassert_valid_intervals(intervals)
        self._fit_intervals = intervals

    # `DataSource` uses data passed at construction time, so it does not need a
    # `df_in` in either `fit()` or `predict()` as a typical `FitPredictNode` does.
    # For this reason the function signature is different.
    def fit(  # type: ignore[override]  # pylint: disable=arguments-differ
        self,
    ) -> Dict[str, pd.DataFrame]:
        """
        :return: training set as df
        """
        hdbg.dassert_is_not(self.df, None)
        self.df = cast(pd.DataFrame, self.df)
        # Filter.
        if self._fit_intervals is not None:
            # TODO(gp): Factor out this code in utils.py and make it support `None`
            #  endpoints.
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._fit_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            fit_df = self.df.loc[idx]
        else:
            fit_df = self.df
        # TODO(gp): Is this copy necessary?
        fit_df = fit_df.copy()
        hdbg.dassert(not fit_df.empty, "`fit_df` is empty")
        # Update `info`.
        info = collections.OrderedDict()
        info["fit_df_info"] = dtfcorutil.get_df_info_as_string(fit_df)
        self._set_info("fit", info)
        return {self.output_names[0]: fit_df}

    def set_predict_intervals(self, intervals: dtfcorutil.Intervals) -> None:
        """
        Same as `set_fit_intervals()`, but for the predict stage.
        """
        # TODO(Paul): Warn if intervals overlap with `fit` intervals.
        # TODO(Paul): Maybe enforce that the intervals be ordered.
        if intervals is not None:
            dtfcorutil.dassert_valid_intervals(intervals)
        self._predict_intervals = intervals

    # TODO(gp): Factor out common code with `fit()`.
    def predict(  # type: ignore[override]  # pylint: disable=arguments-differ
        self,
    ) -> Dict[str, pd.DataFrame]:
        """
        :return: test set as df
        """
        hdbg.dassert_is_not(self.df, None)
        self.df = cast(pd.DataFrame, self.df)
        if self._predict_intervals is not None:
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._predict_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            predict_df = self.df.loc[idx].copy()
        else:
            predict_df = self.df.copy()
        hdbg.dassert(not predict_df.empty)
        # Update `info`.
        info = collections.OrderedDict()
        info["predict_df_info"] = dtfcorutil.get_df_info_as_string(predict_df)
        self._set_info("predict", info)
        return {self.output_names[0]: predict_df}

    # //////////////////////////////////////////////////////////////////////////

    def get_df(self) -> pd.DataFrame:
        hdbg.dassert_is_not(self.df, None, "No DataFrame found!")
        return self.df


# #############################################################################
# Transformer
# #############################################################################


class Transformer(FitPredictNode, abc.ABC):
    """
    Single-input single-output node calling a stateless transformation.

    The transformation is user-defined and called before `fit()` and
    `predict()`.
    """

    # TODO(Paul): Consider giving users the option of renaming the single
    #  input and single output (but verify there is only one of each).
    def __init__(self, nid: dtfcornode.NodeId) -> None:
        super().__init__(nid)

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        hdbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        hdbg.dassert_no_duplicates(df_out.columns)
        # Update `info`.
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        hdbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        hdbg.dassert_no_duplicates(df_out.columns)
        # Update `info`.
        self._set_info("predict", info)
        return {"df_out": df_out}

    # //////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        """
        :return: df, info
        """


# #############################################################################
# Plumbing nodes
# #############################################################################


class YConnector(FitPredictNode):
    """
    Create an output dataframe from two input dataframes.
    """

    # TODO(Paul): Support different input/output names.
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        connector_func: Callable[..., pd.DataFrame],
        connector_kwargs: Optional[Any] = None,
    ) -> None:
        """
        :param nid: unique node id
        :param connector_func:
            * Merge
            ```
            connector_func = lambda df_in1, df_in2, **connector_kwargs:
                df_in1.merge(df_in2, **connector_kwargs)
            ```
            * Reindexing
            ```
            connector_func = lambda df_in1, df_in2, connector_kwargs:
                df_in1.reindex(index=df_in2.index, **connector_kwargs)
            ```
            * User-defined functions
            ```
            # my_func(df_in1, df_in2, **connector_kwargs)
            connector_func = my_func
            ```
        :param connector_kwargs: kwargs associated with `connector_func`
        """
        super().__init__(nid, inputs=["df_in1", "df_in2"])
        self._connector_func = connector_func
        self._connector_kwargs = connector_kwargs or {}
        self._df_in1_col_names = None
        self._df_in2_col_names = None

    def get_df_in1_col_names(self) -> List[str]:
        """
        Allow introspection on column names of input dataframe #1.
        """
        return self._get_col_names(self._df_in1_col_names)

    def get_df_in2_col_names(self) -> List[str]:
        """
        Allow introspection on column names of input dataframe #2.
        """
        return self._get_col_names(self._df_in2_col_names)

    def fit(  # type: ignore[override]  # pylint: disable=arguments-differ
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        df_out, info = self._apply_connector_func(df_in1, df_in2)
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(  # type: ignore[override]  # pylint: disable=arguments-differ
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        df_out, info = self._apply_connector_func(df_in1, df_in2)
        self._set_info("predict", info)
        return {"df_out": df_out}

    @staticmethod
    def _get_col_names(col_names: Optional[List[str]]) -> List[str]:
        hdbg.dassert_is_not(
            col_names,
            None,
            "No column names. This may indicate an invocation prior to graph "
            "execution.",
        )
        col_names = cast(List[str], col_names)
        return col_names

    def _apply_connector_func(
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        self._df_in1_col_names = df_in1.columns.tolist()
        self._df_in2_col_names = df_in2.columns.tolist()
        # TODO(Paul): Add meaningful info.
        df_out = self._connector_func(df_in1, df_in2, **self._connector_kwargs)
        info = collections.OrderedDict()
        info["df_merged_info"] = dtfcorutil.get_df_info_as_string(df_out)
        return df_out, info


# #############################################################################


class ColModeMixin:
    """
    Select columns to propagate in output dataframe.
    """

    # TODO(Paul): Refactor this so that it has clear pre and post processing stages.

    def _apply_col_mode(
        self,
        df_in: pd.DataFrame,
        df_out: pd.DataFrame,
        cols: Optional[List[Any]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Merge transformed dataframe with original dataframe.

        :param df_in: original dataframe
        :param df_out: transformed dataframe
        :param cols: columns in `df_in` that were transformed to obtain `df_out`
            - `None` defaults to all columns in `df_out`
        :param col_mode: Determines what columns are propagated.
            - "merge_all" (default): perform an outer merge between the
            - "replace_selected":
            - "replace_all": all columns are propagated
        :param col_rename_func: function for naming transformed columns, e.g.,
            `lambda x: "zscore_" + x`
            - `None` defaults to identity transform
        :return: dataframe with columns selected by `col_mode`
        """
        hdbg.dassert_isinstance(df_in, pd.DataFrame)
        hdbg.dassert_isinstance(df_out, pd.DataFrame)
        hdbg.dassert(cols is None or isinstance(cols, list))
        cols = cols or df_out.columns.tolist()
        #
        col_rename_func = col_rename_func or (lambda x: x)
        hdbg.dassert_isinstance(col_rename_func, collections.Callable)
        #
        col_mode = col_mode or "merge_all"
        # Rename transformed columns.
        df_out = df_out.rename(columns=col_rename_func)
        self._transformed_col_names = df_out.columns.tolist()
        # Select columns to return.
        if col_mode == "merge_all":
            shared_columns = df_out.columns.intersection(df_in.columns)
            hdbg.dassert(
                shared_columns.empty,
                "Transformed column names `%s` conflict with existing column "
                "names `%s`.",
                df_out.columns,
                df_in.columns,
            )
            df_out = df_in.merge(
                df_out, how="outer", left_index=True, right_index=True
            )
        elif col_mode == "replace_selected":
            df_in_not_transformed_cols = df_in.columns.drop(cols)
            hdbg.dassert(
                df_in_not_transformed_cols.intersection(df_out.columns).empty,
                "Transformed column names `%s` conflict with existing column "
                "names `%s`.",
                df_out.columns,
                df_in_not_transformed_cols,
            )
            df_out = df_in.drop(columns=cols).merge(
                df_out, left_index=True, right_index=True
            )
        elif col_mode == "replace_all":
            pass
        else:
            hdbg.dfatal("Unsupported column mode `%s`", col_mode)
        hdbg.dassert_no_duplicates(df_out.columns.tolist())
        return df_out


# #############################################################################
# Column processing helpers
# #############################################################################

# TODO(gp): -> processors.py


class GroupedColDfToDfColProcessor:
    """
    Provides dataflow processing wrappers for dataframe-to-dataframe functions.

    Examples:
    1.  Suppose we want to learn one model per instrument given a dataframe
        `df` with multilevel columns
        ```
        feat1           feat2           y
        MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3
        ```
        Then, to `preprocess()` we pass in a list of tuples, i.e.,
        `col_groups = [("feat1",), ("feat2",), ("y",)]. The function
        `preprocess()` returns a dictionary keyed by `MN0`, ..., `MN3`, with
        values consisting of dataframes with columns
        ```
        feat1 feat2 y
        ```
        Suppose the learning step returns a dataframe with column "y_hat" (one
        dataframe for each input dataframe). We then apply `postprocess()` to
        the dictionary of results, taking `col_group = (,)`, to obtain a single
        dataframe with multilevel columns
        ```
        y_hat
        MN0 MN1 MN2 MN3
        ```
    """

    @staticmethod
    def preprocess(
        df: pd.DataFrame,
        col_groups: List[Tuple[dtfcorutil.NodeColumn]],
    ) -> Dict[dtfcorutil.NodeColumn, pd.DataFrame]:
        """
        Provides wrappers for transformations operating on many columns.

        :param df: a dataframe with multilevel columns
        :param col_groups: a collection of tuples specifying all but column
            leaves. All tuples provided should provide access to the same
            set of leaf values (the leaf column names are the same). All tuples
            should have the same length.
        :return: a dictionary of single-column-level dataframes indexed by the
            selected leaf column names of `df`. To the single-column-level
            dataframe has column names generated from the last tuple positions
            of the tuples in `col_groups`.
        """
        # The list `col_groups` should be nonempty and not contain any
        # duplicates.
        hdbg.dassert_isinstance(col_groups, list)
        hdbg.dassert_lt(
            0, len(col_groups), msg="Tuple `col_group` must be nonempty."
        )
        hdbg.dassert_no_duplicates(col_groups)
        # This is an implementation requirement that we may be able to relax.
        hdbg.dassert_lte(1, len(col_groups))
        #
        hdbg.dassert_isinstance(df, pd.DataFrame)
        # Sanity check each column group tuple.
        for col_group in col_groups:
            hdbg.dassert_isinstance(col_group, tuple)
            hdbg.dassert_in(col_group, df.columns)
            hdbg.dassert_eq(
                len(col_group),
                df.columns.nlevels - 1,
                f"Dataframe multiindex column depth incompatible with {col_group}",
            )
        # Determine output dataframe column names.
        out_col_names = [col_group[-1] for col_group in col_groups]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("out_col_names=%s", out_col_names)
        hdbg.dassert_no_duplicates(out_col_names)
        # Sort before accessing leaf columns.
        df_out = df.sort_index(axis=1)
        # Determine keys (i.e., leaf column names).
        keys = df_out[col_groups[0]].columns.to_list()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("keys=%s", keys)
        # Ensure all groups have the same keys.
        for col_group in col_groups:
            hdbg.dassert_in(col_group, df_out.columns)
            col_group_keys = df_out[col_group].columns.to_list()
            hdbg.dassert_set_eq(keys, col_group_keys)
        # Swap levels in `df` so that keys are top level.
        df_out = df_out.swaplevel(i=-2, j=-1, axis=1)
        # Sort by keys for faster selection (needed post `swaplevel()`).
        df_out.sort_index(axis=1, level=-2, inplace=True)
        # To generate a dataframe for each key, generate tuples that key
        # up to the last two levels.
        roots = [col_group[:-1] for col_group in col_groups]
        # Get rid of any duplicates.
        roots = list(set(roots))
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("col group roots=%s", roots)
        # Generate one dataframe per key.
        dfs = {}
        for key in keys:
            local_dfs = []
            for root in roots:
                local_df = df_out[root + (key,)]
                local_df = local_df[out_col_names]
                local_dfs.append(local_df)
            local_df = pd.concat(local_dfs, axis=1)
            # Ensure that there is no column name ambiguity.
            hdbg.dassert_no_duplicates(local_df.columns.to_list())
            dfs[key] = local_df
        return dfs

    @staticmethod
    def postprocess(
        dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
        col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> pd.DataFrame:
        """
        As in `_postprocess_dataframe_dict()`.
        """
        return _postprocess_dataframe_dict(dfs, col_group)


# #############################################################################


class CrossSectionalDfToDfColProcessor:
    """
    Provide dataflow processing wrappers for cross-sectional transformations.

    These helpers are useful when we want to apply an operation such as principal
    component projection or residualization to a family of instruments.

    Examples:
    1.  Suppose we want to perform a principal component projection of
        `MN0`, ..., `MN3` of the `ret_0` group of a dataframe `df` with
        multilevel columns as follows:
        ```
        ret_0           close
        MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3
        ```
        Then we invoke `preprocess()` with `col_groups = [("ret_0",)]`.
        The principal component projection operates on a dataframe with columns
        ```
        MN0 MN1 MN2 MN3
        ```
        and returns a dataframe with columns
        ```
        0 1 2 3
        ```
        We apply `postprocess()` to this dataframe with
        `col_groups = [("pca",)]` to obtain
        ```
        pca
        0 1 2 3
        ```
    2.  If we perform residualization on `df` as given above instead of
        principal component projection, then column names are preserved
        after the residualization, and we may apply `postprocess()` to obtain.
        ```
        residual
        MN0 MN1 MN2 MN3
        ```
    """

    @staticmethod
    def preprocess(
        df: pd.DataFrame,
        col_groups: List[Tuple[dtfcorutil.NodeColumn]],
    ) -> Dict[dtfcorutil.NodeColumn, pd.DataFrame]:
        """
        As in `preprocess_multiindex_cols()`.
        """
        hdbg.dassert_isinstance(col_groups, list)
        hdbg.dassert_lt(
            0, len(col_groups), msg="Tuple `col_group` must be nonempty."
        )
        hdbg.dassert_no_duplicates(col_groups)
        # This is an implementation requirement that we may be able to relax.
        hdbg.dassert_lte(1, len(col_groups))
        # Extract dataframe by col_group.
        dfs = {}
        for col_group in col_groups:
            local_df = preprocess_multiindex_cols(df, col_group)
            dfs[col_group] = local_df
        return dfs

    @staticmethod
    def postprocess(
        dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Create a multi-indexed column dataframe from a single-indexed one.

        :param dfs: a dictionary of single-level column dataframe
        :return: a multi-indexed column dataframe, with columns prefixes
            given by `dfs.keys()`.
        """
        hdbg.dassert_isinstance(dfs, dict)
        # Ensure that the dictionary is not empty.
        hdbg.dassert(dfs)
        for root, df in dfs.items():
            # Perform sanity checks on dataframe.
            hdbg.dassert_isinstance(df, pd.DataFrame)
            hdbg.dassert_no_duplicates(df.columns)
            hdbg.dassert_eq(
                1,
                df.columns.nlevels,
            )
        #
        df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        return df


# #############################################################################


class SeriesToDfColProcessor:
    """
    Provide dataflow processing wrappers for series-to-dataframe functions.

    Examples of functions to wrap include:
        - series decompositions (e.g., STL, Fourier coefficients, wavelet
          levels)
        - multiple lags
        - volatility modeling

    Examples:
    1.  Suppose we want to add two lags of the columns `MN0`, ..., `MN3`
        of the `ret_0` group of a dataframe `df` with multilevel columns as
        follows:
        ```
        ret_0           close
        MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3
        ```
        Then we invoke `preprocess()` with `col_group = "ret_0"`.
        Two lags are computed for each column of the dataframe with columns
        ```
        MN0 MN1 MN2 MN3
        ```
        The results of the lag computation are represented by a dictionary with
        keys `MN0`, ..., `MN3` and values consisting of dataframes with columns
        ```
        lag_1 lag_2
        ```
        We apply `postprocess()` to this dataframe with `col_group = ()` (an
        empty tuple) to obtain
        ```
        lag_1           lag_2
        MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3
        ```
    """

    def __init__(self) -> None:
        _LOG.warning(
            "Constructing `SeriesToDfColProcessor`. Consider"
            "using `GroupedColDfToDfProcessor` instead."
        )

    @staticmethod
    def preprocess(
        df: pd.DataFrame,
        col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> pd.DataFrame:
        """
        As in `preprocess_multiindex_cols()`.
        """
        return preprocess_multiindex_cols(df, col_group)

    @staticmethod
    def postprocess(
        dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
        col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> pd.DataFrame:
        """
        As in `_postprocess_dataframe_dict()`.
        """
        return _postprocess_dataframe_dict(dfs, col_group)


# #############################################################################


class SeriesToSeriesColProcessor:
    """
    Provide dataflow processing wrappers for series-to-series functions.

    Examples of functions to wrap include:
    - signal filters (e.g., smooth moving averages, z-scoring, outlier processing)
    - rolling features (e.g., moments, centered moments)
    """

    def __init__(self) -> None:
        _LOG.warning(
            "Constructing `SeriesToSeriesColProcessor`. Consider"
            "using `GroupedColDfToDfProcessor` instead."
        )

    @staticmethod
    def preprocess(
        df: pd.DataFrame,
        col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> pd.DataFrame:
        """
        As in `preprocess_multiindex_cols()`.
        """
        return preprocess_multiindex_cols(df, col_group)

    @staticmethod
    def postprocess(
        srs: List[pd.Series],
        col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> pd.DataFrame:
        """
        Create a multi-indexed column dataframe from `srs` and `col_group`.

        :param srs: a list of symbols uniquely named (by symbol)
        :param col_group: column levels to add
        :return: multi-indexed column dataframe with series names as
            leaf columns
        """
        # Perform basic type checks.
        hdbg.dassert_isinstance(srs, list)
        for series in srs:
            hdbg.dassert_isinstance(series, pd.Series)
        hdbg.dassert_isinstance(col_group, tuple)
        # Create dataframe from series.
        df = pd.concat(srs, axis=1)
        # Ensure that there are no duplicates.
        hdbg.dassert_no_duplicates(df.columns)
        if col_group:
            df = pd.concat([df], axis=1, keys=[col_group])
        return df


# #############################################################################


def preprocess_multiindex_cols(
    df: pd.DataFrame,
    col_group: Tuple[dtfcorutil.NodeColumn],
) -> pd.DataFrame:
    """
    Extract a single-level column dataframe from a multi-indexed one.

    Typically, the last column index level corresponds to an instrument.

    :param df: multi-indexed column dataframe, e.g.,
        ```
        ret_0           close
        MN0 MN1 MN2 MN3 MN0 MN1 MN2 MN3
        ```
    :param col_group: tuple specifying all but leaf instruments, which are
        selected implicitly. E.g., `col_group = "ret_0"` extracts
        `(ret_0, MN0)` through `(ret_0, MN3)`.
    :return: a single-level column dataframe. E.g., a dataframe with
        columns
        ```
        MN0 MN1 MN2 MN3
        ```
        extracted from the `ret_0` group.
    """
    # Perform `col_group` sanity checks.
    hdbg.dassert_isinstance(col_group, tuple)
    # TODO(Paul): Consider whether we want to allow the "degenerate case".
    hdbg.dassert_lt(0, len(col_group), msg="Tuple `col_group` must be nonempty.")
    #
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Do not allow duplicate columns.
    hdbg.dassert_no_duplicates(df.columns)
    # Ensure compatibility between dataframe column levels and col groups.
    hdbg.dassert_eq(
        len(col_group),
        df.columns.nlevels - 1,
        "Dataframe multiindex column depth incompatible with config.",
    )
    # Select single-column-level dataframe and return.
    df_out = df.sort_index(axis=1)
    df_out = df_out[col_group].copy()
    return df_out


def _postprocess_dataframe_dict(
    dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
    col_group: Tuple[dtfcorutil.NodeColumn],
) -> pd.DataFrame:
    """
    Create a multi-indexed column dataframe from keys, values, `col_group`.

    :param dfs: dataframes indexed by symbol.
    :param col_group: column levels to prefix `df` columns with
    :return: multi-level column dataframe
        - leaf columns are symbols
        - the next column level is defined by the columns of the dataframes
          in `dfs` (which are to be the same).
        - the initial levels are given by `col_group`
    """
    hdbg.dassert_isinstance(dfs, dict)
    # Ensure that the dictionary is not empty.
    hdbg.dassert(dfs)
    # Obtain a reference index and column set.
    idx = None
    cols = None
    for symbol, df in dfs.items():
        if not df.empty:
            idx = df.index
            cols = df.columns
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Using symbol=`%s` for reference index and columns", symbol
                )
            break
    hdbg.dassert_is_not(idx, None)
    hdbg.dassert_is_not(cols, None)
    # Perform sanity checks on dataframe.
    empty_dfs = []
    for symbol, df in dfs.items():
        # Ensure that each values of `dfs` is a nonempty dataframe.
        hdbg.dassert_isinstance(df, pd.DataFrame)
        if df.empty:
            empty_dfs.append(symbol)
            _LOG.warning("Dataframe empty for symbol=`%s`.", symbol)
        # Ensure that `df` columns do not have duplicates and are single-level.
        hdbg.dassert_no_duplicates(df.columns)
        hdbg.dassert_eq(
            1,
            df.columns.nlevels,
        )
    # Make empty dfs NaN dfs.
    for symbol in empty_dfs:
        _LOG.warning("Imputing NaNs for symbol=`%s`", symbol)
        dfs[symbol] = pd.DataFrame(index=idx, columns=cols)
    # Ensure that `col_group` is a (possibly empty) tuple.
    hdbg.dassert_isinstance(col_group, tuple)
    # Insert symbols as a column level.
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    # Swap column levels so that symbols are leaves.
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    if col_group:
        df = pd.concat([df], axis=1, keys=[col_group])
    return df


# #############################################################################
# Dataframe stacking/unstacking
# #############################################################################

# TODO(gp): -> stackers.py


class DfStacker:
    """
    Stack and unstack dataframes with identical columns.

    A use case for this transformation is learning a pooled model.
    """

    @staticmethod
    def preprocess(
        dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Stack dataframes with identical columns into a single dataframe.

        :param dfs: dictionary of dataframes with identical columns
        :return: dataframes from `dfs` stacked vertically. The indices are not
            preserved, and the output dataframe has a range index.
        """
        DfStacker._validate_dfs(dfs)
        df = pd.concat(dfs.values()).reset_index(drop=True)
        return df

    @staticmethod
    def postprocess(
        dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame],
        df: pd.DataFrame,
    ) -> Dict[dtfcorutil.NodeColumn, pd.DataFrame]:
        """
        Unstack dataframes according to location in `dfs`

        :param dfs: as in `preprocess()`
        :param df: like the output of `preprocess()` in terms of shape and
            indices
        :return: a dictionary of dataframes keyed as `dfs`. Each value is a
            dataframe with the same index and same columns as the analogous
            dataframe of `dfs`.
        """
        DfStacker._validate_dfs(dfs)
        counter = 0
        out_dfs = {}
        for key, value in dfs.items():
            length = value.shape[0]
            out_df = df.iloc[counter : counter + length].copy()
            hdbg.dassert_eq(
                out_df.shape[0],
                value.shape[0],
                msg="Dimension mismatch for key=%s" % key,
            )
            out_df.index = value.index
            out_dfs[key] = out_df
            counter += length
        return out_dfs

    @staticmethod
    def _validate_dfs(dfs: Dict[dtfcorutil.NodeColumn, pd.DataFrame]) -> None:
        """
        Perform sanity checks on `dfs`.
        """
        # Ensure that `dfs` is nonempty.
        hdbg.dassert(dfs)
        # Ensure that all dataframes in `dfs` share the same index and the same
        # columns.
        key = next(iter(dfs))
        idx = dfs[key].index
        cols = dfs[key].columns.to_list()
        for key, value in dfs.items():
            hdbg.dassert_eq(cols, value.columns.to_list())
            # TODO(Paul): We may want to relax the identical index requirement.
            hdbg.dassert(idx.equals(value.index))
