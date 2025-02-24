from typing import Tuple

import pandas as pd

import core.config as cconfig
import dataflow.core.node as dtfcornode
import helpers.hpandas as hpandas


def test_get_set_state(
    fit_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    config: cconfig.Config,
    node: dtfcornode.Node,
    decimals: float = 3,
) -> Tuple[str, str]:
    """
    Helper for testing `get_fit_state()` and `set_fit_state()` methods.

    :param fit_df: dataframe used for fitting a node
    :param predict_df: dataframe used as node input for `predict()`
    :param config: config for initializing `node`
    :param node: dataflow node class
    :return: expected (generated from trained node), actual (generated from
        node initialized from state)
    """
    node1 = node("sklearn", **config.to_dict())
    # Fit model and get state.
    node1.fit(fit_df)
    state = node1.get_fit_state()
    # Predict using fitted node.
    df_out1 = node1.predict(predict_df)["df_out"]
    expected = hpandas.df_to_str(
        df_out1.round(decimals), num_rows=None, precision=decimals
    )
    # Create a new node, set state, and predict.
    node2 = node("sklearn", **config.to_dict())
    node2.set_fit_state(state)
    df_out2 = node2.predict(predict_df)["df_out"]
    actual = hpandas.df_to_str(
        df_out2.round(decimals), num_rows=None, precision=decimals
    )
    return expected, actual


def get_fit_predict_outputs(
    data: pd.DataFrame,
    node: dtfcornode.Node,
    decimals: float = 3,
) -> Tuple[str, str]:
    """
    Get `node` outputs from both `fit()` and `predict()` calls on `data`.

    In the case of a transformer, these should be identical.

    :param node: initialized Node
    :param decimals: decimal precision of dataframe outputs
    :return: dataframes as strings
    """
    # Generate output from `fit()` and `predict()` calls.
    df_fit_out = node.fit(data)["df_out"]
    df_predict_out = node.predict(data)["df_out"]
    # Convert dataframes to strings.
    fit = hpandas.df_to_str(
        df_fit_out.round(decimals), num_rows=None, precision=decimals
    )
    predict = hpandas.df_to_str(
        df_predict_out.round(decimals), num_rows=None, precision=decimals
    )
    return fit, predict
