"""
Import as:

import oms.portfolio.database_portfolio as opodapor
"""

import collections
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

import core.key_sorted_ordered_dict as cksoordi
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import helpers.hwall_clock_time as hwacltim
import oms.portfolio.portfolio as oporport

_LOG = logging.getLogger(__name__)


# #############################################################################
# DatabasePortfolio
# #############################################################################


class DatabasePortfolio(oporport.Portfolio):
    """
    An implementation of `oporport.Portfolio` using a DB to store the state of
    the holdings_shares.

    A `snapshot_df` contains the image of the current holdings_shares (excluding cash)
    in the account and it is maintained by an external DB, e.g.,

    ```
     tradedate           published_dt   curr_pos
               asset_id         target_pos       net_cost
    2021-12-09    10005  ... 11:54:28  0.0     0      ...
    2021-12-09    10006  ... 11:54:28  0.0     0      ...
    2021-12-09    10009  ... 00:00:00  0.0     0      ...
    ```
    """

    def __init__(
        self,
        *args: Any,
        table_name: str,
        poll_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        """
        Constructor.

        :param table_name: current positions table name
        :param poll_kwargs: polling instruction when waiting for stable
            current positions
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("table_name poll_kwargs"))
        super().__init__(*args, **kwargs)
        #
        self._db_connection = self.broker._db_connection
        self._table_name = table_name
        if poll_kwargs is None:
            poll_kwargs = hasynci.get_poll_kwargs(self._get_wall_clock_time)
        self._poll_kwargs = poll_kwargs
        # wall clock timestamp -> snapshot_df (i.e., the image of the holdings_shares in
        # the account, without cash).
        self._timestamp_to_snapshot_df = collections.OrderedDict()
        # wall clock timestamp -> total net cost of transactions since the BOD.
        self._net_cost = cksoordi.KeySortedOrderedDict(pd.Timestamp)
        if self._retrieve_initial_holdings_shares_from_db:
            self._initial_holdings = self._initialize_holdings_from_db(
                self._initial_holdings
            )
            self._validate_initial_holdings(self._initial_holdings)
        #
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("After initialization:\n%s", repr(self))

    def log_state(self, log_dir: str, *, num_periods: Optional[int] = 1) -> str:
        super().log_state(log_dir, num_periods=num_periods)
        hdbg.dassert(log_dir, "Must specify `log_dir` to log state.")
        #
        bar_timestamp = hwacltim.get_current_bar_timestamp(as_str=True)
        #
        wall_clock_time = self._get_wall_clock_time()
        wall_clock_time_str = wall_clock_time.strftime("%Y%m%d_%H%M%S")
        # TODO(Grisha): Assign to a variable, probably file_name and enable
        # logging.
        f"{bar_timestamp}.{wall_clock_time_str}.csv"
        #
        # snapshot_df = self.get_historical_snapshot_dfs(num_periods)
        # Portfolio._write_df(snapshot_df, log_dir, "snapshot_df", file_name)

    # //////////////////////////////////////////////////////////////////////////

    def _get_snapshot_df(self, restrict_to_universe: bool) -> pd.DataFrame:
        """
        Return a snapshot df like:
        ```
         tradedate asset_id        published_dt  target_position  current_position ...
        2021-12-09    10005 2021-12-09 11:54:28  0.0              0
        2021-12-09    10006 2021-12-09 11:54:28  0.0              0
        2021-12-09    10009 1970-01-01 00:00:00  0.0              0
        ```
        """
        # The current positions table has the following fields:
        # - tradedate (e.g., 2021-10-28)
        # - id (e.g., 10005)
        # - strategyid (e.g., SAU1)
        # - account (e.g., SAU1_CAND)
        # - published_dt (e.g., 2021-10-28 12:01:49.41)
        # - target_position (e.g., 300)
        #   = the fully realized portfolio position
        #   - E.g., the value is 300 if we own 100 AAPL and we want get 200 more so
        #     we send an order for 200
        # - current_position (e.g., 100)
        #   = what we own (e.g., 100 AAPL)
        # - open_quantity (e.g., 200)
        #   = how many shares we have orders open in the market. In other words,
        #     open quantity reflects how much is out getting executed in the market
        #   - Note that it's not always
        #     `open_quantity = target_position - current_position`
        #     since orders might have been cancelled. If `open_quantity = 0` it
        #     means that there are no order in the market
        #   - E.g., if we send orders for 200 AAPL, then current_position = 200, but
        #     if we cancel the orders, current_position = 0, even if target_position
        #     reports what we were targeting 200 shares
        # - net_cost (e.g., 0.0)
        #   = fill-quantity * signed fill_price with respect to the BOD price
        #   - In practice it is the average price paid
        # - currency (e.g., USD)
        # - fx (e.g., 1.0)
        # - action (e.g., BOD)
        #   - TODO(gp): Find out what it means and if interesting
        # - bod_position (e.g., 0)
        #   - = number of shares at BOD
        # - bod_price (e.g., 0.0)
        #   - = price of a share at BOD
        # Build the SQL query to retrieve the current positions.
        query = []
        query.append(f"SELECT * FROM {self._table_name}")
        # Get the trade date.
        wall_clock_timestamp = self._get_wall_clock_time()
        trade_date = wall_clock_timestamp.date()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("wall_clock_timestamp trade_date"))
        where_clause = [f"WHERE tradedate='{trade_date}'"]
        # Restrict query to portfolio universe.
        if restrict_to_universe:
            hdbg.dassert(self.universe, "Universe is empty.")
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("universe=\n%s", self.universe)
            universe = tuple(self.universe)
            if len(universe) == 1:
                universe = str(universe)[:-2] + ")"
            # TODO(Paul): Make sure that we do not exclude IDs with a nonzero current /
            #  target position (ensure that these are included in the universe).
            where_clause.append(f"AND {self._asset_id_col} IN {universe}")
        # Restrict by account if needed.
        if self._account is not None:
            where_clause.append(f"AND account='{self._account}'")
        query.append(" ".join(where_clause))
        #
        query.append(f"ORDER BY {self._asset_id_col}")
        query = "\n".join(query)
        # Retrieve the data from the DB.
        snapshot_df = hsql.execute_query_to_df(self._db_connection, query)
        snapshot_df.rename(columns={self._asset_id_col: "asset_id"}, inplace=True)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "snapshot_df=\n%s",
                hpandas.df_to_str(snapshot_df, num_rows=None, precision=2),
            )
        if not snapshot_df.empty:
            hdbg.dassert_no_duplicates(
                snapshot_df["asset_id"],
                "Each asset_id should be unique in a snapshot_df",
            )
        return snapshot_df

    def _is_stable_snapshot_df(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[bool, pd.DataFrame]:
        snapshot_df = self._get_snapshot_df(*args, **kwargs)
        is_stable = (snapshot_df["open_quantity"] == 0).all()
        return is_stable, snapshot_df

    def _get_stable_snapshot_df(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        """
        Wait until the current positions are stable and then return them.

        The current positions are stable when no outstanding orders are
        open.
        """
        # TODO(gp): Enable this.
        if False:
            polling_func = lambda: self._is_stable_snapshot_df(*args, **kwargs)
            tag = "wait_for_stable_snapshot_df"
            # Conceptually this should be an async polling. To avoid that the async
            # behavior spreads to all the methods, we resort to a sync implementation.
            rc, snapshot_df = hasynci.sync_poll(
                polling_func, tag=tag, **self._poll_kwargs
            )
            _ = rc
        else:
            snapshot_df = self._get_snapshot_df(*args, **kwargs)
        return snapshot_df

    def _observe_holdings_shares(self) -> None:
        """
        Observe the holdings_shares stored in the external DB and update the
        internal data structure to account for them.
        """
        restrict_to_universe = True
        snapshot_df = self._get_stable_snapshot_df(restrict_to_universe)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("snapshot_df=%s", snapshot_df)
        # 1) Update cash from snapshot_df.
        wall_clock_timestamp = self._get_wall_clock_time()
        self._update_executed_trades_notional_and_cash(
            snapshot_df, wall_clock_timestamp
        )
        # 2) Update asset holdings_shares from snapshot_df.
        holdings_shares = snapshot_df[["asset_id", "current_position"]].set_index(
            "asset_id"
        )["current_position"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("holdings_shares"))
        hdbg.dassert_isinstance(holdings_shares, pd.Series)
        holdings_shares = holdings_shares.reindex(
            index=self._initial_universe, copy=False
        )
        holdings_shares.name = wall_clock_timestamp
        # If the database does not have an entry for an asset (e.g., as in
        # a mock database without universe initialization), then a NaN is
        # returned.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "Number of NaN holdings_shares=%d", holdings_shares.isna().sum()
            )
        holdings_shares.fillna(0, inplace=True)
        hdbg.dassert(not holdings_shares.index.has_duplicates)
        self._holdings_shares[wall_clock_timestamp] = holdings_shares
        # 3) Update snapshot_df.
        hdbg.dassert(not snapshot_df.index.has_duplicates)
        self._timestamp_to_snapshot_df[wall_clock_timestamp] = snapshot_df

    # TODO(gp): -> _get_initial_holdings_from_db since we are not assigning it.
    def _initialize_holdings_from_db(
        self, initial_holdings: pd.Series
    ) -> pd.Series:
        """
        Retrieve and validate the holdings_shares stored in an external DB.

        :param initial_holdings: the nonzero holdings_shares from the DB need to be a
            subset of the index in `initial_holdings_shares`
        """
        # All initial holdings_shares must be NaN when we invoke this method.
        hdbg.dassert_eq(initial_holdings.count(), 0)
        # TODO(gp): Explain why we don't restrict to universe here like in
        #  `_observe_holdings_shares()`. Maybe it's because we expect the client to pass
        #  the universe from outside.
        restrict_to_universe = False
        snapshot_df = self._get_stable_snapshot_df(restrict_to_universe)
        # Get current nonzero positions.
        holdings = snapshot_df[["asset_id", "current_position"]].set_index(
            "asset_id"
        )["current_position"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("initial_holdings"))
        hdbg.dassert_isinstance(holdings, pd.Series)
        #
        nonzero_holdings = holdings[holdings != 0]
        hdbg.dassert_isinstance(nonzero_holdings, pd.Series)
        # Ensure that the nonzero positions are a subset of the universe
        # specified by the index of `initial_holdings_shares`.
        hdbg.dassert_is_subset(
            nonzero_holdings.index.to_list(), initial_holdings.index.to_list()
        )
        # Set zero holdings_shares and combine with nonzero initial holdings_shares.
        initial_holdings = initial_holdings.fillna(0)
        hdbg.dassert_isinstance(initial_holdings, pd.Series)
        initial_holdings = initial_holdings.add(nonzero_holdings, fill_value=0)
        return initial_holdings

    # TODO(gp): Make it static
    def _convert_to_holdings_shares_df(
        self, snapshot_df: pd.DataFrame, as_of_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        """
        Convert a snapshot_df from SQL query into a `holdings_df`.
        """
        holdings_df = snapshot_df[["asset_id", "current_position"]]
        holdings_df.columns = oporport.Portfolio.HOLDINGS_COLS
        holdings_df.index = [as_of_timestamp] * snapshot_df.shape[0]
        holdings_df = holdings_df.convert_dtypes()
        return holdings_df

    # TODO(gp): Make it static
    def _get_net_cost(self, snapshot_df: pd.DataFrame) -> pd.Series:
        """
        Return the `net_cost` of assets stored in a `snapshot_df`.

        This is a helper for
        `_update_executed_trades_notional_and_cash()`.
        """
        if snapshot_df.empty:
            return pd.Series([], dtype="float64")
        hdbg.dassert_in("net_cost", snapshot_df.columns)
        # A long position has negative net cost.
        net_cost = -1 * snapshot_df.set_index("asset_id")["net_cost"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("net_cost (cumulative)=%f", net_cost.sum())
        return net_cost

    def _update_executed_trades_notional_and_cash(
        self,
        snapshot_df: pd.DataFrame,
        wall_clock_timestamp: pd.Timestamp,
    ) -> None:
        """
        Compute the current cash amount using:

        - the net cost information from `snapshot_df`; and
        - the previous cash amount
        """
        # `snapshot_df` should not have CASH_ID.
        hdbg.dassert_not_in(oporport.Portfolio.CASH_ID, snapshot_df["asset_id"])
        # Get the cash at the previous timestamp.
        prev_cash_ts, prev_cash = self._cash.peek()
        hdbg.dassert_lt(prev_cash_ts, wall_clock_timestamp)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("prev_cash=%s", prev_cash)
        hdbg.dassert(np.isfinite(prev_cash), "prev_cash=%s", prev_cash)
        # Get the net cost at the previous timestamp.
        if self._net_cost:
            prev_net_cost_ts, prev_net_costs = self._net_cost.peek()
            hdbg.dassert_eq(prev_net_cost_ts, prev_cash_ts)
        else:
            _, holdings_shares = self._holdings_shares.peek()
            idx = holdings_shares.index
            prev_net_costs = pd.Series(0, idx)
        prev_net_cost = prev_net_costs.sum()
        # Get the current net cost.
        current_net_costs = self._get_net_cost(snapshot_df)
        current_net_cost = current_net_costs.sum()
        hdbg.dassert(
            np.isfinite(current_net_cost),
            "current_net_cost (cumulative)=%f",
            current_net_cost,
        )
        # The cost of the previous transactions is the difference of net cost.
        cost = current_net_cost - prev_net_cost
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("cost (net_cost diff)=%f", cost)
        hdbg.dassert(np.isfinite(cost))
        # The current cash is given by the previous cash and the cash spent in the
        # previous transactions.
        updated_cash = prev_cash - cost
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("updated_cash=%s", updated_cash)
        # Update the cash and net cost.
        self._cash[wall_clock_timestamp] = updated_cash
        self._net_cost[wall_clock_timestamp] = current_net_costs
        executed_trades_notional = current_net_costs.subtract(
            prev_net_costs, fill_value=0.0
        )
        hdbg.dassert(not executed_trades_notional.index.has_duplicates)
        self._executed_trades_notional[
            wall_clock_timestamp
        ] = executed_trades_notional
