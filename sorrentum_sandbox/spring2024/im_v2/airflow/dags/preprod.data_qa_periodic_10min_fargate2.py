# This is a utility DAG to conduct QA on real time data download
# The task analyzes the downloaded data stored inside an RDS database with the contents,
# to confirm expected attributes of the data

# IMPORTANT NOTES:
# Make sure to set correct dag schedule `schedule_interval` parameter.

# This DAG's configuration deploys tasks to AWS Fargate to offload the EC2s
# mainly utilized for rt download
import copy
import datetime
import os

import airflow
import airflow_utils.ecs.operator as aiutecop
import airflow_utils.misc as aiutmisc
import airflow_utils.telegram.operator as aiutteop
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator

_FILENAME = os.path.basename(__file__)

# This variable will be propagated throughout DAG definition as a prefix to
# names of Airflow configuration variables, allow to switch from test to preprod/prod
# in one line (in best case scenario).
# _STAGE = _FILENAME.split(".")[0]
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
_USERNAME = ""

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
# List of dataset signatures to perform QA on. i.e.:
# "periodic_daily.airflow.downloaded_1min.parquet.ohlcv.futures.v7.ccxt.binance.v1_0_0"
_QA_JOBS = [
    "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.binance.v1_0_0",
]
# Shared location to store the reconciliaiton notebook into
_QA_NB_DST_DIR = os.path.join(
    "{{ var.value.efs_mount }}", _STAGE, "data_qa", "periodic_10min"
)
_DAG_DESCRIPTION = (
    "Data QA. Run QA notebook and publish results" + " to a shared EFS."
)
_SCHEDULE = "5-59/10 * * * *"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)

# Pass default parameters for the DAG.
default_args = {
    "retries": 0,
    "email": [Variable.get(f"{_STAGE}_notification_email")],
    "email_on_failure": True if _STAGE in ["prod", "preprod"] else False,
    "email_on_retry": False,
    "owner": "airflow",
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2023, 1, 24, 0, 0, 0),
    tags=[_STAGE],
)

invoke_cmd = [
    "mkdir /.dockerenv",
    "&&",
    "invoke run_single_dataset_qa_notebook",
    f"--stage '{_STAGE}'",
    "--start-timestamp '{{ data_interval_start.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--end-timestamp '{{ data_interval_end.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--bid-ask-depth 1",
    "--bid-ask-frequency-sec '60S'",
    "--dataset-signature '{}'",
    "--aws-profile 'ck'",
    f"--base-dst-dir '{_QA_NB_DST_DIR}'",
]

start_comparison = DummyOperator(task_id="start_comparison", dag=dag)
end_comparison = DummyOperator(task_id="end_comparison", dag=dag)
end_dag = DummyOperator(task_id="end_dag", dag=dag)

for dataset_signature in _QA_JOBS:
    # Do a deepcopy of the bash cmd list so we can reformat params on each iteration.
    curr_invoke_cmd = copy.deepcopy(invoke_cmd)
    curr_invoke_cmd[-3] = curr_invoke_cmd[-3].format(dataset_signature)

    comparing_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"data_qa.{dataset_signature}",
        curr_invoke_cmd,
        _ECS_TASK_DEFINITION,
        512,
        2048,
    )

    start_comparison >> comparing_task >> end_comparison >> end_dag

if _STAGE != "test":
    telegram_notification_task = aiutteop.get_telegram_operator(
        dag, _STAGE, "datapull", _DAG_ID, "{{ run_id }}"
    )
    end_comparison >> telegram_notification_task >> end_dag
