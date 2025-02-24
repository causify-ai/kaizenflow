"""
Import as:

import im.ib.data.load.ib_file_path_generator as imidlifpge
"""

import functools
import logging
import os
from typing import Optional

import helpers.hdbg as hdbg
import helpers.hs3 as hs3
import im.common.data.load.file_path_generator as imcdlfpage
import im.common.data.types as imcodatyp
import im.ib.data.config as imibdacon

_LOG = logging.getLogger(__name__)
_AWS_PROFILE = 'ck'

class IbFilePathGenerator(imcdlfpage.FilePathGenerator):
    """
    Generate file path for a symbol.

    File path is: <symbol>_<frequency>.<extension>
    """

    FREQ_PATH_MAPPING = {
        imcodatyp.Frequency.Daily: "daily",
        imcodatyp.Frequency.Hourly: "hourly",
        imcodatyp.Frequency.Minutely: "minutely",
        imcodatyp.Frequency.Tick: "tick",
    }

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def get_latest_symbols_file() -> str:
        """
        Get the latest available file with symbols on S3.
        """
        file_prefix = os.path.join(imibdacon.S3_METADATA_PREFIX, "symbols-")
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        files = s3fs.glob(file_prefix + "*")
        # E.g., files=
        #   ['alphamatic-data/data/ib/metadata/symbols-2021-04-01-143112738505.csv']
        _LOG.debug("files='%s'", files)
        latest_file: str = max(files)
        _LOG.debug("latest_file='%s'", latest_file)
        # Add the prefix.
        latest_file = "s3://" + latest_file
        _LOG.debug("latest_file=%s", latest_file)
        hdbg.dassert(s3fs.exists(latest_file))
        return latest_file

    def generate_file_path(
        self,
        symbol: str,
        frequency: imcodatyp.Frequency,
        asset_class: imcodatyp.AssetClass,
        contract_type: Optional[imcodatyp.ContractType] = None,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        ext: imcodatyp.Extension = imcodatyp.Extension.CSV,
    ) -> str:
        """
        Get the path to a specific IB dataset on S3.

        Format like `continuous_futures/daily/ES.csv.gz`.

        Parameters as in `read_data`.
        :return: path to the file
        :raises ValueError: if parameters are incompatible
        """
        # Check parameters.
        hdbg.dassert_is_not(currency, None)
        hdbg.dassert_is_not(exchange, None)
        # Get asset class part.
        if (
            contract_type == imcodatyp.ContractType.Continuous
            and asset_class == imcodatyp.AssetClass.Futures
        ):
            asset_part = "continuous_futures"
        else:
            asset_part = asset_class.value
        # Get frequency part.
        freq_part = self.FREQ_PATH_MAPPING[frequency]
        # Get extension.
        if ext == imcodatyp.Extension.CSV:
            extension_part = "csv.gz"
        else:
            raise ValueError("Unsupported extension %s" % ext)
        # Get file name.
        file_name = "%s.%s" % (symbol, extension_part)
        # Construct full path.
        file_path = os.path.join(
            imibdacon.S3_PREFIX,
            asset_part,
            exchange,
            currency,
            freq_part,
            file_name,
        )
        return file_path
