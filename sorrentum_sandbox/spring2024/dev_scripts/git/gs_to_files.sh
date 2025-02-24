#!/bin/bash -e

# """
# Filter output of `git status --short`
# """

awk '{ print $2; }'
