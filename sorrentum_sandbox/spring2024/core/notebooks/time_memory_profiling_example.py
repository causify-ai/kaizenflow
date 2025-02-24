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
# # Description

# %% [markdown]
# Demonstrate time and memory profiling tools on a toy example.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %load_ext memory_profiler

import logging
import time

import IPython.display as dspl
import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Functions

# %%
def func1() -> pd.DataFrame:
    time.sleep(2)
    df = pd.DataFrame(["str1"] * int(1e6))
    return df


def func2(df: pd.DataFrame) -> pd.DataFrame:
    time.sleep(3)
    df[1] = df[0] + "_str2"
    return df


def func3() -> pd.DataFrame:
    time.sleep(1)
    df = func1()
    df = func2(df)
    return df


# %% [markdown]
# # Profile time

# %% [markdown]
# ## Profile overall time

# %%
# %%time
df = func3()

# %% [markdown]
# ## Time by function

# %% [markdown]
# The docs do not say that, but under the hood `%prun` uses `cProfile`: https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L22

# %%
# We can suppress output to the notebook by specifying "-q".
# %prun -D tmp.pstats df = func3()

# %%
# !gprof2dot -f pstats tmp.pstats | dot -Tpng -o output.png
dspl.Image(filename="output.png")

# %% [markdown]
# `gprof2dot` supports thresholds that make output more readable: https://github.com/jrfonseca/gprof2dot#documentation

# %%
# !gprof2dot -n 5 -e 5 -f pstats tmp.pstats | dot -Tpng -o output.png
dspl.Image(filename="output.png")

# %% [markdown]
# # Profile memory

# %% [markdown]
# ## Peak memory

# %%
# %%memit
df = func3()

# %% [markdown]
# ## Memory by line

# %% [markdown]
# The function needs to be defined outside of a notebook to profile it by line, but this is how to execute the profiling:

# %%
# %mprun -f func3 df = func3()

# %%
