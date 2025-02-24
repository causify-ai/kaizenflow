#!/bin/bash -e

# """
# Force a revert of files to HEAD.
# """

source helpers.sh

execute "git reset HEAD $*"
execute "git checkout -- $*"
