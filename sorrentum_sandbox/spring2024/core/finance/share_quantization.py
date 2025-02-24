"""
Import as:

import core.finance.share_quantization as cfishqua
"""
import logging
from typing import Dict, Optional, Union

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def quantize_shares(
    shares: Union[pd.Series, pd.DataFrame],
    quantization: Optional[int],
    *,
    asset_id_to_decimals: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Round fractional shares to the specified number of decimals.

    In vectorized flows, `shares` is a time-indexed dataframe.
    In incremental flows, `shares` is a series.

    :param quantization: the number of decimals to round the shares to.
        if None, use `asset_id_to_decimals` for rounding
    :param asset_id_to_decimals: a dict with asset ids as keys and the number
        of decimal places to round the corresponding shares to as values
    """
    _LOG.debug("`shares` before quantization=\n%s", hpandas.df_to_str(shares))
    # Perform sanity-checks.
    hdbg.dassert_type_in(shares, [pd.Series, pd.DataFrame])
    #
    if quantization is not None:
        hdbg.dassert_isinstance(quantization, int)
        hdbg.dassert(
            asset_id_to_decimals is None,
            "`asset_id_to_decimals` must be `None` when `quantization` is passed",
        )
        # Pandas relies on the `numpy.round()` which uses a fast but sometimes
        # inexact algorithm to round floating-point datatypes. This is due to
        # the inexact representation of decimal fractions in the IEEE floating
        # point standard and errors introduced when scaling by powers of ten.
        # Alternatively, Python’s builtin `round()` uses a more accurate
        # but slower algorithm for 64-bit floating point values.
        # E.g., `np.round(1990.09900990099, 30) = 1990.0990099009903`
        # while `round(1990.09900990099, 30) = 1990.09900990099`.
        # Refer to docs for details:
        # `https://numpy.org/doc/stable/reference/generated/numpy.round.html#numpy.round`.
        quantized_shares = shares.round(quantization)
    else:
        hdbg.dassert_isinstance(
            asset_id_to_decimals,
            dict,
            "`asset_id_to_decimals` must be a `dict` when `quantization` is `None`",
        )
        quantized_shares = shares
        # Convert series to a dataframe so that we can use `pd.DataFrame.round()`.
        if isinstance(quantized_shares, pd.Series):
            quantized_shares = quantized_shares.to_frame().T
        # Ensure `asset_id_to_decimals` has an asset_id for every asset.
        hdbg.dassert_is_subset(
            quantized_shares.columns, asset_id_to_decimals.keys()
        )
        # Perform the rounding.
        quantized_shares = quantized_shares.round(asset_id_to_decimals)
        # If series-to-dataframe conversion was performed, undo it here.
        if isinstance(shares, pd.Series):
            quantized_shares = quantized_shares.squeeze()
            quantized_shares.name = shares.name
    _LOG.debug("`quantized_shares`=\n%s", hpandas.df_to_str(quantized_shares))
    return quantized_shares
