import dask.dataframe as dd
import psycopg2 as psycop
from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime
import argparse
import download_yahoo as sisebido

def dump_dask_data():
    connection = psycop.connect(
        host="host.docker.internal",
        dbname="postgres",
        port=5432,
        user="postgres",
        password="docker",
    )


    tablename="yahoo_yfinance_spot_downloaded_1min"
    interval="1m"

    cursor = connection.cursor()
    postgreSQL_select_Query = "select * from "+ tablename
    cursor.execute(postgreSQL_select_Query)

    df = pd.DataFrame(cursor.fetchall())
    df.columns=['open', 'high', 'low', 'close', 'adj_close', 'volume', 'timestamp','currency_pair', 'exchangetimezonename', 'timezone']

    dask_db_select_query = "select * from "+ "dask_dataframe_1min_average_300sec_check3"
    cursor.execute(dask_db_select_query)
    df_average = pd.DataFrame(cursor.fetchall())


    if len(df_average)==0:
        df.index=df.timestamp
        df.rename(columns={"timestamp": "timestamp_2"},inplace=True)
        df=df.sort_values(by=['currency_pair','timestamp_2'])
        df['open']=df['open'].astype('float')
        
        print('creating dask dataframe for generating features')
        df2=dd.from_pandas(df,2)
        result = df2.groupby("currency_pair").open.rolling(window='300s').mean().reset_index().compute()
        result.columns=['currency_pair','timestamp','average_last_300_seconds_open']
        engine = create_engine('postgresql://postgres:docker@host.docker.internal:5432/postgres', echo=False)
        result.to_sql('dask_dataframe_1min_average_300sec_check3', engine, if_exists='append',index=False)
        
    else:
        df.index=df.timestamp
        df.rename(columns={"timestamp": "timestamp_2"},inplace=True)
        df=df.sort_values(by=['currency_pair','timestamp_2'])
        df_average.columns=['currency_pair','timestamp','average_last_300_seconds_open']
        import datetime
        df_filtered=df[df['timestamp_2']>(df_average['timestamp'].max()-datetime.timedelta(seconds=300))]
        df_filtered['open']=df_filtered['open'].astype('float')
        
        print('creating dask dataframe for generating features')
        df2=dd.from_pandas(df_filtered,2)
        
        result = df2.groupby("currency_pair").open.rolling(window='300s').mean().reset_index().compute()
        result=result[result['timestamp']>(df_average['timestamp'].max())]

        result.columns=['currency_pair','timestamp','average_last_300_seconds_open']
        engine = create_engine('postgresql://postgres:docker@host.docker.internal:5432/postgres', echo=False)
        result.to_sql('dask_dataframe_1min_average_300sec_check3', engine, if_exists='append',index=False)
    
    print('Done')