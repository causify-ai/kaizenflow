"""
This is a utility DAG which provides a convenient
way of catching up with data to avoid having to run a long
resource heavy task manually.

General guide (many parts of the DAG can be reused but
some might need custom adjustment based on a particular dataset 
which needs downloading)

The DAG is annotated with enumerated comments explaining
what might need to be changed. i.e.: 
# Guide 1.
"""
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
# Guide 1. Make sure to run the bulk downloaders in the test environment
#  to ensure non-interference with (pre)production systems. 
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
# Guide 2. This will determine which task-definition will be used.
#  As a dev you should have one dedicated to you -> cmamp-test-yours.
_USERNAME = ""

# Guide 4. Here you can set up all of the constants used throughout the DAG.
_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
_DATA_TYPES = ["ohlcv"]
# List jobs in the following tuple format:
#  vendor, exchange, contract, data_type, universe
_JOBS = [
    ("ccxt", "binance", "futures", "ohlcv", "v7.3"),
]
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "periodic_daily"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "parquet"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = f"Daily {_DATA_TYPES} data download."
# Specify when/how often to execute the DAG.
_SCHEDULE = Variable.get(f'{_DAG_ID}_schedule')
_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)
# Guide 5. This variable is set up in the Airflow UI.
s3_bucket_path = f"s3://{Variable.get(f'{_STAGE}_s3_data_bucket')}"

# Pass default parameters for the DAG.
default_args = {
    "retries": 1 if _STAGE in ["prod", "preprod"] else 0,
    "email": [Variable.get(f'{_STAGE}_notification_email')],
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
    # Guide 7. These variables are crucial for 
    #  downloading the data correctly.
    # start_date tells Airflow when the DAG
    #  "should have started"
    # and catchup=True tells Airflow to run 
    #  jobs which "should have" been run in the past.
    catchup=True,
    start_date=datetime.datetime(2023, 3, 20, 0, 0, 0),
    tags=[_STAGE],
)

# Guide 8. 
# Specify the command to be executed upon container start-up.
download_command = [
    "/app/amp/im_v2/common/data/extract/download_bulk.py",
    # Guide 9.
    # Calculate timestamp to download data from the entire past day.
    # This part uses Jinja templating engine, the variable values are dynamically assigned upon each DAG execution
     "--end_timestamp '{{ data_interval_end.replace(hour=0, minute=0, second=0) - macros.timedelta(minutes=1) }}'",
     "--start_timestamp '{{ data_interval_start.replace(hour=0, minute=0, second=0) }}'",
     "--vendor '{}'",
     "--exchange_id '{}'",
     "--universe '{}'",
     "--data_type '{}'",
     "--contract_type '{}'",
     "--aws_profile 'ck'",
     "--assert_on_missing_data",
     f"--s3_path '{s3_bucket_path}'",
     f"--download_mode '{_DOWNLOAD_MODE}'",
     f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
     f"--action_tag '{_ACTION_TAG}'",
     f"--data_format '{_DATA_FORMAT}'",
]

start_task = DummyOperator(task_id='start_dag', dag=dag)
end_download = DummyOperator(task_id='end_dag', dag=dag)

# Guide 10. This syntax would allow you to dynamically generate
# multiple "similar" jobs.
for vendor, exchange, contract, data_type, universe in _JOBS:

    curr_bash_command = copy.deepcopy(download_command)
    curr_bash_command[3] = curr_bash_command[3].format(vendor)
    curr_bash_command[4] = curr_bash_command[4].format(exchange)
    curr_bash_command[5] = curr_bash_command[5].format(universe)
    curr_bash_command[6] = curr_bash_command[6].format(data_type)
    curr_bash_command[7] = curr_bash_command[7].format(contract)
    
    downloading_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"download.{_DOWNLOAD_MODE}.{vendor}.{exchange}.{contract}.{universe}",
        curr_bash_command,
        _ECS_TASK_DEFINITION,
        256, 
        512,
        assign_public_ip=True
    )
    
    # Guide 11. This is where edges of the DAG are set.
    start_task >> downloading_task >> end_download