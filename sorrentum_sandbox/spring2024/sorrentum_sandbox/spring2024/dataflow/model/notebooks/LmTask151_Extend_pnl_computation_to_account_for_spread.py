# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import helpers.hdbg as hdbg
import helpers.hprint as hprint

hprint.config_notebook()

# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.test_logger()
_LOG = logging.getLogger(__name__)

# %% [markdown]
# # Generate random data

# %%
import numpy as np

import oms.obsolete.pnl_simulator as oobpnsim

df = oobpnsim.get_random_market_data(21)

display(df.head(3))
display(df.tail(3))

# %% [markdown]
# ## Lag-based PnL vs Level1 simulation

# %%
mode = "instantaneous"
df_5mins = oobpnsim.resample_data(df, mode)
display(df_5mins)

# %%
df.plot()

# %%
df, df_5mins = oobpnsim.get_example_market_data1()

display(df_5mins)

# %%
# Compute pnl using simulation.
w0 = 100.0
final_w, tot_ret, df_5mins = oobpnsim.compute_pnl_level1(w0, df, df_5mins)

print(final_w, tot_ret)

# %%
# Compute pnl using lags.
# df_5mins["pnl"] = df_5mins["preds"] * df_5mins["ret_0"].shift(-2)
# tot_ret2 = (1 + df_5mins["pnl"]).prod() - 1
# display(df_5mins[:-1])

tot_ret2, df_5mins = oobpnsim.compute_lag_pnl(df_5mins)

# Check that the results are the same.
print("tot_ret=", tot_ret)
print("tot_ret2=", tot_ret2)
np.testing.assert_almost_equal(tot_ret, tot_ret2)

# %% [markdown]
# ## Lag-based PnL vs Level1 vs Level2 simulation

# %%
mode = "instantaneous"
df, df_5mins = oobpnsim.get_example_market_data1()

# Level 1 sim.
initial_wealth = 1000
final_w, tot_ret, df_5mins = oobpnsim.compute_pnl_level1(
    initial_wealth, df, df_5mins
)
# Lag-based sim.
tot_ret2, df_5mins = oobpnsim.compute_lag_pnl(df_5mins)

# Level 2 sim.
config = {
    "price_column": "price",
    "future_snoop_allocation": True,
    "order_type": "price.end",
}

df_5mins = oobpnsim.compute_pnl_level2(df, df_5mins, initial_wealth, config)

df_5mins
