"""
Import as:

import im_v2.crypto_chassis.data.client.crypto_chassis_clients as imvccdcccc
"""

import logging
from typing import Optional

import im_v2.common.data.client as icdc

_LOG = logging.getLogger(__name__)


# #############################################################################
# CryptoChassisHistoricalPqByTileClient
# #############################################################################


class CryptoChassisHistoricalPqByTileClient(
    icdc.HistoricalPqByCurrencyPairTileClient
):
    """
    Read historical data for `CryptoChassis` assets stored as Parquet dataset.

    It can read data from local or S3 filesystem as backend.
    """

    def __init__(
        self,
        universe_version: str,
        resample_1min: bool,
        root_dir: str,
        partition_mode: str,
        *,
        data_snapshot: str = "latest",
        aws_profile: Optional[str] = None,
    ) -> None:
        """
        Constructor.

        See the parent class for parameters description.
        """
        vendor = "crypto_chassis"
        super().__init__(
            vendor,
            universe_version,
            resample_1min,
            root_dir,
            partition_mode,
            data_snapshot=data_snapshot,
            aws_profile=aws_profile,
        )
