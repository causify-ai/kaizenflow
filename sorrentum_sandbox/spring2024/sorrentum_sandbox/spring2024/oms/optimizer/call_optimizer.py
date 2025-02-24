"""
Import as:

import oms.optimizer.call_optimizer as oopcaopt
"""

import logging
import os
from typing import Any, Dict, List, Optional

import invoke
import numpy as np
import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hpickle as hpickle
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def compute_target_holdings_and_trades_notional(
    df: pd.DataFrame,
    *,
    style: str,
    **kwargs: Dict[str, Any],
) -> pd.DataFrame:
    """
    Compute target trades from holdings (dollar-valued) and predictions.

    This is a stand-in for optimization. This function does not have
    access to prices and so does not perform any conversions to or from
    shares. It also needs to be told the id associated with cash.

    :param df: a dataframe with current positions (in dollars) and
        predictions
    :return: a dataframe with target positions and trades (denominated
        in dollars)
    """
    # Sanity-check the dataframe.
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert(not df.empty)
    hdbg.dassert_is_subset(
        ["asset_id", "prediction", "volatility", "holdings_notional"], df.columns
    )
    hdbg.dassert_not_in("target_holdings_notional", df.columns)
    hdbg.dassert_not_in("target_trades_notional", df.columns)
    #
    hdbg.dassert(not df["prediction"].isna().any())
    hdbg.dassert(not df["volatility"].isna().any())
    hdbg.dassert(not df["holdings_notional"].isna().any())
    #
    df = df.set_index("asset_id")
    hdbg.dassert(not df.index.has_duplicates)
    #
    predictions = df["prediction"].rename(0).to_frame().T
    volatility = df["volatility"].rename(0).to_frame().T
    if style == "cross_sectional":
        target_holdings_notional = (
            cofinanc.compute_target_positions_cross_sectionally(
                predictions,
                volatility,
                **kwargs,
            )
        )
    elif style == "longitudinal":
        target_holdings_notional = (
            cofinanc.compute_target_positions_longitudinally(
                predictions,
                volatility,
                spread=None,
                **kwargs,
            )
        )
    else:
        raise ValueError("Unsupported `style`=%s", style)
    hdbg.dassert_eq(target_holdings_notional.shape[0], 1)
    target_holdings_notional = pd.Series(
        target_holdings_notional.values[0],
        index=target_holdings_notional.columns,
        name="target_holdings_notional",
        dtype="float",
    )
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "`target_holdings_notional`=\n%s",
            hpandas.df_to_str(
                target_holdings_notional, print_dtypes=True, print_shape_info=True
            ),
        )
    # These positions are expressed in dollars.
    holdings_notional = df["holdings_notional"]
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "`holdings_notional`=\n%s",
            hpandas.df_to_str(
                holdings_notional, print_dtypes=True, print_shape_info=True
            ),
        )
    target_trades_notional = target_holdings_notional - holdings_notional
    df["target_holdings_notional"] = target_holdings_notional
    df["target_trades_notional"] = target_trades_notional
    return df


def convert_target_holdings_and_trades_to_shares_and_adjust_notional(
    df: pd.DataFrame,
    *,
    quantization: Optional[int],
    asset_id_to_decimals: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Computes target holdings and trades in shares; adjusts target notionals.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert(not df.empty)
    hdbg.dassert_is_subset(
        [
            "price",
            "holdings_shares",
            "target_holdings_notional",
            "target_trades_notional",
        ],
        df.columns,
    )
    hdbg.dassert_not_in("target_holdings_shares", df.columns)
    hdbg.dassert_not_in("target_trades_shares", df.columns)
    #
    hdbg.dassert(not df.index.has_duplicates)
    # Convert target trades in notional to shares, without any quantization.
    target_trades_shares_before_quantization = (
        df["target_trades_notional"] / df["price"]
    )
    target_trades_shares_before_quantization.replace(
        [-np.inf, np.inf], np.nan, inplace=True
    )
    target_trades_shares_before_quantization = (
        target_trades_shares_before_quantization.fillna(0)
    )
    # Compute `target_trades_shares` post-quantization.
    target_trades_shares = cofinanc.quantize_shares(
        target_trades_shares_before_quantization,
        quantization,
        asset_id_to_decimals=asset_id_to_decimals,
    )
    # hdbg.dassert(np.isfinite(target_trades_shares).all())
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Post-quantization target_trades_shares adjusted from %s to %s",
            hpandas.df_to_str(target_trades_shares_before_quantization),
            hpandas.df_to_str(target_trades_shares),
        )
    df["target_trades_shares"] = target_trades_shares
    # Update `target_trades_notional` post-quantization.
    target_trades_notional = target_trades_shares * df["price"]
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Post-quantization target_trades_notional adjusted from %s to %s",
            hpandas.df_to_str(df["target_trades_notional"]),
            hpandas.df_to_str(target_trades_notional),
        )
    df["target_trades_notional"] = target_trades_notional
    # Computer `target_holdings_shares` post-quantization.
    holdings_shares = df["holdings_shares"]
    target_holdings_shares = holdings_shares + target_trades_shares
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "`target_holdings_shares`=%s",
            hpandas.df_to_str(target_trades_notional),
        )
    df["target_holdings_shares"] = target_holdings_shares
    # Update `target_holdings_notional` post-quantization.
    target_holdings_notional = target_holdings_shares * df["price"]
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "Post-quantization target_holdings_notional adjusted from %s to %s",
            hpandas.df_to_str(df["target_holdings_notional"]),
            hpandas.df_to_str(target_holdings_notional),
        )
    df["target_holdings_notional"] = target_holdings_notional
    return df


def run_optimizer(
    config: cconfig.Config,
    df: pd.DataFrame,
    *,
    tmp_dir: str = "tmp.optimizer_stub",
) -> pd.DataFrame:
    """
    Run the optimizer through Docker.

    The flow is:
       - Save the input data in a temp dir
       - Start an `opt` Docker container
       - Run the optimizer
       - Save the optimizer output to a temp dir

    :param tmp_dir: local dir to use to exchange parameters with the "remote"
        optimizer
    """
    # Login in the Docker on AWS to pull the `opt` image.
    # TODO(Grisha): Move this inside the `opt_docker_cmd`.
    # TODO(Grisha): maybe move `docker_login` to the entrypoint?
    # To avoid to call init_logger overwriting the call to it from `main`.
    import helpers.lib_tasks_docker as hlitadoc

    ctx = invoke.context.Context()
    hlitadoc.docker_login(ctx)
    # Serialize the inputs in `tmp_dir`.
    hio.create_dir(tmp_dir, incremental=True)
    input_obj = {"config": config, "df": df}
    input_file = os.path.join(tmp_dir, "input.pkl")
    hpickle.to_pickle(input_obj, input_file)
    # Get path to the `optimizer_stub.py`.
    root_dir = hgit.get_client_root(False)
    optimizer_stub_file_path = os.path.join(
        root_dir, "optimizer/optimizer_stub.py"
    )
    hdbg.dassert_file_exists(optimizer_stub_file_path)
    # Build the command to be executed in `opt` container.
    docker_cmd_: List[str] = []
    docker_cmd_.append(optimizer_stub_file_path)
    docker_cmd_.append(f"--input_file {input_file}")
    output_file = os.path.join(tmp_dir, "output.pkl")
    docker_cmd_.append(f"--output_file {output_file}")
    docker_cmd_.append("-v INFO")
    docker_cmd = " ".join(docker_cmd_)
    # Call `optimizer_stub` through `opt` Docker container.
    optimizer_cmd_: List[str] = []
    # `opt` invokes can only be run from `optimizer` dir.
    optimizer_cmd_.append("cd optimizer &&")
    optimizer_cmd_.append(f"invoke opt_docker_cmd --cmd '{docker_cmd}'")
    optimizer_cmd = " ".join(optimizer_cmd_)
    # TODO(Grisha): call `opt_docker_cmd` directly.
    hsystem.system(optimizer_cmd)
    # Read the output from `tmp_dir`.
    output_file = os.path.join(tmp_dir, "output.pkl")
    output_df = hpickle.from_pickle(output_file)
    return output_df
