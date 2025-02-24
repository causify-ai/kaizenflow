"""
Import as:

import oms.db.ck_credentials as odbckcre
"""

import helpers.hdbg as hdbg

# TODO(gp): Unclear if we need DB table names if we don't use DatabasePortfolio.

# Liveness = real trading (=LIVE) or paper trading (=CANDIDATE)
# Instance_type = CF framework QA / prod
#
# There are 4 possible combinations of instance and liveness e.g.
#     instance=PROD liveness=LIVE
#     instance=PROD liveness=CANDIDATE
#     instance=QA liveness=LIVE
#     instance=QA liveness=CANDIDATE
# Only 3 combinations are actually valid, since (QA,CANDIDATE) is not valid.
# In other terms CF doesn't run paper trading


def dassert_is_config_valid(liveness: str, instance_type: str) -> None:
    hdbg.dassert_in(liveness, ("LIVE", "CANDIDATE", "null"))
    hdbg.dassert_in(instance_type, ("QA", "PROD"))


def get_core_db_postfix(liveness: str, instance_type: str) -> str:
    """
    Map liveness and instance type to a pynudge slot.

    This code is lifted from CF Java code.
    """
    dassert_is_config_valid(liveness, instance_type)
    if liveness != "LIVE":
        # Candidate is meant to test any changes to your model code using a paper
        # trading account.
        ret = "candidate"
    elif instance_type != "PROD":
        # This is used to test the CF framework changes (e.g., running a production
        # model in a QA CF environment). We should not interact directly with QA,
        # since this is handled by CF team.
        ret = "qa"
    else:
        # Any model running in a prod CF environment, using a real (non paper-trading)
        # account).
        ret = "prod"
    return ret


def get_core_db_table(db_table: str, liveness: str, instance_type: str) -> str:
    """
    Return the name of DB table based on liveness and instance_type.

    E.g., 'bod_positions_candidate_view' 'current_locates_qa_view'
    'restrictions_candidate_view'
    """
    return db_table + "_" + get_core_db_postfix(liveness, instance_type)


def get_core_db_view(db_table: str, liveness: str, instance_type: str) -> str:
    """
    Same as `get_core_db_table()` but with a postfix in `_view`.

    E.g., 'bod_positions_candidate_view' 'current_locates_qa_view'
    'restrictions_candidate_view'
    """
    return get_core_db_table(db_table, liveness, instance_type) + "_view"
