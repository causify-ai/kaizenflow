#!/usr/bin/env python
"""
# Start all tunnels.

> ssh_tunnels.py start

# Stop all service tunnels
> ssh_tunnels.py stop

# Report the status of each service tunnel
> ssh_tunnels.py check

# Kill all the ssh tunnels on the machine, for a known service or not.
> ssh_tunnels.py kill

# Starting a tunnel is equivalent to:
> ssh -i {ssh_key_path} -f -nNT -L {local_port}:localhost:{remote_port} {user_name}@{server}
> ssh -f -nNT -L 10003:localhost:10003 saggese@$DEV_SERVER

Import as:

import dev_scripts.infra.old.ssh_tunnels as dsiosstu
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hparser as hparser
import helpers.hsystem as hsystem
import helpers.old.tunnels as holdtunn

_LOG = logging.getLogger(__name__)


# #############################################################################


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _help = """
- start: start a notebook if no notebook server is running at the requested port
- check: print the notebook servers running
- kill: kill a notebook server squatting the requested port
- force_start: kill squatting notebook servers and start a new one
"""
    parser.add_argument(
        "positional",
        nargs=1,
        choices=["start", "stop", "check", "kill"],
        help=_help,
    )
    parser.add_argument("--user", type=str, action="store")
    hparser.add_verbosity_arg(parser)
    #
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Check that we are in the repo since to open the tunnel we need some
    # env vars set by setenv.sh. This is also preventing Test_ssh_tunnel to be
    # run by Jenkins.
    # TODO(gp): Improve this.
    repo_name = hgit.get_repo_full_name_from_client(super_module=True)
    exp_repo_name = ".../..."
    if repo_name != exp_repo_name:
        msg = "Need to run from repo '%s' and not from '%s'" % (
            exp_repo_name,
            repo_name,
        )
        _LOG.error(msg)
        raise RuntimeError(msg)
    #
    if args.user:
        user_name = args.user
    else:
        user_name = hsystem.get_user_name()
    #
    action = args.positional[0]
    _LOG.debug("action=%s", action)
    if action == "start":
        holdtunn.start_tunnels(user_name)
    elif action == "stop":
        holdtunn.stop_tunnels()
    elif action == "check":
        holdtunn.check_tunnels()
    elif action == "kill":
        holdtunn.kill_all_tunnel_processes()
    else:
        hdbg.dfatal("Invalid action='%s'" % action)


if __name__ == "__main__":
    _main()
