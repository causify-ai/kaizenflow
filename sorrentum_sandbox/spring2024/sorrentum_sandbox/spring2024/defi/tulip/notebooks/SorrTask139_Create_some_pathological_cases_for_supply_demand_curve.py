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
import pandas as pd

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
# # Pathological cases

# %% [markdown]
# ## Get orders and set prices.

# %%
base_token = "BTC"
quote_token = "ETH"

# %%
quantities = [1.0, 2.0, 3.0, 4.0]
limit_prices = [1.5, 2.0, 3.0, 3.5]
type_ = "supply"
curve_name = ".".join([base_token, type_])
#
discrete_supply_curve = pd.Series(
    index=quantities,
    data=limit_prices,
    name=curve_name,
)
discrete_supply_curve.index.name = quote_token
discrete_supply_curve

# %%
supply_orders1 = dtimsude.convert_discrete_curve_to_limit_orders(
    discrete_supply_curve
)
supply_orders_df1 = dtuimord.convert_orders_to_dataframe(supply_orders1)
supply_orders_df1

# %%
quantities = [1.0, 2.0, 3.0, 4.0]
limit_prices = [3.5, 2.5, 2.0, 1.5]
type_ = "demand"
curve_name = ".".join([base_token, type_])
#
discrete_demand_curve = pd.Series(
    index=quantities,
    data=limit_prices,
    name=curve_name,
)
discrete_demand_curve.index.name = quote_token
discrete_demand_curve

# %%
demand_orders1 = dtimsude.convert_discrete_curve_to_limit_orders(
    discrete_demand_curve
)
demand_orders_df1 = dtuimord.convert_orders_to_dataframe(demand_orders1)
demand_orders_df1

# %%
prices = {"BTC": 1, "ETH": 2}

# %% [markdown]
# ## Multiple intersection points at quantity Q'

# %%
type_ = "supply"
supply_curve1 = dtimsude.get_supply_demand_discrete_curve(
    type_, supply_orders_df1
)
supply_curve1

# %%
supply_orders_ = dtimsude.convert_discrete_curve_to_limit_orders(supply_curve1)

# %%
type_ = "demand"
demand_curve1 = dtimsude.get_supply_demand_discrete_curve(
    type_, demand_orders_df1
)
demand_curve1

# %%
dtimsude.plot_discrete_curve(demand_curve1)
dtimsude.plot_discrete_curve(supply_curve1)
plt.show()

# %% run_control={"marked": false}
all_orders1 = supply_orders1 + demand_orders1
daocross_results1 = dtuimopt.run_daocross_solver(all_orders1, prices)
display(daocross_results1)

# %%
daoswap_results1 = dtuimopt.run_daoswap_solver(all_orders1)
display(daoswap_results1)

# %% [markdown]
# ## Multiple intersection points at price P'

# %%
quantity_const = 1.0
supply_orders2 = dtimsude.convert_discrete_curve_to_limit_orders(
    discrete_supply_curve,
    quantity_const=quantity_const,
)
supply_orders_df2 = dtuimord.convert_orders_to_dataframe(supply_orders2)
supply_orders_df2

# %%
type_ = "supply"
supply_curve2 = dtimsude.get_supply_demand_discrete_curve(
    type_, supply_orders_df2
)
supply_curve2

# %%
dtimsude.plot_discrete_curve(demand_curve1)
dtimsude.plot_discrete_curve(supply_curve2)
plt.show()

# %%
all_orders2 = supply_orders2 + demand_orders1
daocross_results2 = dtuimopt.run_daocross_solver(all_orders2, prices)
display(daocross_results2)

# %%
daoswap_results2 = dtuimopt.run_daoswap_solver(all_orders2)
display(daoswap_results2)

# %% [markdown]
# ## No intersection

# %%
limit_price_const = 3.0
supply_orders3 = dtimsude.convert_discrete_curve_to_limit_orders(
    discrete_supply_curve,
    limit_price_const=limit_price_const,
)
supply_orders_df3 = dtuimord.convert_orders_to_dataframe(supply_orders3)
supply_orders_df3

# %%
type_ = "supply"
supply_curve3 = dtimsude.get_supply_demand_discrete_curve(
    type_, supply_orders_df3
)
supply_curve3

# %%
dtimsude.plot_discrete_curve(demand_curve1)
dtimsude.plot_discrete_curve(supply_curve3)
plt.show()

# %%
all_orders3 = supply_orders3 + demand_orders1
daocross_results3 = dtuimopt.run_daocross_solver(all_orders3, prices)
display(daocross_results3)

# %%
daoswap_results3 = dtuimopt.run_daoswap_solver(all_orders3)
display(daoswap_results3)

# %%
