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

# %% [markdown]
# # Description
#
# This notebook shows the various functionality of our internal config

# %% [markdown]
# # Imports

# %%
import core.config as cconfig

# %% [markdown]
# # Initialization
#
# - The default config modes are
#     - `update_mode` = "assert_on_overwrite"
#         - We can add new keys to the config regardless of the update mode.
#
#     - `clobber_mode` = "assert_on_write_after_use"
#
#     - `report_mode` = "verbose_log_error"
#
#     - `unused_variables_mode` = "warning_on_error",

# %%
system_log_dir = "/shared_data/CMTask5198_log_dir_1"
id_col = "asset_id"
universe_version = "v7.1"
vendor = "CCXT"
mode = "trade"
test_asset_id = 1467591036
bar_duration = "5T"
expected_num_child_orders = [0, 5]
use_historical = True
config_dict = {
    "meta": {"id_col": id_col, "use_historical": use_historical},
    "system_log_dir": system_log_dir,
    "ohlcv_market_data": {
        "vendor": vendor,
        "mode": mode,
        "universe": {
            "universe_version": universe_version,
            "test_asset_id": test_asset_id,
        },
    },
}
config = cconfig.Config.from_dict(config_dict)
print(config)

# %%
# Converting a config to a dict.
dict1 = config.to_dict()
dict1

# %%
# Create a config from a flattened dict.
config = cconfig.Config._get_config_from_flattened_dict(dict1)
print(config)

# %% [markdown]
# # Get and Set values

# %%
# Chain Accessing.
print("id_col - ", config["meta", "id_col"])
# Nested Accessing.
print("vendor - ", config["ohlcv_market_data"]["vendor"])

# %%
# Access a exsisting key to check a default value is not returned.
config.get("system_log_dir", "default_value")

# %%
# Access a exsisting key to check a default value is not returned
# but the type is checked. Should raise an exception because
# `system_log_dir` is of the type `str`.
config.get("system_log_dir", "default_value", int)

# %%
#  Set a key that doesn't exist.
config["bar_duration"] = "5T"
print(config)

# %% run_control={"marked": true}
# Set a key that already exists.
# Need to update the mode of config to `overwrite`
config.update_mode = "overwrite"
config["bar_duration"] = "6T"
print(config)

# %% [markdown]
# # Update

# %%
# Test the update functionality.
# Update with no common vlaues in configs.
config1 = cconfig.Config()
config_tmp = config1.add_subconfig("read_data")
config_tmp["file_name"] = "foo_bar.txt"
config_tmp["nrows"] = 999
config1["single_val"] = "hello"
config_tmp = config1.add_subconfig("zscore")
config_tmp["style"] = "gaz"
config_tmp["com"] = 28
print(config1)
print("*" * 60)
#
config2 = cconfig.Config()
config_tmp = config2.add_subconfig("write_data")
config_tmp["file_name"] = "baz.txt"
config_tmp["nrows"] = 999
config2["single_val2"] = "goodbye"
print(config2)

# %%
# With default `update_mode=assert_on_overwirte` it
# will raise an assertion.
config1.update(config2, update_mode="overwrite")
print(config1)

# %%
# Update with common values in configs.
config3 = cconfig.Config()
config_tmp = config3.add_subconfig("read_data")
config_tmp["file_name"] = "foo_bar.txt"
config_tmp["nrows"] = 999
config3["single_val"] = "hello"
config_tmp = config3.add_subconfig("zscore")
config_tmp["style"] = "gaz"
config_tmp["com"] = 28
print(config3)
print("*" * 60)
#
config4 = cconfig.Config()
config_tmp = config4.add_subconfig("read_data")
config_tmp["file_name"] = "baz.txt"
config_tmp["nrows"] = 999
config4["single_val"] = "goodbye"
config_tmp = config4.add_subconfig("zscore")
config_tmp["style"] = "super"
config_tmp = config4.add_subconfig("extra_zscore")
config_tmp["style"] = "universal"
config_tmp["tau"] = 32
print(config4)

# %%
config3.update(config4, update_mode="overwrite")
print(config3)

# %%
# Behaviour when update mode is `assign_if_missing`.
# Existing keys will not be modified and no exception
# is raised. New keys are added if not present.
config5 = cconfig.Config()
config5["read_data", "file_name"] = "hello"
config5["read_data2"] = "world"
config3.update(config5, update_mode="assign_if_missing")
print(config3)

# %%
# To update a read only config, set `value=False`.
config.update_mode = "overwrite"
config.clobber_mode = "allow_write_after_use"
config.mark_read_only(value=False)
config["bar_duration"] = "7T"
print(config)

# %% [markdown]
# # Read Only Config

# %%
# Test config read-only property.
# Cannot set or update a value that doesn't exists on a read-only config.
# Should raise an exception.
config.update_mode = "overwrite"
config.clobber_mode = "allow_write_after_use"
config.mark_read_only()
config["bar_duration"] = "7T"

# %% [markdown]
# # Get and Mark as used

# %%
# Test verbose mode with `marked_as_used` == True.
# The leaf keys in heirarchy will be marked as `True`
mode = "verbose"
config.get_and_mark_as_used("meta")
config.to_string(mode)

# %%
# Get and mark a value as used.
config.get_and_mark_as_used("bar_duration")

# %%
# Check if the value is marked as used.
config.get_marked_as_used("bar_duration")

# %% [markdown]
# # General Functionality

# %%
# Convert a config to a python code.
code = config.to_python()
print(code)
print("\n")
print(type(code))

# %%
# Build a config from a python code.
config2 = cconfig.Config.from_python(code)
print(config2)
print("\n")
print(type(config2))

# %%
# Testing the flatten functionality.
config.flatten()

# %%
# Test a config that can be serialized correctly.
config.is_serializable()

# %%
# Keep or skip empty leaves.
config.to_dict(keep_leaves=False)

# %%
# Convert a config to a string.
mode = "verbose"
print(config.to_string(mode="verbose"))
