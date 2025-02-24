"""
Import as:

import im_v2.airflow.dags.airflow_utils.misc as imvadautmi
"""

import datetime


def get_dag_id_from_filename(filename: str) -> str:
    """
    Extract DAG ID from the DAG file name following our name convention.

    To simplify coupling between DAG .py file names and the display
    name shown in UI, derive the UI name directly from the file name.

    {stage}.{dag_id}.py -> dag_id
    preprod.backfill_bulk_ohlcv_data_fargate.py -> backfill_bulk_ohlcv_data_fargate

    :param filename: name of the file to extract DAG ID from
    :return: DAG ID extracted from the file name
    """
    dag_id = filename.rsplit(".", 1)[0]
    return dag_id


def get_stage_from_filename(filename: str) -> str:
    """
    Extract stage from the DAG file name following our name convention.

    {stage}.{dag_name}.py -> stage
    preprod.backfill_bulk_ohlcv_data_fargate -> preprod

    :param filename: name of the file to extract stage from
    :return: stage extracted from the file name
    """
    stage = filename.split(".")[0]
    # Assert stage argument is one of the supported ones.
    assert stage in ["prod", "preprod", "test"]
    return stage


def align_to_5min_grid(date: datetime.datetime) -> datetime.datetime:
    """
    Align a datetime object to 5 min grid.

    examples:
    2023-10-23T15:53:00+00:00 -> 2023-10-23T15:55:00+00:00
    2023-10-23T15:42:00+00:00 -> 2023-10-23T15:40:00+00:00

    :param date: datetime to align to a 5-min grid
    :return: datetime aligned to 5 min grid
    """
    return date.replace(minute=date.minute - date.minute % 5, second=0)


def assert_stage_name(stage: str) -> None:
    """
    Assert stage argument is one of the supported ones.

    :param stage: stage argument to assert
    """
    assert stage in ["prod", "preprod", "test"]


# def strptime(date_str: str) -> datetime.datetime:
#    """
#    Convert string to airflow datetime format.
#
#    :param date_str: date string to convert to datetime object
#    """
#    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
