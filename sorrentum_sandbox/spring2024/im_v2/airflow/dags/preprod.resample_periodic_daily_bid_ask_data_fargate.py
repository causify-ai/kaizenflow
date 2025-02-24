# This is a utility DAG to download OHLCV data daily.

import datetime
import airflow
import airflow_utils.ecs.operator as aiutecop
import airflow_utils.misc as aiutmisc
from airflow.operators.dummy_operator import DummyOperator
from airflow.models import Variable
import copy
import os

_FILENAME = os.path.basename(__file__)

# This variable will be propagated throughout DAG definition as a prefix to 
# names of Airflow configuration variables, allow to switch from test to preprod/prod
# in one line (in best case scenario).
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
_USERNAME = ""

# Deployment type, if the task should be run via fargate (serverless execution)
# or EC2 (machines deployed in our auto-scaling group)
_LAUNCH_TYPE = "fargate"

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
# Provide list of dicts in format:
# {
#   "src_signature": 'periodic_daily...',
#   "dst_signature": 'periodic_faily...' 
# }
_RESAMPLING_JOBS = [
    {
        "src_signature": "periodic_daily.airflow.archived_200ms.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0",
        "dst_signature": "periodic_daily.airflow.resampled_1min.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0" 
    }
]
_DAG_DESCRIPTION = "Resample bid/ask data"
_S3_BUCKET = f"s3://{Variable.get(f'{_STAGE}_s3_data_bucket')}"
# Specify when/how often to execute the DAG.
_SCHEDULE = "20 4 * * *"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)

# Pass default parameters for the DAG.
default_args = {
    "retries": 0,
    "email": [Variable.get(f'{_STAGE}_notification_email')],
    "email_on_failure": True if _STAGE in ["prod", "preprod"] else False,
    "email_on_failure": True,
    "email_on_retry": False,
    "owner": "airflow",
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=3,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=True,
    start_date=datetime.datetime(2023, 11, 1, 0, 0, 0),
    tags=[_STAGE],
)

resample_command = [
    "amp/im_v2/common/data/transform/resample_daily_bid_ask_data.py",
    "--start_timestamp '{{ data_interval_start.replace(hour=0, minute=0, second=0) }}'",
    "--end_timestamp '{{ data_interval_end.replace(hour=0, minute=0, second=0) - macros.timedelta(microseconds=1) }}'",
    "--src_signature '{}'",
    "--dst_signature '{}'",
    f"--src_s3_path '{_S3_BUCKET}'",
    f"--dst_s3_path '{_S3_BUCKET}'",
    "--bid_ask_levels 1",
    "--assert_all_resampled",
]

start_dag = DummyOperator(task_id='start_dag', dag=dag)
end_dag = DummyOperator(task_id='end_dag', dag=dag)

for job in _RESAMPLING_JOBS:

    curr_bash_command = copy.deepcopy(resample_command)
    curr_bash_command[3] = curr_bash_command[3].format(job["src_signature"])
    curr_bash_command[4] = curr_bash_command[4].format(job["dst_signature"])

    resampling_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"resample.{job['src_signature']}",
        curr_bash_command,
        _ECS_TASK_DEFINITION,
        2048,
        8192
    )
    
start_dag >> resampling_task >> end_dag