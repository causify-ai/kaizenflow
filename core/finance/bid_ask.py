"""
Import as:

import core.finance.bid_ask as cfibiask
"""
import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


def process_bid_ask(
    df: pd.DataFrame,
    bid_col: str,
    ask_col: str,
    bid_volume_col: str,
    ask_volume_col: str,
    *,
    requested_cols: Optional[List[str]] = None,
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Process top-of-book bid/ask quotes.

    :param df: dataframe with columns for top-of-book bid/ask info
    :param bid_col: bid price column
    :param ask_col: ask price column
    :param bid_volume_col: column with quoted volume at bid
    :param ask_volume_col: column with quoted volume at ask
    :param requested_cols: the requested output columns; `None` returns all
        available.
    :param join_output_with_input: whether to only return the requested columns
        or to join the requested columns to the input dataframe
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_in(bid_col, df.columns)
    hdbg.dassert_in(ask_col, df.columns)
    hdbg.dassert_in(bid_volume_col, df.columns)
    hdbg.dassert_in(ask_volume_col, df.columns)
    #
    if df.columns.nlevels == 1:
        # Single level column.
        if (df[bid_col] >= df[ask_col]).any().any():
            _LOG.warning("Some bid values are above ask values.")
    elif df.columns.nlevels == 2:
        # Multiindex df.
        if (df[bid_col] >= df[ask_col]).any().any():
            _LOG.warning("Some bid values are above ask values.")
    else:
        raise ValueError("DataFrame type not supported:\n%s", df.head(3))
    supported_cols = [
        "mid",
        "geometric_mid",
        "quoted_spread",
        "relative_spread",
        "log_relative_spread",
        "weighted_mid",
        # These imbalances are with respect to shares.
        "order_book_imbalance",
        "centered_order_book_imbalance",
        "log_order_book_imbalance",
        # TODO: use `notional` instead of `value`.
        "bid_value",
        "ask_value",
        "mid_value",
    ]
    requested_cols = requested_cols or supported_cols
    hdbg.dassert_is_subset(
        requested_cols,
        supported_cols,
        "The available columns to request are %s",
        supported_cols,
    )
    hdbg.dassert(requested_cols)
    requested_cols = set(requested_cols)
    #
    results: Dict[str, Union[pd.Series, pd.DataFrame]] = {}
    #
    # A helper function to add the feature Series to all results.
    def _append_feature_srs(
        tag: str, srs: Union[pd.Series, pd.DataFrame]
    ) -> None:
        """
        Assert result type and append to general results.
        """
        hdbg.dassert_isinstance(tag, str)
        hdbg.dassert_isinstance(srs, (pd.Series, pd.DataFrame))
        hdbg.dassert_not_in(tag, results.keys())
        results[tag] = srs

    #
    for tag in requested_cols:
        if tag == "mid":
            # (bid + ask) / 2.
            srs = (df[bid_col] + df[ask_col]) / 2
        if tag == "geometric_mid":
            # sqrt(bid * ask).
            srs = np.sqrt(df[bid_col] * df[ask_col])
        if tag == "quoted_spread":
            # bid - ask.
            srs = df[ask_col] - df[bid_col]
        if tag == "relative_spread":
            # 2*(ask - bid) / (ask + bid).
            srs = 2 * (df[ask_col] - df[bid_col]) / (df[ask_col] + df[bid_col])
        if tag == "log_relative_spread":
            # log(ask) - log(bid).
            srs = np.log(df[ask_col]) - np.log(df[bid_col])
        if tag == "weighted_mid":
            # bid * ask_volume + ask * bid_volume.
            srs = (
                df[bid_col] * df[ask_volume_col]
                + df[ask_col] * df[bid_volume_col]
            ) / (df[ask_volume_col] + df[bid_volume_col])
        if tag == "order_book_imbalance":
            # bid_volume / (bid_volume + ask_volume).
            srs = df[bid_volume_col] / (df[bid_volume_col] + df[ask_volume_col])
        if tag == "centered_order_book_imbalance":
            # (bid_volume - ask_volume) / (bid_volume + ask_volume).
            srs = (df[bid_volume_col] - df[ask_volume_col]) / (
                df[bid_volume_col] + df[ask_volume_col]
            )
        if tag == "log_order_book_imbalance":
            # log(bid_volume) - log(ask_volume).
            srs = np.log(df[bid_volume_col]) - np.log(df[ask_volume_col])
        if tag == "bid_value":
            # bid * bid_volume.
            srs = df[bid_col] * df[bid_volume_col]
        if tag == "ask_value":
            # ask * ask_volume.
            srs = df[ask_col] * df[ask_volume_col]
        if tag == "mid_value":
            # (bid * bid_volume + ask * ask_volume) / 2.
            srs = (
                df[bid_col] * df[bid_volume_col]
                + df[ask_col] * df[ask_volume_col]
            ) / 2
        # Add to general results.
        _append_feature_srs(tag, srs)
    out_df = pd.concat(results.values(), keys=results.keys(), axis=1)
    # TODO(gp): Maybe factor out this in a `_maybe_join_output_with_input` since
    #  it seems a common idiom.
    if join_output_with_input:
        out_df = out_df.merge(df, left_index=True, right_index=True, how="outer")
        hdbg.dassert(not out_df.columns.has_duplicates)
    return out_df


# TODO(Juraj): the function name should be more clear, i.e.,
# transform_bid_ask_long_to_wide.
def transform_bid_ask_long_data_to_wide(
    df: pd.DataFrame,
    timestamp_col: str,
    *,
    bid_prefix: str = "bid_",
    ask_prefix: str = "ask_",
) -> pd.DataFrame:
    """
    Transform bid-ask data with multiple levels from a long form to a wide
    form.

                                        knowledge_timestamp    level  bid_price
        timestamp
        2022-09-08 21:01:00+00:00 2022-09-08 21:01:15+00:00        1       2.31
        2022-09-08 21:01:00+00:00 2022-09-08 21:01:15+00:00        2       3.22
        2022-09-08 21:01:00+00:00 2022-09-08 21:01:15+00:00        3       2.33

    to:
                                        knowledge_timestamp  bid_price_l1  bid_price_l2  bid_price_3
        timestamp
        2022-09-08 21:01:00+00:00 2022-09-08 21:01:15+00:00         2.31         3.22         2.33
    """
    _LOG.debug(hprint.to_str("timestamp_col bid_prefix ask_prefix"))
    hdbg.dassert_in(timestamp_col, df.reset_index().columns)
    df = df.reset_index()
    # Specify bid-ask and non-bid-ask columns.
    bid_ask_cols = [
        col
        for col in df.columns
        if col.startswith(bid_prefix) or col.startswith(ask_prefix)
    ]
    # Index of pivoted data shouldn't also contain `level` (used as columns) and `id` (creates duplicates).
    non_bid_ask_cols = [
        col for col in df.columns if col not in bid_ask_cols + ["level", "id"]
    ]
    # TODO(Max): Create an assertion that all values for levels are identical,
    # so we are merging the rows without duplicates (i.e., "knowledge_timestamp" and "end_download_timestamp").
    # Merge `level` into bid-ask values (e.g., bid_price_1, bid_price_2, etc.).
    pivoted_data = df.pivot(
        index=non_bid_ask_cols,
        columns=["level"],
        values=bid_ask_cols,
    )
    # Rename the columns to a desired {value}_{level} format.
    pivoted_data.columns = pivoted_data.columns.map("{0[0]}_l{0[1]}".format)
    # Fix indices.
    df = pivoted_data.reset_index()
    df = df.set_index(timestamp_col)
    return df
