"""
Import as:

import core.statistics.signed_runs as cstsirun
"""
import logging

import pandas as pd

import core.signal_processing as csigproc
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_signed_run_starts(srs: pd.Series) -> pd.Series:
    """
    Compute the start of each signed run.

    :param srs: series of floats
    :return: a series with a +1 at the start of each new positive run and a -1
        at the start of each new negative run; NaNs are ignored
    """
    # Drop NaNs before determining run starts.
    signed_runs = csigproc.sign_normalize(srs).dropna()
    # Determine start of runs.
    # A new run starts at position j if and only if
    # - the signed value at `j` is +1 or -1 and
    # - the value at `j - 1` is different from the value at `j`
    is_nonzero = signed_runs != 0
    is_diff = signed_runs.diff() != 0
    run_starts = signed_runs[is_nonzero & is_diff]
    return run_starts.reindex(srs.index)


def compute_signed_run_ends(srs: pd.Series) -> pd.Series:
    """
    Calculate the end of each signed run.

    NOTE: This function is not casual (because of our choice of indexing).

    :param srs: as in `compute_signed_run_starts()`
    :return: as in `compute_signed_run_starts()`, but with positive/negative
        run indicator at the last time of the run. Note that this is not casual.
    """
    # Calculate run ends by calculating the run starts of the reversed series.
    reversed_srs = srs.iloc[::-1]
    reversed_run_starts = compute_signed_run_starts(reversed_srs)
    run_ends = reversed_run_starts.iloc[::-1]
    return run_ends


def compute_signed_run_lengths(
    srs: pd.Series,
) -> pd.Series:
    """
    Calculate lengths of signed runs (in sampling freq).

    :param srs: series of floats
    :return: signed lengths of run, i.e., the sign indicates whether the
        length corresponds to a positive run or a negative run. Index
        corresponds to end of run (not causal).
    """
    signed_runs = csigproc.sign_normalize(srs)
    run_starts = compute_signed_run_starts(srs)
    run_ends = compute_signed_run_ends(srs)
    # Sanity check indices.
    hdbg.dassert(signed_runs.index.equals(run_starts.index))
    hdbg.dassert(run_starts.index.equals(run_ends.index))
    # Get starts of runs or zero position runs (zero positions are filled with
    # `NaN`s in `compute_signed_runs_*`).
    run_starts_idx = run_starts.loc[run_starts != 0].dropna().index
    run_ends_idx = run_ends.loc[run_ends != 0].dropna().index
    # To calculate lengths of runs, we take a running cumulative sum of
    # absolute values so that run lengths can be calculated by subtracting
    # the value at the beginning of each run from its value at the end.
    signed_runs_abs_cumsum = signed_runs.abs().cumsum()
    # Align run starts and ends for vectorized subtraction.
    t0s = signed_runs_abs_cumsum.loc[run_starts_idx].reset_index(drop=True)
    t1s = signed_runs_abs_cumsum.loc[run_ends_idx].reset_index(drop=True)
    # Subtract and correct for off-by-one.
    run_lengths = t1s - t0s + 1
    # Recover run signs.
    run_lengths = run_lengths * run_starts.loc[run_starts_idx].reset_index(
        drop=True
    )
    # Reindex according to the run ends index.
    run_length_srs = pd.Series(
        index=run_ends_idx, data=run_lengths.values, name=srs.name
    )
    return run_length_srs
