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
# # Description

# %% [markdown]
# Profile tests durations for test list.

# %% [markdown]
# # Imports

# %%
import logging
import re

import matplotlib.pyplot as plt

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
# `test_list_name` can be "fast_tests", "slow_tests", "superslow_tests",
# and "fast_slow_tests".

config = {"test_list_name": "fast_slow_tests"}


# %% [markdown]
# # Functions

# %%
def get_profiling_command(test_list_name: str):
    """
    Get command for profiling selected test type.

    Output command needs to be run from the command line outside the
    notebook and container.
    """
    hdbg.dassert_in(
        test_list_name,
        ["fast_tests", "slow_tests", "superslow_tests", "fast_slow_tests"],
    )
    command = f"invoke run_{test_list_name} -p 'dev_scripts --durations 0' 2>&1 | tee tmp.{test_list_name}_profile.txt"
    return command


# %% [markdown]
# # Profile

# %%
print(get_profiling_command(config["test_list_name"]))

# %% [markdown]
# You need to post this command to the terminal and wait for the tests to pass.

# %%
test_output = hio.from_file(f"/app/tmp.{config['test_list_name']}_profile.txt")

# %%
print(test_output)

# %% [markdown]
# Let's profile only calls, ignoring setups and teardowns.

# %%
durations = re.findall("\n  ==> (.*)s call", test_output)
durations = [float(duration) for duration in durations]
durations

# %% run_control={"marked": true}
plt.hist(durations)
_ = plt.title(f"Durations of {config['test_list_name']} in seconds")

# %%
