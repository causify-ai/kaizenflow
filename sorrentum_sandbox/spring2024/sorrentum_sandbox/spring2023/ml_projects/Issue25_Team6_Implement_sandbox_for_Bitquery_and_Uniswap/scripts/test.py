import os
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List

import pandas as pd
import psycopg2
import requests
from sqlalchemy import create_engine

# df = pd.read_csv(r"bitquery_raw.csv")

# # def build_postgress_table(df:pd.DataFrame)
# # Split dataframe into table schema format for postgress
# tran_token_info = df[["transaction_hash","baseCurrency_symbol","baseCurrency_address","quoteCurrency_symbol","quoteCurrency_address"]]
# tran_wallet_info = df[["transaction_hash","transaction_to_address","transaction_txFrom_address"]]
# tran_market_info = df[["transaction_hash","baseAmount","quoteAmount","quotePrice","maximum_price","minimum_price","open_price","close_price"]]
# tran_metadata = df[["transaction_hash","trades","transaction_gas"]]

# Debugging
# print(tran_token_info.head())
# print(len(tran_token_info))

# database connection parameters
host = "localhost"
port = "5432"
dbname = "db"
user = "postgres"
password = "postgres"

# connection to the postgress database
conn = psycopg2.connect(
    host=host, port=port, dbname=dbname, user=user, password=password
)

# # # Use SQLAlchemy to create the table

# engine = create_engine('postgresql://postgres:postgres@localhost:5432/db')

# # # # upload tables to postgress server
# tran_token_info.to_sql('tran_token_info', engine, index=False, if_exists='replace', method='multi', chunksize=3000)
# tran_wallet_info.to_sql('tran_wallet_info', engine, index=False, if_exists='replace', method='multi', chunksize=3000)
# tran_market_info.to_sql('tran_market_info', engine, index=False, if_exists='replace', method='multi', chunksize=3000)
# tran_metadata.to_sql('tran_metadata', engine, index=False, if_exists='replace', method='multi', chunksize=3000)


# Create a cursor to execute SQL queries
cur = conn.cursor()
# Execute a SQL query to retrieve the last row of the table
cur.execute("SELECT * FROM tran_metadata")
result = cur.fetchall()
df = pd.DataFrame(result)
print(df.head())


# # Iterate over the list and insert each dataframe into its respective table
# for item in tables_and_dfs:
#     table_name = item["table_name"]
#     df = item["df"]

#     # Create a new table in the database
#     with conn.cursor() as cur:
#         if table_name == "tran_token_info":
#           cur.execute(f"""
#               CREATE TABLE IF NOT EXISTS tran_token_info (
#                   transaction_hash bigint,
#                   baseCurrency_symbol TEXT,
#                   baseCurrency_address bigint,
#                   quoteCurrency_symbol TEXT,
#                   quoteCurrency_address bigint
#               );
#           """)
#         elif table_name == "tran_wallet_info":
#           cur.execute(f"""
#           CREATE TABLE IF NOT EXISTS tran_wallet_info (
#               transaction_hash bigint,
#               transaction_to_address bigint,
#               transaction_txFrom_address bigint,
#               );
#           """)
#         elif table_name == "tran_market_info":
#           cur.execute(f"""
#           CREATE TABLE IF NOT EXISTS tran_market_info (
#               transaction_hash bigint,
#               baseAmount FLOAT,
#               quoteAmount FLOAT,
#               maximum_price FLOAT,
#               minimum_price FLOAT,
#               open_price FLOAT,
#               close_price FLOAT,
#               );
#           """)
#         elif table_name == "tran_metadata":
#           cur.execute(f"""
#           CREATE TABLE IF NOT EXISTS tran_metadata (
#               transaction_hash TEXT,
#               trades INTEGER,
#               transaction_gas INTEGER,
#               );
#           """)
#     # Convert the dataframe to a string buffer
#     buffer = StringIO()
#     df.to_csv(buffer, index=False, header=False)
#     buffer.seek(0)

#     # Insert the data into the new table
#     with conn.cursor() as cur:
#         cur.copy_from(buffer, table_name, sep=",")
#         conn.commit()

# # Close the connection
# conn.close()


# # Create a new table in the database
# with conn.cursor() as cur:
#     cur.execute(f"""
#         CREATE TABLE IF NOT EXISTS tran_token_info (
#             transaction_hash SERIAL PRIMARY KEY,
#             transaction_to_address TEXT,
#             baseCurrency_address TEXT,
#             quoteCurrency_symbol TEXT,
#             quoteCurrency_address TEXT
#         );
#     """)

#     cur.execute(f"""
#     CREATE TABLE IF NOT EXISTS tran_wallet_info (
#         transaction_hash SERIAL PRIMARY KEY,
#         transaction_to_address TEXT,
#         transaction_txFrom_address TEXT,
#         );
#     """)

#     cur.execute(f"""
#     CREATE TABLE IF NOT EXISTS tran_market_info (
#         transaction_hash SERIAL PRIMARY KEY,
#         baseAmount FLOAT,
#         quoteAmount FLOAT,
#         maximum_price FLOAT,
#         minimum_price FLOAT,
#         open_price FLOAT,
#         close_price FLOAT,
#         );
#     """)

#     cur.execute(f"""
#     CREATE TABLE IF NOT EXISTS tran_metadata (
#         transaction_hash SERIAL PRIMARY KEY,
#         trades INTEGER,
#         transaction_gas INTEGER,
#         );
#     """)

# # # Convert the dataframe to a string buffer
# # buffer = StringIO()
# # tran_token_info.to_csv(buffer, index=False, header=False)
# # buffer.seek(0)

# # # Insert the data into the new table
# # with conn.cursor() as cur:
# #     cur.copy_from(buffer, "tran_token_info", sep=",")
# #     conn.commit()

# # # Convert the dataframe to a string buffer
# # buffer = StringIO()
# # tran_token_info.to_csv(buffer, index=False, header=False)
# # buffer.seek(0)

# # # Insert the data into the new table
# # with conn.cursor() as cur:
# #     cur.copy_from(buffer, "tran_token_info", sep=",")
# #     conn.commit()


# print("here")

# # Create a cursor to execute SQL queries
# cur = conn.cursor()
# # Execute a SQL query to retrieve the last row of the table
# cur.execute("SELECT * FROM tran_token_info")
# result = cur.fetchall()
# print(result)

# # Execute a SQL query to retrieve the last row of the table
# cur.execute("SELECT * FROM tran_token_info ORDER BY index DESC LIMIT 1")

# # Extract the timestamp from the last row
# result = cur.fetchone()
# last_timestamp = result[0]  # Assuming timestamp is the index

# # Convert the timestamp to a datetime object if needed
# last_datetime = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')

# # Format the datetime object in ISO-8601 format
# iso_timestamp = last_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

# print(iso_timestamp)
# # Close the cursor and the connection
# cur.close()

# # Close the connection
# conn.close()


# # create table in database
# # create_table_query = '''CREATE TABLE IF NOT EXISTS tran_token_info (
# #                             transaction_hash varchar(255),
# #                             age int
# #                         )'''

# # Implement a flow to save the historical data from the source in a DB using a set of “tables”
# # Explain the rationale for the choice of the DB

# # Postgress schema
# # Split df to match table schema and send to postgress db


# ### TODO 3 ##

# # Implement a flow to download data from the source in the DB in real-time (in different tables)


# ## to grab timestamp of last entry in postgress db
# # my_query = client.query("""
# #   SELECT TIMESTAMP,
# #     value,
# #     card
# #   FROM my_table
# #   ORDER BY TIMESTAMP DESC
# #   LIMIT 1
# # """)
