import logging
import os

import pytest

import core.config as cconfig
import dev_scripts.notebooks as dsnrn
import helpers.hgit as hgit
import research_amp.cc.algotrading as ramccalg

_LOG = logging.getLogger(__name__)


class TestCmTask3352Notebook(dsnrn.Test_Run_Notebook_TestCase):
    @pytest.mark.superslow("~70 seconds.")
    def test_run_notebook(self) -> None:
        """
        Test if the notebook runs end-to-end with no errors.
        """
        amp_dir = hgit.get_amp_abs_path()
        notebook_path = os.path.join(
            amp_dir,
            "research_amp/cc/notebooks/CMTask3352_pegged_at_mid_algo_simulation.ipynb",
        )
        config_builder = (
            "research_amp.cc.test.test_algo_notebook.build_config_list()"
        )
        self._test_run_notebook(notebook_path, config_builder)


def build_config_list() -> cconfig.ConfigList:
    """
    Build the config to run the notebook.
    """
    config = ramccalg.get_default_config()
    config["id"] = "0"
    configs = [config]
    config_list = cconfig.ConfigList(configs)
    return config_list
