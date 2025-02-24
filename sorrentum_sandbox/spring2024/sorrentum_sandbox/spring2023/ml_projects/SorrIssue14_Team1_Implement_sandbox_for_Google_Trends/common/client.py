"""
Import as:

import sorrentum_sandbox.examples.ml_projects.SorrIssue14_Team1_Implement_sandbox_for_Google_Trends.common.client as ssempstisfgtcc
"""

import abc
from typing import Any, Optional

import pandas as pd


class DataClient(abc.ABC):
    """
    Load data for a given source from disk into main memory.
    """

    @abc.abstractmethod
    def load(
        self,
        dataset_signature: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None
    ) -> Any:
        """
        Load data from a desired source and a desired time interval.

        The time interval is intended as `[start_timestamp, end_timestamp)`, i.e.,
        `start_timestamp` is included, `end_timestamp` is excluded.

        :param dataset_signature: signature of the dataset to load
        :param start_timestamp: beginning of the time period to load. If `None`,
            start with the earliest available data
        :param end_timestamp: end of the time period to load. If `None`, download
            up to the latest available data
        :return: loaded data
        """
        ...
