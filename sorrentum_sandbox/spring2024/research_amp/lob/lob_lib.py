"""
Import as:

import research_amp.lob.lob_lib as ralololi
"""

import numpy as np
import pandas as pd
import scipy as scipy

import helpers.hdbg as hdbg

np.random.seed(seed=1806)


def get_data(n_samples: int = 5) -> pd.DataFrame:
    n_samples = n_samples
    ask_mean = 1.0
    ask_std = 2.0
    bid_mean = 1.0
    bid_std = ask_std
    ask_rv = abs(
        scipy.stats.norm.rvs(loc=ask_mean, scale=ask_std, size=n_samples)
    )
    bid_rv = abs(
        scipy.stats.norm.rvs(loc=bid_mean, scale=bid_std, size=n_samples)
    )
    ob = pd.DataFrame([bid_rv, ask_rv]).T
    ob.columns = ["bids", "asks"]
    return ob


def _get_supply_demand_curve(srs: pd.Series, mode: str) -> pd.Series:
    ascending = mode == "supply"
    # For each value compute the cumsum.
    index = srs.sort_values(ascending=ascending)
    values = [1] * srs.shape[0]
    vals = pd.Series(values, index=index)
    ret = vals.cumsum()
    ret.name = mode
    return ret


def get_supply_demand_curve(ob: pd.DataFrame) -> pd.DataFrame:
    supply = _get_supply_demand_curve(ob["bids"], "demand")
    demand = _get_supply_demand_curve(ob["asks"], "supply")
    df = supply.to_frame().merge(
        demand, how="outer", left_index=True, right_index=True
    )
    df = df.interpolate()
    df.index.name = "price"
    return df


def _find_equilibrium_price(sd):
    supply = sd["supply"]
    demand = sd["demand"]
    excess = supply - demand
    idx = np.where(np.diff(np.sign(excess)) == 2)[0]
    hdbg.dassert_eq(idx.shape[0], 1)
    idx = idx[0]
    hdbg.dassert_lte(excess.iloc[idx], 0)
    hdbg.dassert_lte(0, excess.iloc[idx + 1])
    return idx


def _find_equilibrium_quantity(sd: pd.DataFrame, eq_price: float):
    """
    Once the equilibrium price is found, calculate the equilibrium quantity.
    """
    # Add equilibrium price to supply demand data.
    sd.loc[eq_price] = np.nan
    # Assign supply and demand quantity value to equilibrium price through interpolation.
    sd = sd.sort_index().interpolate()
    # Approximate equilibrium quantity is the mean of supply and demand quantity values at equilibrium price.
    eq_quantity = sd.loc[eq_price].values.mean()
    return eq_quantity


def find_equilibrium(df, print_graph: bool = True):
    """ """
    eq_price_idx = _find_equilibrium_price(df)
    eq_price1 = df.index.values[eq_price_idx]
    eq_price2 = df.index.values[eq_price_idx + 1]
    eq_price = np.mean([eq_price1, eq_price2])
    eq_quantity = _find_equilibrium_quantity(df, eq_price)
    if print_graph:
        print(
            f"Equilibrium price = {eq_price}, Equilibrium quantity  = {eq_quantity}"
        )
        ax = df.plot(use_index=True)
        ymin, ymax = ax.get_ylim()
        xmin, xmax = ax.get_xlim()
        ax.vlines(eq_price, ymin=ymin, ymax=ymax, color="r")
        ax.hlines(eq_quantity, xmin=xmin, xmax=xmax, color="r")
    return eq_price, eq_quantity
