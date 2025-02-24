
import api_query
import sorrentum_sandbox.examples.ml_projects.Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap.db as sisebidb
import pandas as pd
import dask.dataframe as dd

query = "SELECT * FROM uniswap_table"

db_conn = sisebidb.get_db_connection()

table_name = "query_calc"

# read livetable data to dataframe
df_pandas = pd.read_sql(query,db_conn)

# Use DASK to partition pandas dataframe for faster processing
df = dd.from_pandas(df_pandas, npartitions=10)  

# calculate the highest trading wallets
temp= df['transaction_to_address'].value_counts()
calc_val = temp.reset_index().rename(columns={'index': 'wallet_address','transaction_to_address':'trade_frequency'})
pandas_frame = calc_val.compute()

# Convert object dtype to string
pandas_frame['wallet_address'] = pandas_frame['wallet_address'].astype(str)

# save to airflow db
api_query.save_table(table_name,pandas_frame)

# close db connection
db_conn.close()