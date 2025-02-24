import os

import pytest

import core.config as cconfig
import dev_scripts.notebooks as dsnrn
import helpers.hgit as hgit
import helpers.hserver as hserver


def build_config() -> cconfig.ConfigList:
    """
    Simple config builder for the test.
    """
    # We want to execute the notebook as it is, but config builder needs
    # a config from the caller, which we ignore for now
    config = {}
    config = cconfig.Config()
    config_list = cconfig.ConfigList([config])
    return config_list


@pytest.mark.skipif(
    hserver.is_inside_ci(),
    reason="The prod database is not available via GH actions",
)
class Test_run_master_raw_data_gallery_notebook(dsnrn.Test_Run_Notebook_TestCase):
    @pytest.mark.superslow("~157 seconds")
    def test1(self) -> None:
        amp_dir = hgit.get_amp_abs_path()
        notebook_path = "im_v2/common/notebooks/Master_raw_data_gallery.ipynb"
        notebook_path = os.path.join(amp_dir, notebook_path)
        config_builder = "im_v2.common.test.test_master_raw_data_gallery_notebook.build_config()"
        self._test_run_notebook(notebook_path, config_builder)
