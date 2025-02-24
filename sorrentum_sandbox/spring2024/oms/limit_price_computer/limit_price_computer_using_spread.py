"""
Import as:

import oms.limit_price_computer.limit_price_computer_using_spread as olpclpcus
"""
import logging
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import oms.limit_price_computer.limit_price_computer as olpclprco

_LOG = logging.getLogger(__name__)


class LimitPriceComputerUsingSpread(olpclprco.AbstractLimitPriceComputer):
    def __init__(
        self, passivity_factor: float, *, max_deviation: float = 0.01
    ) -> None:
        """
        :param passivity_factor: mid price factor to calculate limit price
        :param max_deviation: threshold to compare the average and latest prices,
            given as a value in range (0, 1) to express a percentage difference
        """
        self.passivity_factor = passivity_factor
        self.max_deviation = max_deviation

    def calculate_limit_price(
        self,
        bid_ask_data: pd.DataFrame,
        side: str,
        price_precision: int,
        execution_freq: pd.Timedelta,
        wave_id: int,
    ) -> Dict[str, Any]:
        """
        Calculate limit price based on recent bid / ask data.

        The limit price is adjusted using the passivity factor.
        The function returns a dict with:
        - calculated limit price;
        - latest bid/ask prices;
        - mean bid/ask prices in the given data;
        - passivity factor;
        - whether limit bid/ask prices are calculated using latest
            price or average price

        :param bid_ask_data: recent bid / ask data of a particular asset,
        :param side: "buy" or "sell"
        :param price_precision: sets the required decimal precision for limit price
        :return: limit price and price data
        """
        # Verify that the passivity factor is in [0,1].
        # TODO(Juraj): temporarily disable assertion.
        # hdbg.dassert_lgt(
        #    0,
        #    passivity_factor,
        #    1,
        #    lower_bound_closed=True,
        #    upper_bound_closed=True,
        # )
        # Note: execution frequency is currently not utilized
        # in spread-based price computation.
        _ = execution_freq
        bid_ask_price_data = self.normalize_bid_ask_data(bid_ask_data)
        # Initialize price dictionary.
        price_dict: Dict[str, Any] = {}
        price_dict["passivity_factor"] = self.passivity_factor
        # TODO(Danya): CmampTask6177.
        # Since spread is not used in current experiments, wave_id utilization
        # in spread-based limit price calculation is currently not implemented.
        price_dict["wave_id"] = wave_id
        # Define necessary columns.
        price_cols = ["bid_price_l1", "ask_price_l1"]
        timestamp_cols = ["end_download_timestamp", "knowledge_timestamp"]
        # Retrieve and compare latest and average prices.
        # The difference between these prices determines the reference
        # bid and ask prices to use further.
        (
            latest_avg_prices_info,
            bid_price,
            ask_price,
        ) = self._compare_latest_and_average_price(
            bid_ask_price_data[price_cols], self.max_deviation
        )
        price_dict.update(latest_avg_prices_info)
        # Retrieve size data for the latest prices.

        # Retrieve the timestamp data related to the latest prices.
        price_timestamp_dict = self.get_latest_timestamps_from_bid_ask_data(
            bid_ask_price_data[timestamp_cols]
        )
        price_dict.update(price_timestamp_dict)
        # Add size data.
        size_dict = self.get_latest_size_from_bid_ask_data(bid_ask_data)
        price_dict.update(size_dict)
        # Adjust limit price based on passivity factor.
        # - limit_price in [bid,ask];
        # - if side == "buy":
        #   - passivity == 1 -> limit_price = bid
        # - limit_price in [bid,ask];
        # - if side == "buy":
        #   - passivity == 1 -> limit_price = bid
        #   - passivity == 0 -> limit_price = ask
        # - if side == "sell":
        #   - passivity == 1 -> limit_price = ask
        #   - passivity == 0 -> limit_price = bid
        # - passivity_factor == 0.5 is a midpoint in both cases.
        if side == "buy":
            limit_price = (bid_price * self.passivity_factor) + (
                ask_price * (1 - self.passivity_factor)
            )
        elif side == "sell":
            limit_price = (ask_price * self.passivity_factor) + (
                bid_price * (1 - self.passivity_factor)
            )
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

    @staticmethod
    def _compare_latest_and_average_price(
        bid_ask_price_data: pd.DataFrame, max_deviation: float
    ) -> Tuple[Dict[str, float], float, float]:
        """
        Retrieve and compare latest and average bid/ask prices.

        If the latest price deviates from the average price by more than
        `max_deviation`, the average price is used as reference to calculate
        the limit price downstream; otherwise, the latest price is used.

        :param bid_ask_price_data: bid/ask prices for a certain asset
        :return:
            - information about the latest and average bid/ask prices
            - reference bid price
            - reference ask price
        """
        # Verify that the maximum deviation is in (0, 1).
        hdbg.dassert_lgt(
            0,
            max_deviation,
            1,
            lower_bound_closed=False,
            upper_bound_closed=False,
        )
        # Get the latest bid/ask price and their timestamp.
        bid_price_latest, ask_price_latest = bid_ask_price_data.iloc[-1]
        # Get the average bid/ask prices over the period.
        bid_price_mean, ask_price_mean = bid_ask_price_data.mean()
        #
        out_data = {
            "latest_bid_price": bid_price_latest,
            "latest_ask_price": ask_price_latest,
            "bid_price_mean": bid_price_mean,
            "ask_price_mean": ask_price_mean,
        }
        # Compare the prices using the `max_deviation` threshold.
        # Determine reference bid price.
        if (
            abs((bid_price_latest - bid_price_mean) / bid_price_latest)
            > max_deviation
        ):
            bid_price = bid_price_mean
            out_data["used_bid_price"] = "bid_price_mean"
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Latest price differs more than %s percent from average price: %s",
                    max_deviation * 100,
                    hprint.to_str("bid_price_latest bid_price_mean"),
                )
        else:
            bid_price = bid_price_latest
            out_data["used_bid_price"] = "latest_bid_price"
        # Determine reference ask price.
        if (
            abs((ask_price_latest - ask_price_mean) / ask_price_latest)
            > max_deviation
        ):
            ask_price = ask_price_mean
            out_data["used_ask_price"] = "ask_price_mean"
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Latest price differs more than %s percent from average price: %s",
                    max_deviation * 100,
                    hprint.to_str("ask_price_latest ask_price_mean"),
                )
        else:
            ask_price = ask_price_latest
            out_data["used_ask_price"] = "latest_ask_price"
        return out_data, bid_price, ask_price
