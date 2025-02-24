import argparse
import datetime

from airflow.models import DAG
from airflow.operators.bash import BashOperator

mydag = DAG(
    dag_id="historical",
    description="Download historical kaiko data",
    tags=["kaiko"],
    start_date=datetime.datetime(2023, 3, 1),
    end_date=datetime.datetime(2023, 4, 1),
    catchup=True,
    schedule=datetime.timedelta(days=1),
)

task = BashOperator(
    task_id="download_1d",
    bash_command="""
    cd /opt/airflow
    python3 download_to_db.py --start_timestamp "{{data_interval_start}}" --end_timestamp "{{data_interval_end}}" --target_table "public.historical"
    """,
)

mydag.add_task(task)

globals()[mydag.dag_id] = mydag
