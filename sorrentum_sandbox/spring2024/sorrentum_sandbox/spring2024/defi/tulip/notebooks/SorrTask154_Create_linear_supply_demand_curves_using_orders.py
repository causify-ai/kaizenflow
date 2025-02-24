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

import matplotlib.pyplot as plt

import defi.tulip.implementation.order as dtuimord
import defi.tulip.implementation.supply_demand as dtimsude
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
try:
    import pulp
except ImportError:
    # !sudo /bin/bash -c "(source /venv/bin/activate; pip install pulp)"
    pass
import defi.tulip.implementation.optimize as dtuimopt

# %%
hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Get aggregated supply / demand

# %%
type_ = "supply"
alpha = 2.0
beta = 10.0
n_orders = 10
agg_supply_curve = dtimsude.get_supply_demand_aggregated_curve(
    type_, alpha, beta, n_orders
)
agg_supply_curve

# %%
type_ = "demand"
alpha = -2.0
beta = 210.0
n_orders = 10
agg_demand_curve = dtimsude.get_supply_demand_aggregated_curve(
    type_, alpha, beta, n_orders
)
agg_demand_curve

# %%
agg_supply_orders = dtimsude.convert_aggregated_curve_to_limit_orders(
    agg_supply_curve
)
agg_supply_orders_df = dtuimord.convert_orders_to_dataframe(agg_supply_orders)
agg_supply_orders_df

# %%
plt.plot(agg_supply_curve)
plt.plot(agg_demand_curve)
plt.show()

# %%
agg_demand_orders = dtimsude.convert_aggregated_curve_to_limit_orders(
    agg_demand_curve
)
agg_demand_orders_df = dtuimord.convert_orders_to_dataframe(agg_demand_orders)
agg_demand_orders_df

# %% [markdown]
# # Implement DaoCross and DaoSwap

# %%
agg_all_orders = agg_supply_orders + agg_demand_orders
prices = {"BTC": 1, "ETH": 50}

# %%
daocross_results = dtuimopt.run_daocross_solver(agg_all_orders, prices)
display(daocross_results)

# %%
daoswap_results = dtuimopt.run_daoswap_solver(agg_all_orders)
display(daoswap_results)

# %% [markdown]
# # Sanity check with discrete supply / demand

# %%
type_ = "supply"
discrete_supply_curve = dtimsude.get_supply_demand_discrete_curve(
    type_, agg_supply_orders_df
)
discrete_supply_curve

# %%
type_ = "demand"
discrete_demand_curve = dtimsude.get_supply_demand_discrete_curve(
    type_, agg_demand_orders_df
)
discrete_demand_curve

# %%
dtimsude.plot_discrete_curve(discrete_demand_curve)
dtimsude.plot_discrete_curve(discrete_supply_curve)
plt.show()

# %%
