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
# This notebook contains examples of data from http://www.kibot.com/
# - The data is loaded using code from `im/kibot/data/`

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging
import os

import pandas as pd
import requests
import requests.adapters as radapt
import requests.packages.urllib3.util as rpuuti
import tqdm

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hprint as hprint
import im.kibot.data.config as imkidacon
import im.kibot.data.extract.download as imkdaexdo
import im.kibot.metadata.load.kibot_metadata as imkmlkime

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Metadata

# %% [markdown]
# - Load Kibot Metadata to estimate contracts and equities available

# %% [markdown]
# ## Continuous contracts

# %%
kibot_metadata = imkmlkime.KibotMetadata()

# %%
# Get available contract types based on `KibotMetadata` documentation.
contract_types = ["1min", "daily", "tick-bid-ask"]

# %%
min_metadata = kibot_metadata.get_metadata("1min")
print(min_metadata.shape)
display(min_metadata.head(3))
display(min_metadata.tail(3))

# %%
daily_metadata = kibot_metadata.get_metadata("daily")
print(daily_metadata.shape)
display(daily_metadata.head(3))
display(daily_metadata.tail(3))

# %%
tick_metadata = kibot_metadata.get_metadata("tick-bid-ask")
print(tick_metadata.shape)
display(tick_metadata.head(3))
display(tick_metadata.tail(3))

# %% [markdown]
# # Downloading data

# %% [markdown]
# - An example of data downloaded from Kibot
# - `im/kibot/data/extract/download.py` is a script that puts compressed data to S3
#    - Examples of metadata of already downloaded datasets is provided above
# - Here we download a small dataset to provide an example of the data

# %% [markdown]
# ## Downloading continuous futures dataset

# %% [markdown]
# - On the example of `all_futures_continuous_contracts_daily`
# - This section follows the `im/kibot/data/extract/download.py` script, focusing on saving the output locally and demonstrating intermediary parsing results.

# %%
# Create directories.
source_dir = "source_data"
hio.create_dir(source_dir, incremental=False)
converted_dir = "converted_data"
hio.create_dir(converted_dir, incremental=False)

# %%
# Load local login information.
with open("kibot_login.txt", "r") as f:
    file = f.read()
    username = file.split("\n")[0]
    password = file.split("\n")[1]

# %%
username

# %%
# Log in.
requests_session = requests.Session()
requests_retry = rpuuti.Retry(
    total=12,
    backoff_factor=2,
    status_forcelist=[104, 403, 500, 501, 502, 503, 504],
)
requests_session.mount("http://", radapt.HTTPAdapter(max_retries=requests_retry))
requests_session.mount("https://", radapt.HTTPAdapter(max_retries=requests_retry))
kibot_account = imkidacon.ENDPOINT + "account.aspx"
login_result = imkdaexdo._log_in(
    kibot_account, username, str(password), requests_session
)

# %% run_control={"marked": true}
my_account_file = os.path.join(source_dir, "my_account.html")
# Download my account html page.
if not os.path.exists(my_account_file):
    _LOG.warning("Missing '%s': downloading it", my_account_file)
    imkdaexdo._download_page(my_account_file, kibot_account, requests_session)
dataset_links_csv_file = os.path.join(converted_dir, "dataset_links.csv")
# Extract available datasets.
dle = imkdaexdo.DatasetListExtractor()
dataset_links_df = dle.extract_dataset_links(
    os.path.join(source_dir, "my_account.html")
)
dataset_links_df.head(3)

# %%
# Create a directory for target dataset.
dataset = "all_futures_continuous_contracts_daily"
dataset_dir = os.path.join(converted_dir, dataset)
hio.create_dir(dataset_dir, incremental=True)
# Get specific payload addresses.
de = imkdaexdo.DatasetExtractor(dataset, requests_session)
to_download = de.get_dataset_payloads_to_download(
    dataset_links_df,
    source_dir,
    converted_dir,
)
to_download.head(3)

# %% run_control={"marked": false}
# Download payloads.
func = lambda row: de.download_payload_page(
    dataset_dir,
    row,
    **{
        "download_compressed": True,
        "skip_if_exists": False,
        "clean_up_artifacts": False,
    },
)
# Download a single payload from Kibot.
tqdm_ = tqdm.tqdm(
    to_download.iloc[1:2].iterrows(),
    total=len(to_download),
    desc="Downloading Kibot data",
)

# %%
for _, row in tqdm_:
    func(row)
# Show downloaded files.
print(os.listdir(dataset_dir))

# %% run_control={"marked": true}
# Example of output data.
df = pd.read_csv(os.path.join(dataset_dir, "TY.csv.gz"))
display(df.head(5))
display(df.tail(5))

# %%
