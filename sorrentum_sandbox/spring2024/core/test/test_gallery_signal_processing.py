import logging
import os

import pytest

import helpers.hgit as hgit
import helpers.hjupyter as hjupyte
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


@pytest.mark.superslow
class Test_gallery_signal_processing1(hunitest.TestCase):
    def test_notebook1(self) -> None:
        file_name = os.path.join(
            hgit.get_amp_abs_path(),
            "core/notebooks/gallery_signal_processing.ipynb",
        )
        scratch_dir = self.get_scratch_space()
        hjupyte.run_notebook(file_name, scratch_dir)
