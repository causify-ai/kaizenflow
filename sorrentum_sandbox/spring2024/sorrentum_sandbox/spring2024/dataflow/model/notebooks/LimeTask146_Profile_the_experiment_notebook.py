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

# %% [markdown]
# # Description
#
# - Initialize with returns, predictions, target volatility, and oos start date
# - Evaluate portfolios generated from the predictions

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import dataflow_model.model_evaluator as cdtfmomoev
import dataflow_model.model_plotter as cdtfmomopl

import core.config as cconfig
import dataflow.model.dataflow_utils as dtfbaexuti
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
# config = cconfig.Config.from_env_var("AM_CONFIG_CODE")
config = None

if config is None:
    # exp_dir = "/app/oos_experiment.RH2Eg.v2_0-top10.5T.run1_test"
    exp_dir = "/app/oos_experiment.RH2Eg.v2_0-top10.5T.run1_test"
    aws_profile = None
    # selected_idxs = None
    selected_idxs = range(3)

    eval_config = cconfig.Config.from_dict(
        {
            "load_experiment_kwargs": {
                "src_dir": exp_dir,
                "file_name": "result_bundle.v2_0.pkl",
                "experiment_type": "ins_oos",
                "selected_idxs": selected_idxs,
                "aws_profile": aws_profile,
            },
            "model_evaluator_kwargs": {
                "predictions_col": "mid_ret_0_vol_adj_clipped_2_hat",
                "target_col": "mid_ret_0_vol_adj_clipped_2",
                # "oos_start": "2017-01-01",
                "oos_start": None,
            },
            "bh_adj_threshold": 0.1,
            "resample_rule": "W",
            "mode": "ins",
            "target_volatility": 0.1,
        }
    )

print(str(eval_config))

# %% [markdown]
# # Initialize ModelEvaluator and ModelPlotter

# %%
load_config = eval_config["load_experiment_kwargs"].to_dict()

# Load only the columns needed by the ModelEvaluator.
load_config["load_rb_kwargs"] = {
    "columns": [
        eval_config["model_evaluator_kwargs"]["target_col"],
        eval_config["model_evaluator_kwargs"]["predictions_col"],
    ]
}
result_bundle_dict = dtfbaexuti.load_experiment_artifacts(**load_config)

# Build the ModelEvaluator.
evaluator = cdtfmomoev.ModelEvaluator.from_result_bundle_dict(
    result_bundle_dict,
    # abort_on_error=False,
    abort_on_error=True,
    **eval_config["model_evaluator_kwargs"].to_dict(),
)
# Build the ModelPlotter.
plotter = cdtfmomopl.ModelPlotter(evaluator)

# %%
for i in range(3):
    asset_id = result_bundle_dict[i].config["load_prices"]["source_node_kwargs"][
        "func_kwargs"
    ]["asset_id"]
    print(asset_id)

import datetime

import pandas as pd

# %%
import vendors_lime.taq_bars.utils as vltbut

# %%
# Load the 1min data.
asset_id = 10025
# asset_id = 10035
# asset_id = 10036
columns = [
    "end_time",
    "close",
    "volume",
    "egid",
    "good_ask",
    "good_bid",
    "good_bid_size",
    "good_ask_size",
]
cache_dir = "/cache/vltbut.get_bar_data.v2_1-all.2009_2019.20210907-07_52_53/cache.get_bar_data.v2_0-all.2009_2019"
df_1min = vltbut.load_single_instrument_data(
    asset_id,
    datetime.date(2009, 1, 1),
    datetime.date(2019, 1, 1),
    columns=columns,
    cache_dir=cache_dir,
)

df_1min.head()

# %%
columns = ["close", "good_bid", "good_ask"]
df_1min[columns].resample("1B").mean().plot()
df_1min[columns].pct_change().resample("1B").mean().plot()
thr = 0.002
df_1min_clean = vltbut.clean_bars(df_1min, columns, thr)

df_1min_clean[columns].resample("1B").mean().plot()
df_1min_clean[columns].pct_change().resample("1B").mean().plot()

# %%
# thr = 0.001
# for column in columns:
#     lower_bound = df_1min[column].quantile(thr)
#     upper_bound = df_1min[column].quantile(1.0 - thr)
#     mask = (df_1min[column] <= lower_bound) | (df_1min[column] >= upper_bound)
#     #print(mask)
#     #df_1min.loc[mask].resample("1B").mean().plot()
#     df_1min[mask] = np.nan
# #df_1min[df_1min <= lower_bound] = np.nan

# #df_1min[["good_ask", "good_bid", "close"]].quantile(0.99)
# df_1min[["good_ask", "good_bid", "close"]].resample("1B").mean().plot()
# #df_1min[["close"]].resample("1B").mean().plot()

# %%
# mask = df_1min["close"] < 0.40
# df_1min[mask]

# ret_0 = df_1min.pct_change()
# ret_0.resample("1B").mean().plot()

# %%
# #mad_func = lambda x: np.fabs(x - x.mean()).mean()
# #mad = df_1min["close"].dropna().rolling(window=60).apply(mad_func, raw=True)

# mad = df_1min["close"].dropna().rolling(window=60).quantile(.01)

# #df_1min["close"] +
# #.plot(style='k')

# mad.resample("1B").mean().plot()

# %%
# df_1min["close"].hist(bins=101)
# df_1min[["close"]].min()

# %%
df_1min_out = (
    df_1min_clean[columns].resample("1T", closed="right", label="right").mean()
)
# mask = df_1min_out < 0.40
# df_1min_out = df_1min_out[~mask]

df_1min_out.ffill(limit=None, inplace=True)
# .sum(min_count=1) #.replace(np.nan, 0)

df_1min_out.columns = ["price", "bid", "ask"]
df_1min_out.resample("1B").mean().plot()

df_1min_out.dropna().head()

# %%
# df_1min_out["price"].hist(bins=101)

# %%
df_price = df_1min_out.resample("5T", closed="right", label="right").last()
df_price["ret_0"] = df_price["price"].pct_change()
df_price.resample("1D").mean().plot()

# %%
# import pandas as pd
# df_5mins.loc[pd.Timestamp("2009-01-02 17:00:00-05:00")]

# %%
# df_1min_out.loc[pd.Timestamp("2009-01-05 13:40:00-05:00"):pd.Timestamp("2009-01-05 14:00:00-05:00")]

# %%
df_1min_out["midpoint"] = (df_1min_out["bid"] + df_1min_out["ask"]) / 2

# %%
df_1min_out.head()

# %%
import oms.obsolete.pnl_simulator as oobpnsim

df_5mins = result_bundle_dict[0].result_df[["mid_ret_0_vol_adj_clipped_2_hat"]]
df_5mins.columns = ["preds"]
df_5mins.dropna(inplace=True)


initial_wealth = 1e6
config = {
    "price_column": "price",
    "future_snoop_allocation": False,
    "order_type": "price@end",
    # "order_type": "midpoint@end",
    # "order_type": "full_spread@end",
    "use_cache": True,
    "cached_columns": ["price", "midpoint", "bid", "ask"],
}
mi = oobpnsim.MarketInterface(
    df_1min_out, config["use_cache"], columns=config.get("cached_columns", None)
)

# %%
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
# wealth, ret, df_5mins_out = oobpnsim.compute_pnl_level1(initial_wealth, df_1min_out, df_5mins)

df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "midpoint@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
# wealth, ret, df_5mins_out = oobpnsim.compute_pnl_level1(initial_wealth, df_1min_out, df_5mins)

df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "midpoint@twap"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)

df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()


# %%
config["order_type"] = "partial_spread_0.5@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
# wealth, ret, df_5mins_out = oobpnsim.compute_pnl_level1(initial_wealth, df_1min_out, df_5mins)

df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "partial_spread_0.0@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
# wealth, ret, df_5mins_out = oobpnsim.compute_pnl_level1(initial_wealth, df_1min_out, df_5mins)

df_5mins_out["wealth"].resample("1b").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "partial_spread_0.3@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
df_5mins_out["wealth"].resample("1b").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "partial_spread_0.51@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
df_5mins_out["wealth"].resample("1b").mean().plot()  # ["2012-01-01":].plot()

# %%
config["order_type"] = "full_spread@end"
df_5mins_out = oobpnsim.compute_pnl_level2(mi, df_5mins, initial_wealth, config)
# wealth, ret, df_5mins_out = oobpnsim.compute_pnl_level1(initial_wealth, df_1min_out, df_5mins)

df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
df_all2 = pd.DataFrame()
for order_type in ["partial_spread_0.5@end", "midpoint@end", "midpoint@twap"]:
    config["order_type"] = order_type
    df_5mins_out = oobpnsim.compute_pnl_level2(
        mi, df_5mins, initial_wealth, config
    )
    df_all2[order_type] = df_5mins_out["wealth"]

df_all2.resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
df_all = pd.DataFrame()
for order_type in [
    # "partial_spread_0.3@end",
    # "partial_spread_0.4@end",
    "partial_spread_0.45@end",
    "partial_spread_0.5@end",
    "partial_spread_0.51@end",
    "partial_spread_0.52@end",
    "partial_spread_0.53@end",
]:
    config["order_type"] = order_type
    df_5mins_out = oobpnsim.compute_pnl_level2(
        mi, df_5mins, initial_wealth, config
    )
    df_all[order_type] = df_5mins_out["wealth"]

df_all.resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
df_5mins_out.tail()

# %%
df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
df_5mins_out["wealth"].resample("1B").mean().plot()  # ["2012-01-01":].plot()

# %%
df_5mins_merged = df_5mins_out.merge(df_price, right_index=True, left_index=True)

_, df_5mins_merged = oobpnsim.compute_lag_pnl(df_5mins_merged)
# display(df_5mins_merged)
# df_5mins_merged["pnl.lag"].cumsum().plot()
df_5mins_merged["pnl.sim1"].cumsum().plot()

# %%
df_5mins_out

# %%

# %% [markdown]
# # Analysis

# %%
pnl_stats = evaluator.calculate_stats(
    mode=eval_config["mode"], target_volatility=eval_config["target_volatility"]
)
display(pnl_stats)

# %% [markdown]
# ## Model selection

# %%
plotter.plot_multiple_tests_adjustment(
    threshold=eval_config["bh_adj_threshold"], mode=eval_config["mode"]
)

# %%
# TODO(gp): Move this chunk of code in a function.
col_mask = (
    pnl_stats.loc["signal_quality"].loc["sr.adj_pval"]
    < eval_config["bh_adj_threshold"]
)
selected = pnl_stats.loc[:, col_mask].columns.to_list()
not_selected = pnl_stats.loc[:, ~col_mask].columns.to_list()

print("num model selected=%s" % hprint.perc(len(selected), pnl_stats.shape[1]))
print("model selected=%s" % selected)
print("model not selected=%s" % not_selected)

# Use `selected = None` to show all the models.

# %%
plotter.plot_multiple_pnls(
    keys=selected,
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)

# %% [markdown]
# ## Return correlation

# %%
plotter.plot_correlation_matrix(
    series="returns",
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)

# %%
plotter.plot_effective_correlation_rank(
    series="returns",
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)

# %% [markdown]
# ## Model correlation

# %%
plotter.plot_correlation_matrix(
    series="pnl",
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)

# %%
plotter.plot_effective_correlation_rank(
    series="pnl",
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)

# %% [markdown]
# ## Aggregate model

# %%
pnl_srs, pos_srs, aggregate_stats = evaluator.aggregate_models(
    keys=selected,
    mode=eval_config["mode"],
    target_volatility=eval_config["target_volatility"],
)
display(aggregate_stats)

# %%
plotter.plot_sharpe_ratio_panel(keys=selected, mode=eval_config["mode"])

# %%
plotter.plot_rets_signal_analysis(
    keys=selected,
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
    target_volatility=eval_config["target_volatility"],
)

# %%
plotter.plot_performance(
    keys=selected,
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
    target_volatility=eval_config["target_volatility"],
)

# %%
plotter.plot_rets_and_vol(
    keys=selected,
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
    target_volatility=eval_config["target_volatility"],
)

# %%
assert 0

# %%
plotter.plot_positions(
    keys=selected,
    mode=eval_config["mode"],
    target_volatility=eval_config["target_volatility"],
)

# %%
# Plot the returns and prediction for one or more models.
model_key = selected[:1]
plotter.plot_returns_and_predictions(
    keys=model_key,
    resample_rule=eval_config["resample_rule"],
    mode=eval_config["mode"],
)
