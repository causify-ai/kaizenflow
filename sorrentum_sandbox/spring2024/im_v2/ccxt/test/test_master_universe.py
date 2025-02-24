import os

import pytest

import core.config as cconfig
import dev_scripts.notebooks.run_notebook_test_case as dsnrnteca
import helpers.hgit as hgit


def build_config() -> cconfig.ConfigList:
    """
    Simple config builder for the test.
    """
    # We want to execute the notebook as it is, but config builder needs
    # a config from the caller, which we ignore for now.
    config = {}
    config = cconfig.Config()
    config_list = cconfig.ConfigList([config])
    return config_list


class Test_run_master_universe(dsnrnteca.Test_Run_Notebook_TestCase):
    @pytest.mark.slow("~14 sec.")
    def test_run_notebook(self) -> None:
        """
        Test that the notebook runs end-to-end without errors.
        """
        amp_dir = hgit.get_amp_abs_path()
        notebook_path = os.path.join(
            amp_dir,
            "im_v2",
            "ccxt",
            "notebooks",
            "Master_universe.ipynb",
        )
        config_builder = "im_v2.ccxt.test.test_master_universe.build_config()"
        self._test_run_notebook(notebook_path, config_builder)
