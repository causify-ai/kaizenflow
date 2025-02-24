# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import logging
from typing import Any, Dict

import pandas as pd

import core.config as cconfig
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.hsecrets.secret_identifier as ohsseide
import reconciliation.sim_prod_reconciliation as rsiprrec

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load target positions

# %%
config = {
    "bar_duration": "5T",
    # Target_dollar_risk_per_name = 0.3.
    "log_dir_run_prod": "/shared_data/CmTask5253_target_dollar_risk_experiment/system_log_dir_0.3/process_forecasts",
    # Target_dollar_risk_per_name = 0.1.
    "log_dir_run_experiment": "/shared_data/CmTask5253_target_dollar_risk_experiment/system_log_dir_0.1/process_forecasts",
    "broker": {
        "strategy_id": "C5b",
        "universe_version": "v7.3",
        "exchange_id": "binance",
        "stage": "prod",
        "account_type": "trading",
        "secret_id": 3,
    },
    "column_names": {
        "dataflow_cols": [
            "holdings_shares",
            "price",
            "holdings_notional",
            "prediction",
            "volatility",
            "spread",
            "target_holdings_notional",
            "target_trades_notional",
            "target_trades_shares",
            "target_holdings_shares",
            "target_trades_shares.before_apply_cc_limits",
            "min_amount",
            "min_cost",
            "amount_precision",
            "max_leverage",
        ],
        "asset_id": "asset_id",
        "timestamp_col": "wall_clock_timestamp",
        "target_trades_shares": "target_trades_shares",
        "target_trades_shares.before_apply_cc_limits": "target_trades_shares.before_apply_cc_limits",
        "target_trades_notional": "target_trades_notional",
        "market_info_cols": {"min_amount": "min_amount", "min_cost": "min_cost"},
    },
}
config = cconfig.Config().from_dict(config)
print(config)


# %% [markdown]
# # Functions

# %%
def _add_market_info_to_df(
    df: pd.DataFrame, market_info: Dict[str, Any], config: cconfig.Config
) -> pd.DataFrame:
    """
    Add market info to the dataframe.
    """
    # Change the format in order to easily map market_info.
    df = df.stack().reset_index()
    # Map limits on asset ids.
    market_info_srs = (
        df[config["column_names"]["asset_id"]].map(market_info).apply(pd.Series)
    )
    df = pd.concat([df, market_info_srs], axis=1)
    # Convert back to the DataFlow format.
    df = df.pivot(
        index=config["column_names"]["timestamp_col"],
        columns=config["column_names"]["asset_id"],
        values=config["column_names"]["dataflow_cols"],
    )
    return df


def check_if_position_is_rejected(
    target_positions_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Check if a position is rejected due to shares, notional or either limit.

    :param target_positions_df: target positions and market limits data
    :return: a table with values that are True, if a position is rejected due
        to a corresponding constraint, False otherwise
    """
    target_trades_shares_before_apply_cc_limits_column = config["column_names"][
        "target_trades_shares.before_apply_cc_limits"
    ]
    target_trades_shares_column = config["column_names"]["target_trades_shares"]
    market_info_min_amount_column = config["column_names"]["market_info_cols"][
        "min_amount"
    ]
    target_trades_notional_column = config["column_names"][
        "target_trades_notional"
    ]
    market_info_min_cost_column = config["column_names"]["market_info_cols"][
        "min_cost"
    ]
    # Preprocess data.
    target_positions_df[target_trades_shares_column] = target_positions_df[
        target_trades_shares_before_apply_cc_limits_column
    ]
    target_positions_df[target_trades_notional_column] = (
        target_positions_df[target_trades_shares_column]
        * target_positions_df["price"]
    )
    # Check the shares contrainst.
    is_shares_limit_rejected = (
        abs(target_positions_df[target_trades_shares_column])
        < target_positions_df[market_info_min_amount_column]
    )
    # Check the notional constraint.
    is_notional_limit_rejected = (
        abs(target_positions_df[target_trades_notional_column])
        <= target_positions_df[market_info_min_cost_column]
    )
    # Check either contraint.
    is_either_limit_rejected = (
        is_shares_limit_rejected | is_notional_limit_rejected
    )
    # Combine the results into a single df.
    df_rejected = pd.concat(
        {
            target_trades_shares_column: target_positions_df[
                target_trades_shares_column
            ],
            market_info_min_amount_column: target_positions_df[
                market_info_min_amount_column
            ],
            "is_shares_limit_rejected": is_shares_limit_rejected,
            target_trades_notional_column: target_positions_df[
                target_trades_notional_column
            ],
            market_info_min_cost_column: target_positions_df[
                market_info_min_cost_column
            ],
            "is_notional_limit_rejected": is_notional_limit_rejected,
            "is_either_limit_rejected": is_either_limit_rejected,
        },
        axis=1,
    )
    return df_rejected


def count_rejected_positions(df: pd.DataFrame) -> pd.Series:
    """
    Count the number of rejected position per constraint.

    :param df: input table that contains True as values if a position is rejected
    :return: rejected positions counts per constraint
    """
    # Keep only the relevant columns.
    rejected_positions = df[
        [
            "is_shares_limit_rejected",
            "is_notional_limit_rejected",
            "is_either_limit_rejected",
        ]
    ]
    # Sum across assets and timestamps.
    rejected_counts = (
        rejected_positions.groupby(level=[0], axis=1, sort=False).sum().sum()
    )
    return rejected_counts


# %% [markdown]
# # Load data

# %%
prod_df = rsiprrec.load_target_positions(
    config["log_dir_run_prod"], normalize_bar_times_freq=config["bar_duration"]
)
hpandas.df_to_str(prod_df, num_rows=5, log_level=logging.INFO)

# %%
experiment_df = rsiprrec.load_target_positions(
    config["log_dir_run_experiment"],
    normalize_bar_times_freq=config["bar_duration"],
)
hpandas.df_to_str(experiment_df, num_rows=5, log_level=logging.INFO)

# %%
# Get broker.
asset_ids = list(
    prod_df.columns.get_level_values(config["column_names"]["asset_id"]).unique()
)
db_stage = "preprod"
market_data = dtfasccxbu.get_Cx_RealTimeMarketData_prod_instance1(asset_ids, db_stage)
#
secret_identifier = ohsseide.SecretIdentifier(
    config["broker"]["exchange_id"],
    config["broker"]["stage"],
    config["broker"]["account_type"],
    config["broker"]["secret_id"],
)
#
passivity_factor = None
broker = obccbrin.get_CcxtBroker_v2_prod_instance1(
    config["broker"]["strategy_id"],
    market_data,
    config["broker"]["universe_version"],
    secret_identifier,
    config["log_dir_run_prod"],
    passivity_factor,
)
market_info = broker.market_info
market_info

# %% [markdown]
# # Get rejected orders

# %%
prod_df = _add_market_info_to_df(prod_df, market_info, config)
# Get prod rejected orders.
prod_df_rejected = check_if_position_is_rejected(prod_df)
hpandas.df_to_str(prod_df_rejected, num_rows=5, log_level=logging.INFO)

# %%
experiment_df = _add_market_info_to_df(experiment_df, market_info, config)
# Get experiment rejected orders.
experiment_df_rejected = check_if_position_is_rejected(experiment_df)
hpandas.df_to_str(experiment_df_rejected, num_rows=5, log_level=logging.INFO)

# %%
prod_counts = count_rejected_positions(prod_df_rejected)
experiment_counts = count_rejected_positions(experiment_df_rejected)
counts_dict = {
    "target_dollar_risk_per_name_0_1": experiment_counts,
    "target_dollar_risk_per_name_0_3": prod_counts,
}
combined_counts = pd.DataFrame.from_dict(counts_dict, orient="index")
combined_counts
