"""
Import as:

import helpers.hsql_test as hsqltest
"""

import abc
import logging
import os

import pytest

import helpers.hdocker as hdocker
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsql as hsql
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# #############################################################################
# TestDbHelper
# #############################################################################


# TODO(Grisha): Why does it require `ck_infra`?
@pytest.mark.requires_ck_infra
@pytest.mark.requires_docker_in_docker
@pytest.mark.skipif(
    not henv.execute_repo_config_code("has_dind_support()")
    and not henv.execute_repo_config_code("use_docker_sibling_containers()"),
    reason="Need docker children / sibling support",
)
class TestDbHelper(hunitest.TestCase, abc.ABC):
    """
    Allow testing code that interacts with a DB.

    It creates / destroys a test DB during setup / teardown of the class. This means
    that the same DB is reused for multiple test methods of the same class.

    The invariant is that each test method should:
    - (ideally) find a clean DB to work with
    - not assume that the DB is clean. If the DB is not clean, tests should clean it
      before starting, or work around it
      - E.g., if a test needs to write a table, but the table is already present and
        partially filled as a leftover from a previous test, the new test should
        delete the table and create it again
    - clean the DB after themselves, i.e., undo the work that has been done
      - E.g., if a test creates a table, then the test should delete the table at
        the end of the test

    - An existing DB can be reused
      - A user can create a persistent local DB in the Docker container, e.g. for OMS:
        ```
        docker> (cd oms; sudo docker-compose \
                    --file /app/oms/devops/compose/docker-compose.yml up \
                    -d \
                    oms_postgres)
        ```
        or
        ```
        docker> invoke oms_docker_up
        ```
      - Then this class skips creating / destructing the DB, making the tests faster
        and allowing easier debugging.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Initialize the test database inside test container.
        """
        _LOG.info("\n%s", hprint.frame("setUpClass"))
        cls._create_docker_files()
        # Read the connection parameters from the env file.
        cls.db_env_file = cls._get_db_env_path()
        connection_info = hsql.get_connection_info_from_env_file(cls.db_env_file)
        _LOG.debug("connection_info=%s", connection_info)
        conn_exists = hsql.check_db_connection(*connection_info)[0]
        if conn_exists:
            _LOG.warning("DB is already up: skipping docker compose")
            # Since we have found the DB already up, we assume that we need to
            # leave it running after the tests
            cls.bring_down_db = False
        else:
            # Start the service.
            cls.docker_compose_file_path = os.path.join(
                hgit.get_amp_abs_path(), cls._get_compose_file()
            )
            # TODO(Grisha): use invoke task CMTask #547.
            cmd = (
                "sudo docker-compose "
                f"--file {cls.docker_compose_file_path} "
                f"--env-file {cls.db_env_file} "
                f"up -d {cls._get_service_name()}"
            )
            _LOG.debug("cmd=%s", cmd)
            hsystem.system(cmd, suppress_output=False)
            # Wait for the DB to be available.
            hsql.wait_db_connection(*connection_info)
            cls.bring_down_db = True
        # Save connection info.
        # TODO(gp): -> db_connection
        cls.connection = hsql.get_connection(*connection_info, autocommit=True)

    # TODO(Grisha): difference between cmamp and kaizenflow.
    @classmethod
    def tearDownClass(cls) -> None:
        """
        Bring down the test container.
        """
        _LOG.info("\n%s", hprint.frame("tearDown"))
        docker_compose_cleanup = cls.bring_down_db
        if docker_compose_cleanup:
            if henv.execute_repo_config_code("use_main_network()"):
                # When using sibling containers `docker-compose down` tries to shut
                # down also the `main_network`, while it is attached to the Docker
                # container running the tests
                # So we clean up the containers and volumes directly.
                # TODO(gp): This could become an invoke target.
                # Remove the container, e.g., `compose-oms_postgres7482-1`.
                service_name = cls._get_service_name()
                container_name = f"compose-{service_name}-1"
                hdocker.container_rm(container_name)
                # Remove the volume, e.g., `compose_oms_postgres7482_data`.
                volume_name = f"compose_{service_name}_data"
                hdocker.volume_rm(volume_name)
            else:
                # TODO(Grisha): use invoke task CMTask #547.
                cmd = (
                    "sudo docker-compose "
                    f"--file {cls.docker_compose_file_path} "
                    f"--env-file {cls.db_env_file} "
                    "down -v"
                )
                hsystem.system(cmd, suppress_output=False)
        else:
            _LOG.warning("Leaving DB up")
        if not hunitest.get_incremental_tests():
            os.unlink(cls._get_compose_file())
            os.unlink(cls._get_db_env_path())

    @classmethod
    @abc.abstractmethod
    def get_id(cls) -> int:
        """
        Return a unique ID to create an OMS instance.

        This ID is used to generate Docker compose / env files and
        services, so that we can avoid collisions in case of parallel
        execution.

        This function is specified by the unit test in a way that is
        unique to each test.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_compose_file(cls) -> str:
        """
        Get path to Docker compose file.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_service_name(cls) -> str:
        """
        Get service name.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_db_env_path(cls) -> str:
        """
        Get path to env file that contains DB connection parameters.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _create_docker_files(cls) -> str:
        """
        Create the compose and env file for the DB run.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_postgres_db(cls) -> str:
        """
        Return the name of the postgres DB to use (e.g., im_postgres_db_local).
        """
        raise NotImplementedError


# #############################################################################
# TestImOmsDbHelper
# #############################################################################


class TestImOmsDbHelper(TestDbHelper, abc.ABC):
    # TODO(gp): Rewrite building a YAML with a package.
    @classmethod
    def _create_docker_files(cls) -> None:
        # Create compose file.
        service_name = cls._get_service_name()
        idx = cls.get_id()
        host_port = 5432 + idx
        txt = f"""version: '3.5'

services:
  # Docker container running Postgres DB.
  {service_name}:
    image: postgres:13
    restart: "no"
    environment:"""
        #
        if not henv.execute_repo_config_code(
            "use_docker_db_container_name_to_connect()"
        ):
            # Use the port to connect.
            txt += f"""
      - POSTGRES_HOST=${{POSTGRES_HOST}}
      - POSTGRES_DB=${{POSTGRES_DB}}
      - POSTGRES_PORT=${{POSTGRES_PORT}}
      - POSTGRES_USER=${{POSTGRES_USER}}
      - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD}}
    volumes:
      - {service_name}_data:/var/lib/postgresql/data
    ports:
      - {host_port}:5432"""
        else:
            # Do not use the port to connect.
            txt += f"""
      - POSTGRES_HOST=${{POSTGRES_HOST}}
      - POSTGRES_DB=${{POSTGRES_DB}}
      - POSTGRES_USER=${{POSTGRES_USER}}
      - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD}}
    volumes:
      - {service_name}_data:/var/lib/postgresql/data"""
        #
        txt += f"""
volumes:
  {service_name}_data: {{}}

networks:
  default:
    #name: {service_name}_network
    name: main_network"""
        compose_file_name = cls._get_compose_file()
        hio.to_file(compose_file_name, txt)
        # Create env file.
        txt = []
        if not henv.execute_repo_config_code(
            "use_docker_db_container_name_to_connect()"
        ):
            if hserver.is_dev4():
                host = "cf-spm-dev4"
            else:
                # host = os.environ["AM_HOST_NAME"]
                host = "localhost"
        else:
            # Use the service name, e.g., `im_postgres...`.
            host = service_name
        postgres_db = cls._get_postgres_db()
        txt.append(f"POSTGRES_HOST={host}")
        txt.append(f"POSTGRES_DB={postgres_db}")
        if not henv.execute_repo_config_code(
            "use_docker_db_container_name_to_connect()"
        ):
            txt.append(f"POSTGRES_PORT={host_port}")
        txt.append("POSTGRES_USER=aljsdalsd")
        txt.append("POSTGRES_PASSWORD=alsdkqoen")
        txt = "\n".join(txt)
        env_file_name = cls._get_db_env_path()
        hio.to_file(env_file_name, txt)
