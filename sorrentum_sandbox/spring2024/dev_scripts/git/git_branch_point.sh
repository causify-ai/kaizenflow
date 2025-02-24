#!/bin/bash -e

# """
# Find the branching point.
# """

source dev_scripts/helpers.sh

CURR=$(gb)
BASE="master"

#FORMAT_CMD='git log -1 --format="%h: (%ar): %an: %s"'
FORMAT_CMD="git log -1 --pretty=format:'$GIT_LOG_OPTS'"
#echo $FORMAT_CMD

# From https://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git

# Show the commit that git will use to merge.
echo "# Merge-point commit"
cmd="git merge-base --fork-point $BASE | xargs -n 1 $FORMAT_CMD"
execute $cmd

# Show all the branch points.
echo "# All branch points"
cmd="git rev-list --boundary $(gb)...$BASE | \\grep '^-' | cut -c2- | $FORMAT_CMD"
execute $cmd

# Show earliest ancestor point.
echo "# Earliest ancestor point"
diff -u <(git rev-list --first-parent $CURR) \
        <(git rev-list --first-parent $BASE) | \
        sed -ne 's/^ //p' | \
        head -1 | \
        xargs -n 1 $FORMAT_CMD
