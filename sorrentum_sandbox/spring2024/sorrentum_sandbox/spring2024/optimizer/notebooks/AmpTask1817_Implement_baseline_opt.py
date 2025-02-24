# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import logging

import pandas as pd

import helpers.hdbg as hdbg
import optimizer.single_period_optimization as osipeopt

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

# _LOG.info("%s", henv.get_system_signature()[0])

# %%
# hprint.config_notebook()

# %% [markdown]
# # Build forecast dataframe

# %%
df = pd.DataFrame(
    [
        [1, 1000, 1, 1000, 0.05, 0.05],
        [2, 1500, 1, 1500, 0.09, 0.07],
        [3, -500, 1, -500, 0.03, 0.08],
    ],
    range(0, 3),
    [
        "asset_id",
        "holdings_shares",
        "price",
        "holdings_notional",
        "prediction",
        "volatility",
    ],
)

# %% [markdown]
# # Build optimizer config

# %%
dict_ = {
    "dollar_neutrality_penalty": 0.0,
    "volatility_penalty": 0.0,
    "relative_holding_penalty": 0.0,
    "relative_holding_max_frac_of_gmv": 0.6,
    "target_gmv": 3000,
    "target_gmv_upper_bound_penalty": 0.0,
    "target_gmv_hard_upper_bound_multiple": 1.00,
    "turnover_penalty": 0.0,
    "solver": "ECOS",
}

# %% [markdown]
# # Optimize

# %%
spo = osipeopt.SinglePeriodOptimizer(dict_, df)

# %%
opt_results = spo.optimize()
display(opt_results.round(3))

# %%
res1 = opt_results.stack().rename("s1")

# %%
res2 = opt_results.stack().rename("s2")

# %%
pd.concat([res1, res2], keys=["s1", "s2"], axis=1)

# %%
pd.concat(
    {
        "s1": res1,
        "s2": res2,
    },
    axis=1,
).T

# %%
spo.compute_stats(opt_results)

# %% [markdown]
# # Process forecast dataframe

# %%
tz = "America/New_York"
idx = [
    pd.Timestamp("2022-01-03 09:35:00", tz=tz),
    pd.Timestamp("2022-01-03 09:40:00", tz=tz),
    pd.Timestamp("2022-01-03 09:45:00", tz=tz),
    pd.Timestamp("2022-01-03 09:50:00", tz=tz),
]
asset_ids = [100, 200]

prediction_data = [
    [-0.25, -0.34],
    [0.13, 0.5],
    [0.84, -0.97],
    [0.86, -0.113],
]

price_data = [[100.0, 100.3], [100.1, 100.5], [100.05, 100.4], [100.2, 100.5]]

volatility_data = [
    [0.00110, 0.00048],
    [0.00091, 0.00046],
    [0.00086, 0.00060],
    [0.00071, 0.00068],
]

prediction_df = pd.DataFrame(prediction_data, idx, asset_ids)
price_df = pd.DataFrame(price_data, idx, asset_ids)
volatility_df = pd.DataFrame(volatility_data, idx, asset_ids)
dag_df = pd.concat(
    {"price": price_df, "volatility": volatility_df, "prediction": prediction_df},
    axis=1,
)

# %%
dag_df

# %%
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

# %%
fewo = ofevwiop.ForecastEvaluatorWithOptimizer(
    "price",
    "volatility",
    "prediction",
    dict_,
)

# %%
dag_df

# %%
portfolio_df, portfolio_stats_df = fewo.annotate_forecasts(
    dag_df, quantization="nearest_share"
)

# %%
portfolio_df

# %%
portfolio_stats_df

# %%
dfs = fewo.compute_portfolio(dag_df, quantization="nearest_share")
