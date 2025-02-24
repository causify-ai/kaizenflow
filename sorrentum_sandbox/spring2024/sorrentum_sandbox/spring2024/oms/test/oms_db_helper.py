import abc
import logging
import os
from typing import Any, Callable

import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hsql as hsql
import helpers.hsql_test as hsqltest
import oms.oms_lib_tasks as oomlitas

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestOmsDbHelper
# #############################################################################


class TestOmsDbHelper(hsqltest.TestImOmsDbHelper, abc.ABC):
    """
    Configure the helper to build an OMS test DB.
    """

    # TODO(gp): For some reason without having this function defined, the
    #  derived classes can't be instantiated because of get_id().
    @classmethod
    @abc.abstractmethod
    def get_id(cls) -> int:
        raise NotImplementedError

    @classmethod
    def _get_compose_file(cls) -> str:
        idx = cls.get_id()
        dir_name = hgit.get_amp_abs_path()
        docker_compose_path = os.path.join(
            dir_name, "oms/devops/compose/docker-compose.yml"
        )
        docker_compose_path_idx: str = hio.add_suffix_to_filename(
            docker_compose_path, idx
        )
        return docker_compose_path_idx

    @classmethod
    def _get_service_name(cls) -> str:
        idx = cls.get_id()
        return "oms_postgres" + str(idx)

    # TODO(gp): Use file or path consistently.
    @classmethod
    def _get_db_env_path(cls) -> str:
        """
        See `_get_db_env_path()` in the parent class.
        """
        # Use the `local` stage for testing.
        idx = cls.get_id()
        env_file_path = oomlitas.get_db_env_path("local", idx=idx)
        return env_file_path  # type: ignore[no-any-return]

    @classmethod
    def _get_postgres_db(cls) -> str:
        return "oms_postgres_db_local"

    def _test_create_table_helper(
        self: Any,
        table_name: str,
        create_table_func: Callable,
        create_table_func_kwargs: Any,
    ) -> None:
        """
        Run sanity check for a DB table.

        - Test that the DB is up
        - Remove the table `table_name`
        - Create the table `table_name` using `create_table_func()`
        - Check that the table exists
        - Delete the table
        """
        # Verify that the DB is up.
        db_list = hsql.get_db_names(self.connection)
        _LOG.info("db_list=%s", db_list)
        # Clean up the table.
        hsql.remove_table(self.connection, table_name)
        # The DB should not have this table.
        db_tables = hsql.get_table_names(self.connection)
        _LOG.info("get_table_names=%s", db_tables)
        self.assertNotIn(table_name, db_tables)
        # Create the table.
        incremental = False
        _ = (
            create_table_func(
                self.connection, incremental, **create_table_func_kwargs
            ),
        )
        # The table should be present.
        db_tables = hsql.get_table_names(self.connection)
        _LOG.info("get_table_names=%s", db_tables)
        self.assertIn(table_name, db_tables)
        # Delete the table.
        hsql.remove_table(self.connection, table_name)
