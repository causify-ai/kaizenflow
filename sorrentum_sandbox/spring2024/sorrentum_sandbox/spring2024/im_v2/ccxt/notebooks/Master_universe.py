# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description
#
# This notebook loads CCXT universes.
#
# See versions descriptions in `im_v2/ccxt/universe/trade/universe_versions.txt`.

# %% [markdown]
# # Imports

# %%
import logging
from typing import Dict

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Show all the universe versions for the vendor

# %%
mode = "trade"
vendor = "CCXT"
ivcu.universe.get_universe_versions(vendor, mode)


# %% [markdown]
# # Load universes

# %%
def load_universe(version: str) -> Dict[ivcu.full_symbol.FullSymbol, int]:
    """
    Load universe for CCXT.

    :return: full symbol -> asset id mappings
    """
    vendor = "CCXT"
    mode = "trade"
    version = version
    # Get universe.
    universe = ivcu.universe.get_vendor_universe(
        vendor, mode, version=version, as_full_symbol=True
    )
    universe_mapping = ivcu.universe_utils.build_numerical_to_string_id_mapping(
        universe
    )
    # Swap asset ids and full symbols to get `{full_symbol: asset_id}` mapping.
    universe_mapping = dict(
        (full_symbol, asset_id)
        for asset_id, full_symbol in universe_mapping.items()
    )
    # Sort for readability.
    universe_mapping = dict(sorted(universe_mapping.items()))
    return universe_mapping


# %% [markdown]
# ## v7

# %%
universe_version = "v7"
universe_mapping = load_universe(universe_version)
universe_mapping

# %%
# Universe as asset ids.
asset_ids = list(universe_mapping.values())
asset_ids

# %%
# Universe as Full symbols.
full_symbols = list(universe_mapping.keys())
full_symbols

# %% [markdown]
# ## v7.1

# %%
universe_version = "v7.1"
universe_mapping = load_universe(universe_version)
universe_mapping

# %%
# Universe as asset ids.
asset_ids = list(universe_mapping.values())
asset_ids

# %%
# Universe as Full symbols.
full_symbols = list(universe_mapping.keys())
full_symbols

# %% [markdown]
# ## v7.2

# %%
universe_version = "v7.2"
universe_mapping = load_universe(universe_version)
universe_mapping

# %%
# Universe as asset ids.
asset_ids = list(universe_mapping.values())
asset_ids

# %%
# Universe as Full symbols.
full_symbols = list(universe_mapping.keys())
full_symbols

# %% [markdown]
# ## v7.3

# %%
universe_version = "v7.3"
universe_mapping = load_universe(universe_version)
universe_mapping

# %%
# Universe as asset ids.
asset_ids = list(universe_mapping.values())
asset_ids

# %%
# Universe as Full symbols.
full_symbols = list(universe_mapping.keys())
full_symbols

# %% [markdown]
# ## v7.4

# %%
universe_version = "v7.4"
universe_mapping = load_universe(universe_version)
universe_mapping

# %%
# Universe as asset ids.
asset_ids = list(universe_mapping.values())
asset_ids

# %%
# Universe as Full symbols.
full_symbols = list(universe_mapping.keys())
full_symbols

# %%
