# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import logging
import sys
from typing import List

import numpy as np
import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import core.plotting as coplotti
import core.signal_processing as csigproc
import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load package `yahoo_fin`

# %%
# https://theautomatic.net/2018/01/25/coding-yahoo_fin-package/
# !sudo {sys.executable} -m pip install --upgrade yahoo_fin
import yahoo_fin.stock_info as si

# %%
historical_data = si.get_data("amzn", start_date = "01/01/2017", end_date = "01/31/2017")

# %%
historical_data

# %% [markdown]
# # Define universe and get adjusted close prices

# %%
tickers = [
#    "IAU", # iShares Gold Trust
    "BTC-USD",
    "SPY",
#     "USIG", # iShares Broad USD Investment Grade Corporate Bond ETF
#     "USRT", # iShares Core US REIT ETF
#     "GSG", # GSCI Commodity
]

# %%
sector_etfs = [
    "XLC", # Communication
    "XLY", # Consumer Discretionary
    "XLP", # Consumer Staples
    "XLE", # Energy
    "XLF", # Financial
    "XLV", # Health Care
    "XLI", # Industrial
    "XLB", # Materials
    "XLRE", # Real Estate
    "XLK", # Technology
    "XLU", # Utilities
]

# %%
start_date = "2015/01/01"
end_date = "2023/08/31"
resampling_freq = "1B"
num_points_rolling_vol = 40


# %%
def get_adj_close(tickers: List[str], start_date: str, end_date: str) -> pd.Series:
    ticker_data = []
    for ticker in tickers:
        data = si.get_data(ticker, start_date=start_date, end_date=end_date)
        data = data["adjclose"].rename(ticker)
        ticker_data.append(data)
    df = pd.concat(ticker_data, axis=1)
    return df


# %%
df = get_adj_close(tickers, start_date, end_date)
df.head()

# %%
color_dict = {
    "SPY": "r",
    "BTC-USD": "y",
}

# %%
resampled_adj_close = df.resample(resampling_freq).last() 

# %%
resampled_adj_close.plot(color=color_dict)

# %%
resampled_adj_close["BTC-USD"].plot(
    title="BTC-USD",
    ylabel="dollars",
    xlabel="date",
    color=color_dict,
)

# %%
resampled_adj_close["SPY"].plot(
    title="SPY",
    ylabel="dollars",
    xlabel="date",
    color=color_dict,
)

# %%
resampled_adj_close.resample("Y").first()

# %% [markdown]
# ## Compute returns and volatility

# %%
first_price = resampled_adj_close.dropna().iloc[0]
first_date = resampled_adj_close.index[0]
last_price = resampled_adj_close.dropna().iloc[-1]
last_date = resampled_adj_close.index[-1]
period_pct_return = last_price / first_price - 1
period = last_date - first_date

# %%
last_price

# %%
last_date

# %%
period_pct_return

# %%
# Plot daily returns as a percentage (including multiplication by 100).
pct_return = resampled_adj_close.pct_change()
(100 * pct_return).plot(
    title="percent return",
    ylabel="% daily return",
    xlabel="date", 
    color=color_dict
)

# %%
# Plot daily log returns.
log_return = np.log(resampled_adj_close).diff()
log_return.plot(title="log_return", color=color_dict)

# %%
# Note that the differences between percentage and log returns
#  significantly affect the SR, especially in the case of BTC.
pct_return.apply(costatis.compute_annualized_sharpe_ratio)

# %%
log_return.apply(costatis.compute_annualized_sharpe_ratio)

# %%
pct_return.apply(costatis.compute_annualized_return_and_volatility)

# %%
# The methodology for return annualization is best suited to log
#  or dollar returns.
log_return.apply(costatis.compute_annualized_return_and_volatility)

# %%
# Convert annualized log returns to percentage returns.
np.exp(log_return.apply(costatis.compute_annualized_return)) - 1

# %%
# Compute drawdown using log return and then convert to a percentage loss.
log_return.apply(costatis.compute_perc_loss_from_high_water_mark).max()

# %%
# The drawdown methodology applies directly to log and dollar returns.
#  Note that if log and percentage returns differ significantly (as is
#  the case with BTC), then the drawdown function may return nonsensical
#  results if incorrectly applied to percentage returns.
pct_return.apply(costatis.compute_drawdown).max()

# %%
dollar_return = resampled_adj_close.diff()

# %%
# Note that dollar return metrics differ meanginfully when the scale
#  of price changes dramatically over the calculation window (as is
#  the case with BTC).
dollar_return.apply(costatis.compute_annualized_sharpe_ratio)

# %%
dollar_return.apply(costatis.compute_annualized_return_and_volatility)

# %%
resampled_adj_close.mean()

# %%
dollar_return.apply(costatis.compute_drawdown).max()

# %%
# Rolling volatility differences due to using log vs percentage returns are much less
#  pronounced, even in the case of a highly volatilite asset like BTC.
np.sqrt((log_return**2).dropna().rolling(num_points_rolling_vol).mean()).plot()

# %%
np.sqrt((pct_return**2).dropna().rolling(num_points_rolling_vol).mean()).plot()

# %%
# Compute daily volatility in percentage terms using percentage return.
#  On these scales, the difference between using `std()` vs an estimator
#  that assumes zero mean is negligible.
vol = pct_return.rolling(num_points_rolling_vol).std()
(100 * vol).plot(
    title="volatlity",
    ylabel="% daily volatility",
    xlabel="date",
    color=color_dict
)

# %%
# Compute volatility-adjusted returns from percentage returns.
adj_rets = pct_return.divide(vol.shift(2)).dropna(how="all").iloc[1:]
adj_rets.plot(
    title="volatility-adjusted return",
    ylabel="standard deviations",
    xlabel="date",
    color=color_dict,
)

# %%
# Use volatility-adjusted returns (from percentage returns) to
#  calculate correlation.
coplotti.plot_correlation_matrix(adj_rets)

# %%
# Note that SR boost achieved from vol-targeting.
adj_rets.apply(costatis.compute_annualized_sharpe_ratio)

# %%
# These need to be rescaled.
adj_rets.apply(costatis.compute_annualized_return_and_volatility)

# %% [markdown]
# # Equally-weighted returns

# %%
sim_start_date = "2016-01-01"

# %%
equally_weighted_pct_return = pct_return.mean(axis=1).rename("equally_weighted_pct_return").loc[sim_start_date:]

# %%
equally_weighted_log_return = np.log(1 + equally_weighted_pct_return).rename("equally_weighted_log_return")

# %%
(1 + equally_weighted_log_return.cumsum()).plot(
    title="50% SPY-50% BTC Blend",
    ylabel="return multiple",
    xlabel="date",
    color="orange",
)

# %%
costatis.compute_annualized_sharpe_ratio(equally_weighted_log_return)

# %%
costatis.compute_annualized_return_and_volatility(equally_weighted_log_return)

# %%
costatis.compute_perc_loss_from_high_water_mark(equally_weighted_log_return).max()

# %% [markdown]
# # Equal risk-weighted returns

# %%
vol.plot()

# %%
risk_weighted_pnl = adj_rets.mean(axis=1).rename("risk_weighted_pnl")

# %%
risk_weighted_pnl.cumsum().plot()

# %%
costatis.compute_annualized_sharpe_ratio(risk_weighted_pnl)

# %%
# These have to be properly rescaled.
costatis.compute_annualized_return_and_volatility(risk_weighted_pnl)

# %%
# This is meaningless without the correct rescaling.
costatis.compute_perc_loss_from_high_water_mark(risk_weighted_pnl).max()

# %%
relative_allocation = (1/vol)#.divide((1/vol).sum(axis=1), axis=0)

# %%
scale_factor = 1/200

# %%
(scale_factor * relative_allocation).sum(axis=1).plot()

# %%
risk_weighted_pct_return = (scale_factor * relative_allocation * pct_return.shift(-2)).mean(axis=1)

# %%
costatis.compute_annualized_return_and_volatility(risk_weighted_pct_return)

# %%
risk_weighted_log_return = np.log(1 + risk_weighted_pct_return)

# %%
costatis.compute_annualized_sharpe_ratio(risk_weighted_log_return)

# %%
costatis.compute_annualized_return_and_volatility(risk_weighted_log_return)

# %%
costatis.compute_perc_loss_from_high_water_mark(risk_weighted_log_return).max()

# %% [markdown]
# # Inverse covariance

# %% [markdown]
# ## Whole-period estimate

# %%
#corr = adj_rets.loc[:sim_start_date].corr()
corr = adj_rets.corr()
inv_corr = csigproc.compute_inverse(corr)
corr_adj_rets = (adj_rets @ inv_corr).mean(axis=1)

# %%
costatis.compute_annualized_sharpe_ratio(corr_adj_rets)

# %%
corr_adj_rets.cumsum().plot()

# %% [markdown]
# ## Rolling estimate

# %%
corrs = adj_rets.rolling(num_points_rolling_vol).corr()
datetimes = corrs.index.levels[0]

# %%
inv_corrs = {}
target_pos = {}
for datetime in datetimes:
    corr = corrs.loc[datetime]
    if not corr.dropna().empty:
        inv_corr = csigproc.compute_inverse(corr)
        inv_corrs[datetime] = inv_corr
        pos = inv_corr.sum()
        pos.name = datetime
        target_pos[datetime] = pos

# %%
# Target positions in volatility-adjusted instruments.
target_pos_df = pd.DataFrame(target_pos).T
target_pos_df.plot()

# %%
# Does not reflect % in cash. 
unscaled_target_pos_df = (target_pos_df / vol).divide((target_pos_df / vol).abs().sum(axis=1), axis=0)

# %%
(100 * unscaled_target_pos_df).plot(
    title="Percentage allocation in dynamic SPY-BTC blend",
    ylabel="% allocation",
    xlabel="date",
    color=color_dict,
)

# %%
rp_pnl = (target_pos_df * adj_rets.shift(-2)).mean(axis=1)

# %%
costatis.compute_annualized_sharpe_ratio(rp_pnl)

# %%
rp_pnl.cumsum().plot()

# %%
pnl_dict = {}
for idx in adj_rets.shift(-2).index:
    if idx in inv_corrs:
        pnl = (inv_corrs[idx] @ adj_rets.shift(-2).loc[idx]).mean()
        pnl_dict[idx] = pnl
    else:
        _LOG.debug("Skipping idx=%s", idx)
rolling_pnl = pd.Series(pnl_dict).shift(2).rename("risk_parity_pnl")

# %%
costatis.compute_annualized_sharpe_ratio(rolling_pnl)

# %%
rolling_pnl.cumsum().plot()

# %%
lev1 = np.log(1 + 0.01 * rolling_pnl)
lev2 = 2 * np.log(1 + 0.01 * rolling_pnl)

# %%
costatis.compute_annualized_sharpe_ratio(lev1)

# %%
costatis.compute_annualized_return_and_volatility(lev1)

# %%
costatis.compute_annualized_return_and_volatility(lev2)

# %%
costatis.compute_perc_loss_from_high_water_mark(lev1).max()

# %%
costatis.compute_perc_loss_from_high_water_mark(lev2).max()

# %%
# Maybe we revive the "Universal Portfolio" approach of Thomas Cover.

# %%
pnls = [
    log_return,
    equally_weighted_log_return.rename("50% SPY-50% BTC"),
    lev1.rename("Kaizen 1x leverage"),
    lev2.rename("Kaizen 2x leverage"),
]

# %%
pnl_df = pd.concat(pnls, axis=1).loc[sim_start_date:]

# %%
(1 + pnl_df.loc[sim_start_date:].cumsum()).plot(
    title="BTC-SPY Blends",
    ylabel="return multiple",
    xlabel="date",
    color={
        "SPY": "r",
        "BTC-USD": "y",
        "50% SPY-50% BTC": "orange",
        "Kaizen 1x leverage": "b",
        "Kaizen 2x leverage": "g",
    },
)

# %%
(1 + pnl_df.loc[sim_start_date:][["Kaizen 1x leverage", "Kaizen 2x leverage"]].cumsum()).plot(
    title="BTC-SPY Blends",
    ylabel="return multiple",
    xlabel="date",
    color={
        "SPY": "r",
        "BTC-USD": "y",
        "50% SPY-50% BTC": "orange",
        "Kaizen 1x leverage": "b",
        "Kaizen 2x leverage": "g",
    },
)

# %%
pnl_df.apply(costatis.compute_annualized_sharpe_ratio)

# %%
(pnl_df / pnl_df.std()).cumsum().plot(
    title="BTC-SPY Blends",
    ylabel="standardized returns",
    xlabel="date",
    color={
        "SPY": "r",
        "BTC-USD": "y",
        "50% SPY-50% BTC": "orange",
        "Kaizen 1x leverage": "b",
        "Kaizen 2x leverage": "g",
    },
)

# %%
