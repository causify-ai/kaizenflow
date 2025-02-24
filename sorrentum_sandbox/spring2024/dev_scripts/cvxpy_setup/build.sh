#!/bin/bash
#
# Build a virtual environment to run cvxpy.
#

set -e

echo "which python="$(which python 2>&1)
echo "python -v="$(python --version 2>&1)
echo "which python3="$(which python3)
echo "python3 -v="$(python3 --version)

VENV_DIR="$HOME/src/venv/amp.cvxpy_venv"
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
pip3 install -r dev_scripts/cvxpy_setup/requirements.txt

echo "# Configure your client with:"
echo "> source dev_scripts/cvxpy_setup/setenv.sh"
