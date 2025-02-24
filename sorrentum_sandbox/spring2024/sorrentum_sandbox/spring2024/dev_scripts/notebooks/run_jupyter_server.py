#!/usr/bin/env python

"""
Start a jupyter server.

# Start a jupyter server killing the existing one:
> run_jupyter_server.py force_start

# This is equivalent to:
> jupyter notebook '--ip=*' --browser chrome . --port 10001

Import as:

import dev_scripts.notebooks.run_jupyter_server as dsnrjuse
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hsystem as hsystem
import helpers.user_credentials as usc

_LOG = logging.getLogger(__name__)

# #############################################################################


def _get_port_process(port):
    """
    Find the pids of the jupyter servers connected to a certain port.
    """

    # 'grep "jupyter-notebook" | grep "\-port" | grep %d' % port
    def _keep_line(port, line):
        keep = (
            ("jupyter-notebook" in line)
            and ("-port" in line)
            and (str(port) in line)
        )
        return keep

    keep_line = lambda line: _keep_line(port, line)
    pids, txt = hsystem.get_process_pids(keep_line)
    _LOG.debug("pids=%s", pids)
    return pids, txt


def _check(port):
    pids, txt = _get_port_process(port)
    _LOG.info("Found %d pids: %s\n%s", len(pids), str(pids), "\n".join(txt))


def _kill(port):
    get_pids = lambda: _get_port_process(port)
    hsystem.kill_process(get_pids)


def _start(port, action):
    pids, txt = _get_port_process(port)
    if pids:
        _LOG.warning(
            "Found other jupyter notebooks running on the same " "port:\n%s",
            "\n".join(txt),
        )
        if action == "force_start":
            _kill(port)
        else:
            print(
                "Exiting: re-run with force_start to kill the processes "
                "squatting the port"
            )
            return
    #
    ip_name = "localhost"
    print("You can connect to: %s:%s" % (ip_name, port))
    cmd = "jupyter notebook '--ip=*' --browser chrome . --port %s" % port
    if action != "only_print_cmd":
        hsystem.system(cmd, suppress_output=False, log_level="echo")
    else:
        print(cmd)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
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
        choices=["start", "force_start", "check", "kill", "only_print_cmd"],
        help=_help,
    )
    parser.add_argument(
        "--port",
        action="store",
        default=None,
        help="Override the " "default port to use",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    # Get the default port.
    credentials = usc.get_credentials()
    jupyter_port = credentials["jupyter_port"]
    hdbg.dassert_is_not(jupyter_port, None)
    if args.port is not None:
        port = int(args.port)
        _LOG.warning("Overriding port %d with port %d", jupyter_port, port)
        jupyter_port = port
    _LOG.info("Target port='%d'", jupyter_port)
    #
    action = args.positional[0]
    _LOG.debug("action=%s", action)
    if action == "check":
        _check(jupyter_port)
    elif action == "kill":
        _kill(jupyter_port)
    elif action in ("start", "force_start", "only_print_cmd"):
        _start(jupyter_port, action)
    else:
        hdbg.dfatal("Invalid action='%s'" % action)


if __name__ == "__main__":
    _main(_parse())
