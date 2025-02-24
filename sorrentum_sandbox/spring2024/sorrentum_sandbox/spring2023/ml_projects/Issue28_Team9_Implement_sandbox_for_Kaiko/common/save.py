"""
Import as:

import sorrentum_sandbox.common.save as sinsasav
"""

import abc

import common.download as sinsadow

# #############################################################################
# DataSaver
# #############################################################################


class DataSaver(abc.ABC):
    """
    Save data to a persistent storage (e.g., PostgreSQL, S3).
    """

    @abc.abstractmethod
    def save(self, data: sinsadow.RawData) -> None:
        """
        Save data to persistent storage.

        :param data: data to save
        """
        ...
