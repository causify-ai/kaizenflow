# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# - Initialize with returns, alpha, and spread
# - Evaluate portfolios generated from the alpha

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import dataflow_model.model_evaluator as cdtfmomoev

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

# _LOG.info("%s", env.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Notebook config

# %%
# Read from env var.
eval_config = cconfig.Config.from_env_var("AM_CONFIG_CODE")

if eval_config is None:
    experiment_dir = ""
    aws_profile = None
    selected_idxs = None

    eval_config = cconfig.Config.from_dict(
        {
            "load_experiment_kwargs": {
                "src_dir": experiment_dir,
                "file_name": "result_bundle.v2_0.pkl",
                "experiment_type": "ins_oos",
                "selected_idxs": selected_idxs,
                "aws_profile": aws_profile,
            },
            "strategy_evaluator_kwargs": {
                "returns_col": "mid_ret_0",
                "position_intent_col": "position_intent_1",
                "spread_col": "spread",
                "abort_on_error": True,
            },
            "bh_adj_threshold": 0.1,
            "resample_rule": "W",
        }
    )

print(str(eval_config))

# %%
# result_bundle_dict[0]

# %%
# Build the ModelEvaluator from the eval config.
evaluator = cdtfmomoev.StrategyEvaluator.from_eval_config(eval_config)

# %%
if False:
    import helpers.hpickle as hpickle

    hpickle.to_pickle(evaluator, "evaluator.pkl")

# %%
assert 0

# %% [markdown]
# # Restart from pickle

# %%
# !du -h evaluator.pkl

# %%
spread_fraction_paid = 0
# keys = range(3)
keys = None
# result = evaluator.compute_pnl(key_type="attribute", keys=keys)
pnl_dict = evaluator.compute_pnl(
    spread_fraction_paid, keys=keys, key_type="instrument"
)

# pnl_dict[0]

# %%
# spread_fraction_paid = 0
# evaluator.calculate_stats(spread_fraction_paid)

import numpy as np

# %%
import pandas as pd

# %%
print(hdbg.get_memory_usage_as_str(None))

# del pnl_dict

import gc

gc.collect()

print(hdbg.get_memory_usage_as_str(None))


# %%
def _compute_pnl_dict(spread_fraction_paid):
    # keys = range(3)
    keys = None
    # result = evaluator.compute_pnl(key_type="attribute", keys=keys)
    pnl_dict = evaluator.compute_pnl(
        spread_fraction_paid, keys=keys, key_type="instrument"
    )
    return pnl_dict


def _get_pnl_df(pnl_dict):
    dfs = []
    for key in list(pnl_dict.keys()):
        srs = pnl_dict[key]["pnl_0"] - pnl_dict[key]["spread_cost_0"]
        srs.name = key
        dfs.append(srs)
    df = pd.concat(dfs, axis=1)
    # df.resample("1B").sum
    return df


def _aggregate_pnl(df):
    aggr_pnl = (
        df.resample("1B")
        .sum()
        .drop([224, 554, 311, 384, 589, 404], axis=1)
        .sum(axis=1)
        .cumsum()
    )
    return aggr_pnl


final_df = []
for sfp in [-0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03]:
    # for sfp in [-0.05, -0.03]:
    pnl_dict = _compute_pnl_dict(sfp)

    df = _get_pnl_df(pnl_dict)
    # print(df.shape)
    # df.head()

    aggr_df = _aggregate_pnl(df)
    # aggr_df.plot()
    aggr_df.name = sfp
    final_df.append(aggr_df)

    print(hdbg.get_memory_usage_as_str(None))

# %%
final_df2 = pd.concat(final_df, axis=1)

final_df2.plot()


# %%
def sr(srs):
    return srs.mean() / srs.std() * np.sqrt(252)


print("ins", sr(final_df2[:"2017-01-01"].diff()))
print("oos", sr(final_df2["2017-01-01":].diff()))

# %% [markdown]
# # Compare to event-based

# %%
sfp_gp = [0.45, 0.5, 0.51, 0.52, 0.53]
sfp_paul = [(x - 0.5) * 2 for x in sfp_gp]
print(sfp_paul)
final_df = []
for sfp in sfp_paul:
    # keys = range(3)
    keys = [0]
    # result = evaluator.compute_pnl(key_type="attribute", keys=keys)
    pnl_dict = evaluator.compute_pnl(sfp, keys=keys, key_type="instrument")

    key = keys[0]
    srs = pnl_dict[key]["pnl_0"] - pnl_dict[key]["spread_cost_0"]
    srs.name = sfp

    final_df.append(srs)

final_df = pd.concat(final_df, axis=1)

final_df.resample("1B").sum().cumsum().plot()

# %%
srs.cumsum().plot()

# %% [markdown]
# # Remove crap

# %%
pnlf_ = df.resample("1B").sum().diff()

pos = abs(pnl_).max()
pos
# mask = pnl_.tail(1) < 0
# pnl_.tail(1)[mask]

# %%
# pos.iloc[0].sort_values()
pos.sort_values().tail(10)

# %%
# df.resample("1B").sum().sum(axis=0).argmin()

# %%
# hdbg.get_memory_usage_as_str(None)

# %%
# #df.sum(axis=1).resample("1B").sum().cumsum().plot(color="k")
# df.resample("1B").sum().sum(axis=1).cumsum().plot(color="k")

# %%
aggr_pnl = (
    df.resample("1B")
    .sum()
    .drop([224, 554, 311, 384, 589, 404], axis=1)
    .sum(axis=1)
    .cumsum()
)

aggr_pnl.plot(color="k")

# %%
import numpy as np


def sr(srs):
    return srs.mean() / srs.std() * np.sqrt(252)


print("ins", sr(aggr_pnl[:"2017-01-01"].diff()))
print("oos", sr(aggr_pnl["2017-01-01":].diff()))

# %%
aggr_pnl["2018-06-06":].plot()
