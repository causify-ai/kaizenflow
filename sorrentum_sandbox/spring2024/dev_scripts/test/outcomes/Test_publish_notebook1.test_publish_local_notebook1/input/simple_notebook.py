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
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2


import core.config as cconfig

# %%
# Initialize config.
config = cconfig.get_config_from_env()

# %% [markdown]
# # Execute

# %%
if config is None:
    raise ValueError("No config provided")

# %%
if config["fail"]:
    raise ValueError("Failure")
print("Success")

# %%
