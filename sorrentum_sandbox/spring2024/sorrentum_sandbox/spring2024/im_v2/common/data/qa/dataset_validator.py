"""
Import as:

import im_v2.common.data.qa.dataset_validator as imvcdqdava
"""

import logging
from typing import List

import helpers.hdbg as hdbg
import sorrentum_sandbox.common.validate as ssacoval

_LOG = logging.getLogger(__name__)


class DataFrameDatasetValidator(ssacoval.DatasetValidator):

    # TODO(Sameep): Add unit test for the function.
    def run_all_checks(self, datasets: List, *, abort_on_error: bool = True) -> str:
        """
        Run all quality assurance (QA) checks on the provided datasets.

        :param datasets: List of one or more datasets (e.g., DataFrames).
        :param abort_on_error: If True, any check failure is considered fatal; if False,
                      non-fatal issues are returned as a formatted string but
                      do not stop execution.
        :return: If abort_on_error is False, return errors as a formatted string;
                 otherwise, an empty string.
        """
        error_msgs: List[str] = []
        _LOG.info("Running all QA checks:")
        for qa_check in self.qa_checks:
            if qa_check.check(datasets):
                _LOG.info("\t" + qa_check.get_status())
            else:
                error_msgs.append("\t" + qa_check.get_status())
        if error_msgs:
            error_msg = "\n".join(error_msgs)
            if abort_on_error:
                hdbg.dfatal(error_msg)
            return error_msg
        return ""
