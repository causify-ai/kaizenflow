"""
Contain functions to manage universes of names.

Import as:

import dataflow.universe as dtfuniver
"""
import logging
import os
import re
from typing import List, Optional, Union

import pandas as pd

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# TODO(Grisha): "Move universe-related functions to `im_v2`" CmTask #1724.


# TODO(gp): Move it to a better place.
Amid = Union[int, str]


# #############################################################################
# S&P 500
# #############################################################################


def get_sp500() -> pd.DataFrame:
    """
    Return SP500 constituents as of 2010-01-01.

    :return: dataframe like ticker date 0 A 2010-01-01 1 AAPL 2010-01-01
        2 ABC 2010-01-01 3 ABT 2010-01-01 4 ACE 2010-01-01
    """
    base = hgit.get_client_root(super_module=True)
    # TODO(gp): Move this file to S3.
    df = pd.read_json(os.path.join(base, "data/sp500_2010-01-01.json"))
    return df


def get_sp500_sample(n: int, seed: int) -> List[str]:
    """
    Return list of `n` random SP500 tickers.

    :param n: number of constituents to return
    :param seed: seed for random sampling
    :return: constituents as a list of tickers
    """
    sp500 = get_sp500()
    df = sp500.sample(n=n, random_state=seed)
    return df["ticker"].to_list()


# #############################################################################
# General
# #############################################################################


def get_universe(universe_str: str) -> List[Amid]:
    """
    Get the correct universe from the provided string.

    :param universe_str: string consisting of vendor, universe version
        and top number of assets or all to get. E.g., `ccxt_v7_1-top1`
        or `ccxt_v7_1-all`
    """
    # E.g., `universe_str == "ccxt_v7_1-top100"`
    vendor_universe_version_str, top_n = cconfig.parse_universe_str(universe_str)
    # Parse the vendor and universe version.
    # E.g., "ccxt_v7_1" -> "ccxt" and "v7_1".
    pattern = r"(\D+(\d+)?)_(\D+\d+(\_\d+)?)"
    match = re.match(pattern, vendor_universe_version_str)
    msg = f"""
    The vendor and universe version are not found in
    `universe_str = {universe_str}`.
    """
    hdbg.dassert_is_not(match, None, msg=msg)
    hdbg.dassert_eq(len(match.groups()), 4, msg=msg)
    # E.g., `ccxt`.
    vendor = match.group(1)
    # Get `universe_verison` and modify it in case the universe has a
    # sub-version, e.g., "v7_1" -> "v7.1".
    # Otherwise, the replacement doesn't affect on the version like "v7".
    universe_version = match.group(3)
    universe_version = universe_version.replace("_", ".")
    if vendor == "kibot":
        full_symbols = _get_kibot_universe(universe_version)
    else:
        # TODO(Nina): consider extending to the function params.
        mode = "trade"
        full_symbols = ivcu.get_vendor_universe(
            vendor, mode, version=universe_version, as_full_symbol=True
        )
    # Filter the universe of symbols according to top_n.
    universe = _get_top_n(full_symbols, top_n)
    return universe


def _get_kibot_universe(universe_version: str) -> List[Amid]:
    """
    Use universe from file.

    :param universe_version: version of the universe, e.g., `v7.4`
    """
    if universe_version == "v1":
        amids_string = "AAPL AMZN MSFT GOOG BRK.B JNJ V PG NVDA MA HD JPM UNH \
            ADBE CRM PYPL VZ NFLX DIS INTC"
        amids = amids_string.split(" ")
    elif universe_version == "v2":
        amids_string = "AAP ABT ACN ADCT AIG AKAM AMAT ANET ASH AVP AYE BBT \
            CAG CBS CIEN COST CRM CSCO CTAS DGX DLPH DLTR DTV EIX EQIX EVRG \
            EXPE FRC HCA HES HON HOT HPE HPQ HSY ICE ILMN IPG JAVA JBHT JWN \
            KEY LIFE LLTC LLY LVLT MAS MHK MHP MIL MNK MOT MXIM NEE NFX NKTR \
            NLSN NSC NSM NUE NVLS NVR NWL ORLY PEG PKG PKI PPL PXD QLGC RDC \
            RHI ROST RSG SHLD SLG STR SWKS TEG TGT THC TIE TMO TMUS TRV UDR \
            UNH VFC VIAV VRTX WELL WMB XEC YUM ZBRA ZMH"
        amids = amids_string.split(" ")
    elif universe_version == "v3":
        # Horrible hack.
        # TODO(gp): Move it to S3 and add a wrapper.
        ticker_df = pd.read_json(
            "/Users/paul/src/lemonade/data/sp500_2010-01-01.json"
        )
        skip_list = [68, 69, 72, 77, 105, 118, 120, 220, 314, 388, 400]
        selected = ticker_df.index.difference(skip_list)
        amids = ticker_df["ticker"].loc[selected].to_list()
    return amids


def _get_top_n(amids: List[Amid], n: Optional[int]) -> List[Amid]:
    """
    Get top-n symbols from the universe.

    :param amids: full universe list
    :param n: number of symbols, if None return the complete list
        without filtering
    """
    if n is None:
        universe = amids
    else:
        hdbg.dassert_lte(1, n)
        hdbg.dassert_lte(n, len(amids))
        universe = amids[:n]
    universe = sorted(universe)
    return universe


# #############################################################################


# def set_amid(
#    config: cconfig.Config,
#    amid_key: cconfig.CompoundKey,
#    amid: Amid,
#    assume_dummy: bool = True,
# ) -> cconfig.Config:
#    """
#    Assign an instrument to a config.
#    """
#    hdbg.dassert_isinstance(config, cconfig.Config)
#    config = config.copy()
#    hdbg.dassert_in(amid_key, config)
#    if assume_dummy:
#        hdbg.dassert_eq(config.get(amid_key), cconfig.DUMMY)
#    # TODO(gp): Use IM FilePathGenerator::generate_file_path()
#    from im.kibot.data.config import S3_PREFIX
#
#    config[amid_key] = os.path.join(S3_PREFIX, "pq/sp_500_1min", amid + ".pq")
#    # config["tags"].append(ticker)
#    return config
#
#
# def build_universe_variants(
#    config: cconfig.Config, amid_key: cconfig.CompoundKey, universe_str: str
# ) -> cconfig.Config:
#    """
#    Add instrument to model.
#    """
#    amids = build_universe(universe_str)
#    if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug("Universe has %d amids", len(amids))
#    configs = [set_amid(config, amid_key, amid) for amid in amids]
#    return configs
