"""
The following module handles retrieving scheduling intervals for all DAGs used
within our environment The nuances of Airflow scheduling intervals:

- Previously a solution of using Airflow variables to store scheduling interval for each DAG was used, this goes against Airflow best practices since each call to airflow.Variable interface creates a DB connection so it is advised against using this approach in the top level code of the DAG definition.
- It is sometimes safer to schedule the same DAGs in different stages in non overlapping interval to avoid throttling or spiking number of active workers.

Import as:

import im_v2.airflow.dags.airflow_utils.schedule.schedule as imvadaussc
"""

# Store scheduling inteval for a DAG in each stage.
_SCHEDULE = {
    "data_qa_periodic_10min_fargate": {
        "prod": "*/10 * * * *",
        "preprod": "*/10 * * * *",
        "test": "*/10 * * * *",
    },
    "data_qa_periodic_daily_fargate": {
        "prod": "0 11 * * *",
        "preprod": "30 10 * * *",
        "test": "0 10 * * *",
    },
}


def get_scheduling_interval(dag_id: str) -> str:
    """
    Get scheduling interval for a given DAG ID.

    :param dag_id: DAG filename without the filename extension, i.e., preprod.data_qa_fargate.py -> preprod.data_qa_fargate
    :return: cron-like expression representing scheduling interval
    """
    stage, dag_name = dag_id.split(".", 1)
    return _SCHEDULE[dag_name][stage]
