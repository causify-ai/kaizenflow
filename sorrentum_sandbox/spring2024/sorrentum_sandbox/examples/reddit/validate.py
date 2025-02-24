"""
QA pipeline for Reddit posts dataset.

Import as:

import sorrentum_sandbox.examples.reddit.validate as ssexreva
"""
import logging
from typing import Any, List

import pandas as pd

import helpers.hdbg as hdbg
import sorrentum_sandbox.common.validate as ssacoval


class EmptyTitleCheck(ssacoval.QaCheck):
    def check(self, dataframes: List[pd.DataFrame], *args: Any) -> bool:
        """
        Check if dataset contains empty titles.
        """
        have_empty_title = bool(sum(len(df[df.title == ""]) for df in dataframes))
        if have_empty_title:
            self._status = "FAILED: Datasets has posts with an empty titles"
        else:
            self._status = "PASSED"
        return not have_empty_title


class PositiveNumberOfCommentsCheck(ssacoval.QaCheck):
    def check(self, dataframes: List[pd.DataFrame], *args: Any) -> bool:
        """
        Check if number of comments in a post is a positive integer.
        """
        all_have_positive_number_of_comments = all(
            (df.num_comments.apply(int) >= 0).all() for df in dataframes
        )
        if not all_have_positive_number_of_comments:
            self._status = (
                "FAILED: Datasets have posts with a non-positive"
                " number of comments"
            )
        else:
            self._status = "PASSED"
        return all_have_positive_number_of_comments
