"""
Import as:

import sorrentum_sandbox.common.download as sinsadow
"""

import abc
from typing import Any, Optional

import pandas as pd

# #############################################################################
# DataDownloader
# #############################################################################


class DataDownloader(abc.ABC):
    """
    Download raw data from a third party source.
    """

    @abc.abstractmethod
    def download(
        self,
        *,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """
        Download data from a desired source.

        :param: same parameters as `DataClient.load()`
        :return: Json Object
        """
        ...
