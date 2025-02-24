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
# The notebook helps to investigate the differences between prod and sim pnl differences.

# %% [markdown]
# # Imports

# %%
import logging

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import reconciliation.sim_prod_reconciliation as rsiprrec

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build config

# %%
config = {
    "bar_duration": "5T",
    "portfolio_path_dict": {
        "prod": "/shared_data/ecs/preprod/prod_reconciliation/C3a/paper_trading/20230904_131000.20230905_130500/prod/system_log_dir.scheduled/process_forecasts/portfolio",
        "sim": "/shared_data/ecs/preprod/prod_reconciliation/C3a/paper_trading/20230904_131000.20230905_130500/simulation/system_log_dir/process_forecasts/portfolio",
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Compare prod vs sim PnL

# %% run_control={"marked": true}
# Load portfolios.
portfolio_dfs, portfolio_stats_dfs = rsiprrec.load_portfolio_dfs(
    config["portfolio_path_dict"].to_dict(),
    config["bar_duration"],
)

# %%
# Differences between PnL data.
prod_portfolio_pnl = portfolio_dfs["prod"]["pnl"].sum(axis=1, min_count=1)
sim_portfolio_pnl = portfolio_dfs["sim"]["pnl"].sum(axis=1, min_count=1)
portfolio_pnl_diff = prod_portfolio_pnl - sim_portfolio_pnl
# Pick the bar 13:20 to spot-check.
portfolio_pnl_diff.sort_values(ascending=False).head(3)

# %%
portfolio_pnl_diff.plot()

# %%
portfolio_dfs["sim"]["executed_trades_notional"].loc["2023-09-04 13:20:00-04:00"]

# %%
# For asset_ids 1891737434 and 1776791608 executed trades are NaN while
# for simulation they are zeros.
portfolio_dfs["prod"]["executed_trades_notional"].loc["2023-09-04 13:20:00-04:00"]

# %%
# Fill NaNs with zeros for prod `executed_trades_notional` when computing pnl.
prod_pnl = (
    portfolio_dfs["prod"]["holdings_notional"]
    .diff()
    .subtract(portfolio_dfs["prod"]["executed_trades_notional"].fillna(0))
    .sum(axis=1)
)
# Keep the sim portfolio as-is since NaNs are already filled with zeros.
sim_pnl = (
    portfolio_dfs["sim"]["holdings_notional"]
    .diff()
    .subtract(portfolio_dfs["sim"]["executed_trades_notional"])
    .sum(axis=1)
)
# After the fix there is no difference between sim and prod pnl.
diff_pnl = prod_pnl - sim_pnl
diff_pnl.plot()
