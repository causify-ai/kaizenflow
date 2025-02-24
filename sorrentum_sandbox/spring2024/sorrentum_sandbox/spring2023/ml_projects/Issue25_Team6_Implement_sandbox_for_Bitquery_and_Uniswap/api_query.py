# API Query for postgres db
import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2 import sql

def api_query_call(query: str) -> pd.DataFrame:
    # Create engine
    conn = psycopg2.connect(
        host="host.docker.internal",
        dbname="airflow",
        port=5532,
        user="postgres",
        password="postgres",
    )

    # create cursor object
    cur = conn.cursor()
    
    # execute query
    cur.execute(query)
    
    # fetch all rows from query result
    rows = cur.fetchall()
    
    # get column names from cursor description
    col_names = [desc[0] for desc in cur.description]
    
    # create dataframe from rows and column names
    df = pd.DataFrame(rows, columns=col_names)
    
    # close cursor and connection
    cur.close()
    conn.close()
    
    # return dataframe
    return df


def save_table(table_name:str, df: pd.DataFrame):
    # Create engine
    conn = psycopg2.connect(
        host="host.docker.internal",
        dbname="airflow",
        port=5532,
        user="postgres",
        password="postgres",
    )
    cur = conn.cursor()

    # insert data into table
    for row in df.itertuples(index=False):
        insert_query = sql.SQL("INSERT INTO {} VALUES ({})").format(
            sql.Identifier(table_name),
            sql.SQL(',').join(sql.Placeholder() * len(row))
        )
        cur.execute(insert_query, row)

    # commit changes and close cursor and connection
    conn.commit()
    cur.close()
    conn.close()    