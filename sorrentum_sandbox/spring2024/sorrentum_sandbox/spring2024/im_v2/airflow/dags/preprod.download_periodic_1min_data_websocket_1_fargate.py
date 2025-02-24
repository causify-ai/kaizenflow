"""
This DAG is used to download realtime data to the IM database via websockets.
"""

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
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
_USERNAME = ""

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
_UNIVERSES = {
    "binance": "v7.3",
}
_DOWNLOAD_JOBS = [
    # For binance futures we have a redundant downloader.
    ("ccxt", "binance", "futures", "ohlcv", 1),
    ("ccxt", "binance", "futures", "ohlcv", 2),
    ("ccxt", "binance", "futures", "bid_ask", 1),
]

# How many levels deep in to order book
# to downlaod per iteration per symbol
_BID_ASK_DEPTH = "{{ var.value.websocket_download_bid_ask_depth }}"
# Specify how long should the DAG be running for (in minutes).
_RUN_FOR = 60
# Specify how much in advance should the DAG be scheduled (in minutes).
# We leave a couple minutes to account for delay in container setup
# such that the download can start at a precise point in time.
_DAG_STANDBY = 6
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "realtime"
_ACTION_TAG = "downloaded_200ms"
_DATA_FORMAT = "postgres"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = "Realtime data download and resampling."
# Specify when/how often to execute the DAG.
_SCHEDULE = "0 * * * *"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)

# Pass default parameters for the DAG.
default_args = {
    "retries": 1 if _STAGE in ["prod", "preprod"] else 0,
    "retry_delay": 0,
    "email": [Variable.get(f"{_STAGE}_notification_email")],
    "email_on_failure": True if _STAGE in ["prod", "preprod"] else False,
    "owner": "airflow",
}

# Create a command, leave values to be parametrized.
download_command = [
    "/app/amp/im_v2/{}/data/extract/download_exchange_data_to_db_periodically.py",
    "--exchange_id '{}'",
    "--universe '{}'",
    "--db_table '{}'",
    "--data_type '{}'",
    "--contract_type '{}'",
    "--vendor {}",
    # This argument gets ignored for OHLCV data type.
    f"--bid_ask_depth {_BID_ASK_DEPTH}",
    f"--db_stage '{_STAGE}'",
    "--aws_profile 'ck'",
    # At this point we set up a logic for real time execution
    # Start date is postponed by _DAG_STANDBY minutes and a short
    # few seconds delay to ensure the bars from the nearest minute are finished.
    "--start_time '{{ macros.datetime.now(dag.timezone).replace(second=0, microsecond=0) + macros.timedelta(minutes=(var.value.rt_data_download_standby_min | int) - 1, seconds=10) }}'",
    "--stop_time '{{ data_interval_end + macros.timedelta(minutes=(var.value.rt_data_download_run_for_min | int) + var.value.rt_data_download_standby_min | int) }}'",
    "--method 'websocket'",
    "--websocket_data_buffer_size 0",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
]

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=3,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2022, 7, 1, 0, 0, 0),
    tags=[_STAGE],
)

start_task = DummyOperator(task_id="start", dag=dag)
end_task = DummyOperator(task_id="end", dag=dag)
end_dag = DummyOperator(task_id="end_dag", dag=dag)

for vendor, exchange, contract, data_type, _id in _DOWNLOAD_JOBS:

    table_name = f"{vendor}_{data_type}_{contract}"
    if data_type == "bid_ask":
        table_name += "_raw"
    if data_type == "trades":
        table_name += "_downloaded_all"

    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_download_command = copy.deepcopy(download_command)
    curr_download_command[0] = curr_download_command[0].format(vendor)
    curr_download_command[1] = curr_download_command[1].format(exchange)
    curr_download_command[2] = curr_download_command[2].format(
        _UNIVERSES[exchange]
    )
    curr_download_command[3] = curr_download_command[3].format(table_name)
    curr_download_command[4] = curr_download_command[4].format(data_type)
    curr_download_command[5] = curr_download_command[5].format(contract)
    curr_download_command[6] = curr_download_command[6].format(vendor)

    downloading_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"{_DOWNLOAD_MODE}.download.{vendor}.{exchange}.{data_type}.{contract}.{_id}",
        curr_download_command,
        _ECS_TASK_DEFINITION,
        256,
        512,
        assign_public_ip=True,
    )

    # Define the sequence of execution of task.
    start_task >> downloading_task >> end_task >> end_dag

if _STAGE != "test":
    telegram_notification_task = aiutteop.get_telegram_operator(
        dag, _STAGE, "datapull", _DAG_ID, "{{ run_id }}"
    )
    end_task >> telegram_notification_task >> end_dag
