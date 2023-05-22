# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import core.plotting as coplotti
import dataflow.backtest.dataflow_backtest_utils as dtfbdtfbaut
import dataflow.model.stats_computer as dtfmostcom
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

# _LOG.info("%s", env.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load features

# %%
feat_iter = dtfbdtfbaut.yield_experiment_artifacts(
    src_dir="",
    file_name="result_bundle.v2_0.pkl",
    load_rb_kwargs={},
)

# %%
key, artifact = next(feat_iter)
display("key=%s", key)
features = artifact.result_df

# %%
features.head()

# %% [markdown]
# # Cross-sectional feature analysis

# %%
coplotti.plot_heatmap(features.corr(), mode="clustermap", figsize=(20, 20))

# %%
coplotti.plot_effective_correlation_rank(features)

# %%
coplotti.plot_projection(features.resample("B").sum(min_count=1))

# %%
sc = dtfmostcom.StatsComputer()

# %%
features.apply(sc.compute_summary_stats).round(3)

# %% [markdown]
# # Single feature analysis

# %%
feature = ""

# %%
coplotti.plot_qq(features[feature])

# %%
coplotti.plot_histograms_and_lagged_scatterplot(
    features[feature], lag=1, figsize=(20, 20)
)

# %%
coplotti.plot_time_series_by_period(
    features[feature],
    "hour",
)

# %%
