# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python [conda env:develop] *
#     language: python
#     name: conda-env-develop-py
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsystem as hsystem

# %%
hprint.config_notebook()

# TODO(gp): Changing level during the notebook execution doesn't work. Fix it.
# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)

# %% [markdown]
# ## Describe-instances

# %%
cmd = "aws ec2 describe-instances"
_, txt = hsystem.system_to_string(cmd)

# %%
data = json.loads(txt)

data

# %%
df = pd.io.json.json_normalize(data["Reservations"], record_path="Instances")
df_tmp = df["InstanceId InstanceType LaunchTime PublicIpAddress State".split()]

display(df_tmp)
# pd.io.json.json_normalize(data["Reservations"]["Instances"])

# %%
# help(pd.io.json.json_normalize)
