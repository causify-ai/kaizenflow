#!/bin/bash -e

# """
# Make a backup of the submodules.
# """

source $AMP_DIR/dev_scripts/helpers.sh

msg=""
if [[ -z $1 ]]; then
    msg=$1
fi;
echo "msg=$msg"

cmd_="git stash save --keep-index '$msg' && git stash apply"

cmd=$cmd_
execute $cmd

cmd="git submodule foreach $cmd_"
execute $cmd
