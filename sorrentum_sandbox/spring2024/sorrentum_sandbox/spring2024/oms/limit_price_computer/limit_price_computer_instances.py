"""
Import as:

import oms.limit_price_computer.limit_price_computer_instances as olpclpcin
"""

from typing import Any, Dict

import oms.limit_price_computer.limit_price_computer as olpclprco
import oms.limit_price_computer.limit_price_computer_using_spread as olpclpcus
import oms.limit_price_computer.limit_price_computer_using_volatility as olpclpcuv


def get_LimitPriceComputer_instance1(
    limit_price_computer_type: str,
    limit_price_computer_kwargs: Dict[str, Any],
) -> olpclprco.AbstractLimitPriceComputer:
    """
    Instantiate `LimitPriceComputer` object.

    :param limit_price_computer_type: a type of `LimitPriceComputer` to use
    :param limit_price_computer_kwargs: required arguments to pass to the
        limit price computer
    """
    if limit_price_computer_type == "LimitPriceComputerUsingSpread":
        limit_price_computer = olpclpcus.LimitPriceComputerUsingSpread(
            **limit_price_computer_kwargs
        )
    elif limit_price_computer_type == "LimitPriceComputerUsingVolatility":
        limit_price_computer = olpclpcuv.LimitPriceComputerUsingVolatility(
            **limit_price_computer_kwargs
        )
    else:
        raise ValueError(
            "limit_price_computer_type='%s' not supported"
            % limit_price_computer_type
        )
    return limit_price_computer