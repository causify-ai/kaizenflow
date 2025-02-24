#!/usr/bin/env python

r"""
Create the conda environment for developing.

This script should have *no* dependencies from anything: it should be able to run
before setenv.sh, on a new system with nothing installed. It can use //amp
libraries.

# Install the `amp` default environment:
> create_conda.py \
        --env_name amp_develop \
        --req_file dev_scripts/install/requirements/amp_develop.yaml \
        --delete_env_if_exists

# Install the `develop` default environment:
> create_conda.py \
        --env_name develop \
        --req_file amp/dev_scripts/install/requirements/amp_develop.yaml \
        --req_file dev_scripts/install/requirements/develop.yaml \
        --delete_env_if_exists

# Quick install to test the script:
> create_conda.py --test_install -v DEBUG

# Test the `develop` environment with a different name before switching the old
# develop env:
> create_conda.py \
        --env_name develop_test \
        --req_file dev_scripts/install/requirements/amp_develop.yaml \
        --delete_env_if_exists

Import as:

import dev_scripts.old.create_conda.install.create_conda as dsoccicco
"""

import argparse
import logging
import os
import sys
from typing import Any, List

# Dir of the current create_conda.py.
_CURR_DIR = os.path.dirname(sys.argv[0])

# This script is `//amp/dev_scripts/install/create_conda.py`, so we need to go
# up two levels to reach `//amp`.
_AMP_REL_PATH = "../.."
_AMP_PATH = os.path.abspath(os.path.join(_CURR_DIR, _AMP_REL_PATH))
assert os.path.exists(_AMP_PATH), f"Can't find '{_AMP_PATH}'"
sys.path.insert(0, _AMP_PATH)
# pylint: disable=wrong-import-position
import dev_scripts.old.create_conda._bootstrap as dsoccobo  # isort:skip # noqa: E402

dsoccobo.bootstrap(_AMP_REL_PATH)

# pylint: disable=wrong-import-position
import helpers.old.conda as holdcond  # isort:skip # noqa: E402
import helpers.hdbg as hdbg  # isort:skip # noqa: E402
import helpers.old.env2 as holdenv2  # isort:skip # noqa: E402
import helpers.hio as hio  # isort:skip # noqa: E402
import helpers.hparser as hparser  # isort:skip # noqa: E402
import helpers.hprint as hprint  # isort:skip # noqa: E402
import helpers.old.user_credentials as holuscre  # isort:skip # noqa: E402

_LOG = logging.getLogger(__name__)


# The following paths are expressed relative to create_conda.py.
# TODO(gp): Allow them to tweak so we can be independent with respect to amp.
#  dev_scripts/install/requirements
_REQUIREMENTS_DIR = os.path.abspath(os.path.join(_CURR_DIR, "requirements"))

# dev_scripts/install/conda_envs
_CONDA_ENVS_DIR = os.path.abspath(os.path.join(_CURR_DIR, "conda_envs"))

# #############################################################################


def _set_conda_root_dir() -> None:
    conda_env_path = holuscre.get_credentials()["conda_env_path"]
    holdcond.set_conda_env_root(conda_env_path)
    #
    # conda info
    #
    _LOG.info("\n%s", hprint.frame("Current conda status"))
    cmd = "conda info"
    holdcond.conda_system(cmd, suppress_output=False)


def _delete_conda_env(args: Any, conda_env_name: str) -> None:
    """
    Deactivate current conda environment and delete the old conda henv.
    """
    # TODO(gp): Clean up cache, if needed.
    #
    # Deactivate conda.
    #
    _LOG.info("\n%s", hprint.frame("Check conda status after deactivation"))
    #
    cmd = "conda deactivate; conda info --envs"
    holdcond.conda_system(cmd, suppress_output=False)
    #
    # Create a package from scratch (otherwise conda is unhappy).
    #
    _LOG.info(
        "\n%s",
        hprint.frame(f"Delete old conda env '{conda_env_name}', if exists"),
    )
    conda_env_dict, _ = holdcond.get_conda_info_envs()
    conda_env_root = holdcond.get_conda_envs_dirs()[0]
    conda_env_path = os.path.join(conda_env_root, conda_env_name)
    #
    conda_env_exists = conda_env_name in conda_env_dict
    _LOG.debug(
        "conda_env_name=%s in conda_env_dict=%s -> conda_env_exists=%s",
        conda_env_name,
        conda_env_dict,
        conda_env_exists,
    )
    # Sometimes conda is flaky and says that there is no env, even if the dir
    # exists.
    conda_env_exists = conda_env_exists or os.path.exists(conda_env_path)
    _LOG.debug(
        "conda_env_path=%s -> conda_env_exists=%s",
        conda_env_path,
        conda_env_exists,
    )
    if conda_env_exists:
        _LOG.warning("Conda env '%s' exists", conda_env_path)
        if args.delete_env_if_exists:
            # Back up the old environment.
            # TODO(gp): Do this.
            # Remove old dir to make conda happy.
            _LOG.warning("Deleting conda env '%s'", conda_env_path)
            # $CONDA remove -y -n $ENV_NAME --all
            cmd = f"conda deactivate; rm -rf {conda_env_path}"
            holdcond.conda_system(cmd, suppress_output=False)
        else:
            msg = (
                f"Conda env '{conda_env_name}' already exists. You need to use"
                " --delete_env_if_exists to delete it"
            )
            _LOG.error(msg)
            sys.exit(-1)
    else:
        _LOG.warning("Skipping deleting environment")


def _process_requirements_file(req_file: str) -> str:
    """
    Process a requirement file to allow conditional builds.

    - Read a requirements file `req_file`
    - Skip lines like:
        # docx    # Not on Mac.
      to allow configuration based on target.
    - Merge the result in a tmp file that is created in the same dir as the
      `req_file`

    :return: name of the new file
    """
    txt = []
    # Read file.
    req_file = os.path.abspath(req_file)
    _LOG.debug("req_file=%s", req_file)
    hdbg.dassert_path_exists(req_file)
    txt_tmp = hio.from_file(req_file).split("\n")
    # Process.
    for line in txt_tmp:
        # TODO(gp): Can one do conditional builds for different machines?
        #  I don't think so.
        if "# Not on Mac." in line:
            continue
        txt.append(line)
    # Save file.
    txt = "\n".join(txt)
    dst_req_file = os.path.join(
        os.path.dirname(req_file), "tmp." + os.path.basename(req_file)
    )
    hio.to_file(dst_req_file, txt)
    return dst_req_file


def _process_requirements_files(req_files: List[str]) -> List[str]:
    """
    Apply _process_requirements_file() to multiple files.

    :return: list of names of the transformed files.
    """
    hdbg.dassert_isinstance(req_files, list)
    hdbg.dassert_lte(1, len(req_files))
    _LOG.debug("req_files=%s", req_files)
    out_files = []
    for req_file in req_files:
        out_file = _process_requirements_file(req_file)
        out_files.append(out_file)
    return out_files


def _create_conda_env(args: Any, conda_env_name: str) -> None:
    """
    Process requirements file and create conda henv.
    """
    _LOG.info("\n%s", hprint.frame(f"Create new conda env '{conda_env_name}'"))
    #
    if args.test_install:
        cmd_txt = f"conda create --yes --name {conda_env_name} -c conda-forge"
    else:
        cmd: List[str] = []
        # Extract extensions.
        extensions = set()
        for req_file in args.req_file:
            hdbg.dassert_path_exists(req_file)
            _, file_extension = os.path.splitext(req_file)
            extensions.add(file_extension)
        hdbg.dassert_eq(
            len(extensions),
            1,
            "There should be only one type of extension: found %s",
            extensions,
        )
        extension = list(extensions)[0]
        _LOG.debug("extension='%s'", extension)
        hdbg.dassert_in(
            extension, (".txt", ".yaml"), "Invalid req file extension"
        )
        if extension == ".yaml":
            cmd.append("conda env create")
        else:
            hdbg.dassert_eq(extension, ".txt")
            cmd.append("conda create")
            # Start installation without prompting the user.
            cmd.append("--yes")
            # cmd.append("--override-channels")
            cmd.append("-c conda-forge")
        cmd.append(f"--name {conda_env_name}")
        req_files = args.req_file
        tmp_req_files = _process_requirements_files(req_files)
        _LOG.debug("tmp_req_files=%s", tmp_req_files)
        # Report the files so we can see what we are actually installing.
        for f in tmp_req_files:
            _LOG.debug("tmp_req_file=%s\n%s", f, hio.from_file(f))
        # TODO(gp): Merge the yaml files (see #579).
        # We leverage the fact that `conda create` can merge multiple
        # requirements files.
        cmd.append(" ".join([f"--file {f}" for f in tmp_req_files]))
        if args.python_version is not None:
            cmd.append(f"python={args.python_version}")
        cmd_txt = " ".join(cmd)
    holdcond.conda_system(cmd_txt, suppress_output=False)


def _run_pip_install(args: Any, conda_env_name: str) -> None:
    if args.test_install:
        # To work around the break of PTask1124.
        pass
    else:
        if False:
            # PTask1005: Moved to pip and pinned for gluonts.
            cmd = [
                f"conda activate {conda_env_name}",
                'pip install --no-deps "mxnet>=1.6.0"',
                "pip install --no-deps gluonnlp",
            ]
            cmd = " && ".join(cmd)
            holdcond.conda_system(cmd, suppress_output=False)


def _test_conda_env(conda_env_name: str) -> None:
    # Test activating.
    _LOG.info("\n%s", hprint.frame(f"Test activate conda env '{conda_env_name}'"))
    cmd = f"conda activate {conda_env_name} && conda info --envs"
    holdcond.conda_system(cmd, suppress_output=False)
    # Check packages.
    _, file_name = holdenv2.save_env_file(conda_env_name, _CONDA_ENVS_DIR)
    # TODO(gp): Not happy to save all the package list in amp. It should go in
    #  a spot with respect to the git root.
    _LOG.warning(
        "You should commit the file '%s' for future reference", file_name
    )


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--delete_env_if_exists", action="store_true")
    parser.add_argument(
        "--env_name", type=str, required=True, help="Environment name"
    )
    parser.add_argument(
        "--req_file",
        action="append",
        default=[],
        required=True,
        help="Requirements file",
    )
    # Debug options.
    parser.add_argument(
        "--test_install",
        action="store_true",
        help="Test the install step without requirements",
    )
    parser.add_argument(
        "--python_version", default=None, type=str, action="store"
    )
    # TODO(gp): Use the action approach from helpers.parser.
    parser.add_argument("--skip_delete_env", action="store_true")
    parser.add_argument("--skip_install_env", action="store_true")
    parser.add_argument("--skip_pip_install", action="store_true")
    parser.add_argument("--skip_test_env", action="store_true")
    #
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    _LOG.info("\n%s", holdenv2.get_system_info(add_frame=True))
    hdbg.dassert_path_exists(_REQUIREMENTS_DIR)
    hdbg.dassert_path_exists(_CONDA_ENVS_DIR)
    #
    _set_conda_root_dir()
    #
    conda_env_name = args.env_name
    #
    if args.skip_delete_env:
        _LOG.warning("Skip delete conda env per user request")
    else:
        _delete_conda_env(args, conda_env_name)
    #
    if args.skip_install_env:
        _LOG.warning("Skip create conda env")
    else:
        _create_conda_env(args, conda_env_name)
    #
    if args.skip_pip_install:
        _LOG.warning("Skip pip install")
    else:
        _run_pip_install(args, conda_env_name)
    #
    if args.skip_test_env:
        _LOG.warning("Skip test conda env")
    else:
        _test_conda_env(conda_env_name)
    #
    _LOG.info("DONE")


if __name__ == "__main__":
    _main(_parse())
