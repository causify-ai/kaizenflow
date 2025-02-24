#!/bin/bash -e

# """
# Retrieve the files checked in by the current user in the n last commits.
# """

if [[ -z $1 ]]; then
  num_commits=1
else
  num_commits=$1
fi;
#echo "num_commits=$num_commits"

# TODO(gp): Improve.
git show --pretty="" --name-only $(git log --author $(git config user.name) -$num_commits | \grep commit | perl -pe 's/commit (.*)/$1/')
