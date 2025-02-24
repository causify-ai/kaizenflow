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
# Implement a simple risk model estimation framework.

# %% [markdown]
# # Imports

# %%
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn.linear_model as slmode

import core.artificial_signal_generators as carsigen
import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import core.finance.market_data_example as cfmadaex
import core.signal_processing as csigproc
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Generate input data

# %%
# Assume there are `n` assets
# - Generate returns for the `n` assets at each time `t` (normalized)
# - Generate `k` features for each asset (centered, normalized)
# - Wrap in a dataframe source node

# %%
n_assets = 4
n_features = 2
n_periods = 10
freq = "B"
period_start = "2023-05-01"
rng_seed = 1


# %%
def get_random_data(
    n_assets: int,
    n_features: int,
    n_periods: int,
    period_start: str,
    freq: str,
    seed: int
) -> pd.DataFrame():
    """
    Generate a dataframe of random returns and random features.
    """
    # Create datetime index for dataframe.
    idx = pd.date_range(start=period_start, periods=n_periods, freq=freq)
    # Create columns names for the X matrix.
    cols = [f"x_{k}" for k in range(1, n_features + 1)]
    cols = cols + ["ret_0"]
    # Instantiate random number generator.
    rng = np.random.default_rng(rng_seed)
    dfs = {}
    for n in range(n_assets):
        asset_id = 100 + n
        dfs[asset_id] = pd.DataFrame(rng.standard_normal(
            (n_periods, n_features + 1)
        ), idx, cols)
    df = pd.concat(dfs, axis=1).swaplevel(axis=1).sort_index(axis=1)
    return df


# %%
# The innermost column level consists of the asset ids.
# The outermost column level is comprised of the column names (features,
#  returns, price data, etc.).
data = get_random_data(
    n_assets,
    n_features,
    n_periods,
    period_start,
    freq,
    rng_seed
)
display(data.head())

# %% [markdown]
# ## Instantiate a node and DAG

# %%
# Here use instantiate a `DataSource` object, which is a subclass of a
#. dataflow `Node`.
# Dataflow supports various source nodes, such as
# - a node that wraps a dataframe (as we use here)
# - a node that wraps a function (where the output of the function is
#   a dataframe)
# - a node that loads data from disk
# - a node that supplies data from our `MarketData` object
node = dtfcore.DfDataSource("data", data)

# %%
# A DAG consists of (fully instantiated) Nodes along with the directed
#  edges between them.
# In this example notebook, we build a DAG incrementally.
# For DAGs we re-use, we specify in code a `DagBuilder` object, which
#  specifies how to build a DAG and provides a means to configure it.
dag = dtfcore.DAG(name="simple_risk_model", mode="loose")

# %%
# Here we use a convenience method for linear DAGs.
dag.append_to_tail(node)
# At each stage in this notebook, we draw the DAG.
dtfcore.draw(dag)

# %%
# We specify which node to run "up to" and whether to run in "fit" or
#  "predict" mode.
# All nodes that are less than or equal to the specified node
#  (in the topological sense) are executed.
data_df = dag.run_leq_node("data", "fit")["df_out"]

# %%
# The data matches the input data.
# In this notebook, all data is processed at once. However, dataflow
#  supports the notion of a clock and supports running in an
#  incremental mode.
data_df.head()

# %% [markdown]
# # Estimate model components

# %% [markdown]
# ## Estimate beta

# %%
cols = data.columns.levels[0]
display(cols)
x_vars = list(cols.difference(["ret_0"]))
y_vars = ["ret_0"]

# %%
# Use one of the dataflow nodes that wraps sklearn.
# This node
# - wraps supervised models
# - learns a model for each asset independently (we also have a wrapper
#   that pools across all assets)
# The "model_func" specifies which sklearn model to use.
# The sklearn model is configured through "model_kwargs", which are
#  forwarded to the model.
node_config = {
    "in_col_groups": [(x,) for x in cols],
    "out_col_group": (),
    "x_vars": x_vars,
    "y_vars": y_vars,
    "steps_ahead": 1,
    "model_func": slmode.LinearRegression,
    "model_kwargs": {
        "fit_intercept": False,
    },
    "nan_mode": "drop",
}
node = dtfcore.MultiindexSkLearnModel(
    "sklearn",
    **node_config,
)

# %%
dag.append_to_tail(node)
dtfcore.draw(dag)

# %%
sklearn_df = dag.run_leq_node("sklearn", "fit")["df_out"]

# %%
sklearn_df.head()

# %% [markdown]
# ## Estimate residual returns variances

# %%
sklearn_df.head()

# %%
# The sklearn modeling node does not automatically perform the
#  residualization. (We do have a different sklearn node that
#  learns a factor model (e.g., PCA) and automatically
#  residualizes.)
# Here we create a node to do the column arithmetic.
node_config = {
    "in_col_groups": [
        ("ret_0.shift_-1",), 
        ("ret_0.shift_-1_hat",),
    ],
    "out_col_group": (),
    "transformer_func": cofeatur.combine_columns,
    "transformer_kwargs": {
        "term1_col": "ret_0.shift_-1",
        "term2_col": "ret_0.shift_-1_hat",
        "out_col": "residual.shift_-1",
        "operation": "sub"
    }
}
node = dtfcore.GroupedColDfToDfTransformer(
    "residualize",
    **node_config,
)

# %%
dag.append_to_tail(node)
dtfcore.draw(dag)

# %%
residualize_df = dag.run_leq_node("residualize", "fit")["df_out"]

# %%
residualize_df.head()

# %%
# Next we use a simple EWMA to explicitly estimate the variances of the
#  residuals (though the sklearn model is internally computing this in
#  the regression).
node_config = {
    "in_col_group": ("residual.shift_-1",), 
    "out_col_group": ("smoothed_squared_residual.shift_-1",),
    "transformer_func": csigproc.compute_rolling_norm,
    "transformer_kwargs": {
        "tau": 10,
    }
}
node = dtfcore.SeriesToSeriesTransformer(
    "compute_rolling_norm",
    **node_config,
)

# %%
dag.append_to_tail(node)
dtfcore.draw(dag)

# %%
compute_rolling_norm_df = dag.run_leq_node(
    "compute_rolling_norm", "fit"
)["df_out"]

# %%
compute_rolling_norm_df.head()

# %% [markdown]
# ## Estimate factor returns variance-covariance matrices

# %%
# TODO: We can compute beta beta^transpose, linearizing the matrix as
#  feature columns, and then apply EWMA smoothing as above.

# %% [markdown]
# # Extract estimates and compute statistics

# %%
# Information supplementary to the dataframes can be accessed
# (such as any sklearn model info).
sklearn_fit_state = dag.get_node("sklearn").get_fit_state()
display(sklearn_fit_state.keys())

# %%
# Note that we may recover from sklearn information such as
# - model coefficients
# - model score
# - full model specification
sklearn_fit_state["_key_fit_state"][100]


# %% [markdown]
# # Alternative DAG construction method

# %%
# In transferring this DAG from a notebook to code, we would do something
# similar to the following:

class SimpleRiskModel_DagBuilder(dtfcore.DagBuilder):
    """
    A pipeline similar to real feature processing.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_trading_period(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        _ = self
        raise NotImplementedError

    def get_required_lookback_in_effective_days(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def set_weights(
        self, config: cconfig.Config, weights: pd.Series
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
        dict_ = {
            self._get_nid("sklearn"): {
                "in_col_groups": [(x,) for x in cols],
                "out_col_group": (),
                "x_vars": x_vars,
                "y_vars": y_vars,
                "steps_ahead": 1,
                "model_kwargs": {
                    "fit_intercept": False,
                },
                "nan_mode": "drop",
            },
            self._get_nid("residualize"): {
                "in_col_groups": [
                    ("ret_0.shift_-1",), 
                    ("ret_0.shift_-1_hat",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "term1_col": "ret_0.shift_-1",
                    "term2_col": "ret_0.shift_-1_hat",
                    "out_col": "residual.shift_-1",
                    "operation": "sub"
                }
            },
            self._get_nid("compute_rolling_node"): {
                "in_col_group": ("residual.shift_-1",), 
                "out_col_group": ("smoothed_squared_residual.shift_-1",),
                "transformer_kwargs": {
                    "tau": 10,
                }
            },
        }
        config = cconfig.Config.from_dict(dict_)
        return config

    def _get_dag(
        self,
        config: cconfig.Config,
        mode: str = "strict",
    ) -> dtfcore.DAG:
        dag = dtfcore.DAG(mode=mode)
        _LOG.debug("%s", config)
        #
        stage = "sklearn"
        nid = self._get_nid(stage)
        node = dtfcore.MultiindexSkLearnModel(
            nid,
            model_func=slmode.LinearRegression,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        node = dtfcore.GroupedColDfToDfTransformer(
            "residualize",
            transformer_func=cofeatur.combine_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        node = dtfcore.SeriesToSeriesTransformer(
            nid,
            transformer_func=csigproc.compute_rolling_norm,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        return dag

# %%
