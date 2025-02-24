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

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import core.config.config_ as cconconf
import core.config.config_utils as ccocouti
import core.explore as coexplor
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.crypto_chassis.data.client.crypto_chassis_clients as imvccdcccc
import research_amp.transform as ramptran

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
def get_CrossSectionalLearning_config() -> cconconf.Config:
    """
    Get config, that specifies params for getting raw data from `crypto
    chassis` and perform PCA calculations later.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            # Parameters for client initialization.
            "im_client": {
                "universe_version": "v1",
                "resample_1min": True,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"),
                    "reorg",
                    "historical.manual.pq",
                ),
                "dataset": "ohlcv",
                "contract_type": "spot",
                "partition_mode": "by_year_month",
                "data_snapshot": "latest",
                "aws_profile": "ck",
            },
            # Parameters for data query.
            "read_data": {
                "start_ts": pd.Timestamp("2022-01-01 00:00", tz="UTC"),
                "end_ts": pd.Timestamp("2022-04-01 00:00", tz="UTC"),
                "columns": None,
                "filter_data_mode": "assert",
            },
            "transform": {
                "ohlcv_cols": [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "full_symbol",
                ],
                "resampling_rule": "5T",
                "rets_type": "pct_change",  # or "log_rets"
            },
        },
        "analysis": {
            "reference_rets": "close.ret_0",  # e.g.,"vwap.ret_0", "twap.ret_0"
            "BTC_is_included": True,
        },
    }
    config = cconfig.Config.from_dict(param_dict)
    return config


# %%
config = get_CrossSectionalLearning_config()
print(config)

# %% [markdown]
# # Load the data

# %%
# Initiate the client.
client = imvccdcccc.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["im_client"]
)
# Get universe of `full_symbols`.
universe = client.get_universe()
# Specify if BTC is included.
if not config["analysis"]["BTC_is_included"]:
    universe = [
        element for element in universe if not element.endswith("BTC_USDT")
    ]
# Load OHLCV data.
ohlcv_cc = client.read_data(universe, **config["data"]["read_data"])
# Post-processing.
ohlcv_cc = ohlcv_cc[config["data"]["transform"]["ohlcv_cols"]]
ohlcv_cc.head(3)

# %%
# Loaded universe.
print(ohlcv_cc["full_symbol"].unique())

# %% [markdown]
# # Compute returns

# %%
# VWAP, TWAP transformation.
df = ramptran.calculate_vwap_twap(
    ohlcv_cc, config["data"]["transform"]["resampling_rule"]
)
# Returns calculation.
df = ramptran.calculate_returns(df, config["data"]["transform"]["rets_type"])
# Choose reference returns to proceed to further analysis.
df = df[config["analysis"]["reference_rets"]]
# Get rid of NaNs.
df = hpandas.dropna(df)
df.head(3)

# %% [markdown]
# # Residualize returns

# %% [markdown]
# ## Estimate PCA

# %% [markdown]
# ### Standartize data

# %%
# Initiate scaler.
sc = StandardScaler()
# Normalize data.
data_normalized = sc.fit_transform(df.values)
# Get back to DataFrame representation.
data_normalized = pd.DataFrame(
    data_normalized, columns=df.columns, index=df.index
)
data_normalized.head(3)

# %%
# Check the normalization (should be ~0 for mean, ~1 for standard deviation).
mean_std_check = pd.DataFrame()
for cols in data_normalized.columns:
    mean_std_check.loc[cols, "mean"] = data_normalized[cols].mean()
    mean_std_check.loc[cols, "std_dev"] = data_normalized[cols].std()

mean_std_check.round(3)

# %% [markdown]
# ### Choose the number of principal components

# %%
pca = PCA().fit(data_normalized)
plt.plot(np.cumsum(pca.explained_variance_ratio_))
plt.xlabel("number_of_components")
plt.ylabel("cumulative_explained_variance")

# %%
explained_variance_ratio_cumsum = np.cumsum(pca.explained_variance_ratio_)
num_of_required_comp = len(
    explained_variance_ratio_cumsum[explained_variance_ratio_cumsum < 0.95]
)
print(f"Number of required PCA components: {num_of_required_comp}")

# %% [markdown]
# ### PCA calculations

# %%
pca_components = PCA(n_components=num_of_required_comp).fit_transform(
    data_normalized
)

# %%
pca_df = pd.DataFrame(data=pca_components)
pca_df

# %% [markdown]
# ### Rolling PCA (omit for now)

# %%
# Params.
sample = df.head(1000)
nan_mode = "drop"
com = 1
# Rolling PCA calculations.
corr_df, eigval_df, eigvec_df = coexplor.rolling_pca_over_time(
    sample, com, nan_mode
)
eigval_df.columns = sample.columns
eigvec_df.columns = sample.columns
coexplor.plot_pca_over_time(eigval_df, eigvec_df)
