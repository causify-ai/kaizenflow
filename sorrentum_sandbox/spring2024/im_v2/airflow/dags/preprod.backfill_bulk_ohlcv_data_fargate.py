"""
This is a utility DAG which provides a convenient way of catching up with data
to avoid having to run a long resource heavy task manually.

General guide (many parts of the DAG can be reused but
some might need custom adjustment based on a particular dataset
which needs downloading)

The DAG is annotated with enumerated comments explaining
what might need to be changed. i.e.
# Guide 1.
"""

import copy
import datetime
import os
from itertools import product

import airflow
import airflow_utils.ecs.operator as aiutecop
import airflow_utils.misc as aiutmisc
from airflow.models import Variable
from airflow.models.param import Param
from airflow.operators.dummy_operator import DummyOperator

_FILENAME = os.path.basename(__file__)

# This variable will be propagated throughout DAG definition as a prefix to
# names of Airflow configuration variables, allow to switch from test to preprod/prod
# in one line (in best case scenario).
# Guide 1. Make sure to run the bulk downloaders in the test environment
#  to ensure non-interference with production system.
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
# Guide 2. This will determine which task-definition will be used.
#  As a dev you should have one dedicated to you -> cmamp-test-you.
_USERNAME = ""

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
# Guide 4. Here you can set up all of the constants used throughout the DAG
#  in a centralized location
_EXCHANGES = ["binance"]
_VENDORS = ["ccxt"]
_UNIVERSES = {"ccxt": "v7.4"}
_CONTRACTS = ["futures"]
_DATA_TYPES = ["ohlcv"]
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "bulk"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "postgres"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "manual"

_DB_TABLE = "ccxt_ohlcv_futures"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)

# Guide 5. These variables are set up in the Airflow UI.
_BID_ASK_DEPTH = "{{ var.value.websocket_download_bid_ask_depth }}"
_DAG_DESCRIPTION = (
    f"Realtime {_DATA_TYPES} data download and resampling, contracts:"
    + f"{_CONTRACTS}, using {_VENDORS} from {_EXCHANGES}."
)
# Guide 6. Set up an arbitrary interval to download the data in chunks.
_SCHEDULE = None

# Pass default parameters for the DAG.
default_args = {
    "retries": 1,
    "retry_delay": 0,
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
    # Guide 7. These variables are crucial for
    #  downloading the data correctly.
    # start_date tells Airflow when the DAG
    #  "should have started"
    # and catchup=False tells Airflow to run
    #  jobs which "should have" been run in the past.
    catchup=False,
    start_date=datetime.datetime(2021, 1, 1, 0, 0, 0),
    tags=[_STAGE],
    params={
        "start_timestamp": Param("2023-07-23T02:20:00+00:00", "Start timestamp."),
        "end_timestamp": Param("23-07-23T02:40:00+00:00", "End timestamp."),
    },
)

# Guide 8. Specify commands which need to be run.
download_command = [
    "/app/amp/im_v2/ccxt/data/extract/download_exchange_data_to_db.py",
    # Guide 9.
    "--start_timestamp '{{ params.start_timestamp }}'",
    "--end_timestamp '{{ params.end_timestamp }}'",
    "--exchange_id '{}'",
    "--universe '{}'",
    "--data_type '{}'",
    "--vendor '{}'",
    "--contract_type '{}'",
    "--aws_profile 'ck'",
    f"--bid_ask_depth {_BID_ASK_DEPTH}",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
    f"--db_stage '{_STAGE}'",
    f"--db_table '{_DB_TABLE}'",
]

# Guide 11. In this particular case the job had 2 steps,
#  so modify based on current needs, if your job does not incur
#  two tasks, comment out the operator and related code.
qa_command = [
    "invoke run_single_dataset_qa_notebook",
    "--start-timestamp '{{ params.start_timestamp }}'",
    "--end-timestamp '{{ params.end_timestamp }}'",
    f"--base-dst-dir '/shared_data/ecs/{_STAGE}/data_qa/manual_backfill'",
    "--dataset-signature 'realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0'",
    f"--stage '{_STAGE}'",
    "--aws-profile 'ck'",
]

start_task = DummyOperator(task_id="start_dag", dag=dag)
end_download = DummyOperator(task_id="end_dag", dag=dag)

for vendor, exchange, contract, data_type in product(
    _VENDORS, _EXCHANGES, _CONTRACTS, _DATA_TYPES
):

    # TODO(Juraj): Make this code more readable.
    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_bash_command = copy.deepcopy(download_command)
    curr_bash_command[3] = curr_bash_command[3].format(exchange)
    curr_bash_command[4] = curr_bash_command[4].format(_UNIVERSES[vendor])
    curr_bash_command[5] = curr_bash_command[5].format(data_type)
    curr_bash_command[6] = curr_bash_command[6].format(vendor)
    curr_bash_command[7] = curr_bash_command[7].format(contract)

    backfill_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"{_DOWNLOAD_MODE}.backfill.{vendor}.{exchange}.{data_type}.{contract}",
        curr_bash_command,
        _ECS_TASK_DEFINITION,
        1024,
        2048,
        assign_public_ip=True,
    )

    qa_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"{_DOWNLOAD_MODE}.qa.{vendor}.{exchange}.{data_type}.{contract}",
        qa_command,
        _ECS_TASK_DEFINITION,
        1024,
        2048,
    )

    start_task >> backfill_task >> qa_task >> end_download
