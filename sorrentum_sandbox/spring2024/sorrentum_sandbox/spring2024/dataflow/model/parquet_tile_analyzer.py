"""
Import as:

import dataflow.model.parquet_tile_analyzer as dtfmpatian
"""

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hparquet as hparque

_LOG = logging.getLogger(__name__)


class ParquetTileAnalyzer:
    """
    A tool for analyzing parquet file metadata.
    """

    @staticmethod
    def collate_parquet_tile_metadata(
        path: str,
    ) -> pd.DataFrame:
        return hparque.collate_parquet_tile_metadata(path)

    @staticmethod
    def compute_metadata_stats_by_asset_id(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        srs = df["file_size_in_bytes"]
        hdbg.dassert_isinstance(srs, pd.Series)
        n_years = srs.groupby(level=[0, 1]).count().groupby(level=0).count()
        n_unique_months = (
            srs.groupby(level=[0, 2]).count().groupby(level=0).count()
        )
        n_files = srs.groupby(level=0).count()
        size_in_bytes = srs.groupby(level=0).sum()
        size = size_in_bytes.apply(hintros.format_size)
        stats_df = pd.DataFrame(
            {
                "n_years": n_years,
                "n_unique_months": n_unique_months,
                "n_files": n_files,
                "size": size,
            }
        )
        return stats_df

    @staticmethod
    def compute_universe_size_by_time(
        df: pd.DataFrame,
    ):
        srs = df["file_size_in_bytes"]
        hdbg.dassert_isinstance(srs, pd.Series)
        n_asset_ids = srs.groupby(level=[1, 2]).count()
        size_in_bytes = srs.groupby(level=[1, 2]).sum()
        size = size_in_bytes.apply(hintros.format_size)
        stats_df = pd.DataFrame(
            {
                "n_asset_ids": n_asset_ids,
                "size": size,
            }
        )
        return stats_df
