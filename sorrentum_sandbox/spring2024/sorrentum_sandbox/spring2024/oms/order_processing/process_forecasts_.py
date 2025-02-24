"""
Import as:

import oms.order_processing.process_forecasts_ as oopprfo
"""

import asyncio
import datetime
import logging
from typing import Any, Dict, Optional

import pandas as pd
from tqdm.autonotebook import tqdm

import core.finance as cofinanc
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hdict as hdict
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.htqdm as htqdm
import helpers.hwall_clock_time as hwacltim
import oms.order_processing.target_position_and_order_generator as ooptpaog
import oms.portfolio.portfolio as oporport

_LOG = logging.getLogger(__name__)


# `ProcessForecastsNode`
# - Adapts `process_forecasts()` to a DataFlow node
# `process_forecasts()`
# - Contains the loop processing the predictions
# - Instantiates `TargetPositionAndOrderGenerator` to do the actual work every bar


# - `wake_up_timestamp`:
#   - used by `DagRunner`
#   - when the system starts processing the DagRunner loop
#   - E.g., the system can wake up at 9:00am to warm up some functions
#
# - `time_out_in_secs`:
#   - used by `DagRunner`
#   - when the system stops running the DagRunner loop
#
# - `ath_start_time`, `ath_end_time`:
#   - used by `process_forecasts()`
#   - describe when the market is open
#   - right now it's used but in a redundant way with `trading_start_time`
#   - we want to snapshot the Portfolio during all the ATH
#
# - `trading_start_time`, `trading_end_time`
#   - used by `process_forecasts()`
#   - we use it to filter the forecasts reaching the Optimizer when the system is
#     producing forecasts
#
# Invariant: `ath_{start,end}_time` and `trading_{start,end}_time` are inclusive
# so that we can use the usual times like 9:30 and 16:00 as boundaries of ATH
# interval.


async def process_forecasts(
    prediction_df: pd.DataFrame,
    volatility_df: pd.DataFrame,
    portfolio: oporport.Portfolio,
    # TODO(gp): It should be a dict -> config_dict, process_forecasts_dict. Do
    #  we need to use a bit of stuttering to make the name unique in the config?
    config: Dict[str, Any],
    # TODO(gp): Should we keep all the dfs close together in the interface?
    *,
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
            # - Force liquidating the holdings in the bar that corresponds to
            #   trading_end_time, which must be not None.
            "liquidate_at_trading_end_time": bool
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
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("\n%s", hprint.frame("process_forecast"))
        _LOG.debug("prediction_df=\n%s", hpandas.df_to_str(prediction_df))
        _LOG.debug("volatility_df=\n%s", hpandas.df_to_str(volatility_df))
        _LOG.debug("portfolio=\n%s", portfolio)
        _LOG.debug("config=\n%s", config)
    #
    # 1) Check the validity of the inputs.
    #
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
    hdbg.dassert_isinstance(portfolio, oporport.Portfolio)
    hdbg.dassert_isinstance(config, dict)
    # Check `restrictions`.
    if restrictions_df is None:
        _LOG.info("restrictions_df is `None`; no restrictions will be enforced")
    #
    # 2) Extract the relevant parameters from `config`.
    #
    # See https://stackoverflow.com/questions/21706609/where-is-the-nonetype-located
    NoneType = type(None)
    # Create an `order_dict` from `config` elements.
    order_dict = hdict.typed_get(
        config, "order_config", expected_type=(dict, NoneType)
    )
    optimizer_dict = hdict.typed_get(
        config, "optimizer_config", expected_type=(dict, NoneType)
    )
    # Extract ATH and trading start times from config.
    ath_start_time = hdict.typed_get(
        config, "ath_start_time", expected_type=(datetime.time, NoneType)
    )
    trading_start_time = hdict.typed_get(
        config, "trading_start_time", expected_type=(datetime.time, NoneType)
    )
    # Extract ATH and trading end times from config.
    ath_end_time = hdict.typed_get(
        config, "ath_end_time", expected_type=(datetime.time, NoneType)
    )
    trading_end_time = hdict.typed_get(
        config, "trading_end_time", expected_type=(datetime.time, NoneType)
    )
    liquidate_at_trading_end_time = hdict.typed_get(
        config,
        "liquidate_at_trading_end_time",
        expected_type=bool,
    )
    share_quantization = hdict.typed_get(
        config,
        "share_quantization",
        expected_type=(int, NoneType),
    )
    # Sanity check trading time.
    _validate_trading_time(
        ath_start_time,
        ath_end_time,
        trading_start_time,
        trading_end_time,
        liquidate_at_trading_end_time,
    )
    # Get execution mode ("real_time" or "batch").
    execution_mode = hdict.typed_get(config, "execution_mode", expected_type=str)
    # Get log dir.
    log_dir = config.get("log_dir", None)
    _LOG.info("log_dir=%s", log_dir)
    #
    # 3) Process the predictions.
    #
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
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "predictions_df=%s\n%s",
            str(prediction_df.shape),
            hpandas.df_to_str(prediction_df),
        )
        _LOG.debug("predictions_df.index=%s", str(prediction_df.index))
    num_rows = len(prediction_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Number of rows in `prediction_df`=%d", num_rows)
    #
    get_wall_clock_time = portfolio.market_data.get_wall_clock_time
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    iter_ = enumerate(prediction_df.iterrows())
    offset_min = pd.DateOffset(minutes=order_dict["order_duration_in_mins"])
    # Initialize a `TargetPositionAndOrderGenerator` object to perform the heavy
    # lifting.
    target_position_and_order_generator = (
        ooptpaog.TargetPositionAndOrderGenerator(
            portfolio,
            order_dict,
            optimizer_dict,
            restrictions_df,
            share_quantization,
            log_dir=log_dir,
        )
    )
    if execution_mode == "batch":
        # In "batch" mode this function is in charge of advancing the bar.
        hwacltim.reset_current_bar_timestamp()
    # `timestamp` is the time when the forecast is available and in the current
    #  setup is also when the order should begin.
    for idx, (timestamp, predictions) in tqdm(
        iter_, total=num_rows, file=tqdm_out
    ):
        # Assert if there are NaNs in `predictions`.
        hdbg.dassert_eq(0, predictions.isna().sum())
        if execution_mode == "batch":
            # Update the global state tracking the current bar.
            # The loop in `RealTimeDagRunner` sets the bar based on align_on_grid.
            # If we are running `run_process_forecasts.py`
            hwacltim.set_current_bar_timestamp(timestamp)
        #
        current_bar_timestamp = hwacltim.get_current_bar_timestamp()
        hdbg.dassert_is_not(current_bar_timestamp, None)
        # Avoid situations when a prediction timestamp is greater than the
        # current bar. E.g., the prediction timestamp is 08:05 while the
        # current bar is 08:00.
        hdbg.dassert_lte(timestamp, current_bar_timestamp)
        current_bar_time = current_bar_timestamp.time()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "\n%s",
                hprint.frame(
                    "# idx=%s timestamp=%s current_bar_time=%s"
                    % (idx, timestamp, current_bar_time)
                ),
            )
        # Wait until get_wall_clock_time() == timestamp.
        if get_wall_clock_time() > timestamp:
            # E.g., it's 10:21:51, we computed the forecast for [10:20, 10:25]
            # bar. As long as it's before 10:25, we want to place the order. If
            # it's later, either assert or log it as a problem.
            hdbg.dassert_lte(get_wall_clock_time(), timestamp + offset_min)
        else:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("async_wait_until")
            await hasynci.async_wait_until(timestamp, get_wall_clock_time)
        # Get the wall clock timestamp.
        wall_clock_timestamp = get_wall_clock_time()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        # if execution_mode == "batch":
        #     if idx == len(predictions_df) - 1:
        #         # For the last timestamp we only need to mark to market, but not
        #         # post any more orders.
        #         continue
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Event: awaiting asyncio.sleep()...")
        # TODO(Grisha): check if the System needs to go to sleep at all.
        # Wait a bit to give all open orders sufficient time to close.
        await asyncio.sleep(0.1)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Event: awaiting asyncio.sleep() done.")
        skip_generating_orders = _skip_generating_orders(
            current_bar_time,
            ath_start_time,
            ath_end_time,
            trading_start_time,
            trading_end_time,
        )
        # 1) Compute the target positions.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "\n%s",
                hprint.frame(
                    "1) Computing target positions: timestamp=%s current_bar_time=%s"
                    % (get_wall_clock_time(), current_bar_time),
                    char1="#",
                ),
            )
        if skip_generating_orders:
            _LOG.warning("Skipping generating orders")
            # Keep logging the state and marking to market even if we don't submit
            # orders.
            # We need to force to mark to market since usually
            # `target_position_and_order_generator.submit_orders()` takes care of
            # logging and
            # `target_position_and_order_generator.compute_target_positions_and_generate_orders()`
            # takes care of marking to market the portfolio.
            mark_to_market = True
            target_position_and_order_generator.log_state(mark_to_market)
            continue
        # TODO(gp): Use an FSM to make the code more reliable.
        # Compute whether to liquidate the holdings or not.
        liquidate_holdings = False
        if liquidate_at_trading_end_time:
            hdbg.dassert_is_not(trading_end_time, None)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "liquidate_at_trading_end_time: "
                    + hprint.to_str("trading_end_time current_bar_time")
                )
            if current_bar_time >= trading_end_time:
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug(
                        "Liquidating holdings: "
                        + hprint.to_str("trading_end_time current_bar_time")
                    )
                liquidate_holdings = True
        # Generate orders.
        volatility = volatility_df.loc[timestamp]
        spread = spread_df.loc[timestamp]
        orders = target_position_and_order_generator.compute_target_positions_and_generate_orders(
            predictions,
            volatility,
            spread,
            liquidate_holdings,
        )
        # 2) Submit orders.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "\n%s",
                hprint.frame(
                    "2) Submitting orders: timestamp=%s current_bar_time=%s"
                    % (get_wall_clock_time(), current_bar_time),
                    char1="#",
                ),
            )
        await target_position_and_order_generator.submit_orders(
            orders, **order_dict
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "TargetPositionAndOrderGenerator=\n%s",
                str(target_position_and_order_generator),
            )
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Event: exiting process_forecasts() for loop.")


# /////////////////////////////////////////////////////////////////////////////


def _validate_trading_time(
    ath_start_time: Optional[datetime.time],
    ath_end_time: Optional[datetime.time],
    trading_start_time: Optional[datetime.time],
    trading_end_time: Optional[datetime.time],
    liquidate_at_trading_end_time: bool,
) -> None:
    """
    Check that trading hours are specified correctly.
    """
    hdbg.dassert_all_defined_or_all_None(
        [ath_start_time, ath_end_time, trading_start_time, trading_end_time]
    )
    # TODO(gp): Not sure about this. For equities it's possible that we
    #  specify ath start/end time, but then we leave trading start/end time
    #  equal to None.
    if ath_start_time is not None:
        hdbg.dassert_lte(ath_start_time, ath_end_time)
        hdbg.dassert_lte(trading_start_time, trading_end_time)
        hdbg.dassert_lte(ath_start_time, trading_start_time)
        hdbg.dassert_lte(trading_end_time, ath_end_time)
    #
    if liquidate_at_trading_end_time:
        hdbg.dassert_is_not(trading_end_time, None)


def _skip_generating_orders(
    time: datetime.time,
    ath_start_time: Optional[datetime.time],
    ath_end_time: Optional[datetime.time],
    trading_start_time: Optional[datetime.time],
    trading_end_time: Optional[datetime.time],
) -> bool:
    """
    Determine whether to skip processing a bar or not.

    This decision is based on the current time and on the ATH / trading
    time limits.
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str(
                "time ath_start_time ath_end_time trading_start_time trading_end_time"
            )
        )
    # TODO(gp): Not sure about this.
    # Sanity check: all values are defined together or are all `None`.
    trading_time_list = [
        ath_start_time,
        ath_end_time,
        trading_start_time,
        trading_end_time,
    ]
    all_defined_cond = all(val is not None for val in trading_time_list)
    #
    skip_bar_cond = False
    if all_defined_cond:
        # Filter based on ATH.
        if time < ath_start_time:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "time=%s < ath_start_time=%s, skipping bar ...",
                    time,
                    ath_start_time,
                )
            skip_bar_cond = True
        if time > ath_end_time:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "time=%s > ath_end_time=%s, skipping bar ...",
                    time,
                    ath_end_time,
                )
            skip_bar_cond = True
        # Filter based on trading times.
        if time < trading_start_time:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "time=%s < trading_start_time=%s, skipping bar ...",
                    time,
                    trading_start_time,
                )
            skip_bar_cond = True
        if time > trading_end_time:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "time=%s > trading_end_time=%s, skipping bar ...",
                    time,
                    trading_end_time,
                )
            skip_bar_cond = True
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("skip_bar_cond"))
    return skip_bar_cond
