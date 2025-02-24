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
# # Description
#
# Reconcile portfolio and target positions: the ones reconstructed from fills vs ones that are logged during a prod system run.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging
import os

import pandas as pd

import core.config as cconfig
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.universe as ivcu
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
import oms.broker.ccxt.ccxt_execution_quality as obccexqu
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.order.order_converter as oororcon
import reconciliation.sim_prod_reconciliation as rsiprrec

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Functions


# %%
# TODO(Dan): Move to a lib.
def verify_no_trades_for_missing_assets(
    reconstructed_df: pd.DataFrame,
    prod_df: pd.DataFrame,
    type_: str,
    share_asset_ids_with_no_fills: float,
) -> None:
    """
    Check that there were no executed/target trades for asset ids that are
    missing in the reconstructed df.

    :param reconstructed_df: data reconstructed from fills/parent orders
    :param prod_df: data loaded from prod run logs directly
    :param type_: data type, "portfolio" or "target_positions"
    :param share_asset_ids_with_no_fills: threshold for acceptable share
        of missing asset ids
    """
    # Set column names to check the absence of trades.
    if type_ == "portfolio":
        trades_col = "executed_trades_shares"
        shares_col = "executed_trades_notional"
    elif type_ == "target_positions":
        trades_col = "target_trades_shares"
        shares_col = "target_trades_notional"
    else:
        raise ValueError("Unsupported `type_`=%s", type_)
    missing_asset_ids = set(prod_df.columns.levels[1]) - set(
        reconstructed_df.columns.levels[1]
    )
    num_missing_asset_ids = len(missing_asset_ids)
    if num_missing_asset_ids > 0:
        # Check that the share of missing asset ids is not greater
        # than an arbitrary threshold.
        num_asset_ids = len(prod_df.columns.levels[1])
        hdbg.dassert_lte(
            num_missing_asset_ids / num_asset_ids,
            share_asset_ids_with_no_fills,
        )
        for asset_id in missing_asset_ids:
            _LOG.info("Missing asset id = %s", asset_id)
            # Check trades in shares.
            trades_shares_sum = (
                prod_df.xs(asset_id, axis=1, level=1, drop_level=False)[
                    trades_col
                ]
                .abs()
                .sum()
                .loc[asset_id]
            )
            # TODO(Dan): Consider to use `hpandas.dassert_approx_eq()`
            #  to account for a floating point error.
            hdbg.dassert_eq(
                0,
                trades_shares_sum,
                msg="Asset id='%s' with no positions/fills has executed/target trades in shares='%s' in total, while 0 is the expected value"
                % (asset_id, trades_shares_sum),
            )
            # Ideally zero trades in shares implies no notional trades,
            # but checking both in case of any data inconsistency.
            trades_notional_sum = (
                prod_df.xs(asset_id, axis=1, level=1, drop_level=False)[
                    shares_col
                ]
                .abs()
                .sum()
                .loc[asset_id]
            )
            hdbg.dassert_eq(
                0,
                trades_shares_sum,
                msg="Asset id='%s' with no with no positions/fills has executed/target nominal trades ='%s' in total, while 0 is the expected value"
                % (asset_id, trades_notional_sum),
            )


def sanity_check_indices_difference(
    reconstructed_df: pd.DataFrame,
    prod_df: pd.DataFrame,
    n_index_elements_to_ignore: int,
) -> None:
    """
    Check that the symmetric indices difference does exceed the threshold.

    :param reconstructed_df: data reconstructed from fills/parent orders
    :param prod_df: data loaded from prod run logs directly
    :param n_index_elements_to_ignore: threshold for number of differing
        indices
    """
    # Sanity check differing indices from reconstructed df.
    reconstructed_df_extra_idx = reconstructed_df.index.difference(prod_df.index)
    hdbg.dassert_lte(len(reconstructed_df_extra_idx), n_index_elements_to_ignore)
    if len(reconstructed_df_extra_idx) > 0:
        # Verify that the difference is a consecutive index.
        hpandas.dassert_strictly_increasing_index(reconstructed_df_extra_idx)
    # Sanity check differing indices from prod df.
    prod_df_extra_idx = prod_df.index.difference(reconstructed_df.index)
    hdbg.dassert_lte(len(prod_df_extra_idx), n_index_elements_to_ignore)
    if len(prod_df_extra_idx) > 0:
        # Verify that the difference is a consecutive index.
        hpandas.dassert_strictly_increasing_index(prod_df_extra_idx)


# %% [markdown]
# # Config

# %%
# When running manually, specify the path to the config to load config from file,
# for e.g., `.../reconciliation_notebook/fast/result_0/config.pkl`.
config_file_name = None
config = cconfig.get_notebook_config(config_file_name)
if config is None:
    id_col = "asset_id"
    system_log_dir = "/shared_data/CmTask7811/20240405_105500.20240405_115000/system_log_dir.manual/process_forecasts"
    # Load pickled SystemConfig.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_dir = system_log_dir.rstrip("/process_forecasts")
    system_config_path = os.path.join(system_config_dir, config_file_name)
    system_config = cconfig.load_config_from_pickle(system_config_path)
    # Get param values from SystemConfig.
    bar_duration_in_secs = rsiprrec.get_bar_duration_from_config(system_config)
    bar_duration = hdateti.convert_seconds_to_pandas_minutes(bar_duration_in_secs)
    universe_version = system_config["market_data_config", "universe_version"]
    price_column_name = system_config["portfolio_config", "mark_to_market_col"]
    table_name = system_config[
        "market_data_config", "im_client_config", "table_name"
    ]
    vendor = "CCXT"
    mode = "trade"
    #
    config_dict = {
        "id_col": id_col,
        "system_log_dir": system_log_dir,
        "market_data": {
            "vendor": vendor,
            "mode": mode,
            "universe_version": universe_version,
            "im_client_config": {
                "table_name": table_name,
            },
        },
        "price_column_name": price_column_name,
        "bar_duration": bar_duration,
        "share_asset_ids_with_no_fills": 0.3,
        "n_index_elements_to_ignore": 2,
        "target_positions_columns_to_compare": [
            "price",
            "holdings_shares",
            "holdings_notional",
            "target_holdings_shares",
            "target_holdings_notional",
            "target_trades_shares",
            "target_trades_notional",
        ],
        "compare_dfs_kwargs": {
            "row_mode": "inner",
            "column_mode": "inner",
            "diff_mode": "pct_change",
            "assert_diff_threshold": 1e-3,
            "log_level": logging.INFO,
        },
    }
    config = cconfig.Config.from_dict(config_dict)
print(config)

# %% [markdown]
# # Reconstruct portfolio and target positions from fills

# %% [markdown]
# ## Load fills

# %%
system_log_dir = config.get_and_mark_as_used(("system_log_dir",))
system_log_dir

# %%
ccxt_log_reader = obcccclo.CcxtLogger(system_log_dir)

# %%
fills_df = ccxt_log_reader.load_ccxt_trades(convert_to_dataframe=True)

# %%
fills_df.head(3)

# %%
id_col = config.get_and_mark_as_used(("id_col",))
bar_duration = config.get_and_mark_as_used(("bar_duration",))
# Aggregate fills by bar.
bar_fills = obccagfu.aggregate_fills_by_bar(
    fills_df, bar_duration, groupby_id_col=id_col
)

# %%
bar_fills.head(3)

# %% [markdown]
# ## Load oms parent orders
#
# These are in the internal `amp` format (not the `ccxt` format)

# %%
parent_order_df = ccxt_log_reader.load_oms_parent_order(convert_to_dataframe=True)

# %%
parent_order_df.head(3)

# %% [markdown]
# ## Load market data

# %%
# TODO(Paul): Refine the cuts around the first and last bars.
start_timestamp = bar_fills["first_datetime"].min() - pd.Timedelta(bar_duration)
_LOG.info("start_timestamp=%s", start_timestamp)
end_timestamp = bar_fills["last_datetime"].max() + pd.Timedelta(bar_duration)
_LOG.info("end_timestamp=%s", end_timestamp)

# %%
universe_version = config.get_and_mark_as_used(
    (
        "market_data",
        "universe_version",
    )
)
vendor = config.get_and_mark_as_used(
    (
        "market_data",
        "vendor",
    )
)
mode = config.get_and_mark_as_used(
    (
        "market_data",
        "mode",
    )
)
table_name = config.get_and_mark_as_used(
    (
        "market_data",
        "im_client_config",
        "table_name",
    )
)
# Get asset ids.
asset_ids = ivcu.get_vendor_universe_as_asset_ids(universe_version, vendor, mode)
# Get prod `MarketData`.
# TODO(Grisha): expose stage to the notebook config.
db_stage = "preprod"
market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(
    asset_ids,
    db_stage,
    table_name=table_name,
)
# Load and resample OHLCV data.
ohlcv_bars = dtfamsysc.load_and_resample_ohlcv_data(
    market_data,
    start_timestamp,
    end_timestamp,
    bar_duration,
)
ohlcv_bars.head()

# %% [markdown]
# ## Compute portfolio

# %%
portfolio_from_fills_df = obccexqu.convert_bar_fills_to_portfolio_df(
    bar_fills,
    ohlcv_bars[config["price_column_name"]],
)
hpandas.df_to_str(portfolio_from_fills_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Compute target positions

# %%
target_positions_from_parent_orders_df = (
    oororcon.convert_order_df_to_target_position_df(
        parent_order_df,
        ohlcv_bars[config["price_column_name"]],
    )
)
hpandas.df_to_str(
    target_positions_from_parent_orders_df, num_rows=5, log_level=logging.INFO
)

# %% [markdown]
# # Load prod portfolio and target positions

# %% [markdown]
# ## Portfolio

# %%
portfolio_dir = os.path.join(system_log_dir, "portfolio")
#
portfolio_df, _ = rsiprrec.load_portfolio_artifacts(portfolio_dir, bar_duration)
portfolio_df.head()

# %% [markdown]
# ## Target positions

# %%
target_positions_df = rsiprrec.load_target_positions(system_log_dir, bar_duration)
# Select only the columns that are necessary for reconciliation.
target_positions_df = target_positions_df[
    config["target_positions_columns_to_compare"]
]
target_positions_df.columns = target_positions_df.columns.remove_unused_levels()
#
target_positions_df.head()

# %% [markdown]
# # Compare portfolio and target positions

# %% [markdown]
# ## Portfolio

# %% [markdown]
# ### Columns

# %%
portfolio_from_fills_df.columns.levels[0]

# %%
portfolio_df.columns.levels[0]

# %%
hdbg.dassert_set_eq(
    portfolio_from_fills_df.columns.levels[0],
    portfolio_df.columns.levels[0],
)

# %%
portfolio_from_fills_df.columns.levels[1]

# %%
portfolio_df.columns.levels[1]

# %%
# Verify that in production portfolio all assets belong to the production universe.
hdbg.dassert_set_eq(
    asset_ids,
    portfolio_df.columns.levels[1],
)
# Having a few `asset_ids` missing in df reconstructed from fills is acceptable
# because they will be missing in case of no trades.
hdbg.dassert_set_eq(
    portfolio_from_fills_df.columns.levels[1],
    portfolio_df.columns.levels[1],
    only_warning=True,
)
# Check that for missing assets ids there were no trades.
type_ = "portfolio"
verify_no_trades_for_missing_assets(
    portfolio_from_fills_df,
    portfolio_df,
    type_,
    config["share_asset_ids_with_no_fills"],
)

# %% [markdown]
# ### Index

# %%
# Set indices to the same timezone.
portfolio_df.index = portfolio_df.index.tz_convert("UTC")
hdbg.dassert_eq(
    portfolio_from_fills_df.index.tz,
    portfolio_df.index.tz,
)

# %%
# Report the symmetric difference. There are some extra consecutive index elements
# in the df reconstructed from fills that can be ignored.
hpandas.dassert_indices_equal(
    portfolio_from_fills_df,
    portfolio_df,
    only_warning=True,
)

# %%
sanity_check_indices_difference(
    portfolio_from_fills_df,
    portfolio_df,
    config["n_index_elements_to_ignore"],
)

# %% [markdown]
# ### Values

# %%
# Compare values at intersecting columns / indices.
portfolio_diff_df = hpandas.compare_dfs(
    portfolio_from_fills_df, portfolio_df, **config["compare_dfs_kwargs"]
)
portfolio_diff_df.head(3)

# %% [markdown]
# ## Target positions

# %% [markdown]
# ### Columns

# %%
target_positions_from_parent_orders_df.columns.levels[0]

# %%
target_positions_df.columns.levels[0]

# %%
hdbg.dassert_set_eq(
    config["target_positions_columns_to_compare"],
    target_positions_from_parent_orders_df.columns.levels[0],
)
hdbg.dassert_set_eq(
    config["target_positions_columns_to_compare"],
    target_positions_df.columns.levels[0],
)

# %%
target_positions_df.columns.levels[1]

# %%
target_positions_from_parent_orders_df.columns.levels[1]

# %%
# Verify that in production target positions all assets belong to the production universe.
hdbg.dassert_set_eq(
    asset_ids,
    target_positions_df.columns.levels[1],
)
# Having a few `asset_ids` missing in df reconstructed from parent orders
# is acceptablebecause they will be missing in case of no positions.
hdbg.dassert_set_eq(
    target_positions_from_parent_orders_df.columns.levels[1],
    target_positions_df.columns.levels[1],
    only_warning=True,
)
# Check that for missing assets ids there were no trades.
type_ = "target_positions"
verify_no_trades_for_missing_assets(
    target_positions_from_parent_orders_df,
    target_positions_df,
    type_,
    config["share_asset_ids_with_no_fills"],
)

# %% [markdown]
# ### Index

# %%
# Set indices to the same timezone.
target_positions_df.index = portfolio_df.index.tz_convert("UTC")
hdbg.dassert_eq(
    target_positions_from_parent_orders_df.index.tz,
    target_positions_df.index.tz,
)

# %%
hpandas.dassert_indices_equal(
    target_positions_from_parent_orders_df,
    target_positions_df,
)

# %% [markdown]
# ### Values

# %%
# Compare values at intersecting columns / indices.
target_position_diff_df = hpandas.compare_dfs(
    target_positions_from_parent_orders_df,
    target_positions_df,
    **config["compare_dfs_kwargs"],
)
target_position_diff_df.head(3)
