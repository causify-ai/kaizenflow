"""
Converts Kibot data on S3 from .csv.gz to SQL.

Import as:

import im.kibot.data.transform.kibot_s3_to_sql_transformer as imkdtkstst
"""

import logging

import pandas as pd

import helpers.hdbg as hdbg
import im.common.data.transform.s3_to_sql_transformer as imcdtststr
import im.common.data.types as imcodatyp

_LOG = logging.getLogger(__name__)


# TODO(*): Move to convert_s3_to_sql_kibot.py?
# TODO(*): -> KibotS3ToSqlTransformer
class S3ToSqlTransformer(imcdtststr.AbstractS3ToSqlTransformer):
    @classmethod
    def transform(
        cls,
        df: pd.DataFrame,
        trade_symbol_id: int,
        frequency: imcodatyp.Frequency,
    ) -> pd.DataFrame:
        """
        Transform Kibot data loaded from S3 to load to SQL.

        :param df: dataframe with data from S3
        :param trade_symbol_id: symbol id in SQL database
        :param frequency: dataframe frequency
        :return: processed dataframe
        """
        # Transform dataframe.
        if frequency == imcodatyp.Frequency.Minutely:
            df = cls._transform_minutely_df(df, trade_symbol_id)
        elif frequency == imcodatyp.Frequency.Daily:
            df = cls._transform_daily_df(df, trade_symbol_id)
        elif frequency == imcodatyp.Frequency.Tick:
            df = cls._transform_tick_df(df, trade_symbol_id)
        else:
            hdbg.dfatal("Unknown frequency '%s'", frequency)
        return df

    @staticmethod
    def _transform_minutely_df(
        df: pd.DataFrame,
        trade_symbol_id: int,
    ) -> pd.DataFrame:
        """
        Prepare minutely dataframe loaded from S3 to load to SQL.

        :return: transformed dataframe
        """
        df.columns = [
            "date",
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        # Transform DataFrame from S3 to DB format.
        df["trade_symbol_id"] = trade_symbol_id
        df["datetime"] = df["date"].str.cat(df["time"], sep=" ")
        del df["date"]
        del df["time"]
        return df

    @staticmethod
    def _transform_daily_df(
        df: pd.DataFrame,
        trade_symbol_id: int,
    ) -> pd.DataFrame:
        """
        Prepare daily dataframe loaded from S3 to load to SQL.

        :return: transformed dataframe
        """
        df.columns = ["date", "open", "high", "low", "close", "volume"]
        # Transform DataFrame from S3 to DB format.
        df["trade_symbol_id"] = trade_symbol_id
        return df

    @staticmethod
    def _transform_tick_df(
        df: pd.DataFrame,
        trade_symbol_id: int,
    ) -> pd.DataFrame:
        """
        Prepare tick dataframe loaded from S3 to load to SQL.

        :return: transformed dataframe
        """
        df.columns = ["date", "time", "price", "size"]
        # Transform DataFrame from S3 to DB format.
        df["trade_symbol_id"] = trade_symbol_id
        df["datetime"] = df["date"].str.cat(df["time"], sep=" ")
        del df["date"]
        del df["time"]
        return df
