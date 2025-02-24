#!/bin/bash -ex
#
# Clone repo and configure the hooks.
# You can wget / copy-paste this script from GitHub interface to bootstrap.
#

# Clone the code.
if [[ 1 == 1 ]]; then
    IDX=$1
    if [[ -z $IDX ]]; then
        echo "ERROR: You need to specify a client, like 1, 2, 3..."
        exit -1
    fi;

    HOSTNAME="github.com"
    BRANCH="alphamatic/amp"
    DST_DIR="amp${IDX}"
    git clone --recursive git@${HOSTNAME}/${BRANCH}.git $DST_DIR
    (cd amp && git checkout master)
fi;

# Configure Python.
echo "which python="$(which python3 2>&1)
echo "python version="$(python3 --version)

# Set amp path.
PWD=$(pwd)
AMP_DIR=$PWD
if [[ ! -d $AMP_DIR ]]; then
    echo "The amp dir '$AMP_DIR' doesn't exist"
    return -1
fi;
export PYTHONPATH=$PYTHONPATH:$AMP_DIR
echo "PYTHONPATH=$PYTHONPATH"

# Install the Git hooks in both repos.
python3 $AMP_DIR/dev_scripts/git/git_hooks/install_hooks.py --action install
