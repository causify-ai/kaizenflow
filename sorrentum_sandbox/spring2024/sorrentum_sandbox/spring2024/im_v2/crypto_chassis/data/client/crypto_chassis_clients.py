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
        root_dir: str,
        partition_mode: str,
        dataset: str,
        contract_type: str,
        data_snapshot: str,
        *,
        version: str = "",
        tag: str = "",
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        See the parent class for parameters description.
        """
        vendor = "crypto_chassis"
        download_universe_version = "v3"
        super().__init__(
            vendor,
            universe_version,
            root_dir,
            partition_mode,
            dataset,
            contract_type,
            data_snapshot,
            version=version,
            download_universe_version=download_universe_version,
            tag=tag,
            aws_profile=aws_profile,
            resample_1min=resample_1min,
        )
