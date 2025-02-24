"""
Import as:

import oms.order_processing.target_position_and_order_generator as ooptpaoge
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import core.config as cconfig
import core.key_sorted_ordered_dict as cksoordi
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hdict as hdict
import helpers.hio as hio
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hwall_clock_time as hwacltim
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.optimizer.call_optimizer as oopcaopt
import oms.optimizer.cc_optimizer_utils as ooccoput
import oms.order.order as oordorde
import oms.portfolio.portfolio as oporport

_LOG = logging.getLogger(__name__)


class TargetPositionAndOrderGenerator(hobject.PrintableMixin):
    """
    Take forecasts for the most recent bar and submit orders.

    - Retrieve the Portfolio holdings
    - Perform optimization on the forecasts
    - Generate the orders
    - Submit the orders through `Broker`
    """

    def __init__(
        self,
        portfolio: oporport.Portfolio,
        order_dict: cconfig.Config,
        optimizer_dict: cconfig.Config,
        # TODO(gp): -> restrictions_df like in `process_forecast()`
        restrictions: Optional[pd.DataFrame],
        share_quantization: Optional[int],
        *,
        log_dir: Optional[str] = None,
    ) -> None:
        """
        Build the object.

        :param order_dict: config for placing the orders, e.g.,
            ```
            order_type: price@twap
            order_duration_in_mins: 5
            ```
        :param optimizer_dict: config for the optimizer, e.g.,
            ```
            backend: pomo
            params:
              style: cross_sectional
              kwargs:
                bulk_frac_to_remove: 0.0
                bulk_fill_method: zero
                target_gmv: 100000.0
            ```
        :param log_dir: directory to log different stages of computation
            - `orders`
                - For each bar timestamp store a list of string representation of
                  the placed orders at that timestamp
            - `target_positions`
                - For each bar timestamp store the target position in terms of
                  asset_id, curr_num_shares, price, etc.
            - `portfolio`
                - Store the output of the included `Portfolio`
        """
        self._portfolio = portfolio
        self._get_wall_clock_time = portfolio.market_data.get_wall_clock_time
        # Save order config.
        self._order_dict = order_dict
        _ = hdict.typed_get(order_dict, "order_type", expected_type=str)
        self._order_duration_in_mins = hdict.typed_get(
            order_dict, "order_duration_in_mins", expected_type=int
        )
        # Depending on `order_type` it could be `str` or `None`, so the type
        # is not checked.
        self._execution_frequency = hdict.checked_get(
            order_dict, "execution_frequency"
        )
        # Save optimizer config.
        _ = hdict.typed_get(optimizer_dict, "backend", expected_type=str)
        self._optimizer_dict = optimizer_dict
        #
        self._restrictions = restrictions
        self._share_quantization = share_quantization
        self._log_dir = log_dir
        # Dict from timestamp to target positions.
        self._target_positions = cksoordi.KeySortedOrderedDict(pd.Timestamp)
        # Dict from timestamp to orders.
        self._orders = cksoordi.KeySortedOrderedDict(pd.Timestamp)

    # //////////////////////////////////////////////////////////////////////////
    # Print.
    # //////////////////////////////////////////////////////////////////////////

    def __str__(self) -> str:
        """
        Return the most recent state of this object as a string.

        E.g.,
        ```
        <oms.order_processing.target_position_and_order_generator.TargetPositionAndOrderGenerator at 0x>
        # last target positions=
                  holdings_shares      price  holdings_notional wall_clock_timestamp  prediction  volatility  spread  target_holdings_notional  target_trades_notional  target_trades_shares  target_holdings_shares
        asset_id
        101                     0    1000.30                0.0                                1      0.0001    0.01             100031.192549           100031.192549                 100.0                   100.0
        # last orders=
        Order: order_id=0 creation_timestamp=2000-01-01 09:35:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York
        ```
        """
        txt = []
        # <...target_position_and_order_generator at 0x>
        txt.append(hprint.to_object_repr(self))
        # TODO(Paul): Make this more like `Portfolio` logging.
        txt.append("# last target positions=")
        if self._target_positions:
            _, target_positions = self._target_positions.peek()
            target_positions_str = hpandas.df_to_str(target_positions)
        else:
            target_positions_str = "None"
        txt.append(target_positions_str)
        #
        txt.append("# last orders=")
        if self._orders:
            _, orders_str = self._orders.peek()
        else:
            orders_str = "None"
        txt.append(orders_str)
        # Assemble result.
        act = "\n".join(txt)
        return act

    # //////////////////////////////////////////////////////////////////////////
    #
    # //////////////////////////////////////////////////////////////////////////

    @staticmethod
    def load_target_positions(
        log_dir: str,
        *,
        tz: str = "America/New_York",
        rename_col_map: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """
        Parse logged `target_position` dataframes.
        :return a dataframe indexed by datetimes and with two column levels. E.g.,

        ```
        asset_id     curr_num_shares   price   position      wall_clock_timestamp prediction   volatility   spread  target_position   target_notional_trade  diff_num_shares_before_quantization  diff_num_shares
            10365                -4.0   305.6    -1222.6 2022-10-05 15:30:02-04:00     0.355         0.002        0            435.7                  1658.3                5.4                                5.0
        ```
        """
        sub_dir = "target_positions"
        files = TargetPositionAndOrderGenerator._get_files(log_dir, sub_dir)
        dfs = []
        for path in tqdm(files, desc=f"Loading `{sub_dir}` files..."):
            df = pd.read_csv(
                path, index_col=0, parse_dates=["wall_clock_timestamp"]
            )
            # Change the index from `asset_id` to the timestamp.
            df = df.reset_index().set_index("wall_clock_timestamp")
            # TODO(Dan): Research why column names are being incorrect sometimes
            #  and save the data with the proper names.
            if rename_col_map:
                df = df.rename(columns=rename_col_map)
            hpandas.dassert_series_type_is(df["asset_id"], np.int64)
            if not isinstance(df.index, pd.DatetimeIndex):
                _LOG.info("Skipping file_name=%s", path)
                continue
            df.index = df.index.tz_convert(tz)
            # Pivot to multiple column levels.
            df = df.pivot(columns="asset_id")
            dfs.append(df)
        df = pd.concat(dfs)
        return df

    @staticmethod
    def load_orders(
        log_dir: str,
    ) -> pd.DataFrame:
        """
        Parse logged orders and return as a dataframe indexed by order id.

        NOTE: Parsing logged orders takes significantly longer than reading
        logged target positions.

        E.g.,
        from `.../system_log_dir/process_forecasts/orders/20221005_153006.csv`
        ```
        Order: order_id=398 creation_timestamp=2022-10-05 15:30:02-04:00 asset_id=10365 type_=price@twap start_timestamp=2022-10-05 15:30:02-04:00 end_timestamp=2022-10-05 15:45:02-04:00 curr_num_shares=-4.0 diff_nu
        m_shares=5.0 tz=America/New_York
        Order: order_id=399 creation_timestamp=2022-10-05 15:30:02-04:00 asset_id=12007 type_=price@twap start_timestamp=2022-10-05 15:30:02-04:00 end_timestamp=2022-10-05 15:45:02-04:00 curr_num_shares=-8.0 diff_nu
        m_shares=6.0 tz=America/New_York
        ...
        ```
        """
        sub_dir = "orders"
        files = TargetPositionAndOrderGenerator._get_files(log_dir, sub_dir)
        dfs = []
        for path in tqdm(files, desc=f"Loading `{sub_dir}` files..."):
            lines = hio.from_file(path)
            lines = lines.split("\n")
            for line in lines:
                if not line:
                    continue
                order = oordorde.Order.from_string(line)
                order = order.to_dict()
                order = pd.Series(order).to_frame().T
                dfs.append(order)
        df = pd.concat(dfs)
        df = df.set_index("order_id")
        return df

    # //////////////////////////////////////////////////////////////////////////

    def compute_target_positions_and_generate_orders(
        self,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
        liquidate_holdings: bool,
    ) -> List[oordorde.Order]:
        """
        Translate returns and volatility forecasts into a list of orders.

        :param predictions: return forecasts
        :param volatility: volatility forecasts
        :param spread: spread forecasts
        :param liquidate_holdings: force liquidating all the current
            holdings
        :return: a list of orders to execute
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("liquidate_holdings"))
        # Convert forecasts into target positions.
        target_positions = self._compute_target_holdings_shares(
            predictions, volatility, spread, liquidate_holdings
        )
        # Convert target positions into orders.
        orders = self._generate_orders_wrapper(target_positions)
        return orders

    # //////////////////////////////////////////////////////////////////////////

    async def submit_orders(self, orders: List[oordorde.Order], **kwargs) -> None:
        """
        Submit `orders` to the broker confirming receipt and log the object
        state.

        :param orders: list of orders to execute
        :param **kargs: args for `submit_order`, like `order_type` and
            `passivity_factor`
        """
        # Submit orders.
        order_type = kwargs["order_type"]
        if not orders:
            _LOG.warning("No orders to submit to broker.")
        broker = self._portfolio.broker
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Event: awaiting broker.submit_orders()...")
        # Call `submit_orders()` regardless of `orders` being empty or not. The
        # reason is that broker needs to update its internal state to reflect
        # that no orders were submited for a given bar.
        await broker.submit_orders(
            orders, order_type, execution_freq=self._execution_frequency
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Event: awaiting broker.submit_orders() done.")
        # Log the entire state after submitting the orders.
        # We don't need to mark to market since `generate_orders()` takes care of
        # marking to market the Portfolio.
        mark_to_market = False
        self.log_state(mark_to_market)

    # TODO(gp): mark_to_market -> mark_to_market_portfolio
    def log_state(self, mark_to_market: bool) -> None:
        """
        Log the state of this object and Portfolio to log_dir.

        This is typically executed after `submit_orders()` and in some
        flows by `process_forecasts()`.

        :param mark_to_market: mark Portfolio to market before logging
            the state.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("log_state")
        if mark_to_market:
            self._portfolio.mark_to_market()
        # Log the state of this object and Portfolio.
        if self._log_dir:
            self._log_state()
            self._portfolio.log_state(os.path.join(self._log_dir, "portfolio"))

    # /////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _get_files(log_dir: str, sub_dir: str) -> List[str]:
        """
        Find all files from the requested dir `{log_dir}/{sub_dir}`.
        """
        dir_name = os.path.join(log_dir, sub_dir)
        # TODO(gp): We should consider only CSV files.
        pattern = "*"
        only_files = True
        use_relative_paths = True
        files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
        files.sort()
        # Add enclosing dir.
        files = [os.path.join(dir_name, file_name) for file_name in files]
        return files

    # TODO(Grisha): consider moving to a lib as a separate function.
    @staticmethod
    def _sanity_check_target_positions(target_positions: pd.DataFrame) -> None:
        """
        Perform a battery of self-consistency checks on target position data.
        """
        # Check that necessary column names are present in the dataframe.
        cols = (
            "price",
            "holdings_shares",
            "holdings_notional",
            "target_holdings_shares",
            "target_holdings_notional",
            "target_trades_shares",
            "target_trades_notional",
        )
        hdbg.dassert_is_subset(cols, target_positions.columns)
        # Set values.
        price = target_positions["price"]
        holdings_shares = target_positions["holdings_shares"]
        holdings_notional = target_positions["holdings_notional"]
        target_holdings_shares = target_positions["target_holdings_shares"]
        target_holdings_notional = target_positions["target_holdings_notional"]
        target_trades_shares = target_positions["target_trades_shares"]
        target_trades_notional = target_positions["target_trades_notional"]
        # 1) Verify that values in shares multiplied by corresponding prices
        # are equal to their notional counterparts.
        # `hpandas.dassert_approx_eq()` is used for checks instead of `dassert_eq()`
        # in order to avoid decimal precision issue.
        atol = 1e-04
        hpandas.dassert_approx_eq(
            holdings_notional, holdings_shares * price, atol=atol
        )
        hpandas.dassert_approx_eq(
            target_holdings_notional, target_holdings_shares * price, atol=atol
        )
        hpandas.dassert_approx_eq(
            target_trades_notional, target_trades_shares * price, atol=atol
        )
        # 2) Verify that `target_holdings` is the sum of `holdings`
        # and `target_trades`.
        hpandas.dassert_approx_eq(
            target_holdings_shares,
            holdings_shares + target_trades_shares,
            atol=atol,
        )
        hpandas.dassert_approx_eq(
            target_holdings_notional,
            holdings_notional + target_trades_notional,
            atol=atol,
        )

    # TODO(gp): -> _log_internal_state or _log_object_state?
    def _log_state(self) -> None:
        """
        Log the most recent state of the object.
        """
        hdbg.dassert(self._log_dir, "Must specify `log_dir` to log state.")
        # TODO(gp): We should also add the bar timestamp as for other objects.
        wall_clock_time = self._get_wall_clock_time()
        wall_clock_time_str = wall_clock_time.strftime("%Y%m%d_%H%M%S")
        bar_timestamp = hwacltim.get_current_bar_timestamp(as_str=True)
        filename = f"{bar_timestamp}.{wall_clock_time_str}.csv"
        # Log the last target position.
        if self._target_positions:
            _, last_target_positions = self._target_positions.peek()
            # TODO(gp): Check that last_key matches the current bar timestamp.
            last_target_positions_filename = os.path.join(
                self._log_dir, "target_positions", filename
            )
            hio.create_enclosing_dir(
                last_target_positions_filename, incremental=True
            )
            last_target_positions.to_csv(last_target_positions_filename)
        # Log the orders.
        if self._orders:
            _, last_orders = self._orders.peek()
            last_orders_filename = os.path.join(self._log_dir, "orders", filename)
            hio.create_enclosing_dir(last_orders_filename, incremental=True)
            hio.to_file(last_orders_filename, last_orders)

    def _compute_target_holdings_shares(
        self,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
        liquidate_holdings: bool,
    ) -> pd.DataFrame:
        """
        Compute target holdings in shares.

        :param predictions: predictions indexed by `asset_id`
        :param volatility: volatility forecasts indexed by `asset_id`
        :param spread: spread forecasts indexed by `asset_id`
        :param liquidate_holdings: force liquidating all the current holdings
        :return: the df with target_positions including `diff_num_shares`
        """
        assets_and_predictions = self._prepare_data_for_optimizer(
            predictions, volatility, spread
        )
        hdbg.dassert_not_in(
            self._portfolio.CASH_ID, assets_and_predictions["asset_id"].to_list()
        )
        # Extract params from the config.
        backend = hdict.checked_get(self._optimizer_dict, "backend")
        optimizer_params = self._optimizer_dict["params"]
        asset_class = hdict.checked_get(self._optimizer_dict, "asset_class")
        apply_cc_limits = hdict.checked_get(
            self._optimizer_dict, "apply_cc_limits"
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "backend optimizer_params asset_class apply_cc_limits"
                )
            )
        # Compute the target positions in notional. This conceptually corresponds
        # to calling an optimizer.
        # TODO(Paul): Align with ForecastEvaluator and update callers.
        if asset_class == "crypto" and apply_cc_limits:
            # The information is available only via CcxtBroker so extract the info only
            # when working with CcxtBroker, be it `DataFrameCcxtBroker` or `CcxtBroker`.
            market_info = self._portfolio.broker.market_info
            # TODO(Grisha): consider exposing `asset_ids_to_decimals` to the ctor or
            # to the `optimizer_dict`, see CmTask4826.
            asset_ids_to_decimals = obccccut.subset_market_info(
                market_info, "amount_precision"
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("asset_ids_to_decimals=%s", asset_ids_to_decimals)
        else:
            asset_ids_to_decimals = None
        if backend == "pomo":
            style = optimizer_params["style"]
            kwargs = optimizer_params["kwargs"]
            df = oopcaopt.compute_target_holdings_and_trades_notional(
                assets_and_predictions,
                style=style,
                **kwargs,
            )
            df = oopcaopt.convert_target_holdings_and_trades_to_shares_and_adjust_notional(
                df,
                quantization=self._share_quantization,
                asset_id_to_decimals=asset_ids_to_decimals,
            )
        elif backend == "batch_optimizer":
            import optimizer.single_period_optimization as osipeopt

            spo = osipeopt.SinglePeriodOptimizer(
                optimizer_params,
                assets_and_predictions,
                restrictions=self._restrictions,
            )
            df = spo.optimize(
                quantization=self._share_quantization,
                asset_id_to_share_decimals=asset_ids_to_decimals,
                liquidate_holdings=liquidate_holdings,
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        elif backend == "dind_optimizer":
            # Call docker optimizer stub.
            raise NotImplementedError
        elif backend == "service_optimizer":
            raise NotImplementedError
        else:
            raise ValueError("Unsupported `backend`=%s", backend)
        if asset_class == "crypto" and apply_cc_limits:
            # Apply notional limits to all the orders. Target amount of order shares
            # is set to 0 if its actual values are below limits. This is specific to
            # crypto Binance.
            # TODO(Grisha): ideally we should remove rounding from `apply_cc_limits()`
            # and use `quantize_shares()` only.
            _LOG.info("Applying notional limits to all the orders.")
            round_mode = "check"
            df = ooccoput.apply_cc_limits(df, self._portfolio.broker, round_mode)
        # Package the output df.
        if liquidate_holdings:
            # If we want to liquidate all the holdings, we want to trade to flatten
            # the current positions.
            target_trades_shares = -df["holdings_shares"]
            target_trades_notional = -df["holdings_notional"]
            _LOG.info(
                "Liquidating holdings: target_trades_shares=\n%s",
                hpandas.df_to_str(target_trades_shares),
            )
            _LOG.info(
                "Liquidating holdings: target_trades_notional=\n%s",
                hpandas.df_to_str(target_trades_notional),
            )
            df["target_trades_shares"] = target_trades_shares
            df["target_trades_notional"] = target_trades_notional
            # After liquidation holdings turn to zero.
            df["target_holdings_shares"] = 0.0
            df["target_holdings_notional"] = 0.0
        df["spread"] = assets_and_predictions.set_index("asset_id")["spread"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        # Sanity check target positions metrics.
        self._sanity_check_target_positions(df)
        return df

    # TODO(gp): This should go before.
    def _prepare_data_for_optimizer(
        self,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
    ) -> pd.DataFrame:
        """
        Clean up data for optimization.

        Cleaning includes ensuring data completeness and NaN handling.

        :param predictions: predictions indexed by `asset_id`
        :param volatility: volatility forecasts indexed by `asset_id`
        """
        hpandas.dassert_indices_equal(predictions, volatility, allow_series=True)
        # TODO(gp): Add check for spread too.
        marked_to_market = self._get_extended_marked_to_market_df(predictions)
        # Combine the portfolio `marked_to_market` dataframe with the predictions.
        df_for_optimizer = self._merge_predictions(
            marked_to_market, predictions, volatility, spread
        )
        cash_id_filter = df_for_optimizer["asset_id"] == self._portfolio.CASH_ID
        df_for_optimizer.rename(
            columns={"value": "holdings_notional"}, inplace=True
        )
        return df_for_optimizer[~cash_id_filter].reset_index(drop=True)

    def _get_extended_marked_to_market_df(
        self,
        predictions: pd.Series,
    ) -> pd.DataFrame:
        """
        Get portfolio `mark_to_market()` df and extend to all predictions.

        If the portfolio is initialized with the trading universe, then this
        should be a no-op.

        :param predictions: predictions indexed by `asset_id`
        """
        marked_to_market_df = self._portfolio.mark_to_market().set_index(
            "asset_id"
        )
        # If there are predictions for assets not currently in `marked_to_market_df`,
        # then attempt to price those assets and extend `marked_to_market_df`
        # (imputing 0's for the holdings).
        unpriced_assets = predictions.index.difference(marked_to_market_df.index)
        if not unpriced_assets.empty:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Unpriced assets by id=\n%s",
                    "\n".join(map(str, unpriced_assets.to_list())),
                )
            prices = self._portfolio.price_assets(unpriced_assets.values)
            mtm_extension = pd.DataFrame(
                index=unpriced_assets,
                columns=["price", "curr_num_shares", "value"],
            )
            hdbg.dassert_eq(len(unpriced_assets), len(prices))
            mtm_extension["price"] = prices
            mtm_extension.index.name = "asset_id"
            marked_to_market_df = pd.concat(
                [marked_to_market_df, mtm_extension], axis=0
            )
        marked_to_market_df.reset_index(inplace=True)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "marked_to_market dataframe=\n%s",
                hpandas.df_to_str(marked_to_market_df),
            )
        marked_to_market_df.rename(
            columns={
                "curr_num_shares": "holdings_shares",
                "value": "holdings_notional",
            },
            inplace=True,
        )
        # TODO(Paul): Rename columns here for now.
        return marked_to_market_df

    def _normalize_series(
        self,
        series: pd.Series,
        index: pd.DatetimeIndex,
        imputation_mode: str,
        name: str,
    ) -> pd.DataFrame:
        """
        Normalize series with `index`, NaN-filling, and df conversion.
        """
        hdbg.dassert_isinstance(series, pd.Series)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Number of values=%i", series.size)
            _LOG.debug("Number of non-NaN values=%i", series.count())
            _LOG.debug("Number of NaN values=%i", series.isna().sum())
        # Ensure that `series` does not include the cash id.
        hdbg.dassert_not_in(self._portfolio.CASH_ID, series.index)
        # Ensure that `index` includes `series.index`.
        hdbg.dassert(series.index.difference(index).empty)
        # Extend `predictions` to `index`.
        series = series.reindex(index)
        # Set the "prediction" for cash to 1. This is for the optimizer.
        series[self._portfolio.CASH_ID] = 1
        # Impute zero for NaNs.
        if imputation_mode == "zero":
            series = series.fillna(0.0)
        elif imputation_mode == "mean":
            series_mean = series.mean()
            series = series.fillna(series_mean)
        else:
            raise ValueError(f"Invalid imputation mode '{imputation_mode}")
        # Convert to a dataframe.
        df = pd.DataFrame(series)
        # Format the predictions dataframe.
        df.columns = [name]
        df.index.name = "asset_id"
        df = df.reset_index()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        return df

    def _merge_predictions(
        self,
        marked_to_market: pd.DataFrame,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
    ) -> pd.DataFrame:
        """
        Merge marked_to_market dataframe with predictions and volatility.

        :return: dataframe with columns `asset_id`, `prediction`, `price`,
            `curr_num_shares`, `value`
            - The dataframe is the outer join of all the held assets in `portfolio`
              and `predictions`
        """
        hpandas.dassert_indices_equal(predictions, volatility, allow_series=True)
        # The portfolio may have grandfathered holdings for which there is no
        # prediction.
        idx = predictions.index.union(
            marked_to_market.set_index("asset_id").index
        )
        predictions = self._normalize_series(
            predictions, idx, "zero", "prediction"
        )
        volatility = self._normalize_series(volatility, idx, "mean", "volatility")
        spread = self._normalize_series(spread, idx, "mean", "spread")
        # Merge current holdings and predictions.
        merged_df = marked_to_market.merge(
            predictions, on="asset_id", how="outer"
        )
        merged_df = merged_df.merge(
            volatility,
            on="asset_id",
            how="outer",
        )
        merged_df = merged_df.merge(
            spread,
            on="asset_id",
            how="outer",
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "Number of NaNs in `holdings_shares` post-merge=`%i`",
                merged_df["holdings_shares"].isna().sum(),
            )
        merged_df = merged_df.convert_dtypes()
        merged_df = merged_df.fillna(0.0)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "After merge: merged_df=\n%s", hpandas.df_to_str(merged_df)
            )
        return merged_df

    # /////////////////////////////////////////////////////////////////////////////

    def _generate_orders_wrapper(
        self, target_positions: pd.DataFrame
    ) -> List[oordorde.Order]:
        """
        Convert target positions into orders.
        """
        # Get the wall clock timestamp and internally log `target_positions`.
        wall_clock_timestamp = self._get_wall_clock_time()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        self._target_positions[wall_clock_timestamp] = target_positions
        # Generate orders from target positions.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "\n%s",
                hprint.frame(
                    "Generating orders: timestamp=%s" % wall_clock_timestamp,
                    char1="#",
                ),
            )
        # Create a config for `Order`.
        # Enter position between now and the end of the current bar.
        order_timestamp_start = wall_clock_timestamp
        # Find the end of the current bar.
        mode = "floor"
        # TODO(Grisha): we use `order_duration_in_mins` to infer a bar length;
        # probably we should use bar duration directly from the `System.config`
        # and remove `order_duration_in_mins` from the ctor of this class.
        # TODO(Grisha): Consider creating a `find_bar_end_timestamp()`.
        bar_duration_in_secs = hdateti.convert_minutes_to_seconds(
            self._order_duration_in_mins
        )
        current_bar_start_timestamp = hdateti.find_bar_timestamp(
            order_timestamp_start,
            bar_duration_in_secs,
            mode=mode,
        )
        current_bar_end_timestamp = current_bar_start_timestamp + pd.DateOffset(
            seconds=bar_duration_in_secs
        )
        #
        order_dict = {
            "type_": self._order_dict["order_type"],
            "creation_timestamp": wall_clock_timestamp,
            "start_timestamp": order_timestamp_start,
            "end_timestamp": current_bar_end_timestamp,
        }
        orders = self._generate_orders(
            target_positions[["holdings_shares", "target_trades_shares"]],
            order_dict,
        )
        # Convert orders to a string representation and internally log.
        orders_as_str = oordorde.orders_to_string(orders)
        self._orders[wall_clock_timestamp] = orders_as_str
        return orders

    def _generate_orders(
        self,
        shares_df: pd.DataFrame,
        order_dict: Dict[str, Any],
    ) -> List[oordorde.Order]:
        """
        Turn a series of asset_id / shares to trade into a list of orders.

        :param shares_df: dataframe indexed by `asset_id`. Contains columns
            `curr_num_shares` and `diff_num_shares`. May contain zero rows.
        :param order_dict: common parameters used to initialize `Order`
        :return: a list of nontrivial orders (i.e., no zero-share orders)
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Generate orders")
        hdbg.dassert_isinstance(order_dict, dict)
        hdbg.dassert_is_subset(
            ("holdings_shares", "target_trades_shares"), shares_df.columns
        )
        orders: List[oordorde.Order] = []
        for asset_id, shares_row in shares_df.iterrows():
            curr_num_shares = shares_row["holdings_shares"]
            diff_num_shares = shares_row["target_trades_shares"]
            hdbg.dassert(
                np.isfinite(curr_num_shares),
                "The curr_num_share value must be finite.",
            )
            if not np.isfinite(diff_num_shares):
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug(
                        "`diff_num_shares`=%f for `asset_id`=%i",
                        diff_num_shares,
                        asset_id,
                    )
                diff_num_shares = 0.0
            diff_num_shares = self._enforce_restrictions(
                asset_id, curr_num_shares, diff_num_shares
            )
            if diff_num_shares == 0.0:
                # No need to place trades.
                continue
            order = oordorde.Order(
                asset_id=asset_id,
                curr_num_shares=curr_num_shares,
                diff_num_shares=diff_num_shares,
                **order_dict,
            )
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("order=%s", order.order_id)
            orders.append(order)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Number of orders generated=%i", len(orders))
        return orders

    def _enforce_restrictions(
        self,
        asset_id: int,
        curr_num_shares: float,
        diff_num_shares: float,
    ) -> float:
        if self._restrictions is None:
            return diff_num_shares
        filter_ = self._restrictions["asset_id"] == asset_id
        restrictions = self._restrictions[filter_]
        if restrictions.empty:
            return diff_num_shares
        # Enforce "is_buy_restricted".
        if (
            restrictions.loc["is_buy_restricted"]
            and curr_num_shares >= 0
            and diff_num_shares > 0
        ):
            diff_num_shares = 0.0
        # Enforce "is_buy_cover_restricted".
        if (
            restrictions.loc["is_buy_cover_restricted"]
            and curr_num_shares < 0
            and diff_num_shares > 0
        ):
            diff_num_shares = 0.0
        # Enforce "is_sell_short_restricted".
        if (
            restrictions.loc["is_sell_short_restricted"]
            and curr_num_shares <= 0
            and diff_num_shares < 0
        ):
            diff_num_shares = 0.0
        # Enforce "is_sell_long_restricted".
        if (
            restrictions.loc["is_sell_long_restricted"]
            and curr_num_shares > 0
            and diff_num_shares < 0
        ):
            diff_num_shares = 0.0
        _LOG.warning("Enforcing restriction for asset_id=%i", asset_id)
        return diff_num_shares
