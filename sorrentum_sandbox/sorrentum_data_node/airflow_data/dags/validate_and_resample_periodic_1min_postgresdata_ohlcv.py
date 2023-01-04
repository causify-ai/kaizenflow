"""
Example DAG to load data from PostgreSQL, validate and transform them and save
back to the DB.
"""

import datetime

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "validate_and_resample_periodic_1min_postgresdata_ohlcv"
_DAG_DESCRIPTION = (
    "Resample binance OHLCV data every 5 minutes and save back to postgres"
)
# Specify when/how often to execute the DAG.
_SCHEDULE = "*/5 * * * *"

# Pass default parameters for the DAG.
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
    start_date=datetime.datetime(2022, 12, 23, 0, 0, 0),
)

bash_command = [
    # Sleep 20 seconds all 1-min data have been loaded into DB.
    "sleep 20",
    "&&",
    "/cmamp/sorrentum_sandbox/examples/binance/example_load_validate_transform.py",
    "--source_table 'binance_ohlcv_spot_downloaded_1min'",
    "--target_table 'binance_ohlcv_spot_resampled_5min'",
    "--start_timestamp {{ data_interval_start }} ",
    "--end_timestamp {{ data_interval_end }}",
]

downloading_task = BashOperator(
    task_id="resample.postgres.ohlcv.binance",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task