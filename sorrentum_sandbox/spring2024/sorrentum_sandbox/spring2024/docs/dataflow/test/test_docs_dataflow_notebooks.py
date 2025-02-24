import os

import pytest

import core.config as cconfig
import dev_scripts.notebooks.run_notebook_test_case as dsnrnteca
import helpers.hgit as hgit


def build_config_list() -> cconfig.ConfigList:
    """
    Build the config to run the notebook.
    """
    # We want to execute the notebook as it is, but config builder needs
    # a config from the caller, which we ignore for now.
    config = cconfig.Config()
    configs = [config]
    config_list = cconfig.ConfigList(configs)
    return config_list


@pytest.mark.superslow("~35 sec.")
class Test_run_tutorial_dataflow_notebook(dsnrnteca.Test_Run_Notebook_TestCase):
    def test1(self) -> None:
        """
        Test if the notebook runs end-to-end with no errors.
        """
        amp_dir = hgit.get_amp_abs_path()
        notebook_path = os.path.join(
            amp_dir,
            "dataflow",
            "notebooks",
            "build_dag_with_different_approaches.how_to_guide.ipynb",
        )
        config_builder = (
            "docs.dataflow.test.test_docs_dataflow_notebooks.build_config_list()"
        )
        self._test_run_notebook(notebook_path, config_builder)
