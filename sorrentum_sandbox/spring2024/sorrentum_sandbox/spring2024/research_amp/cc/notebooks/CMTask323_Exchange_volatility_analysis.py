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
# # Imports

# %%
import os

import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smapi
import statsmodels.tsa.stattools as smtools

import core.config.config_ as cconconf
import core.plotting as coplotti
import helpers.hs3 as hs3
import im_v2.common.universe as ivcu
import research_amp.cc.statistics as ramccsta

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Config

# %%
def get_cmtask323_config() -> cconconf.Config:
    """
    Get task323-specific config.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = AM_AWS_PROFILE
    config["load"]["data_dir"] = os.path.join(
        hs3.get_s3_bucket_path(AM_AWS_PROFILE), "data"
    )
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["data_type"] = "OHLCV"
    config["data"]["universe_version"] = "v03"
    config["data"]["vendor"] = "CCXT"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["volume"] = "volume"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange"] = "exchange_id"
    config["column_names"]["close"] = "close"
    return config


config = get_cmtask323_config()
print(config)


# %% [markdown]
# # Functions

# %%
def compute_volatility_for_each_coin(data: pd.DataFrame, freq: str, span: int):
    """
    Load and transform each (exchange-coin) dataframe to compute 18-period ema
    volatility.

    Parameters: initial DataFrame from the universe, resampling frequency
    """
    data["date"] = data.index
    # TODO(Max): Try out our resampe_df() for resampling.
    resample_close = data.groupby(
        ["currency_pair", "exchange_id", pd.Grouper(key="date", freq=freq)]
    )["close"].last()
    vix_df = resample_close.pct_change().transform(
        lambda x: x.ewm(span=span, adjust=False).std()
    )
    vix_df = vix_df.reset_index()
    return vix_df


def get_daily_close(data: pd.DataFrame, freq: str):
    """
    Load and transform each (exchange-coin) dataframe to compute volatility for
    the whole period.

    Parameters: initial DataFrame from the universe, resampling frequency
    """
    data["date"] = data.index
    resample_close = data.groupby(
        ["currency_pair", "exchange_id", pd.Grouper(key="date", freq=freq)]
    )["close"].last()
    resample_close = resample_close.reset_index()
    return resample_close


def get_df_with_coin_price_volatility(data: pd.DataFrame, display_plot: bool):
    """
    Unify volatility values for each coin and plot the graph.

    Parameters: DataFrame with computed volatility, boolean value to plot the graph
    """
    vix_df = data.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["close"].mean()
    vix_df = vix_df.to_frame()
    vix_df.columns = ["ema_volatility"]
    if display_plot:
        sns.set(rc={"figure.figsize": (15, 8)})
        sns.lineplot(
            data=vix_df, x="date", y="ema_volatility", hue="currency_pair"
        ).set(title=f"EMA of Volatility for each coin")
    return vix_df


def get_overall_returns_volatility(data: pd.DataFrame, display_plot: bool):
    """
    Unify volatility values for each coin for the whole period and plot the
    barplot.

    Parameters: DataFrame with computed volatility, boolean value to plot the graph
    """
    close_df = daily_close.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["close"].mean()
    rets_df = close_df.groupby(["currency_pair"]).pct_change()
    std_df = rets_df.groupby(["currency_pair"]).std()
    if display_plot:
        coplotti.plot_barplot(
            std_df.sort_values(ascending=False),
            title="Volatility per coin for the whole period (1-day basis, log-scaled)",
            figsize=[15, 7],
            yscale="log",
        )
    return std_df


def perform_adf_test(df_daily: pd.DataFrame):
    """
    Perform ADF test to check the stationarity of volatility values
    Parameters: Daily DataFrame with computed volatility
    """
    final_result = []
    coin_list = df_daily.reset_index()["currency_pair"].unique()
    for coin in coin_list:
        result = pd.DataFrame()
        df = df_daily.loc[[coin]]
        df = df[df["ema_volatility"].notna()].copy()
        X = df["ema_volatility"].values
        test_result = smtools.adfuller(X)
        result.loc[f"{coin}", "ADF Statistic"] = test_result[0]
        result.loc[f"{coin}", "p-value"] = test_result[1]
        final_result.append(result)
    final_result = pd.concat(final_result)
    final_result["is_unit_root_and_non-stationary (5% sign. level)"] = (
        final_result["p-value"] > 0.05
    )
    return final_result


def get_df_with_volume_and_volatility(data: pd.DataFrame, freq: str, span: int):
    """
    Load and transform each (exchange-coin) dataframe with volumes and close
    prices (to compute 18-period ema volatility).

    Parameters: initial DataFrame from the universe, resampling frequency
    """
    data["date"] = data.index
    close = data.groupby(
        ["currency_pair", "exchange_id", pd.Grouper(key="date", freq=freq)]
    )["close"].last()
    volume = data.groupby(
        ["currency_pair", "exchange_id", pd.Grouper(key="date", freq=freq)]
    )["volume"].sum()
    close_volume = pd.concat([close, volume], axis=1)
    close_volume["ema_volatility"] = (
        close_volume["close"]
        .pct_change()
        .transform(lambda x: x.ewm(span=span, adjust=False).std())
    )
    vix_volume = close_volume.reset_index()
    return vix_volume


def run_regressions(df: pd.DataFrame, lag_volume: bool):
    """
    Run OLS regression of volatility to volume (with intercept) for daily
    values.

    Parameters: price-volatility DataFrame, bool value for lagging volume variable
    """
    volatility = df.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["ema_volatility"].mean()
    volume = df.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["volume"].sum()
    vix_volume = pd.concat([volatility, volume], axis=1)
    vix_volume = vix_volume.reset_index()
    coin_list = vix_volume["currency_pair"].unique()
    model_results_dict = {}
    for coin in coin_list:
        coin_df = vix_volume[vix_volume["currency_pair"] == coin]
        new_coin_df = coin_df.copy()
        new_coin_df["lag_volume"] = coin_df["volume"].shift(1)
        if lag_volume:
            model = smapi.ols("ema_volatility ~ lag_volume", new_coin_df).fit()
        else:
            model = smapi.ols("ema_volatility ~ volume", new_coin_df).fit()
        map_dict = {coin: model.summary()}
        model_results_dict.update({coin: model.summary()})
    return model_results_dict


def calculate_corr_and_plot_scatter_plots(df: pd.DataFrame, display_plot: bool):
    """
    Plot the scatter plots for (volatility-exchange) pairs.

    Parameters: price-volatility DataFrame, boolean value to plot the graph
    """
    volatility = df.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["ema_volatility"].mean()
    volume = df.groupby(
        ["currency_pair", pd.Grouper(key="date", freq=frequency)]
    )["volume"].sum()
    vix_volume = pd.concat([volatility, volume], axis=1)
    vix_volume = vix_volume.reset_index()
    grouper = vix_volume.groupby(["currency_pair"])
    corr = grouper.corr()
    if display_plot:
        coin_list = vix_volume["currency_pair"].unique()
        for coin in coin_list:
            coin_df = vix_volume[vix_volume["currency_pair"] == coin]
            # TODO(Max): check scatter-plotting functions in core.plotting.py
            sns.lmplot(
                x="ema_volatility",
                y="volume",
                data=coin_df,
                fit_reg=True,
                line_kws={"color": "red"},
            ).fig.suptitle(f"{coin}")
    return corr


# %% [markdown]
# # Volatility Analysis

# %% [markdown]
# ## 1 day

# %%
type(18)

# %% run_control={"marked": false}
frequency = "1D"
universe = ivcu.get_vendor_universe("CCXT", version="v3", as_full_symbol=True)
compute_daily_vix_ema = lambda data: compute_volatility_for_each_coin(
    data, freq=frequency, span=18
)
daily_vix_ema = ramccsta.compute_stats_for_universe(
    universe, config, compute_daily_vix_ema
)

# %%
ema_df_daily = get_df_with_coin_price_volatility(daily_vix_ema, display_plot=True)
display(ema_df_daily)

# %% [markdown]
# ## 5 min

# %%
frequency = "5min"
compute_5min_vix_ema = lambda data: compute_volatility_for_each_coin(
    data, freq=frequency, span=18
)
vix_ema_5min = ramccsta.compute_stats_for_universe(
    universe, config, compute_5min_vix_ema
)

# %%
ema_df_5min = get_df_with_coin_price_volatility(vix_ema_5min, display_plot=True)
display(ema_df_5min)

# %% [markdown]
# ## Volatility for the whole period (1-day frequency)

# %%
frequency = "1D"
compute_daily_close = lambda data: get_daily_close(data, freq=frequency)
daily_close = ramccsta.compute_stats_for_universe(
    universe, config, compute_daily_close
)

# %%
std_df = get_overall_returns_volatility(daily_close, display_plot=True)
display(std_df)

# %% [markdown]
# # Test for stationarity of volatility

# %%
test_results = perform_adf_test(ema_df_daily)
display(test_results)

# %% [markdown]
# After test results we see that __FIL/USDT__ volatility over 1-day is failed to pass the stationarity test. The graph below confirms the persistence of trend: seems like the coin was too volatile right after the listing and failed to keep the same levels during its trading lifetime.

# %%
# TODO(Max): check scatter-plotting functions in core.plotting.py
sns.lineplot(
    data=ema_df_daily.loc[["FIL_USDT"]].reset_index(),
    x="date",
    y="ema_volatility",
    hue="currency_pair",
)

# %% [markdown]
# # Regression Analysis

# %%
frequency = "1D"
compute_daily_vix_ema_and_volume = lambda data: get_df_with_volume_and_volatility(
    data, freq=frequency, span=18
)
daily_vix_ema_volume = ramccsta.compute_stats_for_universe(
    vendor_universe=universe,
    config=config,
    stats_func=compute_daily_vix_ema_and_volume,
)

# %% [markdown]
# ## Regression Results

# %%
regression_results = run_regressions(daily_vix_ema_volume, lag_volume=True)

for coin in regression_results.keys():
    print(f"{coin}:")
    display(regression_results[coin])

# %% [markdown]
# As one can see, for all the currency pairs the regression of volatility to volume with intercept shows significance of volume coefficient (as well as lagged volume). The only exception is __FIL/USDT__, that also failed the stationarity test above.

# %% [markdown]
# ## Correlation and Plots

# %%
corr_df = calculate_corr_and_plot_scatter_plots(
    daily_vix_ema_volume, display_plot=True
)
display(corr_df)
