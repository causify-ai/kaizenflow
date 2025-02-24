#!/bin/bash -e

# """
# This file needs to be sourced:
#   > source setenv_amp.sh
# instead of executed:
#   > ./setenv_amp.sh
# in order to set the env vars in the calling shell.
#
# Parameters passed to this script are propagated to _setenv.py
#
# Keep this script in sync with:
# > vimdiff ./dev_scripts/setenv_....sh amp/dev_scripts/setenv_amp.sh
# """

# Name of the current script, e.g,. `./dev_scripts/setenv_amp.sh`
EXEC_NAME="${BASH_SOURCE[0]}"
echo "Running '$EXEC_NAME' ..."
# Dir to the executable, e.g., `./dev_scripts`
EXEC_DIR=$(dirname "$EXEC_NAME")
# Full path to the executable, e.g.,
#   `/Users/saggese/src/...1/amp/dev_scripts`
EXEC_PATH=$(cd $EXEC_DIR; pwd -P)
echo "EXEC_DIR=$EXEC_DIR"
echo "EXEC_PATH=$EXEC_PATH"

if [[ -z $1 ]]; then
    ENV_NAME="amp_develop"
else
    ENV_NAME=$1
fi
echo "ENV_NAME=$ENV_NAME"

# source helpers.sh
HELPERS_PATH=$EXEC_PATH/helpers.sh
echo "HELPERS_PATH=$HELPERS_PATH"
if [[ ! -e $HELPERS_PATH ]]; then
    echo "ERROR($EXEC_NAME): File '$HELPERS_PATH' doesn't exist: exiting"
    return 1
fi
source $HELPERS_PATH

# Check python version.
get_python_version
rc=$?
if [[ $rc != 0 ]]; then
  echo "ERROR($EXEC_NAME): python is too old: exiting"
  return $rc
fi;

# Create and execute the setenv_amp.sh script to configure the env.
execute_setenv "_setenv_amp" $ENV_NAME

export AMP="."
