"""
DAG to download data from uniswap.
"""

from datetime import datetime, timedelta

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "uniswap_1h_analysis_calculation"
_DAG_DESCRIPTION = "Update data_calculation table using latest uniswap info"
# Specify when often to execute the DAG.
_SCHEDULE = timedelta(hours=1)

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
    start_date=datetime(2023, 4, 27, 0, 0, 0),
)

bash_command = [
    # Sleep 5 seconds to ensure the bar is finished.
    "sleep 5",
    "&&",
    # "python3 -m pip install dask ",
    # "&&",
    "python3 /cmamp/sorrentum_sandbox/examples/ml_projects/Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap/dask_script.py",
]

downloading_task = BashOperator(
    task_id="uniswap.periodic_1hr.analysis.calculation",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
