"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue27_Team8_Implement_sandbox_for_Yahoo_Finance.app.api as ssempitisfyfaa
"""

import pandas as pd
import psycopg2 as psycop


def api_from_db(start_time, end_time, granularity, ticker_list):

    if granularity == "1m":
        table_name = "yahoo_yfinance_spot_downloaded_1min"

    if granularity == "2m":
        table_name = "yahoo_yfinance_spot_downloaded_2min"

    if granularity == "5m":
        table_name = "yahoo_yfinance_spot_downloaded_5min"

    if granularity == "15m":
        table_name = "yahoo_yfinance_spot_downloaded_15min"

    if granularity == "30m":
        table_name = "yahoo_yfinance_spot_downloaded_30min"

    if granularity == "1h":
        table_name = "yahoo_yfinance_spot_downloaded_1hr"

    if granularity == "1d":
        table_name = "yahoo_yfinance_spot_downloaded_1d"

    query = (
        "select * from "
        + table_name
        + " where timestamp >= '"
        + start_time
        + "' and timestamp <= '"
        + end_time
        + "' and currency_pair in ("
    )

    for i in ticker_list:
        query = query + "'" + i + "',"

    query = query[:-1] + ")"

    connection = psycop.connect(
        host="localhost",
        dbname="postgres",
        port=5432,
        user="postgres",
        password="docker",
    )

    cursor = connection.cursor()
    cursor.execute(query)
    data = pd.DataFrame(cursor.fetchall())
    cursor.close()
    connection.close()
    data.columns = [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "timestamp",
        "currency_pair",
        "exchangetimezonename",
        "timezone",
    ]

    return data
