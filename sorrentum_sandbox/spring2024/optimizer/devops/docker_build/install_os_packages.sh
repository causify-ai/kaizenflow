#!/usr/bin/env bash
#
# Install OS level packages.
#

set -ex

FILE_NAME="optimizer/devops/docker_build/install_os_packages.sh"
echo "#############################################################################"
echo "##> $FILE_NAME"
echo "#############################################################################"

export DEBIAN_FRONTEND=noninteractive

# Update the package listing, so we know what package exist.
apt-get update

# Install security updates.
apt-get -y upgrade

APT_GET_OPTS="-y --no-install-recommends"

# Install git.
apt-get install $APT_GET_OPTS git

## Install vim.
apt-get install $APT_GET_OPTS vim

# Install pip.
apt-get install $APT_GET_OPTS python3-venv python3-pip
echo "PYTHON VERSION="$(python3 --version)
echo "PIP VERSION="$(pip3 --version)
python3 -m pip install --upgrade pip

# Install poetry.
pip3 install poetry
echo "POETRY VERSION="$(poetry --version)

# Install homebrew.
apt-get install $APT_GET_OPTS build-essential procps curl file git

# Install sudo.
apt-get install $APT_GET_OPTS sudo

# Clean up.
if [[ $CLEAN_UP_INSTALLATION ]]; then
    echo "Cleaning up installation..."
    apt-get purge -y --auto-remove
    DIRS="/root/.cache /tmp/*"
    du -hs $DIRS | sort -h
    rm -rf $DIRS
else
    echo "No clean up installation"
fi;
