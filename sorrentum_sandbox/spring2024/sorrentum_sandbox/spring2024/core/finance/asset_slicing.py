"""
Import as:

import core.finance.asset_slicing as cfiassli
"""

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def get_asset_slice(
    df: pd.DataFrame, asset_id: int, *, strictly_increasing: bool = True
) -> pd.DataFrame:
    """
    Extract all columns related to `asset_id`.
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=strictly_increasing
    )
    hdbg.dassert_eq(2, df.columns.nlevels)
    hdbg.dassert_in(asset_id, df.columns.levels[1])
    slice_ = df.T.xs(asset_id, level=1).T
    return slice_
