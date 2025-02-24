#!/usr/bin/env python
"""
Load and validate data within a specified time period from a CSV file.
"""

import logging
import os
from typing import Any, Optional

import common.client as sinsacli
import common.validate as sinsaval
import pandas as pd
from utilities import custom_logger

import src.validate as sisebiva

# _LOG = logging.getLogger(__name__)
yaml_log_path = "/var/lib/app/data/"
docker_log_path = "/root/logs/"
_LOG = custom_logger.logger(yaml_log_path + "load_and_validate.py.log")
# #############################################################################
# CsvClient
# #############################################################################


class CsvClient(sinsacli.DataClient):
    """
    Class for loading CSV data from local filesystem into main memory.
    """

    def __init__(self, source_dir: str) -> None:
        """
        Constructor.

        :param source_dir: path to source data from.
        """
        self.source_dir = source_dir

    def load(
        self,
        dataset_signature: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Load CSV data specified by a unique signature.
        """
        dataset_signature += ".csv"
        source_path = os.path.join(self.source_dir, dataset_signature)
        data = pd.read_csv(source_path)

        return data


# #############################################################################
# Script.
# #############################################################################


if __name__ == "__main__":

    topic = "Monsoon"
    topic = topic.lower()
    _LOG.info("-------------------------------------------")
    _LOG.info("Initiating CSV Client with the app volume as storage...")
    csv_client = CsvClient(yaml_log_path)
    _LOG.info("CSV client object created")

    _LOG.info("Filename to fetch: " + topic + ".csv")
    _LOG.info("Fetching the file and converting to DataFrame...")
    data = csv_client.load(topic)
    _LOG.info("File fetched")

    _LOG.info("Initialising Normalization checker...")
    denormalized_dataset_check = sisebiva.DenormalizedDatasetCheck()
    _LOG.info("Checker created")

    _LOG.info("Adding checker to SingleDatasetValidator class...")
    dataset_validator = sinsaval.SingleDatasetValidator(
        [denormalized_dataset_check]
    )
    _LOG.info("Check added")

    _LOG.info("Running Validations...")
    # need to work on the logs for this function call
    dataset_validator.run_all_checks([data])
    # _LOG.info("All checks passed")
