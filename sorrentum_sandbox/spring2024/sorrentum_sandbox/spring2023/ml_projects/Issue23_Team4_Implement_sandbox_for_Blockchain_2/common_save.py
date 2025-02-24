"""
Import as:

import sorrentum_sandbox.common.save as sinsasav
"""

import abc

import sorrentum_sandbox.common.download as ssacodow

# #############################################################################
# DataSaver
# #############################################################################


class DataSaver(abc.ABC):
    """
    Save data to a persistent storage (e.g., PostgreSQL, S3).
    """

    @abc.abstractmethod
    def save(self, data: ssacodow.RawData) -> None:
        """
        Save data to persistent storage.

        :param data: data to save
        """
        ...
