"""
Import as:

import dev_scripts.notebooks.run_notebook_test_case as dsnrnteca
"""

import logging
import os

import helpers.hgit as hgit
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_Run_Notebook_TestCase(hunitest.TestCase):
    """
    Check that a notebook is not broken by running it end-to-end.
    """

    def _test_run_notebook(
        self, notebook_path: str, config_builder: str, *, extra_opts: str = ""
    ) -> None:
        """
        Test that a notebook runs end-to-end.

        :param notebook_path: path to a notebook file to run, use
            `hgit.get_amp_abs_path()` when testing a notebook that is in `amp`
        :param config_builder: a function to use as config builder that returns
            a list of configs
        :param extra_opts: options for "run_notebook.py", e.g., "--publish_notebook"
        """
        dst_dir = self.get_scratch_space()
        #
        amp_dir = hgit.get_amp_abs_path()
        script_path = os.path.join(
            amp_dir, "dev_scripts", "notebooks", "run_notebook.py"
        )
        # Build a command to run the notebook.
        opts = f"--no_suppress_output --num_threads 'serial'{extra_opts} -v DEBUG 2>&1"
        cmd = [
            f"{script_path}",
            f"--notebook {notebook_path}",
            f"--config_builder '{config_builder}'",
            f"--dst_dir {dst_dir}",
            f"{opts}",
        ]
        cmd = " ".join(cmd)
        _LOG.debug("cmd=%s", cmd)
        # Execute.
        rc = hsystem.system(
            cmd, abort_on_error=True, suppress_output=False, log_level="echo"
        )
        _LOG.debug("rc=%s", rc)
        # Make sure that the run finishes successfully.
        self.assertEqual(rc, 0)
