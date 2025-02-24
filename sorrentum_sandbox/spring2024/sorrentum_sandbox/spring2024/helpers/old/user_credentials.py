#!/usr/bin/env python
"""
Import as:

import helpers.old.user_credentials as holuscre
"""

import argparse
import logging
import os
import pprint
from typing import Any, Dict, List, Tuple

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def get_dev_server_ip() -> str:
    """
    Get the dev server name from the user environment.
    """
    env_var_name = ""
    if env_var_name not in os.environ:
        _LOG.error("Can't find '%s': re-run dev_scripts/setenv.sh?", env_var_name)
        raise RuntimeError
    dev_server = os.environ[env_var_name]
    return dev_server


# pylint: disable=too-many-statements
def get_credentials() -> Dict[str, Any]:
    """
    Report information about a user set-up as a function of: 1) user name 2)
    server name 3) git repository name.

    The mandatory information are:
    1) git_user_name
    2) git_user_email
    3) conda_sh_path: the path of the script bootstrapping conda
        - To find "conda_sh_path":
          > which conda
          /data/root/anaconda3/bin/conda
          > find /data/root/anaconda3 -name "conda.sh"
        - In one instruction:
          > CONDA_DIR=$(dirname $(which conda))"/.."; find $CONDA_DIR -name "conda.sh"
        - If there are multiple ones you want to pick the one under
          `profile.d`, e.g., `/anaconda3/etc/profile.d/conda.sh`
    4) conda_env_path: the path of the dir storing the conda environments
        - To find "conda_env_path"
          > conda info
          ...
                 envs directories : /data/saggese/.conda/envs

    The optional information are:
    5) ssh_key_path: the path of the ssh key to use
    6) tunnel_info: list of "personal" ports to forward
        - This is an advanced behavior that allows to specify in your user
          config a set of ports to forward from one computer (typically your
          laptop) to a set of services that are specific of your set-up (e.g.,
          started through `run_jupyter_server.py`)
        - E.g.,
          ```python
            if server_name in ("gpmac.local", "gpmac.lan"):
                if git_repo_name == "":
                    service = ("Jupyter1", get_dev_server_ip(), 10003, 10003)
          ```
          when GP runs `ssh_tunnels.py` from his laptop in a
          `` client, a tunnel is open to the dev
          server where `run_jupyter_server.py` will have started a notebook server
    7) jupyter_port: on which port to start a jupyter server on a specific server
        - It's a good idea for everybody to have a different port to avoid port
          collisions
    8) notebook_html_path: the path where to save html of notebooks
    9) notebook_backup_path: the path where to backup the source .ipynb code of
        notebooks
    """
    #
    user_name = hsystem.get_user_name()
    server_name = hsystem.get_server_name()
    _LOG.debug("user_name='%s'", user_name)
    _LOG.debug("server_name='%s'", server_name)
    git_repo_name = hgit.get_repo_full_name_from_client(super_module=True)
    # Values to assign.
    git_user_name = ""
    git_user_email = ""
    conda_sh_path = ""
    ssh_key_path = "~/.ssh/id_rsa"
    tunnel_info: List[Tuple[str, str, str, str]] = []
    jupyter_port = -1
    notebook_html_path = ""
    notebook_backup_path = ""
    #
    conda_env_path = "~/.conda/envs"
    conda_env_path = os.path.expanduser(conda_env_path)
    if server_name in ():
        conda_sh_path = "/anaconda3/etc/profile.d/conda.sh"
    if user_name == "saggese":
        # GP.
        git_user_name = "saggese"
        git_user_email = "abc@xyz.com"
        if server_name.startswith("gpmac") or server_name.startswith(
            "giacintos-mbp"
        ):
            # Laptop.
            conda_sh_path = "/Users/saggese/opt/anaconda3/etc/profile.d/conda.sh"
            conda_env_path = "/Users/saggese/.conda/envs"
            if git_repo_name == "":
                # Forward port 10003 to the notebook server that is started by
                # `run_jupyter_server.py` when executed on the dev server.
                # service = ("Jupyter1", get_dev_server_ip(), 10003, 10003)
                # tunnel_info.append(service)
                # jupyter_port = 10001
                pass
        elif server_name == "":
            if git_repo_name == "":
                jupyter_port = 10003
        else:
            hdbg.dassert_ne(conda_sh_path, "")
    elif user_name == "paul":
        # Paul.
        git_user_name = "paul"
        git_user_email = "abc@xyz.com"
        if server_name in ("Pauls-MacBook-Pro.local", "Pauls-MBP"):
            conda_sh_path = "/Users/paul/anaconda3/etc/profile.d/conda.sh"
            conda_env_path = "/Users/paul/.conda/envs"
    # Check.
    for var_name, val_name in [
        ("git_user_name", git_user_name),
        ("git_user_email", git_user_email),
        ("conda_sh_path", conda_sh_path),
        ("conda_env_path", conda_env_path),
        # We allow the rest of the variables (e.g., ssh_key_path, tunnel_info) to
        # be empty since in some configurations they can be undefined.
    ]:
        hdbg.dassert_is_not(
            val_name,
            None,
            "Undefined '%s': add your credentials for user_name='%s' and "
            "server_name='%s' to '%s'",
            var_name,
            user_name,
            server_name,
            __file__,
        )
    conda_sh_path = os.path.expanduser(conda_sh_path)
    conda_sh_path = os.path.abspath(conda_sh_path)
    hdbg.dassert_path_exists(conda_sh_path)
    #
    conda_env_path = os.path.abspath(os.path.expanduser(conda_env_path))
    # Not necessarily the conda_env_path exists.
    if not os.path.exists(conda_env_path):
        _LOG.warning("The dir '%s' doesn't exist: creating it", conda_env_path)
        hio.create_dir(conda_env_path, incremental=True)
    hdbg.dassert_path_exists(os.path.dirname(conda_env_path))
    #
    for service in tunnel_info:
        # TODO(gp): We should call in ssh_tunnels.py to keep this encapsulated.
        hdbg.dassert_eq(len(service), 4)
        service_name, server, local_port, remote_port = service
        _ = service_name, server, local_port, remote_port
    ret = {
        "git_user_name": git_user_name,
        "git_user_email": git_user_email,
        "conda_sh_path": conda_sh_path,
        "conda_env_path": conda_env_path,
        "ssh_key_path": ssh_key_path,
        "tunnel_info": tunnel_info,
        "jupyter_port": jupyter_port,
        "notebook_html_path": notebook_html_path,
        "notebook_backup_path": notebook_backup_path,
    }
    _LOG.debug("Credentials: %s", ret)
    return ret


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--user", action="store", default=None, help="Impersonate a user"
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    if args.user:
        hsystem.set_user_name(args.user)
    usc = get_credentials()
    pprint.pprint(usc)


if __name__ == "__main__":
    _main(_parse())
