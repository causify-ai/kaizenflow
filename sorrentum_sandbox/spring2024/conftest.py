import logging
import os
from typing import Any, Generator

import helpers.hdbg as dbg
import helpers.hunit_test as hut

# Hack to workaround pytest not happy with multiple redundant conftest.py
# (bug #34).
if not hasattr(hut, "_CONFTEST_ALREADY_PARSED"):

    # import helpers.hversion as hversi
    # hversi.check_version()

    # pylint: disable=protected-access
    hut._CONFTEST_ALREADY_PARSED = True

    # Store whether we are running unit test through pytest.
    # pylint: disable=line-too-long
    # From https://docs.pytest.org/en/latest/example/simple.html#detect-if-running-from-within-a-pytest-run
    def pytest_configure(config: Any) -> None:
        _ = config
        # pylint: disable=protected-access
        hut._CONFTEST_IN_PYTEST = True

    def pytest_unconfigure(config: Any) -> None:
        _ = config
        # pylint: disable=protected-access
        hut._CONFTEST_IN_PYTEST = False

    # Create a variable to store the object used by pytest to print independently
    # of the capture mode.
    # https://stackoverflow.com/questions/41794888
    import pytest

    @pytest.fixture(autouse=True)
    def populate_globals(capsys):
        hut._GLOBAL_CAPSYS = capsys

    # Add custom options.
    def pytest_addoption(parser: Any) -> None:
        parser.addoption(
            "--update_outcomes",
            action="store_true",
            default=False,
            help="Update golden outcomes of test",
        )
        parser.addoption(
            "--incremental",
            action="store_true",
            default=False,
            help="Reuse and not clean up test artifacts",
        )
        parser.addoption(
            "--dbg_verbosity",
            dest="log_level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the logging level",
        )
        parser.addoption(
            "--dbg",
            action="store_true",
            help="Set the logging level to TRACE",
        )
        parser.addoption(
            "--image_version",
            action="store",
            help="Version of the image to test against",
        )
        parser.addoption(
            "--image_stage",
            action="store",
            help="Stage of the image to test against",
        )

    def pytest_collection_modifyitems(config: Any, items: Any) -> None:
        _ = items
        import helpers.henv as henv

        _WARNING = "\033[33mWARNING\033[0m"
        try:
            print(henv.get_system_signature()[0])
        except:
            print(f"\n{_WARNING}: Can't print system_signature")
        if config.getoption("--update_outcomes"):
            print(f"\n{_WARNING}: Updating test outcomes")
            hut.set_update_tests(True)
        if config.getoption("--incremental"):
            print(f"\n{_WARNING}: Using incremental test mode")
            hut.set_incremental_tests(True)
        # Set the verbosity level.
        level = logging.INFO
        if config.getoption("--dbg_verbosity", None) or config.getoption(
            "--dbg", None
        ):
            if config.getoption("--dbg_verbosity", None):
                level = config.getoption("--dbg_verbosity")
            elif config.getoption("--dbg", None):
                level = logging.TRACE
            else:
                raise ValueError("Can't get here")
            print(f"\n{_WARNING}: Setting verbosity level to %s" % level)
            # When we specify the debug verbosity we monkey patch the command
            # line to add the '-s' option to pytest to not suppress the output.
            # NOTE: monkey patching sys.argv is often fragile.
            import sys

            sys.argv.append("-s")
            sys.argv.append("-o log_cli=true")
        # TODO(gp): redirect also the stderr to file.
        dbg.init_logger(level, in_pytest=True, log_filename="tmp.pytest.log")

    if "PYANNOTATE" in os.environ:
        print("\nWARNING: Collecting information about types through pyannotate")
        # From https://github.com/dropbox/pyannotate/blob/master/example/example_conftest.py
        import pytest

        def pytest_collection_finish(session: Any) -> None:
            """
            Handle the pytest collection finish hook: configure pyannotate.

            Explicitly delay importing `collect_types` until all tests
            have been collected.  This gives gevent a chance to monkey
            patch the world before importing pyannotate.
            """
            # mypy: Cannot find module named 'pyannotate_runtime'
            import pyannotate_runtime  # type: ignore

            _ = session
            pyannotate_runtime.collect_types.init_types_collection()

        @pytest.fixture(autouse=True)
        def collect_types_fixture() -> Generator:
            import pyannotate_runtime

            pyannotate_runtime.collect_types.start()
            yield
            pyannotate_runtime.collect_types.stop()

        def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
            import pyannotate_runtime

            _ = session, exitstatus
            pyannotate_runtime.collect_types.dump_stats("type_info.json")
            print("\n*** Collected types ***")
