"""
Import as:

import im.kibot.sql_writer as imkisqwri
"""

from typing import Optional

import pandas as pd
import psycopg2.extras as pextra

import im.common.data.types as imcodatyp
import im.common.sql_writer as imcosqwri


def get_create_table_query() -> str:
    """
    Get SQL query that is used to create tables for `kibot`.
    """
    sql_query = """
    CREATE TABLE IF NOT EXISTS KIBOT_DAILY_DATA (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        trade_symbol_id integer REFERENCES TRADE_SYMBOL,
        date date,
        open numeric,
        high numeric,
        low numeric,
        close numeric,
        volume bigint,
        UNIQUE (trade_symbol_id, date)
    );

    CREATE TABLE IF NOT EXISTS KIBOT_MINUTE_DATA (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        trade_symbol_id integer REFERENCES TRADE_SYMBOL,
        datetime timestamp,
        open numeric,
        high numeric,
        low numeric,
        close numeric,
        volume bigint,
        UNIQUE (trade_symbol_id, datetime)
    );

    CREATE TABLE IF NOT EXISTS KIBOT_TICK_BID_ASK_DATA (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        trade_symbol_id integer REFERENCES TRADE_SYMBOL,
        datetime timestamp,
        bid numeric,
        ask numeric,
        volume bigint
    );

    CREATE TABLE IF NOT EXISTS KIBOT_TICK_DATA (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        trade_symbol_id integer REFERENCES TRADE_SYMBOL,
        datetime timestamp,
        price numeric,
        size bigint
    );
    """
    return sql_query


class KibotSqlWriter(imcosqwri.AbstractSqlWriter):
    """
    Manager of CRUD operations on a database defined in `im/db`.
    """

    FREQ_ATTR_MAPPING = {
        imcodatyp.Frequency.Daily: {
            "table_name": "KibotDailyData",
            "datetime_field_name": "date",
        },
        imcodatyp.Frequency.Minutely: {
            "table_name": "KibotMinuteData",
            "datetime_field_name": "datetime",
        },
        imcodatyp.Frequency.Tick: {
            "table_name": "KibotTickData",
            "datetime_field_name": "datetime",
        },
    }

    def insert_bulk_daily_data(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Insert daily data for a particular TradeSymbol entry in bulk.

        :param df: a dataframe from s3
        """
        with self.conn:
            with self.conn.cursor() as curs:
                pextra.execute_values(
                    curs,
                    "INSERT INTO KibotDailyData "
                    "(trade_symbol_id, date, open, high, low, close, volume) "
                    "VALUES %s ON CONFLICT DO NOTHING",
                    df.to_dict("records"),
                    template="(%(trade_symbol_id)s, %(date)s, %(open)s,"
                    " %(high)s, %(low)s, %(close)s, %(volume)s)",
                )

    def insert_daily_data(
        self,
        trade_symbol_id: int,
        date: str,
        open_val: float,
        high_val: float,
        low_val: float,
        close_val: float,
        volume_val: int,
        average_val: Optional[float] = None,
        bar_count_val: Optional[int] = None,
    ) -> None:
        """
        Insert daily data for a particular TradeSymbol entry.
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO KibotDailyData "
                    "(trade_symbol_id, date, open, high, low, close, volume) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date,
                        open_val,
                        high_val,
                        low_val,
                        close_val,
                        volume_val,
                    ],
                )

    def insert_bulk_minute_data(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Insert minute data for a particular TradeSymbol entry in bulk.

        :param df: a dataframe from S3
        """
        with self.conn:
            with self.conn.cursor() as curs:
                pextra.execute_values(
                    curs,
                    "INSERT INTO KibotMinuteData "
                    "(trade_symbol_id, datetime, open, high, low, close, volume) "
                    "VALUES %s ON CONFLICT DO NOTHING",
                    df.to_dict("records"),
                    template="(%(trade_symbol_id)s, %(datetime)s, %(open)s,"
                    " %(high)s, %(low)s, %(close)s, %(volume)s)",
                )

    def insert_minute_data(
        self,
        trade_symbol_id: int,
        date_time: str,
        open_val: float,
        high_val: float,
        low_val: float,
        close_val: float,
        volume_val: int,
        average_val: Optional[float] = None,
        bar_count_val: Optional[int] = None,
    ) -> None:
        """
        Insert minute data for a particular TradeSymbol entry.
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO KibotMinuteData "
                    "(trade_symbol_id, datetime, open, high, low, close, volume) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date_time,
                        open_val,
                        high_val,
                        low_val,
                        close_val,
                        volume_val,
                    ],
                )

    def insert_tick_data(
        self,
        trade_symbol_id: int,
        date_time: str,
        price_val: float,
        size_val: int,
    ) -> None:
        """
        Insert tick data for a particular TradeSymbol entry.
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO KibotTickData "
                    "(trade_symbol_id, datetime, price, size) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date_time,
                        price_val,
                        size_val,
                    ],
                )
