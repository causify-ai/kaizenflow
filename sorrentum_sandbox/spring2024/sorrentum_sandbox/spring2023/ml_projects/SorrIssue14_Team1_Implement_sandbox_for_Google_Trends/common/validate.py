"""
Import as:

import sorrentum_sandbox.common.validate as sinsaval
"""

import abc
import logging
from typing import Any, List

# import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# #############################################################################
# QaCheck
# #############################################################################


class QaCheck(abc.ABC):
    """
    Represent a single QA check executed on one or more datasets.

    E.g., check that:
        frequencies of google searches are between 0 and 100
    """

    def __init__(self) -> None:
        self._status: str = "Check has not been executed."

    @abc.abstractmethod
    def check(self, datasets: List[Any], *args: Any) -> bool:
        """
        Perform a QA data validation check on one or more datasets.

        :param datasets: list of one or more datasets (e.g. DataFrames)
        :return: True if the check is passed, False otherwise
        """
        ...

    def get_status(self) -> str:
        """
        Return the formatted status message from the validation.
        """
        return f"{self.__class__.__name__}: {self._status}"


# #############################################################################
# DatasetValidator
# #############################################################################


class DatasetValidator(abc.ABC):
    """
    Apply a set of QA checks to validate one or more datasets.
    """

    def __init__(self, qa_checks: List[QaCheck]) -> None:
        self.qa_checks = qa_checks

    @abc.abstractmethod
    def run_all_checks(self, datasets: List[Any], *args: Any) -> bool:
        """
        Run all checks.

        :param datasets: list of one or more datasets (e.g. DataFrames)
        """
        ...


# #############################################################################
# SingleDatasetValidator
# #############################################################################


class SingleDatasetValidator(DatasetValidator):
    def run_all_checks(self, datasets: List) -> None:
        error_msgs: List[str] = []
        # hdbg.dassert_eq(len(datasets), 1)
        print("Running all QA checks:")
        for qa_check in self.qa_checks:
            if qa_check.check(datasets):
                # _LOG.info(qa_check.get_status())
                print(qa_check.get_status())
            else:
                # error_msgs.append(qa_check.get_status())
                print(qa_check.get_status())
        # if error_msgs:
        #     error_msg = "\n".join(error_msgs)
        #     hdbg.dfatal(error_msg)
