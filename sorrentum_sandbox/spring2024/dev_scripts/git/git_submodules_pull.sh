#!/bin/bash -e

# """
# Force a git pull of all the repos.
# """

AMP_DIR="./amp"
source $AMP_DIR/dev_scripts/helpers.sh

cmd="git pull --autostash"
execute $cmd

cmd="git submodule foreach git pull --autostash"
execute $cmd
