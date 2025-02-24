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

# %% [markdown]
# Calculate longitudinal sweep of slippage in bps.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
import logging

import pandas as pd

import core.config as cconfig
import core.finance.target_position_df_processing as cftpdp
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.universe as ivcu
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
import oms.broker.ccxt.ccxt_execution_quality as obccexqu
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.order.order_converter as oororcon

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
# TODO(Toma): turn this into master notebook.

# %%
config = cconfig.get_config_from_env()
if config:
    _LOG.info("Using config from env vars")
else:
    id_col = "asset_id"
    universe_version = "v7.5"
    vendor = "CCXT"
    mode = "trade"
    bar_duration = "3T"
    config_dict = {
        "meta": {"id_col": id_col},
        "ohlcv_market_data": {
            "vendor": vendor,
            "mode": mode,
            "universe": {
                "universe_version": universe_version,
            },
        },
        "execution_parameters": {
            "bar_duration": bar_duration,
        },
    }
    config = cconfig.Config.from_dict(config_dict)
print(config)

# %% [markdown]
# # Specify the paths to experiments

# %%
# Provide full system_log_dir paths with `process_forecasts` from Algo execution doc.
paths_to_process = [
    "/shared_data/ecs_tokyo/test/system_reconciliation/C12a/prod/20240221_115700.20240221_125400/system_log_dir.manual/process_forecasts",
    "/shared_data/ecs_tokyo/test/system_reconciliation/C12a/prod/20240221_144500.20240221_154200/system_log_dir.manual/process_forecasts",
    "/shared_data/ecs_tokyo/test/system_reconciliation/C12a/prod/20240219_150900.20240219_160600/system_log_dir.manual/process_forecasts",
    "/shared_data/ecs_tokyo/test/system_reconciliation/C12a/prod/20240223_160900.20240223_170600/system_log_dir.manual/process_forecasts",
    "/shared_data/ecs_tokyo/test/system_reconciliation/C12a/prod/20240219_165700.20240219_175400/system_log_dir.manual/process_forecasts",
]

# %% [markdown]
# # Process the experiments

# %%
id_col = config.get_and_mark_as_used(("meta", "id_col"))
universe_version = config.get_and_mark_as_used(
    ("ohlcv_market_data", "universe", "universe_version")
)
vendor = config.get_and_mark_as_used(("ohlcv_market_data", "vendor"))
mode = config.get_and_mark_as_used(("ohlcv_market_data", "mode"))
bar_duration = config.get_and_mark_as_used(
    ("execution_parameters", "bar_duration")
)

# %% run_control={"marked": false}
slippage_in_bps_rows = []

# TODO(Toma): move to a lib.
for log_dir in paths_to_process:
    _LOG.info("Processing `%s`", log_dir)
    # Init the log reader.
    ccxt_log_reader = obcccclo.CcxtLogger(log_dir)
    # # Load and aggregate data.
    # ## Load OMS parent orders.
    parent_order_df = ccxt_log_reader.load_oms_parent_order(
        convert_to_dataframe=True, abort_on_missing_data=False
    )
    # ## Load CCXT fills (trades).
    fills_df = ccxt_log_reader.load_ccxt_trades(
        convert_to_dataframe=True, abort_on_missing_data=False
    )
    # ## Aggregate CCXT Data.
    bar_fills = obccagfu.aggregate_fills_by_bar(
        fills_df, bar_duration, groupby_id_col=id_col
    )
    # ## Load OHLCV data.
    start_timestamp = bar_fills["first_datetime"].min() - pd.Timedelta(
        bar_duration
    )
    end_timestamp = bar_fills["last_datetime"].max() + pd.Timedelta(bar_duration)
    # Get asset ids.
    asset_ids = ivcu.get_vendor_universe_as_asset_ids(
        universe_version, vendor, mode
    )
    # Get prod `MarketData`.
    db_stage = "preprod"
    market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(
        asset_ids, db_stage
    )
    # Load and resample OHLCV data.
    ohlcv_bars = dtfamsysc.load_and_resample_ohlcv_data(
        market_data,
        start_timestamp,
        end_timestamp,
        bar_duration,
    )
    # # Execution quality.
    # Compute `target_position_df` and `portfolio_df`.
    price_df = ohlcv_bars["close"]
    target_position_df = oororcon.convert_order_df_to_target_position_df(
        parent_order_df,
        price_df,
    )
    portfolio_df = obccexqu.convert_bar_fills_to_portfolio_df(
        bar_fills,
        price_df,
    )
    (
        execution_quality_df,
        execution_quality_stats_df,
    ) = cftpdp.compute_execution_quality_df(
        portfolio_df,
        target_position_df,
    )
    # Calculate slippage in BPS.
    # TODO(Toma): improve the way mean is calculated.
    slippage_in_bps = execution_quality_df["slippage_in_bps"].mean()
    # TODO(Toma): add caching previous calculations using decorator, PP with GP.
    row = pd.DataFrame(slippage_in_bps.to_dict(), index=[start_timestamp])
    slippage_in_bps_rows.append(row)

# %% [markdown]
# # Build the longitudinal sweep of slippage Dataframe

# %%
slippage_in_bps_df = pd.concat(slippage_in_bps_rows).sort_index()

# %%
slippage_in_bps_df

# %%
