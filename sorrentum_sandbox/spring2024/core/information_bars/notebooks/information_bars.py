# ---
# jupyter:
# jupytext:
# formats: ipynb,py:percent
# text_representation:
# extension: .py
# format_name: percent
# format_version: '1.3'
# jupytext_version: 1.5.2
# kernelspec:
# display_name: Python 3
# language: python
# name: python3
# ---

# %% [markdown]
# # Imports
#
# Importing all required modules.

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import seaborn as sns
import statsmodels.api as sm

import core.information_bars.bars as cinbabar

# TODO(vr): Use below when Tick data will be in PQ on S3
# import im.kibot.data.load as vkdl
import im.kibot.data.load.file_path_generator as vkdlf
import im.kibot.data.types as vkdt

plt.style.use("seaborn-talk")
plt.style.use("bmh")

# %% [markdown] pycharm={"name": "#%% md\n"}
# # Constants
#
# Defining constants to work with through this notebook.

# %% pycharm={"name": "#%%\n"}
TICK_M = 100
VOLUME_M = 100
DOLLAR_VOLUME_M = 100
PLOT_FIGURE_SIZE = (10, 7)


# %% [markdown]
# # Download

# %% pycharm={"name": "#%%\n"}
# TODO(vr): Use below when Tick data will be in PQ on S3
# downloader = vkdl.KibotDataLoader()
# source_df = downloader.read_data(
# symbol='TT',
# asset_class=vkdt.AssetClass.Futures,
# frequency=vkdt.Frequency.Tick,
# contract_type=vkdt.ContractType.Continuous,
# nrows=1000
# )
# source_df

path_generator = vkdlf.FilePathGenerator()
remote_path = path_generator.generate_file_path(
    symbol="TT",
    asset_class=vkdt.AssetClass.Futures,
    frequency=vkdt.Frequency.Tick,
    contract_type=vkdt.ContractType.Continuous,
    ext=vkdt.Extension.CSV,
)
source_df = pd.read_csv(
    remote_path,
    header=0,
    nrows=1000,
    parse_dates=[["date", "time"]],
    names=["date", "time", "price", "volume"],
)
source_df

# %% pycharm={"name": "#%%\n"}
df = source_df.copy()
df.set_index("date_time", inplace=True)

# %% [markdown] pycharm={"name": "#%% md\n"}
# # Bars

# %% [markdown]
# ## Tick Bars

# %% pycharm={"name": "#%%\n"}
tick_df = cinbabar.get_tick_bars(source_df, threshold=TICK_M)
tick_df.set_index("date_time", inplace=True)
n_ticks = tick_df.shape[0]
volume_ratio = (tick_df.cum_buy_volume.sum() / n_ticks).round()
dollar_ratio = (tick_df.cum_dollar_value.sum() / n_ticks).round()
print(f"num ticks: {n_ticks:,}")
print(f"volume ratio: {volume_ratio}")
print(f"dollar ratio: {dollar_ratio}")
tick_df

# %% [markdown]
# ## Volume Bars

# %% pycharm={"name": "#%%\n"}
v_bar_df = cinbabar.get_volume_bars(source_df, threshold=VOLUME_M)
v_bar_df.set_index("date_time", inplace=True)
v_bar_df

# %% [markdown]
# ## Dollar Bars

# %% pycharm={"name": "#%%\n"}
dv_bar_df = cinbabar.get_dollar_bars(source_df, threshold=DOLLAR_VOLUME_M)
dv_bar_df.set_index("date_time", inplace=True)
dv_bar_df


# %% [markdown] pycharm={"name": "#%% md\n"}
# # Analyzing the Bars

# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Count Quantity of Bars By Each Bar Type (Weekly)
#
# Compare series. Scale them so that we compare "apples" to "apples".

# %% pycharm={"name": "#%%\n"}
def count_bars(df, price_col="cum_dollar_value"):
    return df.resample("s")[price_col].count()


def scale(s):
    return (s - s.min()) / (s.max() - s.min())


# %% pycharm={"name": "#%%\n"}
tc = scale(count_bars(tick_df))
vc = scale(count_bars(v_bar_df))
dc = scale(count_bars(dv_bar_df))
dfc = scale(count_bars(df, price_col="price"))

# %% pycharm={"name": "#%%\n"}
f, ax = plt.subplots(figsize=PLOT_FIGURE_SIZE)
tc.plot(ax=ax, ls="-", label="tick count")
vc.plot(ax=ax, ls="--", label="volume count")
dc.plot(ax=ax, ls="-.", label="dollar count")
ax.set_title("scaled bar counts")
ax.legend()

# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Which Bar Type Has Most Stable Counts?

# %% pycharm={"name": "#%%\n"}
bar_types = ["tick", "volume", "dollar", "df"]
bar_std = [tc.std(), vc.std(), dc.std(), dfc.std()]
counts = pd.Series(bar_std, index=bar_types)
counts.sort_values()


# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Which Bar Type Has the Lowest Serial Correlation?

# %% pycharm={"name": "#%%\n"}
def returns(s):
    arr = np.diff(np.log(s))
    return pd.Series(arr, index=s.index[1:])


# %% pycharm={"name": "#%%\n"}
tr = returns(tick_df.cum_dollar_value)
vr = returns(v_bar_df.cum_dollar_value)
dr = returns(dv_bar_df.cum_dollar_value)
df_ret = returns(df.price)

bar_returns = [tr, vr, dr, df_ret]


# %% pycharm={"name": "#%%\n"}
def get_test_stats(bar_types, bar_returns, test_func, *args, **kwargs):

    dct = {
        bar_plot: (int(bar_ret.shape[0]), test_func(bar_ret, *args, **kwargs))
        for bar_plot, bar_ret in zip(bar_types, bar_returns)
    }

    df = (
        pd.DataFrame.from_dict(dct)
        .rename(index={0: "sample_size", 1: f"{test_func.__name__}_stat"})
        .T
    )
    return df


autocorrs = get_test_stats(bar_types, bar_returns, pd.Series.autocorr)

# %% pycharm={"name": "#%%\n"}
autocorrs.sort_values("autocorr_stat")

# %% pycharm={"name": "#%%\n"}
autocorrs.abs().sort_values("autocorr_stat")


# %% pycharm={"name": "#%%\n"}
def plot_autocorr(bar_types, bar_returns):
    _, axes = plt.subplots(len(bar_types), figsize=PLOT_FIGURE_SIZE)
    min_lags = min(map(len, bar_returns))
    for i, (bar_plot, typ) in enumerate(zip(bar_returns, bar_types)):
        sm.graphics.tsa.plot_acf(
            bar_plot,
            lags=min_lags - 1,
            ax=axes[i],
            alpha=0.05,
            unbiased=True,
            fft=True,
            zero=False,
            title=f"{typ} AutoCorr",
        )
    plt.tight_layout()


def plot_hist(bar_types, bar_returns):
    _, axes = plt.subplots(len(bar_types), figsize=PLOT_FIGURE_SIZE)
    for i, (bar_plot, typ) in enumerate(zip(bar_returns, bar_types)):
        g = sns.distplot(bar_plot, ax=axes[i], kde=False, label=typ)
        g.set(yscale="log")
        axes[i].legend()
    plt.tight_layout()


# %% pycharm={"name": "#%%\n"}
plot_autocorr(bar_types, bar_returns)

# %% pycharm={"name": "#%%\n"}
plot_hist(bar_types, bar_returns)


# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Partition Bar Series into Monthly, Compute Variance of Returns, and Variance of Variance

# %% pycharm={"name": "#%%\n"}
def partition_monthly(s):
    return s.resample("1M").var()


# %% pycharm={"name": "#%%\n"}
tr_rs = partition_monthly(tr)
vr_rs = partition_monthly(vr)
dr_rs = partition_monthly(dr)
df_ret_rs = partition_monthly(df_ret)
monthly_vars = [tr_rs, vr_rs, dr_rs, df_ret_rs]

# %% pycharm={"name": "#%%\n"}
get_test_stats(bar_types, monthly_vars, np.var).sort_values("var_stat")


# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Compute Jarque-Bera Test, Which Has The Lowest Test Statistic?

# %% pycharm={"name": "#%%\n"}
def jb(x, test=True):
    np.random.seed(12345678)
    if test:
        return stats.jarque_bera(x)[0]
    return stats.jarque_bera(x)[1]


get_test_stats(bar_types, bar_returns, jb).sort_values("jb_stat")


# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Compute Shapiro-Wilk Test
#
# Shapiro-Wilk test statistic > larger is better.

# %% pycharm={"name": "#%%\n"}
def shapiro(x, test=True):
    np.random.seed(12345678)
    if test:
        return stats.shapiro(x)[0]
    return stats.shapiro(x)[1]


get_test_stats(bar_types, bar_returns, shapiro).sort_values("shapiro_stat")[::-1]
