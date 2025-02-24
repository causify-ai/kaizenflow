from airflow.models import DAG
from airflow.operators.bash import BashOperator
import datetime

mydag = DAG(
    dag_id="analysis",
    description="Analyse realtime kaiko data",
    tags=["kaiko"],
    start_date=datetime.datetime(2023, 4, 1),
    catchup=True,
    schedule=datetime.timedelta(days=1)
)

task = BashOperator(
    task_id="download_1d",
    bash_command="""
    cd /opt/airflow
    python3 dask_work.py --date "{{data_interval_start}}" --target_table "public.analysis"
    """
)

mydag.add_task(task)

globals()[mydag.dag_id] = mydag