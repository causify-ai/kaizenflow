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

# %% [markdown]
# Compute and analyze model performance stats.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import datetime
import logging
from typing import Any, Callable, List

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as st

import core.config.config_ as cconconf
import core.config.config_utils as ccocouti
import core.statistics.requires_statsmodels as cstresta
import core.statistics.sharpe_ratio as cstshrat
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.crypto_chassis.data.client as iccdc

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs

# %%
def get_notebook_config() -> cconconf.Config:
    """
    Get notebook specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "im_client_params": {
            "universe_version": "v2",
            "resample_1min": True,
            "dataset": "ohlcv",
            "contract_type": "spot",
            "data_snapshot": "20220530",
        },
        "data": {
            "dir_name": "/shared_data/model/historical/experiment.E1a.crypto_chassis_v2-all.5T.2018_2022/tiled_results/",
            "columns": "volume vwap vwap.ret_0 vwap.ret_0.vol_adj vwap.ret_0.vol_adj.c vwap.ret_0.vol_adj.shift_-2 vwap.ret_0.vol_adj.shift_-2_hat".split(),
            "start_date": datetime.date(2018, 1, 1),
            "end_date": datetime.date(2022, 5, 1),
        },
        "column_names": {
            "asset_id": "asset_id",
            "timestamp": "end_ts",
            "volume": "volume",
            "y": "vwap.ret_0.vol_adj.shift_-2",
            "y_hat": "vwap.ret_0.vol_adj.shift_-2_hat",
            "hit": "hit",
            "trade_pnl": "trade_pnl",
        },
        "stats_kwargs": {
            "quantile_ranks": 10,
            # 28500 is the number of 5-minute intervals in ATH in a year.
            "time_scaling": 28500,
            "n_resamples": 1000,
            "alpha": 0.05,
        },
        "plot_kwargs": {
            "y_min_lim_hit_rate": 49,
            "y_max_lim_hit_rate": 54,
            "color": "C0",
            "capsize": 0.2,
            "xticks_rotation": 70,
        },
    }
    config = cconfig.Config.from_dict(param_dict)
    return config


# %%
config = get_notebook_config()
print(config)


# %% [markdown]
# # Functions

# %%
def load_predictions_df(config: cconconf.Config) -> pd.DataFrame:
    """
    Get data with ML predictions.
    """
    backtest_df_iter = dtfmod.yield_processed_parquet_tiles_by_year(
        config["data"]["dir_name"],
        config["data"]["start_date"],
        config["data"]["end_date"],
        config["column_names"]["asset_id"],
        data_cols=config["data"]["columns"],
        asset_ids=None,
    )
    #
    #
    predict_df = pd.concat(backtest_df_iter)
    predict_df = predict_df.sort_index()
    return predict_df


# TODO(Max): Move the code out of the lib so we can unit test,
# e.g., we want to add (small) specific unit tests for hit.
# TODO(Max): Harmonize the code with calculate_hit_rate and other code there.
# E.g., factor out the piece of calculate_hit_rate that computes hit, etc.
def preprocess_predictions_df(
    config: cconconf.Config, predict_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Preprocess data with ML predictions for analysis.

    Input:

    ```
                        volume                  vwap
    asset_id            1464553467  1467591036  1464553467  1467591036
    end_ts
    2018-01-01 09:35:00   314.0657     47.3976    729.7789  12887.3945
    2018-01-01 09:40:00   178.6543     35.1098    731.0134  12913.6854
    ```

    Output:

    ```
                                              volume        vwap
    end_ts                        asset_id
    2018-01-01 09:35:00  binance::ETH_USDT  314.0657    729.7789
                         binance::BTC_USDT   47.3976  12887.3945
    2018-01-01 09:40:00  binance::ETH_USDT  178.6543    731.0134
                         binance::BTC_USDT   35.1098  12913.6854
    ```
    """
    # Convert the prediction stats data to Multiindex by time and asset id.
    metrics_df = predict_df.stack()
    # Drop NaNs to compute the performance statistics.
    metrics_df = hpandas.dropna(metrics_df, report_stats=True)
    # Compute hit.
    metrics_df["hit"] = (
        metrics_df[config["column_names"]["y"]]
        * metrics_df[config["column_names"]["y_hat"]]
        >= 0
    )
    # Convert hit rates to desired format (`calculate_hit_rate` input).
    metrics_df["hit"] = metrics_df["hit"].replace(True, 1)
    metrics_df["hit"] = metrics_df["hit"].replace(False, -1)
    # Compute trade PnL.
    metrics_df["trade_pnl"] = (
        metrics_df[config["column_names"]["y"]]
        * metrics_df[config["column_names"]["y_hat"]]
    )
    # TODO(*): Think about avoiding using `ImClient` for mapping.
    # Convert asset ids to full symbols using `ImClient` mapping.
    im_client = iccdc.get_CryptoChassisHistoricalPqByTileClient_example1(
        **config["im_client_params"]
    )
    metrics_df.index = metrics_df.index.set_levels(
        metrics_df.index.levels[1].map(
            im_client._asset_id_to_full_symbol_mapping
        ),
        level=1,
    )
    return metrics_df


# TODO(*): Consider using bootstraping function from SciPy
#  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html.
# TODO(Dan): Consider to return CI values.
def bootstrap(
    data: pd.Series, func: Callable, n_resamples: int = 100
) -> List[Any]:
    """
    Bootstrap computations on specified number of data resamples.

    :param data: input data to resample
    :param func: function accepting a series and returning a single scalar value
    :param n_resamples: number of resamples to create
    :return: bootstrapped computations
    """
    res_list = []
    for i in range(n_resamples):
        resampled_data = data.sample(frac=1, replace=True)
        res = func(resampled_data)
        res_list.append(res)
    return res_list


def compute_sharpe_ratio(
    config: cconconf.Config, metrics_df: pd.DataFrame, by_col: str
) -> None:
    """
    Compute Sharpe Ratio by specified column.
    """
    res_list = []
    for by, data in metrics_df.groupby(by_col):
        srs = data[config["column_names"]["trade_pnl"]].dropna()
        func = lambda pnl: cstshrat.compute_sharpe_ratio(
            pnl, time_scaling=config["stats_kwargs"]["time_scaling"]
        )
        # Multiple Sharpe Ratios are being computed on many resamples
        # in order to find and plot confidence intervals.
        sharpe_ratio_srs = pd.Series(
            bootstrap(srs, func, config["stats_kwargs"]["n_resamples"]),
            name="sharpe_ratio",
        )
        # Transform and combine data for plotting.
        sharpe_ratio_df = sharpe_ratio_srs.to_frame()
        sharpe_ratio_df[by_col] = by
        res_list.append(sharpe_ratio_df)
    res_df = pd.concat(res_list)
    #
    return res_df


def calculate_hit_rate_with_CI(
    df: pd.DataFrame, group_by: str, value_col: str
) -> pd.DataFrame:
    """
    Compute hit rates, confidence intervals and errors relative to the specific
    entity.

    :param df: data with hit rates values
    :param group_by: column name for grouping entity
    :param value_col: column name for PnL data
    :return: data with CIs and errors
    """
    # Calculate mean value of statistics as well as CIs for each entity.
    hit_df_stacked = df.groupby([group_by])[value_col].apply(
        lambda data: cstresta.calculate_hit_rate(
            data, alpha=config["stats_kwargs"]["alpha"]
        )
    )
    # Process the output and add errors.
    hit_df = hit_df_stacked.unstack()
    hit_errors_df = add_errors_to_ci_data(hit_df)
    return hit_errors_df


def calculate_CI_for_PnLs_or_SR(
    df: pd.DataFrame, group_by: str, value_col: str
) -> pd.DataFrame:
    """
    Compute mean PnL or Sharpe Ratio, confidence intervals and errors relative
    to the specific entity.

    :param df: data with PnL or Sharpe Ratio values
    :param group_by: column name for grouping entity
    :param value_col: column name for PnL or Sharpe Ratio data
    :return: data with CIs and errors
    """
    grouper = df.groupby([group_by])[value_col]
    # Calculate mean value of statistics for each entity.
    pnl_df = grouper.mean().to_frame()
    # Compute confidence intervals.
    conf_ints = grouper.apply(
        lambda data: st.t.interval(
            1 - config["stats_kwargs"]["alpha"],
            data.size - 1,
            np.mean(data),
            st.sem(data),
        )
    )
    # Attach confidence intervals to the mean value data.
    pnl_df[["low", "high"]] = pd.DataFrame(conf_ints.tolist(), index=pnl_df.index)
    # Unify columns and calculate errors (required values for plotting).
    pnl_errors_df = add_errors_to_ci_data(pnl_df)
    return pnl_errors_df


def add_errors_to_ci_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process CI data and add errors.
    """
    # Unify columns for all plotting data.
    df.columns = ["y", "ci_low", "ci_high"]
    # Required values for plotting (`yerr` input).
    df["errors"] = (df["ci_high"] - df["ci_low"]) / 2
    return df


def plot_stats_barplot(
    df: pd.DataFrame,
    sort_by: str,
    ascending: bool,
    ylabel: str,
    ylim_min: str,
    ylim_max: str,
) -> None:
    """
    :param df: data with prediction statistics
    :param sort_by: sorting parameter (e.g., by value, by asset, or None)
    :param ylabel: name of the Y-axis graph
    :param ylim_min: lower value on Y-axis graph scale
    :param ylim_max: upper value on Y-axis graph scale
    :return: barplot with model performance statistics
    """
    # Sort data according to the input params.
    if sort_by == "x":
        df_sorted = df.sort_index(ascending=ascending)
    elif not sort_by:
        df_sorted = df.copy()
    else:
        df_sorted = df.sort_values(by=sort_by, ascending=ascending)
    # Specify errors for plotting.
    errors = df_sorted["errors"]
    # Plotting params.
    df_sorted["y"].plot.bar(
        yerr=errors,
        capsize=4,
        width=0.8,
    )
    plt.xticks(rotation=xticks_rotation)
    plt.ylabel(ylabel)
    plt.ylim(ylim_min, ylim_max)
    plt.show()


def plot_bars_with_widget(
    df: pd.DataFrame,
    ylabel: str,
    ylim_min: float,
    ylim_max: float,
) -> None:
    """
    Add widgets to expand the sorting parameters for barplots.

    :param df: data with prediction statistics
    :param ylabel: name of the Y-axis graph
    :param ylim_min: lower value on Y-axis graph scale
    :param ylim_max: upper value on Y-axis graph scale
    :return: barplot with edible model performance statistics
    """
    _ = widgets.interact(
        plot_stats_barplot,
        df=widgets.fixed(df),
        sort_by=widgets.ToggleButtons(
            options=["x", "y", "ci_low", "ci_high", False], description="Sort by:"
        ),
        ascending=widgets.ToggleButtons(
            options=[True, False], description="Ascending:"
        ),
        ylabel=widgets.fixed(ylabel),
        ylim_min=widgets.FloatText(
            value=ylim_min,
            description="Min y-value:",
        ),
        ylim_max=widgets.FloatText(
            value=ylim_max,
            description="Max y-value:",
        ),
    )


# %% [markdown]
# # Load data with predictions

# %%
predict_df = load_predictions_df(config)
print(predict_df.shape)
predict_df.head(3)

# %% [markdown]
# # Compute overall PnL

# %%
(
    predict_df[config["column_names"]["y"]]
    * predict_df[config["column_names"]["y_hat"]]
).sum(axis=1).cumsum().plot()

# %% [markdown]
# # Get data for analysis

# %%
metrics_df = preprocess_predictions_df(config, predict_df)
metrics_df.head()

# %%
# Reset index to ease further preprocessing.
# TODO(Dan): Move index resetting under plotting funtions.
metrics_df_reset_index = metrics_df.reset_index()

# %% [markdown]
# # Stats

# %%
# Set oftenly used config parameters.
asset_id = config["column_names"]["asset_id"]
timestamp = config["column_names"]["timestamp"]
volume = config["column_names"]["volume"]
y = config["column_names"]["y"]
y_hat = config["column_names"]["y_hat"]
hit = config["column_names"]["hit"]
trade_pnl = config["column_names"]["trade_pnl"]
#
quantile_ranks = config["stats_kwargs"]["quantile_ranks"]
y_min_lim_hit_rate = config["plot_kwargs"]["y_min_lim_hit_rate"]
y_max_lim_hit_rate = config["plot_kwargs"]["y_max_lim_hit_rate"]
color = config["plot_kwargs"]["color"]
capsize = config["plot_kwargs"]["capsize"]
xticks_rotation = config["plot_kwargs"]["xticks_rotation"]

# %% [markdown]
# ## By asset

# %% [markdown]
# ### Hit rate

# %%
hit_by_asset = calculate_hit_rate_with_CI(metrics_df_reset_index, asset_id, hit)
plot_bars_with_widget(
    hit_by_asset, "hit_rate", y_min_lim_hit_rate, y_max_lim_hit_rate
)

# %% [markdown]
# ### PnL

# %%
# Compute PnL for each asset id.
pnl_stats = (
    metrics_df.groupby(asset_id)[trade_pnl].sum().sort_values(ascending=False)
)
pnl_stats = pnl_stats.rename("y").to_frame()
# Confidence Intervals are currently excluded.
pnl_stats["errors"] = 0
# Plot PnL per asset id.
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_stats, "avg_pnl_by_asset", 0, 450)

# %%
# Plot cumulative PnL over time per asset id.
_ = metrics_df[trade_pnl].dropna().unstack().cumsum().plot()

# %%
# Plot average trade PnL per asset id.
avg_pnl_by_asset = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, asset_id, trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(avg_pnl_by_asset, "avg_pnl_by_asset", 0, 0.005)

# %% [markdown]
# ### Sharpe Ratio

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_asset = compute_sharpe_ratio(config, metrics_df_reset_index, asset_id)
# Add CIs and errors.
sr_ci_by_asset = calculate_CI_for_PnLs_or_SR(
    sr_by_asset, asset_id, "sharpe_ratio"
)
# Visualize results.
plot_bars_with_widget(sr_ci_by_asset, "sharpe_ratio", 0, 9)

# %% [markdown]
# ## By time

# %%
metrics_df_reset_index["hour"] = metrics_df_reset_index[timestamp].dt.hour
metrics_df_reset_index["weekday"] = metrics_df_reset_index[
    timestamp
].dt.day_name()
metrics_df_reset_index["month"] = metrics_df_reset_index[
    timestamp
].dt.month_name()

# %% [markdown]
# ### Hit Rate

# %%
hits_by_time_hour = calculate_hit_rate_with_CI(
    metrics_df_reset_index, "hour", hit
)
plot_bars_with_widget(
    hits_by_time_hour, "avg_hit_rate", y_min_lim_hit_rate, y_max_lim_hit_rate
)

# %%
hits_by_time_weekday = calculate_hit_rate_with_CI(
    metrics_df_reset_index, "weekday", hit
)
plot_bars_with_widget(
    hits_by_time_weekday, "avg_hit_rate", y_min_lim_hit_rate, y_max_lim_hit_rate
)

# %%
hits_by_time_month = calculate_hit_rate_with_CI(
    metrics_df_reset_index, "month", hit
)
plot_bars_with_widget(
    hits_by_time_month, "avg_hit_rate", y_min_lim_hit_rate, y_max_lim_hit_rate
)

# %% [markdown]
# ### PnL

# %%
pnl_by_time_hour = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, "hour", trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_by_time_hour, "avg_pnl", 0, 0.005)

# %%
pnl_by_time_weekday = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, "weekday", trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_by_time_weekday, "avg_pnl", 0, 0.004)

# %%
pnl_by_time_month = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, "month", trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_by_time_month, "avg_pnl", 0, 0.0055)

# %% [markdown]
# ### Sharpe Ratio

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_hour = compute_sharpe_ratio(config, metrics_df_reset_index, "hour")
# Add CIs and errors.
sr_ci_by_hour = calculate_CI_for_PnLs_or_SR(sr_by_hour, "hour", "sharpe_ratio")
# Visualize results.
plot_bars_with_widget(sr_ci_by_hour, "sharpe_ratio", 0, 9)

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_weekday = compute_sharpe_ratio(config, metrics_df_reset_index, "weekday")
# Add CIs and errors.
sr_ci_by_weekday = calculate_CI_for_PnLs_or_SR(
    sr_by_weekday, "weekday", "sharpe_ratio"
)
# Visualize results.
plot_bars_with_widget(sr_ci_by_weekday, "sharpe_ratio", 0, 7)

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_month = compute_sharpe_ratio(config, metrics_df_reset_index, "month")
# Add CIs and errors.
sr_ci_by_month = calculate_CI_for_PnLs_or_SR(sr_by_month, "month", "sharpe_ratio")
# Visualize results.
plot_bars_with_widget(sr_ci_by_month, "sharpe_ratio", 0, 9)

# %% [markdown]
# ## By prediction magnitude

# %%
prediction_magnitude = ".".join([y_hat, "quantile_rank"])
metrics_df_reset_index[prediction_magnitude] = pd.qcut(
    metrics_df_reset_index[y_hat], quantile_ranks, labels=False
)

# %% [markdown]
# ### Hit rate

# %%
hits_by_prediction_magnitude = calculate_hit_rate_with_CI(
    metrics_df_reset_index, prediction_magnitude, hit
)
plot_bars_with_widget(
    hits_by_prediction_magnitude,
    "avg_hit_rate",
    y_min_lim_hit_rate,
    y_max_lim_hit_rate,
)

# %% [markdown]
# ### PnL

# %%
pnl_by_prediction_magnitude = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, prediction_magnitude, trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_by_prediction_magnitude, "avg_pnl", 0, 0.01)

# %% [markdown]
# ### Sharpe Ratio

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_prediction_magnitude = compute_sharpe_ratio(
    config, metrics_df_reset_index, prediction_magnitude
)
# Add CIs and errors.
sr_ci_by_prediction_magnitude = calculate_CI_for_PnLs_or_SR(
    sr_by_prediction_magnitude, prediction_magnitude, "sharpe_ratio"
)
# Visualize results.
plot_bars_with_widget(sr_ci_by_prediction_magnitude, "sharpe_ratio", -1, 12)

# %% [markdown]
# ## By volume

# %%
volume_quantile = ".".join([volume, "quantile_rank"])
metrics_df_reset_index[volume_quantile] = metrics_df_reset_index.groupby(
    asset_id
)[volume].transform(lambda x: pd.qcut(x, quantile_ranks, labels=False))

# %% [markdown]
# ### Hit rate

# %%
hits_by_volume = calculate_hit_rate_with_CI(
    metrics_df_reset_index, volume_quantile, hit
)
plot_bars_with_widget(
    hits_by_volume, "avg_hit_rate", y_min_lim_hit_rate, y_max_lim_hit_rate
)

# %% [markdown]
# ### PnL

# %%
pnl_by_volume = calculate_CI_for_PnLs_or_SR(
    metrics_df_reset_index, volume_quantile, trade_pnl
)
# TODO(Max): infer y-limits automatically.
plot_bars_with_widget(pnl_by_volume, "avg_pnl", 0.0005, 0.0045)

# %% [markdown]
# ### Sharpe Ratio

# %%
# Compute bootstrapped Sharpe Ratio.
sr_by_volume_quantile = compute_sharpe_ratio(
    config, metrics_df_reset_index, volume_quantile
)
# Add CIs and errors.
sr_ci_by_volume_quantile = calculate_CI_for_PnLs_or_SR(
    sr_by_volume_quantile, volume_quantile, "sharpe_ratio"
)
# Visualize results.
plot_bars_with_widget(sr_ci_by_volume_quantile, "sharpe_ratio", 0, 9)
