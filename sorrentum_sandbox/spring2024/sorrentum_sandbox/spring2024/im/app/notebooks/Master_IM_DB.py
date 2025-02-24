# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description
#
# This notebook allows to connect to an IM instance and access data.

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import helpers.hdbg as hdbg

# %%

# %%
# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.test_logger()
_LOG = logging.getLogger(__name__)

# %% run_control={"marked": false}
# dbname=os.environ["POSTGRES_DB"]
# host=os.environ["POSTGRES_HOST"]
# port=int(os.environ["POSTGRES_PORT"])
# user=os.environ["POSTGRES_USER"]
# password=os.environ["POSTGRES_PASSWORD"]

import pandas.io.sql as sqlio

import helpers.hsql as hsql

# conn_as_str = "user= password= dbname=im_postgres_db_local host=im_postgres_local port=5550"
conn = hsql.get_connection_from_string(conn_as_str)

db_names = hsql.get_db_names(conn)
print("db_names=%s" % db_names)

table_names = hsql.get_table_names(conn)
print("table_names=%s" % table_names)

table_name = "tradesymbol"
sql = "SELECT * FROM %s;" % table_name
df = sqlio.read_sql_query(sql, conn)

df

# %%
