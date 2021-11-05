"""
Import as:

import im.common.db.utils as imcodbuti
"""

import logging
import os

import helpers.sql as hsql

_LOG = logging.getLogger(__name__)


def db_connection_to_str(connection: hsql.DbConnection) -> str:
    """
    Get database connection details using environment variables. Connection
    details include:

        - Database name
        - Host
        - Port
        - Username
        - Password

    :param connection: a database connection
    :return: database connection details
    """
    info = connection.info
    txt = []
    txt.append("dbname='%s'" % info.dbname)
    txt.append("host='%s'" % info.host)
    txt.append("port='%s'" % info.port)
    txt.append("user='%s'" % info.user)
    txt.append("password='%s'" % info.password)
    txt = "\n".join(txt)
    return txt


def is_inside_im_container() -> bool:
    """
    Return whether we are running inside IM app.

    :return: True if running inside the IM app, False otherwise
    """
    # TODO(*): Why not testing only STAGE?
    condition = (
        os.environ.get("STAGE") == "TEST"
        and os.environ.get("POSTGRES_HOST") == "im_postgres_test"
    ) or (
        os.environ.get("STAGE") == "LOCAL"
        and os.environ.get("POSTGRES_HOST") == "im_postgres_local"
    )
    return condition
