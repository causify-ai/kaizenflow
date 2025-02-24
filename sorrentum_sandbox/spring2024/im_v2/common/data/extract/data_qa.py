#!/usr/bin/env python
"""
NOTE: This script is deprecated refer to .../data/qa/notebooks/*.ipynb

Compare data on DB and S3, raising an Exception when difference was found.

Use as:
# Compare daily S3 and realtime data for binance.
> im_v2/common/data/extract/data_qa.py \
   --db_stage 'dev' \
   --start_timestamp 20221008-000000 \
   --end_timestamp 20221013-000000 \
   --db_table 'ccxt_ohlcv_preprod' \
   --aws_profile 'ck' \
   --s3_dataset_signature 'periodic_daily.airflow.downloaded_1min.csv.ohlcv.futures.v7.ccxt.binance.v1_0_0' \
   --s3_path 's3://cryptokaizen-data-test' \
   --bid_ask_accuracy 3

Import as:

import im_v2.common.data.extract.data_qa as imvcodedq
"""
import abc
import argparse
import logging
from typing import Any, List

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparser as hparser
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe.full_symbol as imvcufusy

_LOG = logging.getLogger(__name__)


# #############################################################################
# Class composition for the next version of data QA
# #############################################################################


class QaCheck(abc.ABC):
    """
    Represent a single QA check executed on one or more dataframes.

    E.g.,

    - check that OHLCV data is in the right format (e.g., timestamps are not
      missing, L < O, L < H, V != 0)
    - check that two data dataframes from different providers are compatible
      (e.g., the error is less than 1%)
    """

    def __init__(self) -> None:
        self._status: str = "Check has not been executed."

    def __str__(self) -> str:
        """
        Return a description of a check.
        """
        return f"{self.__class__}: {self._status}"

    @abc.abstractmethod
    def check(self, dataframes: List[pd.DataFrame], *args: Any) -> bool:
        """
        Perform an individual QA data validation check on DataFrame(s).

        # TODO(Juraj): by accepting list we can have a unified interface for
        #  single dataset and cross dataset checks but we not sure yet.
        :param data: List of DataFrames
        :return: True if the check is passed, False otherwise
        """
        ...

    def get_status(self) -> str:
        return self._status


class DatasetValidator(abc.ABC):

    # TODO(Juraj): Similiarly as above, by accepting list of signatures
    # we can have a unified interface for single dataset and cross dataset checks.
    def __init__(
        self, dataset_signatures: List[str], qa_checks: List[QaCheck]
    ) -> None:
        # The class will hold a reference to a raw data client instance
        #  which takes care of loading the data.
        self.dataset_signatures = dataset_signatures
        self.qa_checks = qa_checks

    @abc.abstractmethod
    def run_all_checks(self, logger: logging.Logger, *args) -> None:
        """
        Run all checks.
        """
        ...


class EmptyDatasetCheck(QaCheck):
    def check(self, dataframes: List[pd.DataFrame], *args: Any) -> bool:
        """
        Assert a DataFrame is not empty.
        """
        hdbg.dassert_eq(len(dataframes), 1)
        is_empty = dataframes[0].empty
        self._status = "FAILED: Dataset is empty" if is_empty else "PASSED"
        return is_empty


class SingleDatasetValidator(DatasetValidator):
    def run_all_checks(self, logger: logging.Logger) -> None:
        error_msgs: List[str] = []
        for qa_check in self.qa_checks:
            if qa_check.check(dataset_signatures[0]):
                logger.info(check.get_status)
            else:
                error_msgs.append(check.get_status)
        if error_msgs:
            error_msg = "\n".join(error_msgs)
            hdbg.dfatal(error_msg)
