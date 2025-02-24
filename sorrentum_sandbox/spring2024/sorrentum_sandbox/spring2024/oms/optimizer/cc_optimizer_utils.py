"""
Import as:

import oms.optimizer.cc_optimizer_utils as ooccoput
"""

import logging
from typing import Any, Dict

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import oms.broker.broker as obrobrok

_LOG = logging.getLogger(__name__)


def _apply_cc_limits(
    order: pd.Series,
    asset_market_info: Dict[str, Any],
    stage: str,
    round_mode: str,
) -> pd.Series:
    hdbg.dassert_isinstance(order, pd.Series)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Order before adjustments: %s", order)
    #
    min_amount = asset_market_info["min_amount"]
    price = order["price"]
    min_cost = asset_market_info["min_cost"]
    final_order_amount = order["target_trades_shares"]
    #
    if stage == "local":
        # Force minimum order amount for testnet.
        min_amount = min_cost * 3 / price
        # Apply back the sign.
        if final_order_amount < 0:
            final_order_amount = -min_amount
    elif stage in ["preprod", "prod"]:
        # 1) Set the target number of shares to 0 if the order's number of
        # shares is below the minimum required.
        if abs(final_order_amount) < min_amount:
            _LOG.warning(
                "Order: %s\nAmount of asset in order = %s is below minimal value = %s. "
                + "Setting the target number of shares to 0.",
                str(order),
                abs(final_order_amount),
                min_amount,
            )
            final_order_amount = 0.0
        # 2) Set the target number of shares to 0 if the order's notional value
        # is below the minimal cost.
        # We estimate the total value of the order using the order's `price`.
        total_cost = price * abs(order["target_trades_shares"])
        if total_cost <= min_cost:
            _LOG.warning(
                "Order: %s\nNotional value of asset in order = %s is below minimal value = %s. "
                + "Setting the target number of shares to 0.",
                str(order),
                total_cost,
                min_cost,
            )
            final_order_amount = 0.0
    else:
        raise ValueError(f"Unsupported stage={stage}")
    hdbg.dassert_isinstance(final_order_amount, float)
    if final_order_amount != 0:
        # 3) Round the order amount in accordance with exchange rules.
        amount_precision = asset_market_info["amount_precision"]
        rounded_order_amount = round(final_order_amount, amount_precision)
        if round_mode == "round":
            # Round the number.
            final_order_amount = rounded_order_amount
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Rounding order amount to %s decimal points. Result: %s",
                    amount_precision,
                    final_order_amount,
                )
        elif round_mode == "check":
            # Check that the number of digits is the correct one according
            # to exchange rules.
            hdbg.dassert_eq(final_order_amount, rounded_order_amount)
        else:
            raise ValueError(f"Unsupported round_mode={round_mode}")
    else:
        # 3) In case of no trades keep holdings unchanged.
        order["target_holdings_notional"] = order["holdings_notional"]
        order["target_holdings_shares"] = order["holdings_shares"]
        # No trades in shares implies no trades notional.
        order["target_trades_notional"] = 0.0
    #
    order["target_trades_shares"] = final_order_amount
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Order after adjustments: %s", order)
    return order


def apply_cc_limits(
    forecast_df: pd.DataFrame, broker: obrobrok.Broker, round_mode: str
) -> pd.DataFrame:
    """
    Apply notional limits for DataFrame of multiple orders.

    If target trades absolute values are below the exchange limits:
        - target trades (shares and notional) are set to 0
        - holdings (shares and notional) remain unchanged
          (i.e. target holdings = current holdings)

    :param forecast_df: DataFrame with forecasts, e.g.
        ```
                    holdings_shares     price  holdings_notional             wall_clock_timestamp  prediction  volatility  spread  target_holdings_notional  target_trades_notional  target_trades_shares  target_holdings_shares
        asset_id
        6051632686                0    4.1756                  0 2022-11-28 14:26:43.876138-05:00   -0.103183    0.002433       0                    4.1756                  4.1756                   1.0                     1.0
        8717633868                0   12.3396                  0 2022-11-28 14:26:43.876138-05:00   -0.597408    0.001374       0                  -12.3396                -12.3396                  -1.0                    -1.0
        2540896331                0    6.5356                  0 2022-11-28 14:26:43.876138-05:00   -0.561495    0.000781       0                  -52.2848                -52.2848                  -8.0                    -1.0
        ```
    :param broker: Broker class instance
    :param round_mode: shares rounding mode
        "round": round the amount of shares according to the exchange rules
        "check": check with an assertion whether target shares are rounded or not
    :return: DataFrame with updated orders
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Order df before adjustments: forecast_df=\n%s",
            hpandas.df_to_str(forecast_df, num_rows=None),
        )
    hdbg.dassert_in("target_trades_shares", forecast_df.columns)
    stage = broker.stage
    hdbg.dassert_in(stage, ["local", "prod", "preprod"])
    market_info = broker.market_info
    #
    # Save shares before limits application.
    forecast_df["target_holdings_shares.before_apply_cc_limits"] = forecast_df[
        "target_holdings_shares"
    ]
    forecast_df["target_holdings_notional.before_apply_cc_limits"] = forecast_df[
        "target_holdings_notional"
    ]
    forecast_df["target_trades_shares.before_apply_cc_limits"] = forecast_df[
        "target_trades_shares"
    ]
    forecast_df["target_trades_notional.before_apply_cc_limits"] = forecast_df[
        "target_trades_notional"
    ]
    forecast_df_tmp = []
    # Apply exchange restrictions to individual orders.
    for idx, row in forecast_df.iterrows():
        row_tmp = _apply_cc_limits(row, market_info[idx], stage, round_mode)
        forecast_df_tmp.append(row_tmp)
    # Combine orders into one dataframe.
    forecast_df_tmp = pd.concat(forecast_df_tmp, axis=1).T
    forecast_df_tmp.index.name = forecast_df.index.name
    hdbg.dassert_eq(str(forecast_df.shape), str(forecast_df_tmp.shape))
    forecast_df = forecast_df_tmp
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Order df after adjustments: forecast_df=\n%s",
            hpandas.df_to_str(forecast_df, num_rows=None),
        )
    return forecast_df
