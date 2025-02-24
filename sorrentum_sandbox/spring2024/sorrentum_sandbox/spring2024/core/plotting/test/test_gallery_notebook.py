import logging
import os

import pytest

import core.config as cconfig
import dev_scripts.notebooks as dsnrn
import helpers.hgit as hgit

_LOG = logging.getLogger(__name__)


def build_config_list() -> cconfig.ConfigList:
    """
    Simple config builder used by the test.
    """
    config_dict = {"figsize": (20, 10)}
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


@pytest.mark.superslow("~40 sec.")
class TestGalleryNotebook(dsnrn.Test_Run_Notebook_TestCase):
    def test_run_notebook(self) -> None:
        """
        Test if gallery notebook runs end-to-end with no errors.
        """
        amp_path = hgit.get_amp_abs_path()
        notebook_path = os.path.join(
            amp_path, "core/plotting/notebooks/gallery_notebook.ipynb"
        )
        config_func_path = (
            "core.plotting.test.test_gallery_notebook.build_config_list()"
        )
        self._test_run_notebook(notebook_path, config_func_path)
