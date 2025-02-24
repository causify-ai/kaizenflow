"""
Import as:

import dataflow.core.nodes.transformers as dtfconotra
"""
import collections
import inspect
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

import numpy as np
import pandas as pd

import core.finance as cofinanc
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

_ResamplingRule = Union[pd.DateOffset, pd.Timedelta, str]


# #############################################################################
# Column transformers.
# #############################################################################


class ColumnTransformer(dtfconobas.Transformer, dtfconobas.ColModeMixin):
    """
    Perform non-index modifying changes of columns.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        # TODO(Paul): May need to assume `List` instead.
        cols: Optional[Iterable[str]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        :param nid: unique node id
        :param transformer_func: df -> df
            - The keyword `info` (if present) means that:
                - An empty dict is passed in to this `info`
                - The resulting (populated) dict is included in the node's
                  `_info`
        :param transformer_kwargs: `transformer_func` kwargs
        :param cols: columns to transform; `None` defaults to all available.
        :param col_rename_func: function for naming transformed columns, e.g.,
            `lambda x: "zscore_" + x`
        :param col_mode: determines what columns are propagated by the node.
            Same values as in `apply_col_mode()`.
        :param nan_mode: determines how to handle NaNs
            - `leave_unchanged` (default): do not process NaNs
            - `drop`: it applies to all columns simultaneously.
        """
        super().__init__(nid)
        if cols is not None:
            hdbg.dassert_isinstance(cols, list)
        self._cols = cols
        self._col_rename_func = col_rename_func
        self._col_mode = col_mode
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        # Store the list of columns after the transformation.
        self._transformed_col_names = None
        self._nan_mode = nan_mode or "leave_unchanged"
        # State of the object. This is set by derived classes.
        self._fit_cols = cols

    @property
    def transformed_col_names(self) -> List[str]:
        col_names = self._transformed_col_names
        hdbg.dassert_is_not(
            col_names,
            None,
            "No transformed column names. This may indicate "
            "an invocation prior to graph execution.",
        )
        col_names = cast(List[str], col_names)
        return col_names

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df_in = df.copy()
        df = df.copy()
        if self._fit_cols is None:
            self._fit_cols = df.columns.tolist() or self._cols
        hdbg.dassert_is_subset(self._fit_cols, df.columns)
        df = df[self._fit_cols]
        # Handle NaNs.
        idx = df.index
        if self._nan_mode == "leave_unchanged":
            pass
        elif self._nan_mode == "drop":
            df = df.dropna()
        else:
            raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()
        # Perform the column transformation operations.
        # Introspect to see whether `_transformer_func` contains an `info`
        # parameter. If so, inject an empty dict to be populated when
        # `_transformer_func` is executed.
        func_sig = inspect.signature(self._transformer_func)
        if "info" in func_sig.parameters:
            func_info = collections.OrderedDict()  # type: ignore
            df = self._transformer_func(
                df, info=func_info, **self._transformer_kwargs
            )
            info["func_info"] = func_info
        else:
            df = self._transformer_func(df, **self._transformer_kwargs)
        # Reindex df to align it with the original data.
        df = df.reindex(index=idx)
        # TODO(Paul): Consider supporting the option of relaxing or foregoing this
        #  check.
        hdbg.dassert(
            df.index.equals(df_in.index),
            "Input/output indices differ but are expected to be the same!",
        )
        # Maybe merge transformed columns with a subset of input df columns.
        df = self._apply_col_mode(
            df_in,
            df,
            cols=self._fit_cols,
            col_rename_func=self._col_rename_func,
            col_mode=self._col_mode,
        )
        # Update `info`.
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


class SeriesTransformer(dtfconobas.Transformer, dtfconobas.ColModeMixin):
    """
    Perform non-index modifying changes of columns.

    TODO(Paul): Factor out code common with `SeriesToSeriesTransformer`.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        # TODO(Paul): May need to assume `List` instead.
        cols: Optional[Iterable[Union[int, str]]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        :param nid: unique node id
        :param transformer_func: srs -> df. The keyword `info` (if present) is
            assumed to have a specific semantic meaning. If present,
                - An empty dict is passed in to this `info`
                - The resulting (populated) dict is included in the node's
                  `_info`
        :param transformer_kwargs: transformer_func kwargs
        :param cols: columns to transform; `None` defaults to all available.
        :param col_rename_func: function for naming transformed columns, e.g.,
            lambda x: "zscore_" + x
        :param col_mode: `merge_all`, `replace_selected`, or `replace_all`.
            Determines what columns are propagated by the node.
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to
            columns individually.
        """
        super().__init__(nid)
        if cols is not None:
            hdbg.dassert_isinstance(cols, list)
        self._cols = cols
        self._col_rename_func = col_rename_func
        self._col_mode = col_mode
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        # Store the list of columns after the transformation.
        self._transformed_col_names = None
        self._nan_mode = nan_mode or "leave_unchanged"
        self._fit_cols = cols

    @property
    def transformed_col_names(self) -> List[str]:
        col_names = self._transformed_col_names
        hdbg.dassert_is_not(
            col_names,
            None,
            "No transformed column names. This may indicate "
            "an invocation prior to graph execution.",
        )
        col_names = cast(List[str], col_names)
        return col_names

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df_in = df.copy()
        df = df.copy()
        if self._fit_cols is None:
            self._fit_cols = df.columns.tolist() or self._cols
        if self._cols is None:
            hdbg.dassert_set_eq(self._fit_cols, df.columns)
        df = df[self._fit_cols]
        idx = df.index
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()  # type: ignore
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        srs_list = []
        for col in self._fit_cols:
            srs, col_info = _apply_func_to_series(
                df[col],
                self._nan_mode,
                self._transformer_func,
                self._transformer_kwargs,
            )
            hdbg.dassert_isinstance(srs, pd.Series)
            srs.name = col
            if col_info is not None:
                func_info[col] = col_info
            srs_list.append(srs)
        info["func_info"] = func_info
        df = pd.concat(srs_list, axis=1)
        df = df.reindex(index=idx)
        # TODO(Paul): Consider supporting the option of relaxing or
        # foregoing this check.
        hdbg.dassert(
            df.index.equals(df_in.index),
            "Input/output indices differ but are expected to be the same!",
        )
        # Maybe merge transformed columns with a subset of input df columns.
        df = self._apply_col_mode(
            df_in,
            df,
            cols=df.columns.tolist(),
            col_rename_func=self._col_rename_func,
            col_mode=self._col_mode,
        )
        #
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


# #############################################################################
# Multi-level column transformers
# #############################################################################


class GroupedColDfToDfTransformer(dtfconobas.Transformer):
    """
    Wrap transformers using the `GroupedColDfToDfColProcessor` pattern.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        transformer_func: Callable[..., Union[pd.Series, pd.DataFrame]],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        col_mapping: Optional[
            Dict[dtfcorutil.NodeColumn, dtfcorutil.NodeColumn]
        ] = None,
        permitted_exceptions: Tuple[Any] = (),
        *,
        drop_nans: bool = False,
        reindex_like_input: bool = True,
        join_output_with_input: bool = True,
    ) -> None:
        """
        For reference, let.

          - N = df.columns.nlevels
          - leaf_cols = df[in_col_group].columns

        :param nid: unique node id
        :param in_col_groups: a list of group of cols specified by the first
            N - 1 levels
        :param out_col_group: new output col group names. This specifies the
            names of the first N - 1 levels. The leaf_cols names remain the
            same.
        :param transformer_func: df -> {df, srs}
        :param transformer_kwargs: transformer_func kwargs
        :param col_mapping: dictionary of output column names keyed by input
            column names
        :param permitted_exceptions: exceptions to ignore when applying the
            transformer function
        :param drop_nans: apply `dropna()` after grouping and extracting
            `in_col_groups` columns
        :param reindex_like_input: reindex result of `transformer_func` like
            the input dataframe
        :param join_output_with_input: whether to join the output with the input. A
            common case where this should typically be set to `False` is in
            resampling.
        """
        super().__init__(nid)
        # TODO(Paul): Add more checks here.
        hdbg.dassert_isinstance(in_col_groups, list)
        hdbg.dassert_isinstance(out_col_group, tuple)
        self._in_col_groups = in_col_groups
        self._out_col_group = out_col_group
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._col_mapping = col_mapping or {}
        self._drop_nans = drop_nans
        self._reindex_like_input = reindex_like_input
        self._join_output_with_input = join_output_with_input
        self._permitted_exceptions = permitted_exceptions
        # The leaf col names are determined from the dataframe at runtime.
        self._leaf_cols = None

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        #
        if self._join_output_with_input:
            df_in = df.copy()
        #
        in_dfs = dtfconobas.GroupedColDfToDfColProcessor.preprocess(
            df, self._in_col_groups
        )
        self._leaf_cols = list(in_dfs.keys())
        #
        info = collections.OrderedDict()  # type: ignore
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        out_dfs = {}
        for key in self._leaf_cols:
            df_out, key_info = _apply_func_to_data(
                in_dfs[key],
                self._transformer_func,
                self._transformer_kwargs,
                self._drop_nans,
                self._reindex_like_input,
                self._permitted_exceptions,
            )
            if df_out is None:
                _LOG.warning(
                    "No output for key=%s, imputing empty dataframe", key
                )
                df_out = pd.DataFrame()
            hdbg.dassert_isinstance(df_out, pd.DataFrame)
            if key_info is not None:
                func_info[key] = key_info
            if self._col_mapping:
                df_out = df_out.rename(columns=self._col_mapping)
            out_dfs[key] = df_out
        info["func_info"] = func_info
        df = dtfconobas.GroupedColDfToDfColProcessor.postprocess(
            out_dfs, self._out_col_group
        )
        if self._join_output_with_input:
            df = dtfcorutil.merge_dataframes(df_in, df)
        # TODO(Grisha): Dag execution time increases. See CmTask6664
        # for details.
        # info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        info["df_transformed_info"] = ""
        return df, info


class CrossSectionalDfToDfTransformer(dtfconobas.Transformer):
    """
    Wrap transformers using the `CrossSectionalDfToDfProcessor` pattern.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        out_col_groups: List[Tuple[dtfcorutil.NodeColumn]],
        transformer_func: Callable[..., Union[pd.Series, pd.DataFrame]],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        col_mapping: Optional[
            Dict[dtfcorutil.NodeColumn, dtfcorutil.NodeColumn]
        ] = None,
        permitted_exceptions: Tuple[Any] = (),
        *,
        drop_nans: bool = False,
        reindex_like_input: bool = True,
        join_output_with_input: bool = True,
    ) -> None:
        """
        Params same as in `GroupedColDfToDfTransformer.__init__()`.
        """
        super().__init__(nid)
        # TODO(Paul): Add more checks here.
        hdbg.dassert_isinstance(in_col_groups, list)
        hdbg.dassert_isinstance(out_col_groups, list)
        hdbg.dassert_eq(len(in_col_groups), len(out_col_groups))
        for idx in range(0, len(in_col_groups)):
            hdbg.dassert_isinstance(in_col_groups[idx], tuple)
            hdbg.dassert_isinstance(out_col_groups[idx], tuple)
            hdbg.dassert_eq(len(in_col_groups[idx]), len(out_col_groups[idx]))
        self._in_col_groups = in_col_groups
        self._out_col_groups = out_col_groups
        col_group_mapping = {}
        for idx in range(0, len(in_col_groups)):
            col_group_mapping[in_col_groups[idx]] = out_col_groups[idx]
        self._col_grouping_mapping = col_group_mapping
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._col_mapping = col_mapping or {}
        self._drop_nans = drop_nans
        self._reindex_like_input = reindex_like_input
        self._join_output_with_input = join_output_with_input
        self._permitted_exceptions = permitted_exceptions
        # The leaf col names are determined from the dataframe at runtime.
        self._leaf_cols = None

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        #
        if self._join_output_with_input:
            df_in = df.copy()
        #
        in_dfs = dtfconobas.CrossSectionalDfToDfColProcessor.preprocess(
            df, self._in_col_groups
        )
        #
        info = collections.OrderedDict()  # type: ignore
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        out_dfs = {}
        for key in in_dfs.keys():
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Applying cross-sectional function for key=%s", key)
            out_key = self._col_grouping_mapping[key]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Output key is out_key=%s", out_key)
            df_out, key_info = _apply_func_to_data(
                in_dfs[key],
                self._transformer_func,
                self._transformer_kwargs,
                self._drop_nans,
                self._reindex_like_input,
                self._permitted_exceptions,
            )
            if df_out is None:
                _LOG.warning(
                    "No output for key=%s, imputing empty dataframe", key
                )
                df_out = pd.DataFrame()
            hdbg.dassert_isinstance(df_out, pd.DataFrame)
            if key_info is not None:
                func_info[key] = key_info
            if self._col_mapping:
                df_out = df_out.rename(columns=self._col_mapping)
            out_dfs[out_key] = df_out
        info["func_info"] = func_info
        df = dtfconobas.CrossSectionalDfToDfColProcessor.postprocess(out_dfs)
        if self._join_output_with_input:
            df = dtfcorutil.merge_dataframes(df_in, df)
        # TODO(Grisha): Dag execution time increases. See CmTask6664
        # for details.
        # info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        info["df_transformed_info"] = ""
        return df, info


class SeriesToDfTransformer(dtfconobas.Transformer):
    """
    Wrap transformers using the `SeriesToDfColProcessor` pattern.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_group: Tuple[dtfcorutil.NodeColumn],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        transformer_func: Callable[..., pd.Series],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        *,
        drop_nans: bool = False,
        reindex_like_input: bool = True,
        join_output_with_input: bool = True,
    ) -> None:
        """
        For reference, let.

          - N = df.columns.nlevels
          - leaf_cols = df[in_col_group].columns

        :param nid: unique node id
        :param in_col_group: a group of cols specified by the first N - 1
            levels
        :param out_col_group: new output col group names. This specifies the
            names of the first N - 1 levels. The leaf_cols names remain the
            same.
        :param transformer_func: srs -> srs
        :param transformer_kwargs: transformer_func kwargs
        :param drop_nans: apply `dropna()` after grouping and extracting
            `in_col_groups` columns
        :param reindex_like_input: reindex result of `transformer_func` like
            the input dataframe
        join_output_with_input: whether to join the output with the input. A
            common case where this should typically be set to `False` is in
            resampling.
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(in_col_group, tuple)
        hdbg.dassert_isinstance(out_col_group, tuple)
        self._in_col_group = in_col_group
        self._out_col_group = out_col_group
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._drop_nans = drop_nans
        self._reindex_like_input = reindex_like_input
        self._join_output_with_input = join_output_with_input
        # The leaf col names are determined from the dataframe at runtime.
        self._leaf_cols = None

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # Preprocess to extract relevant flat dataframe.
        df_in = df.copy()
        df = dtfconobas.SeriesToDfColProcessor.preprocess(df, self._in_col_group)
        # Apply `transform()` function column-wise.
        self._leaf_cols = df.columns.tolist()
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()  # type: ignore
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        dfs = {}
        leaf_cols = self._leaf_cols
        leaf_cols = cast(List[str], leaf_cols)
        for col in leaf_cols:
            df_out, col_info = _apply_func_to_data(
                df[col],
                self._transformer_func,
                self._transformer_kwargs,
                self._drop_nans,
                self._reindex_like_input,
            )
            if df_out is None:
                _LOG.warning("No output for col=%s", col)
                continue
            hdbg.dassert_isinstance(df_out, pd.DataFrame)
            if col_info is not None:
                func_info[col] = col_info
            dfs[col] = df_out
        info["func_info"] = func_info
        # Combine the series representing leaf col transformations back into a
        # single dataframe.
        df = dtfconobas.SeriesToDfColProcessor.postprocess(
            dfs, self._out_col_group
        )
        if self._join_output_with_input:
            df = dtfcorutil.merge_dataframes(df_in, df)
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


class SeriesToSeriesTransformer(dtfconobas.Transformer):
    """
    Wrap transformers using the `SeriesToSeriesColProcessor` pattern.

    When operating on multiple columns, this applies the transformer function
    one series at a time. Additionally, NaN-handling is performed "locally"
    (one series at a time, without regard to NaNs in other columns).

    Example: df like
                          close                     vol
                          MN0   MN1    MN2   MN3    MN0    MN1    MN2    MN3
    2010-01-04 10:30:00 -2.62  8.81  14.93 -0.88  100.0  100.0  100.0  100.0
    2010-01-04 11:00:00 -2.09  8.27  16.75 -0.92  100.0  100.0  100.0  100.0
    2010-01-04 11:30:00 -2.52  6.97  12.56 -1.52  100.0  100.0  100.0  100.0
    2010-01-04 12:00:00 -2.54  5.30   8.90 -1.54  100.0  100.0  100.0  100.0
    2010-01-04 12:30:00 -1.91  2.02   4.65 -1.77  100.0  100.0  100.0  100.0

    Then, e.g., to calculate, returns, we could take
      - `in_col_group = "close",`
      - `out_col_group = "ret_0",`
    Notice that the trailing comma makes these tuples.

    The transformer_func and `nan_mode` would operate on the price columns
    individually and return one return column per price column, e.g.,
    generating

                          ret_0                   close                     vol
                          MN0   MN1   MN2   MN3   MN0   MN1    MN2   MN3    MN0    MN1    MN2    MN3
    2010-01-04 10:30:00 -0.02  0.11  0.16 -0.35 -2.62  8.81  14.93 -0.88  100.0  100.0  100.0  100.0
    2010-01-04 11:00:00 -0.20 -0.06  0.12  0.04 -2.09  8.27  16.75 -0.92  100.0  100.0  100.0  100.0
    2010-01-04 11:30:00  0.20 -0.16 -0.25  0.66 -2.52  6.97  12.56 -1.52  100.0  100.0  100.0  100.0
    2010-01-04 12:00:00  0.01 -0.24 -0.29  0.01 -2.54  5.30   8.90 -1.54  100.0  100.0  100.0  100.0
    2010-01-04 12:30:00 -0.25 -0.62 -0.48  0.15 -1.91  2.02   4.65 -1.77  100.0  100.0  100.0  100.0
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        in_col_group: Tuple[dtfcorutil.NodeColumn],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
        transformer_func: Callable[..., pd.Series],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        permitted_exceptions: Tuple[Any] = (),
        *,
        drop_nans: bool = False,
        reindex_like_input: bool = True,
        join_output_with_input: bool = True,
    ) -> None:
        """
        For reference, let.

          - N = df.columns.nlevels
          - leaf_cols = df[in_col_group].columns

        :param nid: unique node id
        :param in_col_group: a group of cols specified by the first N - 1
            levels
        :param out_col_group: new output col group names. This specifies the
            names of the first N - 1 levels. The leaf_cols names remain the
            same.
        :param transformer_func: srs -> srs
        :param transformer_kwargs: transformer_func kwargs
        :param drop_nans: apply `dropna()` after grouping and extracting
            `in_col_groups` columns
        :param reindex_like_input: reindex result of `transformer_func` like
            the input series
        join_output_with_input: whether to join the output with the input
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(in_col_group, tuple)
        hdbg.dassert_isinstance(out_col_group, tuple)
        hdbg.dassert_eq(
            len(in_col_group),
            len(out_col_group),
            msg="Column hierarchy depth must be preserved.",
        )
        self._in_col_group = in_col_group
        self._out_col_group = out_col_group
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._drop_nans = drop_nans
        self._reindex_like_input = reindex_like_input
        self._join_output_with_input = join_output_with_input
        self._permitted_exceptions = permitted_exceptions
        # The leaf col names are determined from the dataframe at runtime.
        self._leaf_cols = None

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # Preprocess to extract relevant flat dataframe.
        df_in = df.copy()
        df = dtfconobas.SeriesToSeriesColProcessor.preprocess(
            df, self._in_col_group
        )
        # Apply `transform()` function column-wise.
        self._leaf_cols = df.columns.tolist()
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()  # type: ignore
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        srs_list = []
        leaf_cols = self._leaf_cols
        leaf_cols = cast(List[str], leaf_cols)
        for col in leaf_cols:
            srs, col_info = _apply_func_to_data(
                df[col],
                self._transformer_func,
                self._transformer_kwargs,
                self._drop_nans,
                self._reindex_like_input,
                self._permitted_exceptions,
            )
            if srs is None:
                _LOG.warning("No output for key=%s, imputing NaNs", col)
                srs = pd.Series(np.nan, index=df[col].index)
            hdbg.dassert_isinstance(srs, pd.Series)
            srs.name = col
            if col_info is not None:
                func_info[col] = col_info
            srs_list.append(srs)
        info["func_info"] = func_info
        # Combine the series representing leaf col transformations back into a
        # single dataframe.
        df = dtfconobas.SeriesToSeriesColProcessor.postprocess(
            srs_list, self._out_col_group
        )
        if self._join_output_with_input:
            df = dtfcorutil.merge_dataframes(df_in, df)
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


def _apply_func_to_data(
    data: Union[pd.Series, pd.DataFrame],
    func: Callable,
    func_kwargs: Dict[str, Any],
    drop_nans: bool = False,
    reindex_like_input: bool = True,
    exceptions: Tuple[Any] = (),
) -> Tuple[
    Optional[Union[pd.Series, pd.DataFrame]], Optional[collections.OrderedDict]
]:
    idx = data.index
    if drop_nans:
        data = data.dropna()
    info: Optional[collections.OrderedDict] = collections.OrderedDict()
    # Perform the column transformation operations.
    # Introspect to see whether `_transformer_func` contains an `info`
    # parameter. If so, inject an empty dict to be populated when
    # `_transformer_func` is executed.
    func_sig = inspect.signature(func)
    if "info" in func_sig.parameters:
        try:
            result = func(
                data,
                info=info,
                **func_kwargs,
            )
        except exceptions as e:
            _LOG.warning("Exception encountered: %s" % str(e))
            return (None, None)
    else:
        try:
            result = func(data, **func_kwargs)
        except exceptions as e:
            _LOG.warning("Exception encountered: %s" % str(e))
            return (None, None)
        info = None
    if reindex_like_input:
        result = result.reindex(idx)
    return result, info


# TODO(Paul): Consider deprecating.
def _apply_func_to_series(
    srs: pd.Series,
    nan_mode: str,
    func: Callable,
    func_kwargs: Dict[str, Any],
) -> Tuple[Union[pd.Series, pd.DataFrame], Optional[collections.OrderedDict]]:
    """
    Apply `func` to `srs` with `func_kwargs` after first applying `nan_mode`.

    This is mainly a wrapper for propagating `info` back when `func` supports
    the parameter.

    TODO(*): We should consider only having `nan_mode` as one of the
    `func_kwargs`, since now many functions support it directly.
    """
    drop_nans = False
    reindex_like_input = True
    if nan_mode == "leave_unchanged":
        pass
    elif nan_mode == "drop":
        drop_nans = True
    else:
        raise ValueError(f"Unrecognized `nan_mode` {nan_mode}")
    hdbg.dassert_isinstance(srs, pd.Series)
    result, info = _apply_func_to_data(
        srs, func, func_kwargs, drop_nans, reindex_like_input
    )
    return result, info


# #############################################################################
# Method and function wrappers.
# #############################################################################


class DataframeMethodRunner(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        method_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(nid)
        hdbg.dassert(method)
        # TODO(Paul): Ensure that this is a valid method.
        self._method = method
        self._method_kwargs = method_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df = getattr(df, self._method)(**self._method_kwargs)
        # Not all methods return DataFrames. We want to restrict to those that
        # do.
        hdbg.dassert_isinstance(df, pd.DataFrame)
        #
        info = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


class FunctionWrapper(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        func: Callable,
        func_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(nid)
        self._func = func
        self._func_kwargs = func_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df_out = self._func(df, **self._func_kwargs)
        hdbg.dassert_isinstance(df_out, pd.DataFrame)
        # Update `info`.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df_out)
        return df_out, info


# #############################################################################
# Resamplers (deprecated)
# #############################################################################


# TODO(Paul): Deprecate.
class Resample(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        agg_func: str,
        resample_kwargs: Optional[Dict[str, Any]] = None,
        agg_func_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        :param nid: node identifier
        :param rule: resampling frequency
        :param agg_func: a function that is applied to the resampler
        :param resample_kwargs: kwargs for `resample`. Should not include
            `rule` since we handle this separately.
        :param agg_func_kwargs: kwargs for agg_func
        """
        super().__init__(nid)
        self._rule = rule
        self._agg_func = agg_func
        self._resample_kwargs = resample_kwargs or {}
        self._agg_func_kwargs = agg_func_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        resampler = cofinanc.resample(
            df, rule=self._rule, **self._resample_kwargs
        )
        func = getattr(resampler, self._agg_func)
        df = func(**self._agg_func_kwargs)
        # Update `info`.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


# TODO(Paul): Deprecate.
class TwapVwapComputer(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        rule: _ResamplingRule,
        price_col: dtfcorutil.NodeColumn,
        volume_col: dtfcorutil.NodeColumn,
        offset: Optional[str] = None,
    ) -> None:
        """
        Calculate TWAP and VWAP prices from price and volume columns.

        This function wraps `compute_twap_vwap()`. Params as in that
        function.

        :param nid: node identifier
        """
        super().__init__(nid)
        self._rule = rule
        self._price_col = price_col
        self._volume_col = volume_col
        self._offset = offset

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df = cofinanc.compute_twap_vwap(
            df,
            self._rule,
            price_col=self._price_col,
            volume_col=self._volume_col,
            offset=self._offset,
        )
        #
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


# TODO(Paul): Deprecate.
class MultiindexTwapVwapComputer(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        rule: _ResamplingRule,
        price_col_group: Tuple[dtfcorutil.NodeColumn],
        volume_col_group: Tuple[dtfcorutil.NodeColumn],
        out_col_group: Tuple[dtfcorutil.NodeColumn],
    ) -> None:
        """
        Calculate TWAP and VWAP prices from price and volume columns.

        This function wraps `compute_twap_vwap()`. Params as in that
        function.
        """
        super().__init__(nid)
        self._rule = rule
        self._price_col_group = price_col_group
        self._volume_col_group = volume_col_group
        self._price_col_name = price_col_group[-1]
        self._volume_col_name = volume_col_group[-1]
        self._out_col_group = out_col_group

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        price_df = dtfconobas.preprocess_multiindex_cols(
            df, self._price_col_group
        )
        volume_df = dtfconobas.preprocess_multiindex_cols(
            df, self._volume_col_group
        )
        hdbg.dassert_eq_all(price_df.columns, volume_df.columns)
        dfs = {}
        for col in price_df.columns:
            price_col = price_df[col]
            price_col.name = self._price_col_name
            volume_col = volume_df[col]
            volume_col.name = self._volume_col_name
            df = pd.concat([price_col, volume_col], axis=1)
            df = cofinanc.compute_twap_vwap(
                df,
                self._rule,
                price_col=self._price_col_name,
                volume_col=self._volume_col_name,
            )
            dfs[col] = df
        # Insert symbols as a column level.
        df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        # Swap column levels so that symbols are leaves.
        df = df.swaplevel(i=0, j=1, axis=1)
        df.sort_index(axis=1, level=0, inplace=True)
        if self._out_col_group:
            df = pd.concat([df], axis=1, keys=[self._out_col_group])
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df)
        return df, info


# #############################################################################
# Column Arithmetic
# #############################################################################


class Calculator(dtfconobas.Transformer):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        term1: dtfcorutil.NodeColumn,
        term2: dtfcorutil.NodeColumn,
        out_col_name: dtfcorutil.NodeColumn,
        operation: str,
        arithmetic_kwargs: Optional[Dict[str, Any]] = None,
        term1_delay: Optional[int] = 0,
        term2_delay: Optional[int] = 0,
        nan_mode: Optional[str] = None,
    ) -> None:
        super().__init__(nid)
        self._term1 = term1
        self._term2 = term2
        self._out_col_name = out_col_name
        hdbg.dassert_in(
            operation,
            ["multiply", "divide", "add", "subtract"],
            "Operation %s not supported.",
        )
        self._operation = operation
        self._arithmetic_kwargs = arithmetic_kwargs or {}
        self._term1_delay = term1_delay
        self._term2_delay = term2_delay
        self._nan_mode = nan_mode or "leave_unchanged"

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        hdbg.dassert_in(self._term1, df.columns.to_list())
        hdbg.dassert_in(self._term2, df.columns.to_list())
        hdbg.dassert_not_in(self._out_col_name, df.columns.to_list())
        df_out = df.copy()
        terms = df_out[[self._term1, self._term2]]
        if self._nan_mode == "leave_unchanged":
            pass
        elif self._nan_mode == "drop":
            terms = terms.dropna()
        else:
            raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
        term1 = terms[self._term1].shift(self._term1_delay)
        term2 = terms[self._term2].shift(self._term2_delay)
        result = getattr(term1, self._operation)(term2, **self._arithmetic_kwargs)
        result = result.reindex(index=df.index)
        df_out[self._out_col_name] = result
        # Update `info`.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = dtfcorutil.get_df_info_as_string(df_out)
        return df_out, info
