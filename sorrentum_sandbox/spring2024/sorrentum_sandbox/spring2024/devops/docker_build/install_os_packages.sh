#!/usr/bin/env bash
#
# Install OS level packages.
#

set -ex

FILE_NAME="devops/docker_build/install_os_packages.sh"
echo "#############################################################################"
echo "##> $FILE_NAME"
echo "#############################################################################"

DEBIAN_FRONTEND=noninteractive

# Update the package listing, so we know what package exist.
apt-get update

# Install security updates.
apt-get -y upgrade

APT_GET_OPTS="-y --no-install-recommends"

# TODO(gp): We can remove lots of this.
apt-get install $APT_GET_OPTS cifs-utils

# To update Git to latest version after `2.25.1`.
# https://www.linuxcapable.com/how-to-install-and-update-latest-git-on-ubuntu-20-04/
# sudo add-apt-repository ppa:git-core/ppa -y
apt-get install $APT_GET_OPTS git

apt-get install $APT_GET_OPTS keyutils
apt-get install $APT_GET_OPTS make

# We need `ip` to test Docker for running in privileged mode.
# See AmpTask2200 "Update tests after pandas update".
apt-get install $APT_GET_OPTS iproute2

# Install vim.
apt-get install $APT_GET_OPTS vim

# This is needed to compile ujson.
# See https://github.com/alphamatic/lm/issues/155.
apt-get install $APT_GET_OPTS build-essential autoconf libtool python3.9-dev python3.9-distutils
update-alternatives --install /usr/local/bin/python python /usr/bin/python3.9 40
update-alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.9 40


# Install pip.
apt-get install $APT_GET_OPTS curl
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py -k
python3.9 get-pip.py
apt-get install $APT_GET_OPTS python3.9-venv
echo "PYTHON VERSION="$(python3 --version)
echo "PIP VERSION="$(pip3 --version)
# Install poetry.
pip3 install poetry
echo "POETRY VERSION="$(poetry --version)

# Install AWS CLI V2.
# For more info see https://docs.aws.amazon.com/cli/latest/userguide/getting-started-version.html.
# Changelog: https://raw.githubusercontent.com/aws/aws-cli/v2/CHANGELOG.rst.
apt-get install $APT_GET_OPTS ca-certificates unzip
# Get the latest version of AWS CLI based on the architecture.
ARCH=$(uname -m)
echo "ARCH=$ARCH"
if [[ $ARCH == "x86_64" ]]; then
    echo "Installing AWS CLI V2 for x86_64(Linux) architecture"
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
elif [[ $ARCH == "aarch64" ]]; then
    echo "Installing AWS CLI V2 for aarch64(Mac) architecture"
    curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
else
    echo "Unknown architecture $ARCH"
    exit 1
fi;
unzip awscliv2.zip
rm awscliv2.zip
./aws/install
echo "AWS_CLI VERSION="$(aws --version)

# Install homebrew.
#apt-get install $APT_GET_OPTS build-essential procps curl file git

# Install github CLI.
# From https://github.com/cli/cli/blob/trunk/docs/install_linux.md.
DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
apt-get install $APT_GET_OPTS software-properties-common
apt-get install $APT_GET_OPTS dirmngr
apt-get install $APT_GET_OPTS gpg-agent
# GitHub was recently forced to change the key they use for signing
# details in CmTask #2803.
apt-key adv --keyserver keyserver.ubuntu.com --recv-key 23F3D4EA75716059
apt-add-repository https://cli.github.com/packages
apt-get update
apt-get install $APT_GET_OPTS gh
echo "GH VERSION="$(gh --version)

# This is needed to install pygraphviz.
# See https://github.com/alphamatic/amp/issues/1311.
# It needs tzdata so it needs to go after installing tzdata.
apt-get install $APT_GET_OPTS libgraphviz-dev

# This is needed to install dot.
apt-get install $APT_GET_OPTS graphviz

# This is needed for Postgres DB.
apt-get install $APT_GET_OPTS postgresql-client

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
