"""
Import as:

import helpers.hsql as hsql
"""

import helpers.henv as henv

# The problem here is that part of the code base end up including `hsql` which
# requires `psycopg2` even though it's not called at run-time.
# To simplify the dependency management we include the code of `hsql` only if
# `psycopg2` is present. If not, we just create a stub for the needed type hints.
if henv.has_module("psycopg2"):
    from helpers.hsql_implementation import *  # isort:skip  # noqa: F401,F403 # pylint: disable=unused-import,unused-wildcard-import,wildcard-import

else:
    from typing import Any

    DbConnection = Any


def create_in_operator(values: List[str], column_name: str) -> str:
    """
    Transform a list of possible values into an IN operator clause.

    :param values: a list of possible values for the given column, e.g. `["binance", "ftx"]`
    :param column_name: the name of the column, e.g. 'exchange_id'
    :return: IN operator clause with specified values,
      e.g. `"exchange_id IN ('binance', 'ftx')"`
    """
    in_operator = (
        f"{column_name} IN (" + ",".join([f"'{value}'" for value in values]) + ")"
    )
    return in_operator
