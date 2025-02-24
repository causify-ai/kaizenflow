"""
Import as:

import oms.order_processing.process_forecasts_example as ooppfoex
"""
import datetime
from typing import Any, Dict


def get_process_forecasts_dict_example1() -> Dict[str, Any]:
    dict_ = {
        "order_config": {
            "order_type": "price@twap",
            "order_duration_in_mins": 5,
        },
        "optimizer_config": {
            "backend": "batch_optimizer",
            "asset_class": "equities",
            "apply_cc_limits": None,
            "dollar_neutrality_penalty": 0.1,
            "volatility_penalty": 0.5,
            "turnover_penalty": 0.0,
            "target_gmv": 1e6,
            "target_gmv_upper_bound_multiple": 1.01,
            # "verbose": True,
            "solver": "SCS",
        },
        "execution_mode": "batch",
        "ath_start_time": datetime.time(9, 30),
        "trading_start_time": datetime.time(9, 35),
        "ath_end_time": datetime.time(16, 0),
        "trading_end_time": datetime.time(15, 55),
        "liquidate_at_trading_end_time": False,
        "remove_weekends": True,
    }
    return dict_
