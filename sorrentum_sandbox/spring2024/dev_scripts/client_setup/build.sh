#!/bin/bash
#
# Build a thin virtual environment to run workflows on the dev machine.
#

# TODO(gp): Use python 3.9 and keep this in sync with
# devops/docker_build/pyproject.toml

set -e

# Difference btw Kaizenflow and cmamp. Kaizenflow people do not require aws
# installation.
# TODO(gp): Once we need to share data on S3 will need to re-enable.
# Check if AWS CLI V2 is already installed.
# if command -v aws &>/dev/null; then
#     aws_version=$(aws --version)
# else
#     echo "AWS CLI is not installed. Please install it and try again."
#     exit 1
# fi;

echo "which python="$(which python 2>&1)
echo "python -v="$(python --version 2>&1)
echo "which python3="$(which python3)
echo "python3 -v="$(python3 --version)

# Resolve the dir containing the Git client.
# For now let's keep using the central version of /venv independenly of where
# the Git client is (e.g., `.../src` vs `.../src_vc`).
AM_SRC_DIR="$HOME/src"
echo "AM_SRC_DIR=$AM_SRC_DIR"
if [[ ! -d $AM_SRC_DIR ]]; then
    echo "ERROR: Dir AM_SRC_DIR='$AM_SRC_DIR' doesn't exist"
    exit -1
fi;

# Keep this in sync with `dev_scripts/setenv_amp.sh`
# TODO(gp): VENV_DIR should be shared among the scripts through a file.
VENV_DIR="$AM_SRC_DIR/venv/amp.client_venv"
echo "# VENV_DIR=$VENV_DIR"

if [[ -d $VENV_DIR ]]; then
    echo "# Deleting old virtual environment in '$VENV_DIR'"
    rm -rf $VENV_DIR
fi;
echo "# Creating virtual environment in '$VENV_DIR'"
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install packages.
# TODO(gp): Switch to poetry.
python3 -m pip install --upgrade pip
pip3 install -r dev_scripts/client_setup/requirements.txt

echo "# aws=$aws_version"
INVOKE_VER=$(invoke --version)
echo "# invoke=$INVOKE_VER"
POETRY_VER=$(poetry --version)
echo "# poetry=$POETRY_VER"
DOCKER_COMPOSE_VER=$(docker-compose --version)
echo "# docker-compose=$DOCKER_COMPOSE_VER"

DOCKER_VER=$(docker --version)
echo "# docker=$DOCKER_VER"

# TODO(gp): Install this only on Mac.

if [[ $(uname) == "Darwin" ]]; then
    # Update brew.
    brew update
    BREW_VER=$(brew --version)
    echo "# brew version=$BREW_VER"

    # Install GitHub CLI.
    brew install gh
    GH_VER=$(gh --version)
    echo "# gh version=$GH_VER"

    # Install dive.
    # https://github.com/wagoodman/dive
    #brew install dive
    #echo "dive version="$(dive --version)
fi;

echo "# Installation successful"
echo "# Configure your client with:"
echo "> source dev_scripts/setenv_amp.sh"
