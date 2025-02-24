import datetime
import airflow
import airflow_utils.ecs.operator as aiutecop
import airflow_utils.misc as aiutmisc
from airflow.operators.dummy_operator import DummyOperator
import airflow_utils.telegram.operator as aiutteop
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

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
_DAG_BUILDERS = ["C1b", "C3a", "C5b"]
_DAG_BUILD_CTOR_SUFFIX = {
    "C1b": "",
    "C3a": "_tmp",
    "C8b": "_tmp",
    "C5b": ""
}
_DAG_REPO = {
    "C1b": "orange",
    "C3a": "orange",
    "C8b": "orange",
    "C5b": "lemonade" 
}
_DAG_DESCRIPTION = "Test System DAG"
_SCHEDULE = "*/10 * * * *"
_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, True, _USERNAME)

# Pass default parameters for the DAG.
default_args = {
    "retries": 1,
    "retry_delay": 0,
    "email": [Variable.get(f"{_STAGE}_trading_notification_email")],
    "email_on_failure": True if _STAGE in ["prod", "preprod"] else False,
    "email_on_retry": False,
    "owner": "airflow",
}

def get_pnl_start_date(date):
    """
    Utility function to align a date to 5 min grid
    """
    if datetime.datetime.utcnow().time() <= date.time():
         date -= datetime.timedelta(days=1)
    return date

def get_pnl_end_date(date):
    """
    Utility function to align a date to 5 min grid
    """
    if datetime.datetime.utcnow().time() > date.time():
        date += datetime.timedelta(days=1, minutes=-5)
    else:
        date -= datetime.timedelta(minutes=5)
    return date
            

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=2,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    user_defined_filters={
        "get_pnl_start_date": get_pnl_start_date,  # Macro can also be a function
        "get_pnl_end_date": get_pnl_end_date
    },
    user_defined_macros = {
        "date": "{{ data_interval_end if 'scheduled' in run_id else macros.datetime.now() }}",
    },
    start_date=datetime.datetime(2022, 8, 1, 0, 0, 0),
    tags=[_STAGE],
)


efs_mount = "{{ var.value.efs_mount }}"
# We use data_interval_end because the DAG is supposed to start in real-time.
#dag_run_mode = "{{ 'scheduled' if 'scheduled' in run_id else 'manual' }}"
# This refers to the system run mode.
dag_run_mode = "scheduled"
start_timestamp = "{{ macros.datetime.today().replace(hour=13, minute=10, second=0, microsecond=0) | \
                    get_pnl_start_date | ts_nodash | replace('T', '_') }}"
end_timestamp = "{{ macros.datetime.today().replace(hour=13, minute=10, second=0, microsecond=0) | \
                    get_pnl_end_date | ts_nodash | replace('T', '_') }}"
#run_date = "{{ data_interval_end.date() | string | replace('-', '') }}"
run_mode_for_log = "{{ '' if 'scheduled' in run_id else '.manual' }}"

pnl_observer_cmd = [
    "mkdir /.dockerenv",
    "&&",
    "invoke run_master_pnl_real_time_observer_notebook",
    "--dag-builder-ctor-as-str '{}'",
    "--prod-data-root-dir '{}'",
    "--run-mode 'paper_trading'",
    "--mark-as-last-5minute-run"
]
    
start_task = DummyOperator(task_id='start_dag', dag=dag)
end_task = DummyOperator(task_id='end_system_tasks', dag=dag)
end_dag = DummyOperator(task_id='end_dag', dag=dag)

for dag_builder in _DAG_BUILDERS:
    
    log_base_dir = f"{efs_mount}/{_STAGE}/system_reconciliation/"
    curr_pnl_observer_cmd = copy.deepcopy(pnl_observer_cmd)
    
    dag_builder_ctor_as_str = "dataflow_{}.pipelines.{}.{}_pipeline{}.{}_DagBuilder{}".format(
        _DAG_REPO[dag_builder],
        dag_builder[:2], 
        dag_builder,
        _DAG_BUILD_CTOR_SUFFIX[dag_builder], 
        dag_builder, 
        _DAG_BUILD_CTOR_SUFFIX[dag_builder]
    )
    
    curr_pnl_observer_cmd[3] = curr_pnl_observer_cmd[3].format(dag_builder_ctor_as_str)
    curr_pnl_observer_cmd[4] = curr_pnl_observer_cmd[4].format(log_base_dir)

    pnl_observer_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"{dag_builder}.pnl_observer",
        curr_pnl_observer_cmd,
        _ECS_TASK_DEFINITION,
        1024, 
        4096,
    )
             
    start_task >> pnl_observer_task >> end_task >> end_dag
    
if _STAGE != "test":
    telegram_notification_task = aiutteop.get_telegram_operator(dag, _STAGE, "trading", _DAG_ID, "{{ run_id }}")
    end_task >> telegram_notification_task >> end_dag