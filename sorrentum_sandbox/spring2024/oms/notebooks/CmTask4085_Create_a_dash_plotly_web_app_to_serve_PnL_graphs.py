# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 0 Imports

# %%
import datetime
import logging

import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import reconciliation as reconcil

# %load_ext autoreload
# %autoreload 2

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown] heading_collapsed=true
# # Current and yesterday

# %% hidden=true


# Load portfolio stats.
portfolio_dir = "/shared_data/ecs/preprod/system_reconciliation/C1b/20230512/system_log_dir.scheduled.20230512_131000.20230513_130500/process_forecasts/portfolio"
_, stats_df = reconcil.load_portfolio_artifacts(portfolio_dir)
# Compute cumulative PnL.
cumulative_pnl = stats_df["pnl"].cumsum()

# %% hidden=true
import pandas as pd

pd.Series(cumulative_pnl.index).agg(["min", "max"])

# %% hidden=true
len(cumulative_pnl)

# %% hidden=true
cumulative_pnl

# %% hidden=true
cumulative_pnl.plot()

# %% [markdown]
# # since 2022 and since 2019

# %%
dir_name = "/shared_data/model/historical/pnl_for_website/build_tile_configs.C3a.ccxt_v7_1-all.5T.2019-09-01_2023-05-15.ins/tiled_results/"
start_date = datetime.date(2019, 9, 1)
end_date = datetime.date(2023, 5, 15)
asset_id_col = "asset_id"
data_cols = {
    "price": "vwap",
    "volatility": "garman_klass_vol",
    "prediction": "feature",
}
data_cols_list = list(data_cols.values())
iter_ = dtfmod.yield_processed_parquet_tiles_by_year(
    dir_name,
    start_date,
    end_date,
    asset_id_col,
    data_cols_list,
    asset_ids=None,
)
df_res = hpandas.get_df_from_iterator(iter_)

# %%
fep = dtfmod.ForecastEvaluatorFromPrices(
    data_cols["price"],
    data_cols["volatility"],
    data_cols["prediction"],
)

# %%
_, bar_metrics = fep.annotate_forecasts(
    df_res,
    quantization="no_quantization",
    burn_in_bars=3,
    style="longitudinal",
    liquidate_at_end_of_day=False,
    initialize_beginning_of_day_trades_to_zero=False,
)

# %%
cumul_pnl = bar_metrics["pnl"].resample("D").sum(min_count=1).cumsum()

# %%
cumul_pnl.plot()

# %%
