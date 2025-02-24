"""
Import as:

import oms.order_processing.target_position_and_order_generator_example as otpaogeex
"""

import asyncio
import logging
from typing import Optional

import oms.order_processing.target_position_and_order_generator as ooptpaoge
import oms.portfolio.portfolio_example as opopoexa

_LOG = logging.getLogger(__name__)


def get_TargetPositionAndOrderGenerator_example1(
    event_loop: Optional[asyncio.AbstractEventLoop],
    market_data,
) -> ooptpaoge.TargetPositionAndOrderGenerator:
    portfolio = opopoexa.get_DataFramePortfolio_example1(
        event_loop,
        market_data=market_data,
    )
    order_dict = {
        "order_type": "price@twap",
        "order_duration_in_mins": 5,
        "execution_frequency": "1T",
    }
    optimizer_dict = {
        "backend": "pomo",
        "asset_class": "equities",
        "apply_cc_limits": None,
        "params": {
            "style": "cross_sectional",
            "kwargs": {
                "bulk_frac_to_remove": 0.0,
                "bulk_fill_method": "zero",
                "target_gmv": 1e5,
            },
        },
    }
    share_quantization = 0
    target_position_and_order_generator = (
        ooptpaoge.TargetPositionAndOrderGenerator(
            portfolio,
            order_dict,
            optimizer_dict,
            None,
            share_quantization,
        )
    )
    return target_position_and_order_generator


def get_TargetPositionAndOrderGenerator_example2(
    event_loop: Optional[asyncio.AbstractEventLoop],
    market_data,
) -> ooptpaoge.TargetPositionAndOrderGenerator:
    portfolio = opopoexa.get_DataFramePortfolio_example1(
        event_loop,
        market_data=market_data,
    )
    order_dict = {
        "order_type": "price@twap",
        "order_duration_in_mins": 5,
        "execution_frequency": "1T",
    }
    optimizer_dict = {
        "backend": "batch_optimizer",
        "asset_class": "equities",
        "apply_cc_limits": None,
        "params": {
            "dollar_neutrality_penalty": 0.1,
            "transaction_cost_penalty": 0.5,
            "target_gmv": 1e5,
            "target_gmv_upper_bound_penalty": 0.0,
            "target_gmv_hard_upper_bound_multiple": 1.0,
            "relative_holding_penalty": 0.0,
            "relative_holding_max_frac_of_gmv": 0.5,
        },
    }
    restrictions = None
    share_quantization = 0
    target_position_and_order_generator = (
        ooptpaoge.TargetPositionAndOrderGenerator(
            portfolio,
            order_dict,
            optimizer_dict,
            restrictions,
            share_quantization,
        )
    )
    return target_position_and_order_generator
