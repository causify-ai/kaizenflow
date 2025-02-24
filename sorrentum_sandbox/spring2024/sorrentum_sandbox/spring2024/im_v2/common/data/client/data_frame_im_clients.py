"""
Import as:

import im_v2.common.data.client.data_frame_im_clients as imvcdcdfimc
"""

from typing import Any, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import im_v2.common.data.client.abstract_im_clients as imvcdcaimcl
import im_v2.common.universe as ivcu


class DataFrameImClient(imvcdcaimcl.ImClientReadingMultipleSymbols):
    """
    `ImClient` that serves data from a passed dataframe indexed with
    timestamps.

    This is used to feed synthetic data to the `ImClient` interface.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        universe: List[ivcu.FullSymbol],
        *,
        full_symbol_col_name: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        Example of an input dataframe:

        ```
                                        full_symbol ... close  volume  feature1
        timestamp
        2021-07-26 13:42:00+00:00  binance:BTC_USDT     101.0     100       1.0
        2021-07-26 13:43:00+00:00  binance:BTC_USDT     101.0     100       1.0
        2021-07-26 13:44:00+00:00  binance:BTC_USDT     101.0     100       1.0
        ```
        """
        # Validate that the input universe is a non-empty list.
        hdbg.dassert_container_type(universe, list, ivcu.FullSymbol)
        hdbg.dassert_lte(1, len(universe))
        # Set the input universe before calling the parent class ctor since
        # it is used by `get_universe()` which is necessary for the parent
        # class initialisation.
        self._universe = sorted(universe)
        # Initialise the parent class.
        vendor = "data_frame"
        # For this specific client we pass the universe to the ctor, so
        # the version is not needed, i.e. could be any. Passing here just
        # to make the parent class happy.
        universe_version = None
        super().__init__(
            vendor,
            universe_version,
            full_symbol_col_name=full_symbol_col_name,
            resample_1min=resample_1min,
        )
        self._df = df

    @staticmethod
    def get_metadata() -> pd.DataFrame:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_universe(self) -> List[ivcu.FullSymbol]:
        """
        See description in the parent class.
        """
        return self._universe

    # ///////////////////////////////////////////////////////////////////////////
    # Private interface.
    # ///////////////////////////////////////////////////////////////////////////

    # TODO(Dan): Implement usage of `columns` parameter.
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
        See the parent class for description.
        """
        # Filter by full symbols.
        full_symbols_mask = self._df[full_symbol_col_name].isin(full_symbols)
        data = self._df[full_symbols_mask]
        # Filter data by specified timestamps.
        hpandas.dassert_index_is_datetime(data)
        if start_ts:
            data = data.loc[data.index >= start_ts]
        if end_ts:
            data = data.loc[data.index <= end_ts]
        return data
