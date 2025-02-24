"""
Import as:

import core.statistics.random_samples as cstrasam
"""

import logging
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def get_iid_standard_gaussian_samples(n_samples: int, seed: int) -> pd.Series:
    """
    Draw `n_samples` of iid standard Gaussian rvs.

    :param n_samples: number of samples to draw
    :param seed: seed to forward to numpy random number generator
    :return: series of `n_samples` IID Gaussian random samples
    """
    rng = np.random.default_rng(seed=seed)
    gaussians = rng.standard_normal(size=n_samples)
    srs = pd.Series(
        gaussians,
        range(1, n_samples + 1),
        name=f"n_samples={n_samples}_seed={seed}",
    )
    return srs


def get_iid_rademacher_samples(n_samples: int, seed: int) -> pd.Series:
    """
    Draw `n_samples` of iid Rademacher rvs.

    :param n_samples: number of samples to draw
    :param seed: seed to forward to numpy random number generator
    :return: series of `n_samples` IID Rademacher random samples
    """
    rng = np.random.default_rng(seed=seed)
    samples = rng.integers(low=0, high=2, size=n_samples)
    srs = pd.Series(
        samples,
        range(1, n_samples + 1),
        name=f"n_samples={n_samples}_seed={seed}",
    )
    srs = (2 * srs - 1).astype(np.int64)
    return srs


def get_iid_samples_from_cdf(
    cdf: pd.Series, n_samples: int, seed: int
) -> pd.Series:
    """
    Sample from a CDF using the inverse transform sampling method.
    """
    hdbg.dassert_isinstance(cdf, pd.Series)
    # Ensure that all values are nonnegative.
    hdbg.dassert_lte(0, cdf.min())
    # Ensure that indices are increasing.
    hpandas.dassert_increasing_index(cdf)
    # Ensure that the values are increasing.
    hdbg.dassert_eq((cdf - cdf.shift(1) < 0).sum(), 0)
    # Ensure that all values are less than or equal to one,
    #  within some epsilon tolerance.
    epsilon = 1e-4
    hdbg.dassert_lte(cdf.max(), 1 + epsilon)
    # TODO(Paul): Add a check to ensure that the last value is sufficiently
    #   close to 1.
    # Generate IID uniform random samples.
    rng = np.random.default_rng(seed=seed)
    uniforms = rng.uniform(size=n_samples)
    # Perform the inverse transform step for each uniform random sample.
    samples = []
    for uniform in uniforms:
        srs = cdf[cdf >= uniform]
        if not srs.empty:
            sample = srs.idxmin()
        else:
            sample = cdf.idxmin()
        samples.append(sample)
    srs = pd.Series(
        samples,
        range(1, n_samples + 1),
        name=f"n_samples={n_samples}_seed={seed}",
    )
    return srs


def convert_increments_to_random_walk(srs: pd.Series) -> pd.Series:
    """
    Convert increments to a random walk starting from zero.
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    vals = [0] + srs.to_list()
    #
    random_walk = pd.Series(vals, index=range(srs.size + 1), name=srs.name)
    random_walk = random_walk.cumsum()
    return random_walk


def annotate_random_walk(
    srs: pd.Series,
    add_extended_annotations: bool = False,
) -> pd.DataFrame:
    """
    Annotate a random walk with running features.

    "Adjusted" features center the random walk at the origin and divide
    by the square root of the number of steps (taken so far).
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    srs_list = [srs]
    # Add running max.
    running_max = srs.cummax().rename("high")
    srs_list.append(running_max)
    # Add running min.
    running_min = srs.cummin().rename("low")
    srs_list.append(running_min)
    # Add walk with a standard name.
    random_walk = srs.rename("close")
    srs_list.append((random_walk))
    # Add running mean.
    running_mean = srs.expanding(1).mean().rename("mean")
    srs_list.append(running_mean)
    # Add running standard deviation.
    running_std = srs.expanding(1).std().rename("std")
    srs_list.append(running_std)
    #
    if add_extended_annotations:
        # Add range.
        range_ = (running_max - running_min).rename("range")
        srs_list.append(range_)
        running_max_minus_random_walk = (running_max - random_walk).rename(
            "high_minus_close"
        )
        srs_list.append(running_max_minus_random_walk)
        #
        sqrt_srs = pd.Series(
            [np.sqrt(n) for n in range(1, srs.size + 1)], index=srs.index
        )
        first_value = srs.iloc[0]
        normalized_max = ((running_max - first_value) / sqrt_srs).rename(
            "adj_high"
        )
        srs_list.append(normalized_max)
        normalized_min = ((running_min - first_value) / sqrt_srs).rename(
            "adj_low"
        )
        srs_list.append(normalized_min)
        normalized_random_walk = ((random_walk - first_value) / sqrt_srs).rename(
            "adj_close"
        )
        srs_list.append(normalized_random_walk)
        normalized_mean = ((running_mean - first_value) / sqrt_srs).rename(
            "adj_mean"
        )
        srs_list.append(normalized_mean)
        normalized_std = (running_std / sqrt_srs).rename("adj_std")
        srs_list.append(normalized_std)
        #
        normalized_range = (range_ / sqrt_srs).rename("adj_range")
        srs_list.append(normalized_range)
        normalized_max_minus_random_walk = (
            running_max_minus_random_walk / sqrt_srs
        ).rename("adj_high_minus_close")
        srs_list.append(normalized_max_minus_random_walk)
    #
    df = pd.concat(srs_list, axis=1)
    return df


def summarize_random_walk(
    srs: pd.Series,
) -> pd.DataFrame:
    """
    Compute random walk summary stats.
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert(not srs.isna().any())
    # Number of random walk steps (assuming first value is the starting point).
    n_steps = srs.count() - 1
    # Adjustment factor for normalization.
    sqrt_count = np.sqrt(n_steps)
    #
    mean = srs.mean()
    std = srs.std()
    # OHLC-type stats and range.
    open_ = srs.iloc[0]
    high = srs.max()
    low = srs.min()
    close = srs.iloc[-1]
    range_ = high - low
    #
    dict_ = {
        # OHLCV-type stats.
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "n_steps": n_steps,
        #
        "range": range_,
        "mean": mean,
        "std": std,
        # Count-adjusted stats.
        "adj_high": (high - open_) / sqrt_count,
        "adj_low": (low - open_) / sqrt_count,
        "adj_close": (close - open_) / sqrt_count,
        #
        "adj_range": (high - low) / sqrt_count,
        "adj_mean": mean / sqrt_count,
        "adj_std": std / sqrt_count,
    }
    return pd.Series(dict_, name=srs.name)


def apply_func_to_random_walk(
    func: Callable,
    sample_sizes: List[int],
    seeds: Iterable[int],
    increment_func: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Apply function `func` to random walks.

    :param func: a function that accepts a random walk and returns a
        pd.Series
    :param sample_sizes: list of sample sizes to use in generating
        random walks
    :param seeds: seeds to iterate over for each sample size
    :param increment_func: function that accepts a "sample_size" and
        "seed" to generate random walk increments
    """
    if increment_func is None:
        increment_func = get_iid_standard_gaussian_samples
    func_results = []
    for n_samples in tqdm(sample_sizes, desc="samples_sizes"):
        for seed in tqdm(seeds, desc="seeds"):
            increments = increment_func(n_samples, seed)
            random_walk = convert_increments_to_random_walk(increments)
            result = func(random_walk)
            func_results.append(result)
    df = pd.concat(func_results, axis=1).T
    return df


def get_staged_random_walk(
    stage_steps: List[int], seed: int
) -> Dict[int, pd.Series]:
    """
    Return a random walk split into stages, indexed by stage.
    """
    n_stages = len(stage_steps)
    _LOG.debug("n_stages=%s", n_stages)
    n_steps = sum(stage_steps) + n_stages - 1
    _LOG.debug("n_steps=%i", n_steps)
    # Generate a random walk.
    rw_increments = get_iid_standard_gaussian_samples(n_steps, seed)
    rw = convert_increments_to_random_walk(rw_increments)
    # Split the random walk into stages.
    walk_stages = {}
    running_step_count = 0
    for stage_num, n_steps in enumerate(stage_steps):
        next_running_step_count = running_step_count + n_steps + 1
        srs_stage = rw.iloc[running_step_count:next_running_step_count]
        srs_stage = srs_stage.reset_index(drop=True)
        running_step_count = next_running_step_count
        walk_stages[stage_num] = srs_stage
    return walk_stages


def summarize_staged_random_walk(
    staged_random_walk: Dict[int, pd.Series]
) -> pd.DataFrame:
    bars = []
    for stage, rw in staged_random_walk.items():
        hdbg.dassert_isinstance(rw, pd.Series)
        dict_ = {
            "open": rw.iloc[0],
            "high": rw.max(),
            "low": rw.min(),
            "close": rw.iloc[-1],
            "n_steps": rw.count() - 1,
            "mean": rw.mean(),
            "std": rw.std(),
        }
        srs = pd.Series(dict_, name=stage)
        bars.append(srs)
    bars = pd.concat(bars, axis=1).T
    return bars


def generate_permutations(n_elements: int, n_permutations: int, seed: int):
    rng = np.random.default_rng(seed=seed)
    permutations = []
    for n in range(1, 1 + n_permutations):
        srs = pd.Series(rng.permutation(n_elements), name=n)
        permutations.append(srs)
    permutations = pd.concat(permutations, axis=1)
    return permutations


def interpolate_with_brownian_bridge(
    initial_value: float,
    final_value: float,
    volatility: float,
    n_steps: int,
    seed: int,
) -> pd.Series:
    """
    Interpolate two points with a Brownian bridge.

    :param initial_value: first value of Brownian bridge
    :param final_value: final value of Brownian bridge
    :param n_steps: number of steps to take in the bridge
    :param volatility: standard deviation of a Brownian motion running
        from initial_value to final_value in time 1
    :param seed: seed for generating increments
    :return: a Brownian bridge connecting `initial_value` and `final_value`
        with specific steps and total interval volatility
    """
    # Generate iid standard normal increments.
    increments = get_iid_standard_gaussian_samples(n_steps, seed)
    # Rescale according to n_steps and volatility.
    hdbg.dassert_lt(0, volatility)
    scaling_factor = volatility / np.sqrt(n_steps)
    _LOG.debug("standard deviation of increments=%f", scaling_factor)
    increments *= scaling_factor
    # Convert rescaled increments to random walk.
    rw = convert_increments_to_random_walk(increments)
    # Convert random walk to Brownian bridge.
    steps = pd.Series(range(0, rw.size), index=rw.index)
    bb = rw - (steps / steps.iloc[-1]) * rw.iloc[-1]
    hdbg.dassert_eq(
        bb.iloc[0],
        bb.iloc[-1],
        msg="Brownian bridge does not start and end at the same value!",
    )
    # Add drift.
    drift = steps / n_steps * (final_value - initial_value)
    # Shifted Brownian bridge to reach initial and final values.
    shifted_bb = initial_value + bb + drift
    hdbg.dassert_eq(
        shifted_bb.iloc[0],
        initial_value,
        msg="Brownian bridge does not start at `initial_value`!",
    )
    hdbg.dassert_eq(
        shifted_bb.iloc[-1],
        final_value,
        msg="Brownian bridge does not end at `final_value`!",
    )
    return shifted_bb
