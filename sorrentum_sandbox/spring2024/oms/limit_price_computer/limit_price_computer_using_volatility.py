"""
Import as:

import oms.limit_price_computer.limit_price_computer_using_volatility as olpclpcuv
"""
import logging
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import oms.limit_price_computer.limit_price_computer as olpclprco

_LOG = logging.getLogger(__name__)


class LimitPriceComputerUsingVolatility(olpclprco.AbstractLimitPriceComputer):
    def __init__(
        self,
        volatility_multiple: Union[float, List[float]],
        # TODO(Paul): Add a lookback parameter,
    ) -> None:
        """
        Init.

        :param volatility_multiple: control limit order placement from bid/ask
            in terms of multiples of bid/ask volatility.

            The multiplier can be a `float` if it's constant among all orders
            submitted with this price computer, or a list if the multiplier
            changes from wave to wave. In the latter case, every element of the
            list corresponds to a wave based on index, e.g. for 5 child order
            waves: `volatility_multiple = [0.25, 0.5, 1, 1.5, 2]`, element with
            idx=0 represents the multiple for the `wave_id=0`, with `idx=1` for
            `wave_id=1`, etc.
        """
        super().__init__()
        self._volatility_multiple = volatility_multiple

    def compute_metrics_from_price_data(
        self, price_data: pd.Series
    ) -> Tuple[float, float, float, int]:
        """
        Analyzes bid-ask price data to compute volume, sum of squares of diff,
        last price, count.

        :param price_data: bid/ask price data series
        :return: tuple of volume, diff of sum of squares, last price and
            count
        """
        # Get top-of-book price and compute sum-of-squares of diffs and count.
        tob_diff = price_data.diff()
        diff_ssq = (tob_diff**2).sum()
        count = tob_diff.count()
        # TODO(Paul): Adjust vols for the lookback/execution window
        vol = np.sqrt(diff_ssq / count)
        # Get latest bid/ask prices.
        last = price_data.iloc[-1]
        return vol, diff_ssq, last, count

    def calculate_limit_price(
        self,
        bid_ask_data: pd.DataFrame,
        side: str,
        price_precision: int,
        execution_freq: str,
        wave_id: int,
    ) -> Dict[str, float]:
        """
        Calculate limit price based on recent bid / ask data.

        See `AbstractLimitPriceComputer` for param description.

        :return: limit price and price data such as volume, last price.
            Example of output schema :
            ```
            {
                'ask_vol': float,
                'bid_vol': float,
                'last_ask': float,
                'last_bid': float,
                'limit_price': float,
                'total_vol': float,
                'volatility_multiple': float,
                'exchange_timestamp': pd.Timestamp,
                'knowledge_timestamp': pd.Timestamp,
                'end_download_timestamp': pd.Timestamp,
            }
            ```
        """
        # Verify the execution frequency is provided in the correct format.
        hdbg.dassert_isinstance(execution_freq, pd.Timedelta)
        bid_ask_price_data = self.normalize_bid_ask_data(bid_ask_data)
        # Initialize price dictionary.
        price_dict: Dict[str, Any] = {}
        # Assign the volatility multiple for the current wave.
        if isinstance(self._volatility_multiple, list):
            # If the volatility multiple is a list, get the value corresponding
            # to the current wave_id.
            hdbg.dassert_lt(wave_id, len(self._volatility_multiple))
            volatility_multiple = self._volatility_multiple[wave_id]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(hprint.to_str("wave_id volatility_multiple"))
        else:
            # If it's constant, use the constant value.
            hdbg.dassert_isinstance(self._volatility_multiple, float)
            volatility_multiple = self._volatility_multiple
        # TODO(Paul): Consider whether we want to allow
        #  `volatility_multiple < 0` for placing orders inside the spread or
        #  for effective market orders.
        hdbg.dassert_lte(0, volatility_multiple)
        price_dict["volatility_multiple"] = volatility_multiple
        price_dict["wave_id"] = wave_id
        # Retrieve the timestamp data related to the latest prices.
        timestamp_cols = ["end_download_timestamp", "knowledge_timestamp"]
        price_timestamp_dict = self.get_latest_timestamps_from_bid_ask_data(
            bid_ask_price_data[timestamp_cols]
        )
        price_dict.update(price_timestamp_dict)
        # Get bid/ask size data.
        size_dict = self.get_latest_size_from_bid_ask_data(bid_ask_data)
        price_dict.update(size_dict)
        # Resample the bid/ask data.
        bid_ask_price_data = bid_ask_price_data.resample("100ms").last().ffill()
        price_dict["num_data_points_resampled"] = bid_ask_price_data.shape[0]
        # Get bid price volume, sum of square and latest data.
        (
            bid_vol,
            bid_diff_ssq,
            last_bid,
            bid_count,
        ) = self.compute_metrics_from_price_data(
            bid_ask_price_data["bid_price_l1"]
        )
        # Calculate the scaling multiplier.
        # We take 5 snapshots per second and upsample to double the frequency.
        # Hence the hardcoded value.
        samples_per_second = 10
        # Convert execution frequency to seconds.
        execution_freq = execution_freq.seconds
        scaling_multiplier = np.sqrt(execution_freq * samples_per_second)
        price_dict["scaling_multiplier"] = scaling_multiplier
        # Apply the scaling multiplier to bid and ask volatility.
        bid_vol = bid_vol * scaling_multiplier
        price_dict["bid_vol"] = bid_vol
        price_dict["bid_vol_bps"] = 1e4 * bid_vol / last_bid
        price_dict["latest_bid_price"] = last_bid
        # Same as above but for ask price.
        (
            ask_vol,
            ask_diff_ssq,
            last_ask,
            ask_count,
        ) = self.compute_metrics_from_price_data(
            bid_ask_price_data["ask_price_l1"]
        )
        ask_vol = ask_vol * scaling_multiplier
        price_dict["ask_vol"] = ask_vol
        price_dict["ask_vol_bps"] = 1e4 * ask_vol / last_ask
        # Compute total vol using both bid and ask price movements.
        price_dict["ask_vol"] = ask_vol
        price_dict["latest_ask_price"] = last_ask
        # Compute vol using both bid and ask price movements.
        total_ssq = bid_diff_ssq + ask_diff_ssq
        total_count = bid_count + ask_count
        total_vol = np.sqrt(total_ssq / total_count)
        total_vol = total_vol * scaling_multiplier
        price_dict["total_vol"] = total_vol
        # Get last mid price.
        last_mid = (last_ask + last_bid) / 2
        price_dict["latest_mid_price"] = last_mid
        # Get total vol in bps.
        total_vol_bps = 1e4 * total_vol / last_mid
        price_dict["total_vol_bps"] = total_vol_bps
        # Calculate vol to spread ratio.
        spread = last_ask - last_bid
        price_dict["spread"] = spread
        spread_bps = 1e4 * spread / last_mid
        price_dict["spread_bps"] = spread_bps
        price_dict["total_vol_to_spread_bps"] = total_vol_bps / spread_bps
        # Adjust limit price based on volatility multiple.
        if side == "buy":
            limit_price = last_ask - total_vol * volatility_multiple
        elif side == "sell":
            limit_price = last_bid + total_vol * volatility_multiple
        else:
            raise ValueError(f"Invalid side='{side}'")
        limit_price_with_precison = np.round(limit_price, price_precision)
        if limit_price != limit_price_with_precison:
            _LOG.warning(
                "Limit price changed due to precision limit: "
                + hprint.to_str(
                    "limit_price_with_precison \
                        limit_price price_precision"
                )
            )
        price_dict["limit_price"] = limit_price_with_precison
        return price_dict
