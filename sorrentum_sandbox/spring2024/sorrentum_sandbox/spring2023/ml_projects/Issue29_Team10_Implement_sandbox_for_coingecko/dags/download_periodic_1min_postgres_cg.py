"""
DAG to download OHLCV data from CoinGecko
"""
import airflow 
import os
import logging
from airflow.models import Variable , TaskInstance
from airflow import DAG, settings

# Operators; we need this to operate!
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
import datetime
import pendulum 
import calendar

# from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_1min_postgres_coingecko"
_DAG_DESCRIPTION = (
    "Download Coingecko data every hour and save to Postgres"
)
# Specify when to execute the DAG.
_SCHEDULE = '0 * * * *'

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
    start_date=datetime.datetime(2023, 4, 15, 0, 0, 0),
)

# create dynamic variables for data_invterval_start/end
def bridge(data_interval_start):

    date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    utc_time_start = calendar.timegm(date.utctimetuple())


    logging.info("Setting Airflow Variable from_timestamp1 to " + str(utc_time_start))
    Variable.set('from_timestamp1', str(utc_time_start))
    

def bridge2(data_interval_end):

    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple())


    logging.info("Setting Airflow Variable to_timestamp1 to " + str(utc_time))
    Variable.set('to_timestamp1', str(utc_time))
 



from_timestamp1 = Variable.get("from_timestamp1")
logging.info("The current from_timestamp1 value is " + str(from_timestamp1))


to_timestamp1 = Variable.get("to_timestamp1")
logging.info("The current to_timestamp1 value is " + str(to_timestamp1))

bridge_task = PythonOperator(task_id='bridge', dag=dag, provide_context=True, python_callable=bridge, op_args=[])
bridge_task2 = PythonOperator(task_id='bridge2', dag=dag, provide_context=True, python_callable=bridge2, op_args=[])
]

downloading_task = BashOperator(
    task_id="download.periodic_1min.postgres.ohlcv.coingecko",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    env = {"pythonpath":"{{ var.value.get('pythonpath') }}", "from_timestamp":"{{ var.value.get('from_timestamp1') }}", "to_timestamp":"{{ var.value.get('to_timestamp1') }}"},
    dag=dag,
)
# set downstream tasks to execute in order
bridge_task.set_downstream(bridge_task2)
bridge_task2.set_downstream(downloading_task)

