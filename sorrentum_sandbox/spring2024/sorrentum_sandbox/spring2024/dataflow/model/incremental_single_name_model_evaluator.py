"""
Import as:

import dataflow.model.incremental_single_name_model_evaluator as dtfmisnmoev
"""

from __future__ import annotations

import collections
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import pandas as pd

import core.finance as cofinanc
import core.signal_processing as csigproc
import core.statistics as costatis
import dataflow.model.dataflow_model_utils as dtfmdtfmout
import dataflow.model.stats_computer as dtfmostcom
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hlogging as hloggin

_LOG = logging.getLogger(__name__)


def compute_stats_for_single_name_artifacts(
    src_dir: str,
    file_name: str,
    prediction_col: str,
    target_col: str,
    start: Optional[hdateti.Datetime],
    end: Optional[hdateti.Datetime],
    selected_idxs: Optional[Iterable[int]] = None,
    aws_profile: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generates single-name stats.

    This function only requires maintaining at most one result bundle
    in-memory at a time.

    :return: dataframe of stats, with keys as column names and a row
        multiindex for grouped stats
    """
    stats = collections.OrderedDict()
    load_rb_kwargs = {"columns": list([prediction_col, target_col])}
    iterator = dtfmdtfmout.yield_experiment_artifacts(
        src_dir,
        file_name,
        load_rb_kwargs=load_rb_kwargs,
        selected_idxs=selected_idxs,
        aws_profile=aws_profile,
    )
    for key, artifact in iterator:
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "compute_stats_for_single_name_artifacts: memory_usage=%s",
                hloggin.get_memory_usage_as_str(None),
            )
        # Extract df and restrict to [start, end].
        df_for_key = artifact.result_df.loc[start:end].copy()
        # Compute (intraday) PnL.
        pnl = df_for_key[prediction_col] * df_for_key[target_col]
        df_for_key["pnl"] = pnl
        # Compute (intraday) stats.
        stats_computer = dtfmostcom.StatsComputer()
        stats[key] = stats_computer.compute_finance_stats(
            df_for_key,
            returns_col=target_col,
            positions_col=prediction_col,
            pnl_col="pnl",
        )
    # Generate dataframe from dictionary of stats.
    stats_df = pd.DataFrame(stats)
    # Perform multiple tests adjustment.
    adj_pvals = costatis.multipletests(
        stats_df.loc["signal_quality"].loc["sr.pval"], nan_mode="drop"
    ).rename("sr.adj_pval")
    # Add multiple test info to stats dataframe.
    adj_pvals = pd.concat(
        [adj_pvals.to_frame().transpose()], keys=["signal_quality"]
    )
    stats_df = pd.concat([stats_df, adj_pvals], axis=0)
    _LOG.info("memory_usage=%s", hloggin.get_memory_usage_as_str(None))
    return stats_df


def aggregate_single_name_models(
    src_dir: str,
    file_name: str,
    position_intent_1_col: str,
    ret_0_col: str,
    spread_0_col: str,
    prediction_col: str,
    target_col: str,
    start: Optional[hdateti.Datetime],
    end: Optional[hdateti.Datetime],
    selected_idxs: Optional[Iterable[int]] = None,
    aws_profile: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[Union[str, int], pd.DataFrame]]:
    expected_columns = [
        position_intent_1_col,
        ret_0_col,
        spread_0_col,
        prediction_col,
        target_col,
    ]
    load_rb_kwargs = {"columns": expected_columns}
    iterator = dtfmdtfmout.yield_experiment_artifacts(
        src_dir,
        file_name,
        load_rb_kwargs=load_rb_kwargs,
        selected_idxs=selected_idxs,
        aws_profile=aws_profile,
    )
    portfolio = pd.DataFrame()
    dfs = collections.OrderedDict()
    for key, artifact in iterator:
        _LOG.info(
            "aggregate_single_name_models: memory_usage=%s",
            hloggin.get_memory_usage_as_str(None),
        )
        # Extract df and restrict to [start, end].
        df_for_key = artifact.result_df.loc[start:end].copy()
        df_for_key = _process_single_name_result_df(
            df_for_key,
            position_intent_1_col=position_intent_1_col,
            ret_0_col=ret_0_col,
            spread_0_col=spread_0_col,
            prediction_col=prediction_col,
            target_col=target_col,
            start=start,
            end=end,
        )
        # Add to portfolio.
        portfolio = df_for_key.add(portfolio, fill_value=0)
        # Resample.
        dfs[key] = df_for_key.resample("B").sum(min_count=1)
    _LOG.info("memory_usage=%s", hloggin.get_memory_usage_as_str(None))
    return portfolio, dfs


def load_result_dfs(
    src_dir: str,
    file_name: str,
    load_rb_kwargs: Dict[str, Any],
    selected_idxs: Optional[Iterable[int]] = None,
    aws_profile: Optional[str] = None,
    start: Optional[hdateti.Datetime] = None,
    end: Optional[hdateti.Datetime] = None,
) -> Dict[int, pd.DataFrame]:
    """
    Loads result dataframes.

    Use `load_rb_kwargs` to restrict to desired columns.

    This function should be used judiciously on large runs due to the memory
    requirements.
    """
    iterator = dtfmdtfmout.yield_experiment_artifacts(
        src_dir,
        file_name,
        load_rb_kwargs=load_rb_kwargs,
        selected_idxs=selected_idxs,
        aws_profile=aws_profile,
    )
    dfs = collections.OrderedDict()
    for key, artifact in iterator:
        _LOG.info(
            "load_result_dfs: memory_usage=%s",
            hloggin.get_memory_usage_as_str(None),
        )
        # Extract df and restrict to [start, end].
        df = artifact.result_df.loc[start:end].copy()
        dfs[key] = df
    _LOG.info("memory_usage=%s", hloggin.get_memory_usage_as_str(None))
    return dfs


def _process_single_name_result_df(
    df: pd.DataFrame,
    position_intent_1_col: str,
    ret_0_col: str,
    spread_0_col: str,
    prediction_col: str,
    target_col: str,
    start: hdateti.Datetime,
    end: hdateti.Datetime,
) -> pd.DataFrame:
    """
    Process a result bundle df corresponding to a single name.

    This function
      - Calculates PnL in two ways
      - Calculates half-spread costs
      - Standardizes column names

    :param df: result dataframe
    :param position_intent_1_col: one-step ahead position intents in units of
        money
    :param ret_0_col: returns of underlying instrument realized at current time
    :param spread_0_col: relative spread at current time
    :param prediction_col: prediction generated by model (e.g., prediction of
        two-step ahead z-scored returns)
    :param target_col: the target of `prediction`, aligned with `prediction`
        (e.g., two-step ahead z-scored returns)
    :param start: first time to load (inclusive); `None` means all available
    :param end: last time to load (inclusive); `None` means all available
    :return: dataframe with pnl and spread costs calculated
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    expected_columns = [
        position_intent_1_col,
        ret_0_col,
        spread_0_col,
        prediction_col,
        target_col,
    ]
    hdbg.dassert_is_subset(expected_columns, df.columns.to_list())
    hdbg.dassert_not_in("pnl_0", expected_columns)
    hdbg.dassert_not_in("research_pnl_2", expected_columns)
    hdbg.dassert_not_in("half_spread_cost", expected_columns)
    df = df[expected_columns].loc[start:end].copy()
    df.rename(
        columns={
            position_intent_1_col: "position_intent_1",
            ret_0_col: "ret_0",
            spread_0_col: "spread_0",
            prediction_col: "prediction",
            target_col: "target",
        },
        inplace=True,
    )
    long_and_short_intents = csigproc.split_positive_and_negative_parts(
        df["position_intent_1"]
    )
    df["position_intent_1_long"] = long_and_short_intents["positive"]
    df["position_intent_1_short"] = long_and_short_intents["negative"]
    # Compute PnL from predictions (e.g., in z-score space).
    research_pnl_2 = df["prediction"] * df["target"]
    df["research_pnl_2"] = research_pnl_2
    # Compute PnL in original returns space.
    pnl_0 = cofinanc.compute_pnl(
        df, position_intent_col="position_intent_1", return_col="ret_0"
    )
    df["pnl_0"] = pnl_0
    half_spread_cost = cofinanc.compute_spread_cost(
        df,
        target_position_col="position_intent_1",
        spread_col="spread_0",
        spread_fraction_paid=0.5,
    )
    df["half_spread_cost"] = half_spread_cost
    return df


def load_info(
    src_dir: str,
    file_name: str,
    info_path: List[str],
    selected_idxs: Optional[Iterable[int]] = None,
    aws_profile: Optional[str] = None,
) -> Dict[int, Any]:
    """
    Return a subset of `info` from result bundles.

    :param info_path: a list of keys to traverse for subsetting `info`. An
        empty list means no restriction.
    :return: dict keyed by experiment, with value equal to `info`
        restricted to `info_path`
    """
    iterator = dtfmdtfmout.yield_experiment_artifacts(
        src_dir,
        file_name,
        load_rb_kwargs={"columns": []},
        selected_idxs=selected_idxs,
        aws_profile=aws_profile,
    )
    info_dict = collections.OrderedDict()
    for key, artifact in iterator:
        info = artifact.info
        for k in info_path:
            info = info[k]
        info_dict[key] = info
    _LOG.info("memory_usage=%s", hloggin.get_memory_usage_as_str(None))
    return info_dict
