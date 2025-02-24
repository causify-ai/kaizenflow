"""
Import as:

import core.statistics.cross_validation as cstcrval
"""

import collections
import datetime
import functools
import logging
import math
from typing import Any, Iterable, List, Tuple, Union

import pandas as pd
import sklearn.model_selection

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)

# #############################################################################
# Cross-validation
# #############################################################################


def get_rolling_splits(
    idx: pd.Index, n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Partition index into chunks and returns pairs of successive chunks.

    If the index looks like
        [0, 1, 2, 3, 4, 5, 6]
    and n_splits = 4, then the splits would be
        [([0, 1], [2, 3]),
         ([2, 3], [4, 5]),
         ([4, 5], [6])]

    A typical use case is where the index is a monotonic increasing datetime
    index. For such cases, causality is respected by the splits.
    """
    hpandas.dassert_strictly_increasing_index(idx)
    n_chunks = n_splits + 1
    hdbg.dassert_lte(1, n_splits)
    # Split into equal chunks.
    chunk_size = int(math.ceil(idx.size / n_chunks))
    hdbg.dassert_lte(1, chunk_size)
    chunks = [idx[i : i + chunk_size] for i in range(0, idx.size, chunk_size)]
    hdbg.dassert_eq(len(chunks), n_chunks)
    #
    splits = list(zip(chunks[:-1], chunks[1:]))
    return splits


def get_oos_start_split(
    idx: pd.Index, datetime_: Union[datetime.datetime, pd.Timestamp]
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index using OOS (out-of-sample) start datetime.
    """
    hpandas.dassert_strictly_increasing_index(idx)
    ins_mask = idx < datetime_
    hdbg.dassert_lte(1, ins_mask.sum())
    oos_mask = ~ins_mask
    hdbg.dassert_lte(1, oos_mask.sum())
    ins = idx[ins_mask]
    oos = idx[oos_mask]
    return [(ins, oos)]


# TODO(Paul): Support train/test/validation or more.
def get_train_test_pct_split(
    idx: pd.Index, train_pct: float
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index into train and test sets by percentage.
    """
    hpandas.dassert_strictly_increasing_index(idx)
    hdbg.dassert_lt(0.0, train_pct)
    hdbg.dassert_lt(train_pct, 1.0)
    #
    train_size = int(train_pct * idx.size)
    hdbg.dassert_lte(0, train_size)
    train_split = idx[:train_size]
    test_split = idx[train_size:]
    return [(train_split, test_split)]


def get_expanding_window_splits(
    idx: pd.Index, n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Generate splits with expanding overlapping windows.
    """
    hpandas.dassert_strictly_increasing_index(idx)
    hdbg.dassert_lte(1, n_splits)
    tscv = sklearn.model_selection.TimeSeriesSplit(n_splits=n_splits)
    locs = list(tscv.split(idx))
    splits = [(idx[loc[0]], idx[loc[1]]) for loc in locs]
    return splits


def truncate_index(idx: pd.Index, min_idx: Any, max_idx: Any) -> pd.Index:
    """
    Return subset of idx with values >= min_idx and < max_idx.
    """
    hpandas.dassert_strictly_increasing_index(idx)
    # TODO(*): PTask667: Consider using bisection to avoid linear scans.
    min_mask = idx >= min_idx
    max_mask = idx < max_idx
    mask = min_mask & max_mask
    hdbg.dassert_lte(1, mask.sum())
    return idx[mask]


def combine_indices(idxs: Iterable[pd.Index]) -> pd.Index:
    """
    Combine multiple indices into a single index for cross-validation splits.

    This is computed as the union of all the indices within the largest common
    interval.

    TODO(Paul): Consider supporting multiple behaviors with `mode`.
    """
    for idx in idxs:
        hpandas.dassert_strictly_increasing_index(idx)
    # Find the maximum start/end datetime overlap of all source indices.
    max_min = max([idx.min() for idx in idxs])
    _LOG.debug("Latest start datetime of indices=%s", max_min)
    min_max = min([idx.max() for idx in idxs])
    _LOG.debug("Earliest end datetime of indices=%s", min_max)
    truncated_idxs = [truncate_index(idx, max_min, min_max) for idx in idxs]
    # Take the union of truncated indices. Though all indices fall within the
    # datetime range [max_min, min_max), they do not necessarily have the same
    # resolution or all values.
    composite_idx = functools.reduce(lambda x, y: x.union(y), truncated_idxs)
    return composite_idx


def convert_splits_to_string(splits: collections.OrderedDict) -> str:
    txt = "n_splits=%s\n" % len(splits)
    for train_idxs, test_idxs in splits:
        txt += "train=%s [%s, %s]" % (
            len(train_idxs),
            min(train_idxs),
            max(train_idxs),
        )
        txt += "\n"
        txt += "test=%s [%s, %s]" % (
            len(test_idxs),
            min(test_idxs),
            max(test_idxs),
        )
        txt += "\n"
    return txt


def get_train_test_splits(
    idx: pd.Index,
    mode: str,
    *args: Any
    # TODO(Grisha): should we do `pd.DatetimeIndex`?
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split a timestamp index into multiple train and test sets according to
    various criteria.

    The output is a list of pairs (train, test) splits that has at least
    one split possible.

    E.g.,
    If an index looks like `[2022-08-31 20:00:00, ..., 2022-10-30 20:00:00]`,
    and mode = "rolling", n_splits = 2 the output is:
    ```
    [
        # Split 1.
        (
            # Train set.
            [2022-08-31 20:00:00, ..., 2022-09-20 20:00:00],
            # Test set.
            [2022-09-20 20:05:00, ..., 2022-10-10 20:05:00]
        ),
        # Split 2.
        (
            # Train set.
            [2022-09-20 20:05:00, ..., 2022-10-10 20:05:00],
            # Test set.
            [2022-10-10 20:10:00, ..., 2022-10-30 20:00:00]
        )
    ]
    ```

    :param idx: index to partition
    :param mode: a mode that defines how to split the index
        - "ins": in-sample, i.e. train set = test set
        - "oos": see `get_oos_start_split()`
        - "rolling": see `get_rolling_splits()`
    :return: train/test splits
    """
    hpandas.dassert_strictly_increasing_index(idx)
    hdbg.dassert_isinstance(mode, str)
    _LOG.debug(hprint.to_str("mode args"))
    if mode == "ins":
        splits = [(idx, idx)]
    elif mode == "oos":
        splits = get_oos_start_split(idx, *args)
    elif mode == "rolling":
        splits = get_rolling_splits(idx, *args)
    else:
        raise ValueError(f"Invalid mode={mode}")
    return splits
