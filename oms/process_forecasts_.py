"""
Import as:

import oms.process_forecasts_ as oprofore
"""

import asyncio
import datetime
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import core.config as cconfig
import core.finance as cofinanc
import core.key_sorted_ordered_dict as cksoordi
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.htqdm as htqdm
import helpers.hwall_clock_time as hwacltim
import oms.call_optimizer as ocalopti
import oms.order as omorder
import oms.portfolio as omportfo

_LOG = logging.getLogger(__name__)


async def process_forecasts(
    prediction_df: pd.DataFrame,
    volatility_df: pd.DataFrame,
    portfolio: omportfo.Portfolio,
    # TODO(gp): It should be a dict.
    # TODO(gp): Remove the two nested process_forecasts_config in the config.
    config: cconfig.Config,
    # TODO(gp): Should we keep all the dfs close together in the interface?
    # TODO(gp): Add a *
    spread_df: Optional[pd.DataFrame],
    restrictions_df: Optional[pd.DataFrame],
) -> None:
    """
    Place orders corresponding to the predictions stored in the passed df.

    Orders will be realized over the span of two intervals of time (i.e., two lags).

    - The PnL is realized two intervals of time after the corresponding prediction
    - The columns reported in the df are for the beginning of the interval of time
    - The columns ending with `+1` represent what happens in the next interval
      of time

    :param prediction_df: a dataframe indexed by timestamps with one column for the
        predictions for each asset
    :param volatility_df: like `prediction_df`, but for volatility
    :param spread_df: like `prediction_df`, but for the bid-ask spread
    :param portfolio: initialized `Portfolio` object
    :param config: the required params are:
          # TODO(gp): Is this updated?
          ```
          {
            "order_dict": dict,
            "optimizer_dict": dict,
            "ath_start_time": Optional[datetime.time],
            "trading_start_time": Optional[datetime.time],
            "ath_end_time": Optional[datetime.time],
            "trading_end_time": Optional[datetime.time],
            "execution_mode": str ["real_time", "batch"],
            "remove_weekends": Optional[bool],
            "log_dir": Optional[str],
          }
          ```
        - `execution_mode`:
            - `batch`: place the trades for all the predictions (used in historical
               mode)
            - `real_time`: place the trades only for the last prediction in the df
              (used in real-time mode)
        - `log_dir`: directory for logging state
    """
    # TODO(gp): Move all this in a _validate method
    # Check `predictions_df`.
    hpandas.dassert_time_indexed_df(
        prediction_df, allow_empty=True, strictly_increasing=True
    )
    # Check `volatility_df`.
    hpandas.dassert_time_indexed_df(
        volatility_df, allow_empty=True, strictly_increasing=True
    )
    # Check `spread_df`.
    if spread_df is None:
        _LOG.info("spread_df is `None`; imputing 0.0 spread")
        spread_df = pd.DataFrame(0.0, prediction_df.index, prediction_df.columns)
    hpandas.dassert_time_indexed_df(
        spread_df, allow_empty=True, strictly_increasing=True
    )
    # Check index/column compatibility among the dfs.
    hpandas.dassert_axes_equal(prediction_df, volatility_df)
    hpandas.dassert_axes_equal(prediction_df, spread_df)
    # Check `portfolio`.
    hdbg.dassert_isinstance(portfolio, omportfo.Portfolio)
    hdbg.dassert_isinstance(config, cconfig.Config)
    # hdbg.dassert_isinstance(config, dict)
    # Check `restrictions`.
    if restrictions_df is None:
        _LOG.info("restrictions_df is `None`; no restrictions will be enforced")
    # Create an `order_config` from `config` elements.
    # TODO(gp): If config is a dict then we need to change get_object_from_config.
    #  We can have a similar function in hdict or hpython.
    order_config = cconfig.get_object_from_config(
        config, "order_config", cconfig.Config, None
    )
    _validate_order_config(order_config)
    #
    optimizer_config = cconfig.get_object_from_config(
        config, "optimizer_config", cconfig.Config, None
    )
    _validate_optimizer_config(optimizer_config)
    # Extract ATH and trading start times from config.
    ath_start_time = config.get("ath_start_time")
    trading_start_time = config.get("trading_start_time")
    ath_end_time = config.get("ath_end_time")
    trading_end_time = config.get("trading_end_time")
    # Sanity check trading time.
    _validate_trading_time(
        ath_start_time, ath_end_time, trading_start_time, trading_end_time
    )
    # Get execution mode ("real_time" or "batch").
    execution_mode = cconfig.get_object_from_config(
        config, "execution_mode", str, None
    )
    if execution_mode == "real_time":
        prediction_df = prediction_df.tail(1)
    elif execution_mode == "batch":
        pass
    else:
        raise ValueError(f"Unrecognized execution mode='{execution_mode}'")
    # TODO(Paul): Pass in a trading calendar explicitly instead of simply
    #   filtering out weekends.
    if "remove_weekends" in config and config["remove_weekends"]:
        prediction_df = cofinanc.remove_weekends(prediction_df)
        volatility_df = cofinanc.remove_weekends(volatility_df)
        spread_df = cofinanc.remove_weekends(spread_df)
    # Get log dir.
    log_dir = config.get("log_dir", None)
    _LOG.info("log_dir=%s", log_dir)
    # We should not have anything left in the config that we didn't extract.
    # hdbg.dassert(not config, "config=%s", str(config))
    _LOG.debug(
        "predictions_df=%s\n%s",
        str(prediction_df.shape),
        hpandas.df_to_str(prediction_df),
    )
    _LOG.debug("predictions_df.index=%s", str(prediction_df.index))
    num_rows = len(prediction_df)
    _LOG.debug("Number of rows in `prediction_df`=%d", num_rows)
    #
    get_wall_clock_time = portfolio.market_data.get_wall_clock_time
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    iter_ = enumerate(prediction_df.iterrows())
    offset_min = pd.DateOffset(minutes=order_config["order_duration_in_mins"])
    # Initialize a `ForecastProcessor` object to perform the heavy lifting.
    forecast_processor = ForecastProcessor(
        portfolio,
        order_config,
        optimizer_config,
        restrictions_df,
        log_dir=log_dir,
    )
    hwacltim.reset_current_bar_timestamp()
    # `timestamp` is the time when the forecast is available and in the current
    #  setup is also when the order should begin.
    for idx, (timestamp, predictions) in tqdm(
        iter_, total=num_rows, file=tqdm_out
    ):
        _LOG.debug(
            "\n%s",
            hprint.frame("# idx=%s timestamp=%s" % (idx, timestamp)),
        )
        # Update the global state tracking the current bar.
        # TODO(gp): The outermost loop in run_dag should set the bar based on
        #  align_on_grid.
        hwacltim.set_current_bar_timestamp(timestamp)
        # Wait until get_wall_clock_time() == timestamp.
        if get_wall_clock_time() > timestamp:
            # E.g., it's 10:21:51, we computed the forecast for [10:20, 10:25]
            # bar. As long as it's before 10:25, we want to place the order. If
            # it's later, either assert or log it as a problem.
            hdbg.dassert_lte(get_wall_clock_time(), timestamp + offset_min)
        else:
            _LOG.debug("async_wait_until")
            await hasynci.async_wait_until(timestamp, get_wall_clock_time)
        # Get the wall clock timestamp.
        wall_clock_timestamp = get_wall_clock_time()
        _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        # Get the time of day of the wall clock timestamp.
        time = wall_clock_timestamp.time()
        skip_bar = _skip_bar(
            time,
            ath_start_time,
            ath_end_time,
            trading_start_time,
            trading_end_time,
        )
        if skip_bar:
            _LOG.warning("Skipping bar for time: `%s`", time)
            continue
        # if execution_mode == "batch":
        #     if idx == len(predictions_df) - 1:
        #         # For the last timestamp we only need to mark to market, but not
        #         # post any more orders.
        #         continue
        # Wait 1 second to give all open orders sufficient time to close.
        _LOG.debug("Event: awaiting asyncio.sleep()...")
        await asyncio.sleep(1)
        _LOG.debug("Event: awaiting asyncio.sleep() done.")
        # Compute the target positions.
        _LOG.debug(
            "\n%s",
            hprint.frame(
                "Computing target positions: timestamp=%s" % wall_clock_timestamp,
                char1="#",
            ),
        )
        volatility = volatility_df.loc[timestamp]
        spread = spread_df.loc[timestamp]
        orders = forecast_processor.generate_orders(
            predictions, volatility, spread
        )
        await forecast_processor.submit_orders(orders)
        _LOG.debug("ForecastProcessor=\n%s", str(forecast_processor))
    _LOG.debug("Event: exiting process_forecasts() for loop.")


# TODO(Grisha): @Dan Move to `helpers/hdbg.py`
def dassert_all_defined_or_all_None(
    vals: List[Any],
    msg: Optional[str] = None,
    *args: Any,
    only_warning: bool = False,
) -> None:
    """
    Check that all the values in a list are either all defined or all None.
    """
    all_defined_cond = all(val is not None for val in vals)
    all_none_cond = all(val is None for val in vals)
    cond = all_defined_cond or all_none_cond
    if not cond:
        txt = f"Some values in list are defined and some are None: '{vals}'"
        hdbg._dfatal(txt, msg, *args, only_warning=only_warning)


def _validate_trading_time(
    ath_start_time: Optional[datetime.time],
    ath_end_time: Optional[datetime.time],
    trading_start_time: Optional[datetime.time],
    trading_end_time: Optional[datetime.time],
) -> None:
    """
    Check that trading hours are specified correctly.
    """
    dassert_all_defined_or_all_None(
        [ath_start_time, ath_end_time, trading_start_time, trading_end_time]
    )
    if ath_start_time is not None:
        hdbg.dassert_lte(ath_start_time, ath_end_time)
        hdbg.dassert_lte(trading_start_time, trading_end_time)
        hdbg.dassert_lte(ath_start_time, trading_start_time)
        hdbg.dassert_lte(trading_end_time, ath_end_time)


def _skip_bar(
    time: datetime.time,
    ath_start_time: Optional[datetime.time],
    ath_end_time: Optional[datetime.time],
    trading_start_time: Optional[datetime.time],
    trading_end_time: Optional[datetime.time],
) -> bool:
    """
    Determine whether to skip a bar processing or not.
    """
    skip_bar_cond = False
    trading_time_list = [
        ath_start_time,
        ath_end_time,
        trading_start_time,
        trading_end_time,
    ]
    all_defined_cond = all(val is not None for val in trading_time_list)
    if all_defined_cond:
        # Perform trading time filtering.
        if time < ath_start_time:
            _LOG.debug(
                "time=`%s` < `ath_start_time=`%s`, skipping...",
                time,
                ath_start_time,
            )
            skip_bar_cond = True
        if time >= ath_end_time:
            _LOG.debug(
                "time=`%s` > `ath_end_time=`%s`, skipping...",
                time,
                ath_end_time,
            )
            skip_bar_cond = True
        # Continue if we are outside of our trading window.
        if time < trading_start_time or time > trading_end_time:
            skip_bar_cond = True
    return skip_bar_cond


# #############################################################################
# ForecastProcessor
# #############################################################################


# process_forecasts_config
class ForecastProcessor:
    """
    Take forecasts for the most recent bar and submit orders.

    - Retrieve the Portfolio holdings
    - Perform optimization on the forecasts
    - Generate orders
    - Submit orders
    """

    def __init__(
        self,
        portfolio: omportfo.Portfolio,
        # TODO(gp): dict?
        order_config: cconfig.Config,
        optimizer_config: cconfig.Config,
        # TODO(gp): -> restrictions_df like the process_forecast
        restrictions: Optional[pd.DataFrame],
        *,
        log_dir: Optional[str] = None,
    ) -> None:
        """

        :param order_config: config for the
            - E.g.,
              ```
              order_type: price@twap
              order_duration_in_mins: 5
              ```
        :param optimizer_config: config for the optimizer, e.g.,
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
            - Saved by `ForecastProcessor`
                - `orders`
                - `portfolio`
                - `target_positions`
            - Saved by `ForecastEvaluatorFromPrices` (not instantiated by this
                object anymore)
                - evaluate_forecasts
        """
        self._portfolio = portfolio
        self._get_wall_clock_time = portfolio.market_data.get_wall_clock_time
        # Process order config.
        # TODO(Paul): process config with checks.
        _validate_order_config(order_config)
        self._order_config = order_config
        self._offset_min = pd.DateOffset(
            minutes=order_config["order_duration_in_mins"]
        )
        # Process optimizer config.
        _validate_optimizer_config(optimizer_config)
        self._optimizer_config = optimizer_config
        #
        self._restrictions = restrictions
        self._log_dir = log_dir
        #
        self._target_positions = cksoordi.KeySortedOrderedDict(pd.Timestamp)
        self._orders = cksoordi.KeySortedOrderedDict(pd.Timestamp)

    def __str__(self) -> str:
        """
        Return the most recent state of the ForecastProcessor as a string.
        """
        act = []
        if self._target_positions:
            _, target_positions = self._target_positions.peek()
            target_positions_str = hpandas.df_to_str(target_positions)
        else:
            target_positions_str = "None"
        act.append("# last target positions=\n%s" % target_positions_str)
        if self._orders:
            _, orders_str = self._orders.peek()
        else:
            orders_str = "None"
        act.append("# last orders=\n%s" % orders_str)
        act = "\n".join(act)
        return act

    @staticmethod
    def read_logged_target_positions(
        log_dir: str,
        *,
        tz: str = "America/New_York",
    ) -> pd.DataFrame:
        """
        Parse logged `target_position` dataframes.

        :return a dataframe indexed by datetimes and with two column levels
        """
        name = "target_positions"
        dir_name = os.path.join(log_dir, name)
        pattern = "*"
        only_files = True
        use_relative_paths = True
        files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
        files.sort()
        dfs = []
        for file_name in tqdm(files, desc=f"Loading `{name}` files..."):
            path = os.path.join(dir_name, file_name)
            df = pd.read_csv(
                path, index_col=0, parse_dates=["wall_clock_timestamp"]
            )
            # Change the index from `asset_id` to the timestamp.
            df = df.reset_index().set_index("wall_clock_timestamp")
            hpandas.dassert_series_type_is(df["asset_id"], np.int64)
            if not isinstance(df.index, pd.DatetimeIndex):
                _LOG.info("Skipping file_name=%s", file_name)
                continue
            df.index = df.index.tz_convert(tz)
            # Pivot to multiple column levels.
            df = df.pivot(columns="asset_id")
            dfs.append(df)
        df = pd.concat(dfs)
        return df

    @staticmethod
    def read_logged_orders(
        log_dir: str,
    ) -> pd.DataFrame:
        """
        Parse logged orders and return as a dataframe indexed by order id.

        NOTE: Parsing logged orders takes significantly longer than reading
        logged target positions.
        """
        name = "orders"
        dir_name = os.path.join(log_dir, name)
        pattern = "*"
        only_files = True
        use_relative_paths = True
        files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
        files.sort()
        dfs = []
        for file_name in tqdm(files, desc=f"Loading `{name}` files..."):
            path = os.path.join(dir_name, file_name)
            lines = hio.from_file(path)
            lines = lines.split("\n")
            for line in lines:
                if not line:
                    continue
                order = omorder.Order.from_string(line)
                order = order.to_dict()
                order = pd.Series(order).to_frame().T
                dfs.append(order)
        df = pd.concat(dfs)
        df = df.set_index("order_id")
        return df

    def log_state(self) -> None:
        """
        Log the most recent state of the object.
        """
        hdbg.dassert(self._log_dir, "Must specify `log_dir` to log state.")
        #
        wall_clock_time = self._get_wall_clock_time()
        wall_clock_time_str = wall_clock_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{wall_clock_time_str}.csv"
        # Log the target position.
        if self._target_positions:
            last_key, last_target_positions = self._target_positions.peek()
            last_target_positions_filename = os.path.join(
                self._log_dir, "target_positions", filename
            )
            hio.create_enclosing_dir(
                last_target_positions_filename, incremental=True
            )
            last_target_positions.to_csv(last_target_positions_filename)
        # Log the orders.
        if self._orders:
            last_key, last_orders = self._orders.peek()
            last_orders_filename = os.path.join(self._log_dir, "orders", filename)
            hio.create_enclosing_dir(last_orders_filename, incremental=True)
            hio.to_file(last_orders_filename, last_orders)

    def generate_orders(
        self,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
    ) -> List[omorder.Order]:
        """
        Translate returns and volatility forecasts into a list of orders.

        :param predictions: returns forecasts
        :param volatility: volatility forecasts
        :param spread: spread forecasts
        :return: a list of orders to execute
        """
        # Convert forecasts into target positions.
        target_positions = self._compute_target_positions_in_shares(
            predictions, volatility, spread
        )
        # Get the wall clock timestamp and internally log `target_positions`.
        wall_clock_timestamp = self._get_wall_clock_time()
        _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        self._target_positions[wall_clock_timestamp] = target_positions
        # Generate orders from target positions.
        _LOG.debug(
            "\n%s",
            hprint.frame(
                "Generating orders: timestamp=%s" % wall_clock_timestamp,
                char1="#",
            ),
        )
        # Enter position between now and the next `order_duration_in_mins` minutes.
        # Create a config for `Order`.
        timestamp_start = wall_clock_timestamp
        timestamp_end = wall_clock_timestamp + self._offset_min
        order_dict_ = {
            "type_": self._order_config["order_type"],
            "creation_timestamp": wall_clock_timestamp,
            "start_timestamp": timestamp_start,
            "end_timestamp": timestamp_end,
        }
        order_config = cconfig.get_config_from_nested_dict(order_dict_)
        orders = self._generate_orders(
            target_positions[["curr_num_shares", "diff_num_shares"]], order_config
        )
        # Convert orders to a string representation and internally log.
        orders_as_str = omorder.orders_to_string(orders)
        self._orders[wall_clock_timestamp] = orders_as_str
        return orders

    async def submit_orders(self, orders: List[omorder.Order]) -> None:
        """
        Submit `orders` to the broker and confirm receipt.

        :param orders: list of orders to execute
        """
        # Submit orders.
        if orders:
            broker = self._portfolio.broker
            _LOG.debug("Event: awaiting broker.submit_orders()...")
            await broker.submit_orders(orders)
            _LOG.debug("Event: awaiting broker.submit_orders() done.")
        else:
            _LOG.debug("No orders to submit to broker.")
        # Log the state of Portfolio.
        if self._log_dir:
            self.log_state()
            self._portfolio.log_state(os.path.join(self._log_dir, "portfolio"))

    # /////////////////////////////////////////////////////////////////////////////

    def _compute_target_positions_in_shares(
        self,
        predictions: pd.Series,
        volatility: pd.Series,
        spread: pd.Series,
    ) -> pd.DataFrame:
        """
        Compute target holdings in shares.

        :param predictions: predictions indexed by `asset_id`
        :param volatility: volatility forecasts indexed by `asset_id`
        :param spread: spread forecasts indexed by `asset_id`
        """
        assets_and_predictions = self._prepare_data_for_optimizer(
            predictions, volatility, spread
        )
        hdbg.dassert_not_in(
            self._portfolio.CASH_ID, assets_and_predictions["asset_id"].to_list()
        )
        # Compute the target positions in cash (call the optimizer).
        # TODO(Paul): Align with ForecastEvaluator and update callers.
        # compute_target_positions_func
        # compute_target_positions_kwargs
        backend = self._optimizer_config["backend"]
        if backend == "pomo":
            style = self._optimizer_config["params"]["style"]
            kwargs = self._optimizer_config["params"]["kwargs"]
            df = ocalopti.compute_target_positions_in_cash(
                assets_and_predictions,
                style=style,
                **kwargs,
            )
        elif backend == "batch_optimizer":
            import optimizer.single_period_optimization as osipeopt

            spo = osipeopt.SinglePeriodOptimizer(
                self._optimizer_config,
                assets_and_predictions,
                restrictions=self._restrictions,
            )
            df = spo.optimize()
            _LOG.debug("df=\n%s", hpandas.df_to_str(df))
            df = df.merge(
                assets_and_predictions.set_index("asset_id")[
                    ["price", "curr_num_shares"]
                ],
                how="outer",
                left_index=True,
                right_index=True,
            )
        elif backend == "dind_optimizer":
            # Call docker optimizer stub.
            raise NotImplementedError
        elif backend == "service_optimizer":
            raise NotImplementedError
        else:
            raise ValueError("Unsupported `backend`=%s", backend)
        # Convert the target positions from cash values to target share counts.
        # Round to nearest integer towards zero.
        # df["diff_num_shares"] = np.fix(df["target_trade"] / df["price"])
        diff_num_shares = df["target_notional_trade"] / df["price"]
        diff_num_shares.replace([-np.inf, np.inf], np.nan, inplace=True)
        diff_num_shares = diff_num_shares.fillna(0)
        df["diff_num_shares"] = diff_num_shares
        df["spread"] = assets_and_predictions.set_index("asset_id")["spread"]
        _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        return df

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
        hdbg.dassert(
            predictions.index.equals(volatility.index),
            "`predictions` and `volatility` have mismatched indices of asset ids",
        )
        marked_to_market = self._get_extended_marked_to_market_df(predictions)
        # Combine the portfolio `marked_to_market` dataframe with the predictions.
        df_for_optimizer = self._merge_predictions(
            marked_to_market, predictions, volatility, spread
        )
        cash_id_filter = df_for_optimizer["asset_id"] == self._portfolio.CASH_ID
        df_for_optimizer.rename(columns={"value": "position"}, inplace=True)
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
        marked_to_market = self._portfolio.mark_to_market().set_index("asset_id")
        # If there are predictions for assets not currently in `marked_to_market`,
        # then attempt to price those assets and extend `marked_to_market`
        # (imputing 0's for the holdings).
        unpriced_assets = predictions.index.difference(marked_to_market.index)
        if not unpriced_assets.empty:
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
            marked_to_market = pd.concat(
                [marked_to_market, mtm_extension], axis=0
            )
        marked_to_market.reset_index(inplace=True)
        _LOG.debug(
            "marked_to_market dataframe=\n%s"
            % hpandas.df_to_str(marked_to_market)
        )
        return marked_to_market

    def _normalize_series(
        self,
        series: pd.Series,
        index: pd.DatetimeIndex,
        imputation: str,
        name: str,
    ) -> pd.DataFrame:
        """
        Normalize series with `index`, NaN-filling, and df conversion.
        """
        hdbg.dassert_isinstance(series, pd.Series)
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
        if imputation == "zero":
            series = series.fillna(0.0)
        elif imputation == "mean":
            series_mean = series.mean()
            series = series.fillna(series_mean)
        else:
            raise ValueError("Invalid imputation mode")
        # Convert to a dataframe.
        df = pd.DataFrame(series)
        # Format the predictions dataframe.
        df.columns = [name]
        df.index.name = "asset_id"
        df = df.reset_index()
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
            `curr_num_shares`, `value`.
            - The dataframe is the outer join of all the held assets in `portfolio` and
              `predictions`
        """
        # `predictions` and `volatility` should have exactly the same index.
        hdbg.dassert(predictions.index.equals(volatility.index))
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
        _LOG.debug(
            "Number of NaNs in `curr_num_shares` post-merge=`%i`",
            merged_df["curr_num_shares"].isna().sum(),
        )
        merged_df = merged_df.convert_dtypes()
        merged_df = merged_df.fillna(0.0)
        _LOG.debug("After merge: merged_df=\n%s", hpandas.df_to_str(merged_df))
        return merged_df

    def _generate_orders(
        self,
        shares_df: pd.DataFrame,
        order_config: Dict[str, Any],
    ) -> List[omorder.Order]:
        """
        Turn a series of asset_id / shares to trade into a list of orders.

        :param shares_df: dataframe indexed by `asset_id`. Contains columns
            `curr_num_shares` and `diff_num_shares`. May contain zero rows.
        :param order_config: common parameters used to initialize `Order`
        :return: a list of nontrivial orders (i.e., no zero-share orders)
        """
        _LOG.debug("# Generate orders")
        hdbg.dassert_is_subset(
            ("curr_num_shares", "diff_num_shares"), shares_df.columns
        )
        orders: List[omorder.Order] = []
        for asset_id, shares_row in shares_df.iterrows():
            curr_num_shares = shares_row["curr_num_shares"]
            diff_num_shares = shares_row["diff_num_shares"]
            hdbg.dassert(
                np.isfinite(curr_num_shares),
                "The curr_num_share value must be finite.",
            )
            if not np.isfinite(diff_num_shares):
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
            order = omorder.Order(
                asset_id=asset_id,
                curr_num_shares=curr_num_shares,
                diff_num_shares=diff_num_shares,
                **order_config.to_dict(),
            )
            _LOG.debug("order=%s", order.order_id)
            orders.append(order)
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


# #############################################################################


def _validate_order_config(config: cconfig.Config) -> None:
    hdbg.dassert_isinstance(config, cconfig.Config)
    order_type_type = str
    order_type = cconfig.get_object_from_config(
        config, "order_type", order_type_type, None
    )
    hdbg.dassert_isinstance(order_type, order_type_type)
    order_duration_in_mins_type = int
    order_duration_in_mins = cconfig.get_object_from_config(
        config, "order_duration_in_mins", order_duration_in_mins_type, None
    )
    # TODO(gp): is_subclass because it can be a float or int?
    hdbg.dassert_issubclass(order_duration_in_mins, order_duration_in_mins_type)


def _validate_optimizer_config(config: cconfig.Config) -> None:
    hdbg.dassert_isinstance(config, cconfig.Config)
    backend_type = str
    backend = cconfig.get_object_from_config(
        config, "backend", backend_type, None
    )
    hdbg.dassert_issubclass(backend, backend_type)
    # target_gmv_type = float
    # target_gmv = cconfig.get_object_from_config(
    #     config, "target_gmv", target_gmv_type, None
    # )
    # hdbg.dassert_issubclass(target_gmv, target_gmv_type)
