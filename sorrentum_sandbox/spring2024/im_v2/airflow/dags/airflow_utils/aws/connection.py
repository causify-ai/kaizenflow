"""
Import as:

import im_v2.airflow.dags.airflow_utils.aws.connection as imvadauaco
"""

from typing import Optional


def get_connection_by_stage(stage: str) -> Optional[str]:
    """
    Interface to return correct reference to AWS connection for EcsOperators.

    In production, the MWAA obtains the credentials automatically so we
    pass `None` to the aws_conn_id whereas we use `aws_default` in the
    self-hosted environment.
    """
    return None if stage == "prod" else "aws_default"
