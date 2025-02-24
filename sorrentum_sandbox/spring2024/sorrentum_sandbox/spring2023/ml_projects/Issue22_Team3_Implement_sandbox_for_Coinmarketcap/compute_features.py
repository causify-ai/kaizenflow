"""
Transformation data for Reddit.

Import as:

import sorrentum_sandbox.examples.reddit.transform as ssexretr
"""
import logging
import re
from typing import List, Optional, Tuple

import pandas as pd
import dask.dataframe as dd

_LOG = logging.getLogger(__name__)

def get_nvt_ratio(ddf):
    """
    NVT Ratio = Market Cap / Transaction Volume

    :param: ddf
    :return: NVT Ratio
    """
    return ddf['market_cap'] / ddf['volume_24h']

def get_mc_fdmc_ratio(ddf):
    """
    :param: ddf
    :return: Market Cap / Fully Diluted Market Cap
    """
    # Ensure both variables are of type 'float'
    ddf['market_cap'] = ddf['market_cap'].astype(float)
    ddf['fully_diluted_market_cap'] = ddf['fully_diluted_market_cap'].astype(float)
    
    # Perform the division
    return ddf['market_cap'] / ddf['fully_diluted_market_cap']


def extract_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Extract features from list of posts.

    :param data: list of bitcoin data
    :return: List of computed data
    """
    output = pd.DataFrame()
    # convert pandas dataframe to dask dataframe
    ddf = dd.from_pandas(data, npartitions=10)

    # compute features
    # Get the NVT Ratio and Market Cap / Fully Diluted Market Cap
    ddf['nvt_ratio'] = get_nvt_ratio(ddf)
    ddf['mc_fdmc_ratio'] = get_mc_fdmc_ratio(ddf)

    # convert dask dataframe to pandas dataframe
    output = ddf.compute()

    # rename column mapket_cap_dominance to mc_dominance
    output = output.rename(columns={'market_cap_dominance': 'mc_dominance'})
    # only keep the columns we want 
    output = output[["name", "price", "nvt_ratio", "mc_fdmc_ratio", "mc_dominance", "last_updated"]]
    return output
