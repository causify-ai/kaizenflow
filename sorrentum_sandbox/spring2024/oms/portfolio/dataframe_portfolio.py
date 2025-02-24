"""
Import as:

import oms.portfolio.dataframe_portfolio as opdapor
"""

import collections
import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import oms.portfolio.portfolio as oporport

_LOG = logging.getLogger(__name__)


# #############################################################################
# DataFramePortfolio
# #############################################################################


class DataFramePortfolio(oporport.Portfolio):
    """
    An implementation of `oporport.Portfolio` using a DataFrame to store the
    information.
    """

    # A `fills_df` represents orders that have been executed (e.g., how many shares,
    # at how much).

    # Columns required in a `fills_df`.
    FILLS_COLS = [
        "asset_id",
        "timestamp",
        "num_shares",
        "price",
    ]

    @staticmethod
    def _validate_fills_df(fills_df: pd.DataFrame) -> None:
        """
        Ensure that `fills_df` passes basic sanity checks.
        """
        # The input should be a nonempty dataframe.
        hdbg.dassert_isinstance(fills_df, pd.DataFrame)
        hdbg.dassert(not fills_df.empty, "The dataframe must be nonempty.")
        # The dataframe must have the correct columns.
        hdbg.dassert_is_subset(
            DataFramePortfolio.FILLS_COLS,
            fills_df.columns.to_list(),
            "Columns do not conform to requirements.",
        )
        # The columns should be of the correct types.
        hdbg.dassert_eq(
            fills_df["asset_id"].dtype.type,
            np.int64,
            "The column `asset_id` should only contain integer ids.",
        )
        hdbg.dassert_eq(
            fills_df["num_shares"].dtype.type,
            np.float64,
            "The column `curr_num_shares` should be a float column.",
        )
        #
        hdbg.dassert_eq(fills_df["timestamp"].dtype.type, pd.Timestamp)
        hdbg.dassert(hasattr(fills_df["timestamp"].dtype, "tz"))
        # The dataframe must not contain a row for cash.
        hdbg.dassert_not_in(
            DataFramePortfolio.CASH_ID,
            fills_df["asset_id"].to_list(),
            "Order for cash detected.",
        )
        # There should be no more than one row per asset.
        hdbg.dassert_no_duplicates(fills_df["asset_id"].to_list())
        # All share values should be finite.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("fills_df=%s", fills_df)
        hdbg.dassert(
            np.isfinite(fills_df["num_shares"]).all(),
            "All share values must be finite.",
        )

    def _observe_holdings_shares(self) -> None:
        """
        Update holdings_shares at the current wall clock time using fills
        information.
        """
        # Get fills.
        fills_df = self._get_fills()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "fills_df=\n%s",
                hpandas.df_to_str(fills_df, print_shape_info=True),
            )
        # Get latest holdings_shares
        (
            prev_asset_holdings_ts,
            prev_holdings_shares,
        ) = self._holdings_shares.peek()
        prev_cash_holdings_ts, prev_cash = self._cash.peek()
        wall_clock_timestamp = self._get_wall_clock_time()
        hdbg.dassert_lt(prev_cash_holdings_ts, wall_clock_timestamp)
        new_cash = prev_cash
        # Update holdings_shares using the `fills_df`.
        new_holdings_shares = prev_holdings_shares.copy()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "new_holdings_shares=\n%s",
                hpandas.df_to_str(new_holdings_shares, print_shape_info=True),
            )
        executed_trades_notional = pd.Series([], dtype="float64")
        if fills_df is not None:
            DataFramePortfolio._validate_fills_df(fills_df)
            # last_timestamp <= fills_df.index <= timestamp
            hdbg.dassert_lte(prev_asset_holdings_ts, fills_df["timestamp"].min())
            hdbg.dassert_lte(fills_df["timestamp"].max(), wall_clock_timestamp)
            executed_trades_shares = fills_df.set_index("asset_id")["num_shares"]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "executed_trades_shares=\n%s",
                    hpandas.df_to_str(
                        executed_trades_shares, print_shape_info=True
                    ),
                )
            trades_price_per_share = fills_df.set_index("asset_id")["price"]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "trades_price_per_share=\n%s",
                    hpandas.df_to_str(
                        trades_price_per_share, print_shape_info=True
                    ),
                )
            executed_trades_notional = (
                executed_trades_shares * trades_price_per_share
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "executed_trades_notional=\n%s",
                    hpandas.df_to_str(
                        executed_trades_notional, print_shape_info=True
                    ),
                )
            cash_diff = -executed_trades_notional.sum()
            hdbg.dassert(np.isfinite(cash_diff))
            new_holdings_shares = new_holdings_shares.add(
                executed_trades_shares, fill_value=0
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "new_holdings_shares=\n%s",
                    hpandas.df_to_str(new_holdings_shares, print_shape_info=True),
                )
            new_cash += cash_diff
        hdbg.dassert(not new_holdings_shares.index.has_duplicates)
        self._holdings_shares[wall_clock_timestamp] = new_holdings_shares
        # Executed trades notional are computed from fills and if there are no trades
        # for an asset, executed trades notional will not be computed for this asset.
        # Keep all the assets by imputing zeros for those with no trades.
        executed_trades_notional = executed_trades_notional.reindex(
            index=prev_holdings_shares.index, fill_value=0
        )
        hdbg.dassert(not executed_trades_notional.index.has_duplicates)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "executed_trades_notional=\n%s",
                hpandas.df_to_str(
                    executed_trades_notional, print_shape_info=True
                ),
            )
        self._executed_trades_notional[
            wall_clock_timestamp
        ] = executed_trades_notional
        self._cash[wall_clock_timestamp] = new_cash

    def _initialize_holdings_from_db(self) -> pd.Series:
        # For now we don't assume that `DataFramePortfolio` is saved on permanent
        # storage, since it is typically used for simulations.
        # TODO(Paul, GP): Consider allowing saving and retrieval of
        #  `DataFramePortfolio`.
        _ = self
        raise NotImplementedError

    def _get_fills(self) -> pd.DataFrame:
        """
        Get the fills from the broker and convert it into a `fills_df`.

        :return: fills_df
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("")
        # Get the fills from the broker.
        fills = self.broker.get_fills()
        # Convert the fills into a `fills_df`.
        fill_rows = []
        for fill in fills:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("# Processing fill=%s", fill)
            # Copy contents of the fill.
            fill_row: Dict[str, Any] = collections.OrderedDict()
            fill_row.update(fill.to_dict())
            #
            fill_rows.append(pd.Series(fill_row))
        #
        if fill_rows:
            # Infer type and timezone from the first fill since they are the
            # same across fills.
            timestamp_type = pd.Series([fill_rows[0]["timestamp"]]).dtype
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(hprint.to_str("timestamp_type"))
            fills_df = pd.concat(fill_rows, axis=1).transpose()
            # Coerce numerical data types.
            # - asset_id coercion to int64 may fail if there are NaNs (there
            #     should not be any NaNs)
            # - in general, num_shares and price should be floats, but without
            #   being this specific, they may get coerced to ints in certain
            #   edge cases
            # - when transposing a df a timestamp type is lost (i.e. the type
            #    becomes `object`), refer to
            #   `https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.transpose.html`.
            fills_df = fills_df.astype(
                {
                    "asset_id": "int64",
                    "num_shares": "float64",
                    "price": "float64",
                    "timestamp": timestamp_type,
                }
            )
        else:
            fills_df = None
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "fills_df=\n%s",
                hpandas.df_to_str(fills_df, num_rows=None, precision=2),
            )
        return fills_df
