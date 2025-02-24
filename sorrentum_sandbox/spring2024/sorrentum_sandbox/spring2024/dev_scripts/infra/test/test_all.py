import logging

import pytest

import helpers.hgit as hgit
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################


# TODO(gp): Only Jenkins can run this to avoid to kill the tunnel. Enable this
# test somehow.
# @pytest.mark.skipif('hsystem.get_user_name() != "jenkins"')
@pytest.mark.skip
class Test_ssh_tunnel(hunitest.TestCase):
    def test1(self) -> None:
        exec_name = hgit.find_file_in_git_tree("ssh_tunnels.py")
        _LOG.debug("exec_name=%s", exec_name)
        # We execute all the phases in multiple rounds to make sure things
        # are fine.
        # TODO(gp): Add some automatic checking.
        actions = [
            #
            "start",
            "check",
            "stop",
            "check",
            #
            "kill",
            "check",
        ]
        for action in actions:
            _LOG.debug("action=%s", action)
            cmd = "%s %s -v INFO" % (exec_name, action)
            hsystem.system(cmd, suppress_output="ON_DEBUG_LEVEL")
