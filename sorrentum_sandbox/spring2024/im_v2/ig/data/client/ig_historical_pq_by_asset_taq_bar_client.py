"""
Import as:

import im_v2.ig.data.client.ig_historical_pq_by_asset_taq_bar_client as imvidcihpbatbc
"""

import logging
from typing import Any, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import im_v2.common.data.client as imvcdcli
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


class IgHistoricalPqByTileTaqBarClient(imvcdcli.HistoricalPqByTileClient):
    """
    Provide historical TAQ bar data stored as Parquet by-asset.

    The original Parquet by-date data is transformed in Parquet by-asset
    through the script `im_lime/ig/ig_transform_pq_by_date_to_by_asset.py`.
    """

    # TODO(gp): Factor out with our approach of *args and **kwargs.
    def __init__(
        self,
        vendor: str,
        root_dir_name: str,
        aws_profile: Optional[str],
        partition_mode: str,
        # TODO(gp): Pass this.
        full_symbol_col_name: str = "igid",
    ):
        # TODO(gp): Not sure how to set this.
        universe_version = None
        infer_exchange_id = False
        super().__init__(
            vendor,
            universe_version,
            root_dir_name,
            partition_mode,
            infer_exchange_id=infer_exchange_id,
            aws_profile=aws_profile,
            full_symbol_col_name=full_symbol_col_name,
        )

    # For IG `asset_id` and `full_symbol` have the same values but with different
    # types (int vs str).
    @staticmethod
    def get_asset_ids_from_full_symbols(
        full_symbols: List[ivcu.FullSymbol],
    ) -> List[int]:
        numeric_asset_id = list(map(int, full_symbols))
        return numeric_asset_id

    def get_universe(self) -> List[ivcu.FullSymbol]:
        # We don't need the mapping `asset_id -> full_symbol` since the IG
        # universe is already in the form of `asset_ids`, so we return an empty
        # universe here and override the functions doing the `asset_id <->
        # full_symbol` conversion.
        return []

    def get_metadata(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_full_symbols_from_asset_ids(
        self, asset_ids: List[int]
    ) -> List[ivcu.FullSymbol]:
        _ = self
        full_symbols = list(map(str, asset_ids))
        return full_symbols

    # /////////////////////////////////////////////////////////////////////////////

    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        full_symbol_col_name: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Same as abstract method.
        """
        df = super()._read_data_for_multiple_symbols(
            full_symbols, start_ts, end_ts, columns, full_symbol_col_name
        )
        _LOG.debug("before df=\n%s", hpandas.df_to_str(df, print_dtypes=True))
        # IG historical data doesn't have a knowledge time so we use the end of the
        # interval as a proxy for it, which for now it's the index.
        hdbg.dassert_not_in("timestamp_db", df.columns)
        # TODO(gp): we are considering keeping end_time as a column instead of an
        #  index.
        # df["timestamp_db"] = df["end_time"]
        df["timestamp_db"] = df.index
        df[full_symbol_col_name] = df[full_symbol_col_name].astype(str)
        _LOG.debug("after df=\n%s", hpandas.df_to_str(df, print_dtypes=True))
        return df
