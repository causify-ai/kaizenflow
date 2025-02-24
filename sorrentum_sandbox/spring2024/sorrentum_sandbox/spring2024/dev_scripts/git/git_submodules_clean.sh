#!/bin/bash -e

# """
# Clean all the submodules with `git clean -fd`.
# """

# TODO(gp): Stash to be safe.

AMP_DIR="amp"
source $AMP_DIR/dev_scripts/helpers.sh

cmd="git clean -fd"
execute $cmd

cd amp
cmd="git clean -fd"
execute $cmd
cd ..
