"""
Import as:

import core.finance.market_impact as cfimaimp
"""

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg


def estimate_market_order_price(
    df: pd.DataFrame,
    price_col: str,
    size_col: str,
) -> pd.DataFrame:
    """
    Estimate instantaneous price impact of a market order using book levels.

    :param df: dataframe of price/size book data indexed by depth
    :param price_col: name of price column
    :param size_col: name of size column
    :return: dataframe of market order impact information including
      - cumulative size up to level
      - cumulative volume up to level
      - mean price through level (assuming all size at level is executed)
      - price degradation in bps through level
    """
    # Perform data sanity checks.
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_in(price_col, df.columns)
    hdbg.dassert_in(size_col, df.columns)
    # Check that it is an integer index.
    hdbg.dassert_eq(df.index.dtype.type, np.int64)
    # Compute market impact-related quantities.
    cumulative_size = df[size_col].cumsum()
    notional = df[price_col] * df[size_col]
    cumulative_notional = notional.cumsum()
    mean_price_through_level = cumulative_notional / cumulative_size
    best_price = df[price_col][1]
    price_degradation_bps = (
        1e4 * abs(mean_price_through_level - best_price) / best_price
    )
    # Package results.
    result = {
        "price": df[price_col],
        "size": df[size_col],
        "notional": notional,
        "cumulative_size": cumulative_size,
        "cumulative_notional": cumulative_notional,
        "mean_price_through_level": mean_price_through_level,
        "price_degradation_bps": price_degradation_bps,
    }
    result_df = pd.concat(result, axis=1)
    return result_df
