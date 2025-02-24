#!/bin/bash -e

# """
# Find files with git conflicts.
# """

source helpers.sh

execute "git diff --name-only --diff-filter=U"
