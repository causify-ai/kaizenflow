"""
DAG to download Reddit data.
"""


import datetime

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_forecast_periodic_5mins_postgres_prices_bitcoin"
_DAG_DESCRIPTION = "Download Bitcoin market prices every day and save to dbs"
# Specify when to execute the DAG.
_SCHEDULE = "*/5 * * * *"

# Default parameters for the DAG.
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2023, 4, 10, 0, 0, 0),
)

# Create bash command to read the code download_to_db_forecast.py that is executed in Airflow.
bash_command = [
    # Sleep 5 seconds to ensure the post is submitted.
    "sleep 5",
    "&&",
    "/usr/bin/python3 /cmamp/sorrentum_sandbox/examples/ml_projects/Issue23_Team4_Implement_sandbox_for_Blockchain_2/download_to_db_forecast.py",
    "--start_timestamp {{ data_interval_start }}",
    "--time_span '6years'",
    "--target_table 'Real_Time_Market_Price'",
    "--api 'https://api.blockchain.info/charts'",
    "--chart_name 'market-price'",
    "--target_table_forecast 'Forecast_Market_Price'",
    "-v DEBUG",
]

# Create task to run the code download_to_db_forecast.py based on the bash command and the dag previously defined.
downloading_task = BashOperator(
    task_id="download.airflow.downloaded.forecast.5mins.db.prices.bitcoin",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

# Execute task in Airflow.
downloading_task
