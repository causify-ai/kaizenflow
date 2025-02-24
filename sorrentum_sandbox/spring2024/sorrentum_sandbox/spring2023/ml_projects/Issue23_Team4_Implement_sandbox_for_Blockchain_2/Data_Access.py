import psycopg2
import pandas as pd



# Access data
def get_data(table_name):
    
    params = {
        "host": "host.docker.internal",
        "dbname": "airflow",
        "port": 5532,
        "user": "postgres",
        "password": "postgres"
    }
    connection = None

    try:
        connection = psycopg2.connect(**params)
        # print("Connected to the database successfully.")
    except Exception as e:
        print(f"An error occurred while connecting to the database: {e}")
    query = f"SELECT * FROM {table_name}"
    if connection:

        data = pd.read_sql_query(query, connection)
        # print(data.head())
        connection.close()
        return data

        
    else:
        print("Unable to create a DataFrame as the connection was not established.")
