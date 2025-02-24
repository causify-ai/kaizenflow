import psycopg2 as psycop
from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime
import argparse
import download_yahoo as sisebido

# parser = argparse.ArgumentParser()
# parser.add_argument('--table', action='store',required=True)
# parser.add_argument('--interval', action='store',required=True)

# opt = parser.parse_args()


def dump_latest_data(table, interval):
    connection = psycop.connect(
        host="host.docker.internal",
        dbname="postgres",
        port=5432,
        user="postgres",
        password="docker",
    )

    tablename = table
    interval = interval

    cursor = connection.cursor()
    postgreSQL_select_Query = "select * from " + tablename
    cursor.execute(postgreSQL_select_Query)

    df = pd.DataFrame(cursor.fetchall())
    df.columns = [
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

    start_timestamp = df["timestamp"].max()
    from datetime import datetime

    end_timestamp = datetime.utcnow()
    downloader = sisebido.YFinanceDownloader()
    raw_data = downloader.download(start_timestamp, end_timestamp, interval)

    k = raw_data.get_data()
    p = k[k["timestamp"] > start_timestamp.to_datetime64()]
    from datetime import timezone as tz

    p["timestamp"] = p["timestamp"].apply(lambda x: x.replace(tzinfo=tz.utc))
    engine = create_engine(
        "postgresql://postgres:docker@host.docker.internal:5432/postgres",
        echo=False,
    )
    p.to_sql(tablename, engine, if_exists="append", index=False)
