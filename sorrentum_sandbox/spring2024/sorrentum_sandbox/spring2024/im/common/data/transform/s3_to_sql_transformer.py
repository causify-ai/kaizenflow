"""
Import as:

import im.common.data.transform.s3_to_sql_transformer as imcdtststr
"""

import abc
import logging

import pandas as pd

import im.common.data.types as imcodatyp

_LOG = logging.getLogger(__name__)


class AbstractS3ToSqlTransformer(abc.ABC):
    @classmethod
    def transform(
        cls,
        df: pd.DataFrame,
        trade_symbol_id: int,
        frequency: imcodatyp.Frequency,
    ) -> pd.DataFrame:
        """
        Transform data stored on S3 to load to SQL.

        :param df: dataframe with data from S3
        :param trade_symbol_id: symbol id in SQL database
        :param frequency: dataframe frequency
        :return: processed dataframe
        """
