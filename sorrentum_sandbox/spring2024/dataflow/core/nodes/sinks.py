"""
Import as:

import dataflow.core.nodes.sinks as dtfconosin
"""

import collections
import itertools
import logging
import os
from typing import Dict, Iterable, Tuple

import pandas as pd

import core.finance as cofinanc
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import dataflow.core.utils as dtfcorutil
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hparquet as hparque

_LOG = logging.getLogger(__name__)


# TODO(gp): Add incremental mode to clean up the dir before writing into it.
class WriteDf(dtfconobas.FitPredictNode):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        dir_name: str,
    ) -> None:
        """
        Write fit / predict dataframes into `dir_name` as Parquet files.
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(dir_name, str)
        self._dir_name = dir_name

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._write_df(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._write_df(df_in, fit=False)

    def _write_df(
        self, df: pd.DataFrame, fit: bool = True
    ) -> Dict[str, pd.DataFrame]:
        if self._dir_name:
            hdbg.dassert_lt(1, df.index.size)
            # Create the directory if it does not already exist.
            hio.create_dir(self._dir_name, incremental=True)
            # Get the latest `df` index value.
            if isinstance(df.index, pd.DatetimeIndex):
                # NOTE: If needed, we can pass in only the last two elements.
                epochs = cofinanc.compute_epoch(df)
                epoch = epochs.iloc[-1].values[0]
            else:
                raise NotImplementedError
            file_name = f"{epoch}.parquet"
            file_name = os.path.join(self._dir_name, file_name)
            hdbg.dassert_path_not_exists(file_name)
            # Write the file.
            # TODO(Paul): Maybe allow the node to configure the log level.
            hparque.to_parquet(df, file_name, log_level=logging.DEBUG)
        # Collect info.
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df)
        mode = "fit" if fit else "predict"
        self._set_info(mode, info)
        # Pass the dataframe through.
        return {"df_out": df}


class WriteCols(dtfconobas.FitPredictNode):
    def __init__(
        self,
        nid: dtfcornode.NodeId,
        dir_name: str,
        col_mapping: Dict[str, str],
    ) -> None:
        super().__init__(nid)
        hdbg.dassert_isinstance(dir_name, str)
        self._dir_name = dir_name
        hdbg.dassert_isinstance(col_mapping, dict)
        hdbg.dassert_eq(
            len(col_mapping),
            len(set(col_mapping.values())),
            "Target names not unique!",
        )
        if col_mapping:
            hdbg.dassert(dir_name, "Received a `col_mapping` but no `dir_name`.")
        if dir_name:
            hdbg.dassert(
                col_mapping, "Received a `dir_name` but no `col_mapping`."
            )
        self._col_mapping = col_mapping

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._write_cols(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._write_cols(df_in, fit=False)

    def _write_cols(
        self, df: pd.DataFrame, fit: bool = True
    ) -> Dict[str, pd.DataFrame]:
        for key in self._col_mapping.keys():
            hdbg.dassert_in(key, df.columns)
        # TODO(Paul): Factor out the shared code.
        if self._dir_name and self._col_mapping:
            hdbg.dassert_lt(1, df.index.size)
            # Create the directory if it does not already exist.
            hio.create_dir(self._dir_name, incremental=True)
            # Get the latest `df` index value.
            if isinstance(df.index, pd.DatetimeIndex):
                # NOTE: If needed, we can pass in only the last two elements.
                epochs = cofinanc.compute_epoch(df)
                epoch = epochs.iloc[-1].values[0]
            else:
                raise NotImplementedError
            for k, v in self._col_mapping.items():
                srs = df.iloc[-1][k]
                hdbg.dassert_isinstance(srs, pd.Series)
                srs.name = str(epoch) + "_" + v
                file_name = os.path.join(self._dir_name, srs.name + ".csv")
                hdbg.dassert_path_not_exists(file_name)
                # Write file.
                srs.to_csv(file_name)
        # Collect info.
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcorutil.get_df_info_as_string(df)
        mode = "fit" if fit else "predict"
        self._set_info(mode, info)
        # Pass the dataframe through.
        return {"df_out": df}


# TODO(gp): -> hparquet.py or split into a generator and a reading part.
def read_dfs(dir_name: str) -> Iterable[Tuple[str, pd.DataFrame]]:
    """
    Yield `(file_name, df)` from `dir_name`.

    :param dir_name: directory containing dataframes in Parquet format
    :return: iterable of tuples of the form `(file_name, df)`
    """
    # Glob the `.pq` files.
    pattern = "*.pq"
    only_files = True
    use_relative_paths = False
    file_names = sorted(
        hio.listdir(dir_name, pattern, only_files, use_relative_paths)
    )
    _LOG.info("Number of Parquet files found=%s", len(file_names))
    for file_name in file_names:
        # Load the dataframe.
        df = hparque.from_parquet(file_name)
        # Extract the file_name without the base or extension.
        tail = os.path.split(file_name)[1]
        key = os.path.splitext(tail)[0]
        #
        yield key, df


# TODO(gp): -> hpandas.py?
def consolidate_dfs(df_iter: Iterable[Tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    """
    Consolidate dataframes in `df_iter` into a single dataframe.

    - The dataframes in the iterable are expected to agree on any overlap
    - A use case is to consolidate dataframes generated incrementally through
      a real-time process

    :param df_iter: iterable of the form (key, dataframe)
    :return: a dataframe consolidated along the index
    """
    # Tee the iterator to process successive dataframes together.
    iter1, iter2 = itertools.tee(df_iter)
    next(iter2)
    df_out = None
    for k2, df2 in iter2:
        k1, df1 = next(iter1)
        _LOG.info("Processing keys `%s` and `%s`", k1, k2)
        # It is expected that `df2` will have at least one index value not in
        # `df1`.
        new_idx_vals = df2.index.difference(df1.index)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "Number of index values in `%s` not in `%s` is=%s",
                k2,
                k1,
                len(new_idx_vals),
            )
        dropped_idx_vals = df1.index.difference(df2.index)
        if len(dropped_idx_vals) > 0:
            _LOG.warning(
                "%s index values are in `%s` but not in `%s`",
                len(dropped_idx_vals),
                k1,
                k2,
            )
        # Compare the dataframes on the intersection of their indices.
        shared_idx = df1.index.intersection(df2.index)
        df_diff = df1.loc[shared_idx].compare(df2.loc[shared_idx])
        if df_diff.size > 0:
            _LOG.warning(
                "Dataframes `%s` and `%s` differ on overlap at %s index value(s)",
                k2,
                k1,
                len(df_diff.index),
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Index value(s) where dataframes differ=`%s`",
                    str(df_diff.index),
                )
        # Generate a combined dataframe. In the event that the dataframes
        # disagree, on an overlap, we use the latest dataframe as the
        # reference.
        if df_out is None:
            df_out = df2.combine_first(df1)
        else:
            df_out = df2.combine_first(df_out)
    hpandas.dassert_strictly_increasing_index(df_out)
    return df_out
