"""
QA pipeline for Google Trends .

Import as:

import sorrentum_sandbox.examples.ml_projects.SorrIssue14_Team1_Implement_sandbox_for_Google_Trends.src.validate as ssempstisfgtsv
"""

from typing import Any, List

import common.validate as sinsaval
import pandas as pd


class DenormalizedDatasetCheck(sinsaval.QaCheck):
    """
    Assert that a DataFrame is not normalized.
    """

    def check(self, dataframes: List[pd.DataFrame], *args: Any) -> bool:

        for dataframe in dataframes:
            if len(dataframe[dataframe["Frequency"] < 0]) >= 1:
                self._status = "FAILED: search frequencies less than 0"
                return False

            elif len(dataframe[dataframe["Frequency"] > 100]) >= 1:
                self._status = "FAILED: search frequencies greater than 100"
                return False

            else:
                self._status = "PASSED"
                return True
