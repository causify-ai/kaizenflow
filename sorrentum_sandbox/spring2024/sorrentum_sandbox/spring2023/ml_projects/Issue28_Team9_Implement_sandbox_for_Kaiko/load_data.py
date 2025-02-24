"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue28_Team9_Implement_sandbox_for_Kaiko.load_data as ssempitisfkld
"""

import db_kaiko
import pandas


def load_table(table_name) -> pandas.DataFrame:
    connection = db_kaiko.get_db_connection()
    client = db_kaiko.PostgresClient(connection)
    table = client.load(table_name)
    return table


# load data from PostgreSQL
def historical():
    return load_table("public.historical")


def realtime():
    return load_table("public.realtime")


def test():
    return load_table("public.test")


# save as csv file
def historical_save_csv():
    db = historical().sort_values(by="trade_id")
    db.to_csv("data/historical.csv", index=False)


def realtime_save_csv():
    db = realtime().sort_values(by="trade_id")
    db.to_csv("data/realtime.csv", index=False)


def test_save_csv():
    db = test().sort_values(by="trade_id")
    db.to_csv("data/test.csv", index=False)


# load data from csv file
def historical_from_csv():
    return pandas.read_csv("data/historical.csv")


def realtime_from_csv():
    return pandas.read_csv("data/realtime.csv")


def test_from_csv():
    return pandas.read_csv("data/test.csv")
