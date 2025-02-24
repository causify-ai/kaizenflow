from airflow import DAG
from airflow.providers.telegram.operators.telegram import TelegramOperator
from airflow.models import Variable

def get_telegram_operator(dag: DAG, stage: str, purpose: str, dag_id: str, run_id: str) -> TelegramOperator:
    """
    Get telegram notification operator.
    
    :param dag: DAG to assign the operator to
    :param stage: stage to run in (test, preprod, prod)
    :param purpose: what type of notification is this related to: datapull, or trading
    :param dag_id: Named of the DAG, to identify which DAG failed
    :param run_id: ID of the current dag run (to identify which specific run the notification belongs to)
    :return: Telegram operator assigned to the passed Airflow DAG
    """
    # Two currently supported types of notifications.
    assert purpose in ["datapull", "trading"]
    
    # Construct the variable name based on the stage and purpose
    chat_id_var_name = f"{stage}_{purpose}_telegram_room_id"

    # Retrieve the chat ID from Airflow variable
    chat_id = Variable.get(chat_id_var_name, default_var="datapull")  # Handling the case when variable is not set

    tg_operator = TelegramOperator(
        task_id="send_telegram_notification_on_failure",
        telegram_conn_id=f"{stage}_telegram_conn",  # The API token
        chat_id=chat_id,  # The dynamic chat ID
        text=f"DAG {dag_id} failed \nrun ID: {run_id}",
        dag=dag,
        trigger_rule='one_failed'
    )
    return tg_operator
