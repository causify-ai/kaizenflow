# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.3.4
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports

# %%
import numpy as np
import pandas as pd

import core.explore as coexplor

# %load_ext autoreload
# %autoreload 2

# %% [markdown]
# # coexplor.display_df

# %%
np.random.seed(100)

x = 5 * np.random.randn(100)
y = x + np.random.randn(*x.shape)
df = pd.DataFrame()
df["x"] = x
df["y"] = y

coexplor.display_df(df)

# %% [markdown]
# # coexplor.ols_regress_series

# %%
np.random.seed(100)

x = 5 * np.random.randn(100)
y = x + np.random.randn(*x.shape)
df = pd.DataFrame()
df["x"] = x
df["y"] = y

coexplor.ols_regress_series(df["x"], df["y"], intercept=True)

# %% [markdown]
# # Qgrid

import pandas as pd

# %%
import qgrid

print(pd.__version__)
print(qgrid.__version__)

# %%
df = pd.DataFrame(
    {
        "num_legs": [2, 4, 8, 0],
        "num_wings": [2, 0, 0, 0],
        "num_specimen_seen": [10, 2, 1, 8],
    },
    index=["falcon", "dog", "spider", "fish"],
)

df

# %%
qgrid_widget = coexplor.to_qgrid(df)
qgrid_widget

# %%
# If you modify the df with grid, you need to get the modified version.
# I.e., the dataframe is not modified in place.
modified_df = qgrid_widget.get_changed_df()
display(modified_df)

print(df.equals(modified_df))

# %%
import numpy as np
import pandas as pd
import qgrid

randn = np.random.randn
df_types = pd.DataFrame(
    {
        "A": pd.Series(
            [
                "2013-01-01",
                "2013-01-02",
                "2013-01-03",
                "2013-01-04",
                "2013-01-05",
                "2013-01-06",
                "2013-01-07",
                "2013-01-08",
                "2013-01-09",
            ],
            index=list(range(9)),
            dtype="datetime64[ns]",
        ),
        "B": pd.Series(randn(9), index=list(range(9)), dtype="float32"),
        "C": pd.Categorical(
            [
                "washington",
                "adams",
                "washington",
                "madison",
                "lincoln",
                "jefferson",
                "hamilton",
                "roosevelt",
                "kennedy",
            ]
        ),
        "D": [
            "foo",
            "bar",
            "buzz",
            "bippity",
            "boppity",
            "foo",
            "foo",
            "bar",
            "zoo",
        ],
    }
)
df_types["E"] = df_types["D"] == "foo"
qgrid_widget = qgrid.show_grid(df_types, show_toolbar=True)
qgrid_widget
