#!/bin/bash -e

# """
# Show information about the branches.
# """

source helpers.sh

# Print information about branch.

# TODO(gp): Add a --format and print date / author of last commit, merged / not merged.
#cmd='git branch -av'
#execute $cmd

# Print information about branch author.

# From https://stackoverflow.com/questions/12055198/find-out-a-git-branch-creator
cmd="git for-each-ref --format='%(color:cyan)%(authordate:format:%m/%d/%Y %I:%M %p)    %(align:25,left)%(color:yellow)%(authorname)%(end) %(color:reset)%(refname:strip=3)' --sort=authordate refs/remotes"
execute $cmd
