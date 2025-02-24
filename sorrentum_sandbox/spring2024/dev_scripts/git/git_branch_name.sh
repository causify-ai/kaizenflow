#!/bin/bash -e

# """
# Print name of the branch.
# """

# We don't use any wrapper so that we can use this result.

git rev-parse --abbrev-ref HEAD
