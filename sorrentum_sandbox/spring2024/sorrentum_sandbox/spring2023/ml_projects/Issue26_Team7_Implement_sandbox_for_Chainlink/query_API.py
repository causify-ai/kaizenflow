import pandas as pd
import psycopg2

# Create a function that takes string input of a SQL query and output a dataframe contain the desired data.
def query_from_db(query):
    # Connection to the posrgreSQL in the airflow container.
    connection = psycopg2.connect(
        host="host.docker.internal",
        dbname="airflow",
        port=5532,
        user="postgres",
        password="postgres",
    )

    cursor = connection.cursor()
    cursor.execute(query)

    # Get the data from the cursor and make a dataframe for it.
    history_rows = cursor.fetchall()
    df = pd.DataFrame(
        history_rows, columns=[desc[0] for desc in cursor.description]
    )

    # Close the connection,
    cursor.close()
    connection.close()

    return df
