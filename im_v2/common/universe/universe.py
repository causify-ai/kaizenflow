"""
Import as:

import im_v2.common.universe.universe as imvcounun
"""
import glob
import os
import re
from typing import Dict, List, Optional, Union

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import im_v2.common.data.client as icdc


def _extract_universe_version(universe_file: str) -> int:
    """
    Extract version number from universe_vXX.json file. e.g.
    'universe_v03.json' -> 3.

    :param file_name:
    :return: universe file version number
    """
    basename = os.path.basename(universe_file).rstrip(".json")
    m = re.search(r"(\d+)$", basename)
    hdbg.dassert(
        m,
        "Can't parse file '%s', correct format is e.g. 'universe_v03.json'.",
        basename,
    )
    # Groups return tuple.
    return int(m.groups(1)[0])  # type: ignore[union-attr, arg-type]


def _get_universe_file_path(vendor: str, *, version: Optional[str] = None) -> str:
    """
    Get universe file path based on version.

    :param vendor: vendor to load data for (e.g., CCXT, Talos)
    :param version: universe release version (e.g. "v01"). If None it uses
      the latest version available
    :return: file path to the universe file corresponding to the specified version
    """
    vendor = vendor.lower()
    # Get path to vendor universe dir.
    vendor_dir = os.path.join(hgit.get_amp_abs_path(), f"im_v2/{vendor}/universe")
    hdbg.dassert_dir_exists(vendor_dir)
    if version is None:
        # Find all universe files.
        vendor_universe_pattern = os.path.join(vendor_dir, "universe_v*.json")
        universe_files = list(glob.glob(vendor_universe_pattern))
        hdbg.dassert_ne(len(universe_files), 0)
        file_path = max(universe_files, key=_extract_universe_version)
    else:
        # TODO(Juraj): #1487 Assert version format (include 'small').
        file_name = "".join(["universe_", version, ".json"])
        file_path = os.path.join(vendor_dir, file_name)
    hdbg.dassert_exists(file_path)
    return file_path

def _get_trade_universe(
    vendor: str,
    *,
    version: Optional[str] = None,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Load trade universe for which we have historical data.

    :param vendor: vendor to load data for (e.g., CCXT/Talos)
    :param version: release version
    :return: trade universe as a nested dictionary of vendor (e.g., CCXT),
      exchange name (e.g., binance) to list of symbols e.g.,
        {
            "Talos": {
                "binance": [
                "ADA_USDT",
                "AVAX_USDT",
                "BNB_USDT",
                "BTC_USDT",
                "DOGE_USDT",
                "EOS_USDT",
                "ETH_USDT",
                "LINK_USDT",
                "SOL_USDT"
                ],
                ...
        }
    """
    file_path = _get_universe_file_path(vendor, version=version)
    hdbg.dassert_exists(file_path)
    universe = hio.from_json(file_path)
    hdbg.dassert_in(vendor, universe)
    return universe[vendor]  # type: ignore[no-any-return]

def get_vendor_universe(
    vendor: str, *, version: Optional[str] = None, as_full_symbol: bool = False) -> Union[List[icdc.FullSymbol], Dict[str, Dict[str, List[str]]]]:
    """
    Load vendor universe either as a list of 
    currency pairs per each vendor or list of full symbols.

    :param vendor: vendor to load data for (e.g., CCXT, Talos)
    :param version: release version
    :param as_full_symbol: if True transform the universe into list of full symbols e.g. gateio::XRP_USDT
    :return: vendor universe as a list of symbol or list of full symbols e.g.:
        {
            "Talos": {
                "binance": [
                "ADA_USDT",
                "AVAX_USDT",
                "BNB_USDT",
                "BTC_USDT",
                "DOGE_USDT",
                "EOS_USDT",
                "ETH_USDT",
                "LINK_USDT",
                "SOL_USDT"
                ],
                ...
        }
        or ["gateio::XRP_USDT", "kucoin::SOL_USDT"]
    """
    vendor_universe =  _get_trade_universe(vendor, version=version)
    if as_full_symbol:
        # Convert vendor universe dict to a sorted list of full symbols.
        vendor_universe = [
            icdc.build_full_symbol(exchange_id, currency_pair)
            for exchange_id, currency_pairs in vendor_universe.items()
            for currency_pair in currency_pairs
        ]
        # Sort list of symbols in the universe.
        vendor_universe = sorted(vendor_universe)
    return vendor_universe
