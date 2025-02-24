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
# # Description

# %% [markdown]
# Print out all the links to the published notebooks stored in the given text file.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
import os

import pandas as pd
from IPython.display import HTML, display

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.execution_analysis_configs as oexancon

# %%
hdbg.init_logger(verbosity=logging.INFO)
_LOG = logging.getLogger(__name__)
_LOG.info("%s", henv.get_system_signature()[0])
hprint.config_notebook()

# %% [markdown]
# # Config

# %%
config = cconfig.get_config_from_env()
if config:
    _LOG.info("Using config from env vars")
else:
    timestamp_dir = "/shared_data/CmTask7895/system_reconciliation/C11a/prod/20240419_103500.20240419_113000/"
    analysis_notebooks_file_path = os.path.join(
        timestamp_dir,
        "system_log_dir.manual",
        "analysis_notebooks",
        "analysis_notebooks_links.csv",
    )
    config_list = oexancon.get_master_trading_system_report_notebook_config(
        timestamp_dir, analysis_notebooks_file_path
    )
    config = config_list[0]
print(config)


# %% [markdown]
# # Utils


# %%
# TODO(Vlad): The same as in the `Master_buildmeister_dashboard`. Have to be moved to the helpers.
# TODO(Toma): Move functions to `oms/notebooks/notebooks_utils.py`.
def make_clickable(url: str) -> str:
    """
    Wrapper to make the URL value clickable.

    :param url: URL value to convert
    :return: clickable URL link
    """
    return f'<a href="{url}" target="_blank">{url}</a>'


def get_balances(ccxt_log: obcccclo.CcxtLogger) -> pd.DataFrame:
    """
    Load balances Dataframe.
    """
    balances_before = ccxt_log_reader.load_balances()
    # Get the balances JSON from 1-element list returned by `load_balances` and
    # transform per-asset information to Dataframe.
    balances_df = pd.DataFrame(balances_before[0]["info"]["assets"])
    balances_df = balances_df[["asset", "walletBalance"]]
    return balances_df


# %% [markdown]
# # Print the notebooks links

# %%
df = pd.read_csv(config["analysis_notebooks_file_path"])
df["URL"] = df["URL"].apply(make_clickable)
display(HTML(df.to_html(escape=False)))

# %% [markdown]
# # Load balances

# %% [markdown] run_control={"marked": false}
# ## Before run

# %%
# Init the log reader.
log_dir = os.path.join(config["timestamp_dir"], "flatten_account.before")
ccxt_log_reader = obcccclo.CcxtLogger(log_dir)

# %%
balances_df = get_balances(ccxt_log_reader)
display(balances_df)

# %% [markdown]
# ## After run

# %%
# Init the log reader.
log_dir = os.path.join(config["timestamp_dir"], "flatten_account.after")
ccxt_log_reader = obcccclo.CcxtLogger(log_dir)

# %%
balances_df = get_balances(ccxt_log_reader)
display(balances_df)

# %%
