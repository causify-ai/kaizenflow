# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging

import sklearn as sklear

import core.dataframe_modeler as cdatmode
import core.signal_processing as csigproc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im.kibot.data.load.futures_forward_contracts as imkdlffoco
import im.kibot.data.load.kibot_s3_data_loader as imkdlksdlo
import im.kibot.metadata.load.kibot_metadata as imkmlkime

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# ## Map contracts to start and end dates

# %%
lfc_hc = imkmlkime.KibotHardcodedContractLifetimeComputer(365, 7)

lfc_hc.compute_lifetime("CLJ17")

# %%
lfc_ta = imkmlkime.KibotTradingActivityContractLifetimeComputer()

lfc_ta.compute_lifetime("CLJ17")

# %%
symbols = ["ES", "CL", "NG"]
file = "../contracts.csv"


fcl = imkmlkime.FuturesContractLifetimes(file, lfc_hc)

# %%
fcl.save(["CL", "NG"])

# %%
data = fcl.load(["NG"])

# %%
data["NG"].head()

# %% [markdown]
# ## Create continuous contracts

# %%
fcem = imkmlkime.FuturesContractExpiryMapper(data)

# %%
fcem.get_nth_contract("NG", "2010-01-01", 1)

# %%
srs = fcem.get_nth_contracts("NG", "2010-01-10", "2010-01-20", freq="B", n=1)

# %%
srs

# %%
kdl = imkdlksdlo.KibotS3DataLoader()

# %%
ffc_obj = imkdlffoco.FuturesForwardContracts(kdl)

# %%
ffc_obj._replace_contracts_with_data(srs)

# %% [markdown]
# ## Combine front and back contracts - price

# %%
contract_df = fcem.get_contracts(
    ["NG" + str(j) for j in range(1, 13)], "2010-01-01", "2015-12-31", freq="B"
)

# %%
contract_df.head()

# %%
price_df = ffc_obj.replace_contracts_with_data(contract_df, "close")

# %%
price_df.plot()

# %%
dfm = (
    cdatmode.DataFrameModeler(df=price_df, oos_start="2013-01-01")
    .compute_ret_0(method="predict")
    .apply_column_transformer(
        transformer_func=csigproc.compute_rolling_zscore,
        transformer_kwargs={
            "tau": 10,
            "min_periods": 20,
        },
        col_mode="replace_all",
        method="predict",
    )
)

# %%
dfm.plot_time_series()

# %%
dfm.plot_pca_components(num_components=4)

# %%
dfm.plot_explained_variance()

# %% run_control={"marked": false}
res = dfm.apply_residualizer(
    model_func=sklear.decomposition.PCA,
    x_vars=["NG" + str(j) + "_ret_0" for j in range(1, 13)],
    model_kwargs={"n_components": 2},
    method="predict",
).apply_column_transformer(
    transformer_func=csigproc.compute_rolling_zscore,
    transformer_kwargs={
        "tau": 10,
        "min_periods": 20,
    },
    col_mode="replace_all",
    method="predict",
)
# .apply_volatility_model(
#    cols=["NG" + str(j) + "_ret_0" for j in range(1, 13)],
#    steps_ahead=2,
# )


# %%
res.df

# %%
res.plot_time_series()

# %%
res.plot_pca_components(num_components=4)

# %%
dfm.plot_explained_variance()

# %%
res.plot_correlation_matrix(mode="ins")

# %% [markdown]
# ## Combine front and back contracts - volume

# %%
volume_df = ffc_obj.replace_contracts_with_data(contract_df, "vol")

# %%
volume_df

# %%
volume_df.plot(logy=True)

# %%
