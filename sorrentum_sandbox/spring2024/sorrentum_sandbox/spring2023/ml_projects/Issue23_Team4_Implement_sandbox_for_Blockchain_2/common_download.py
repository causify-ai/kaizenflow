"""
Import as:

import sorrentum_sandbox.common.download as sinsadow
"""

import abc
from typing import Any, Optional

import pandas as pd

# #############################################################################
# RawData
# #############################################################################


# TODO(gp): P1, Not sure it's worth to have a wrapper here.
class RawData:
    """
    Wrapper class for downloaded data to support a uniform interface.
    """

    def __init__(self, data: Any) -> None:
        self._data = data

    def get_data(self) -> Any:
        """
        Retrieve the data from the object.
        """
        return self._data


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
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any
    ) -> RawData:
        pass
        """
        Download data from a desired source.

        :param: same parameters as `DataClient.load()`
        :return: raw downloaded dataset
        """
        ...
