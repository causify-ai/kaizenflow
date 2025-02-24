#!/bin/bash -e

GIT_ROOT_DIR=$(git rev-parse --show-toplevel)
echo "GIT_ROOT_DIR=$GIT_ROOT_DIR"

if [[ ! -d $GIT_ROOT_DIR ]]; then
    echo "ERROR: Can't find the root dir $GIT_ROOT_DIR"
    exit -1
fi;

sudo chown -R $(whoami):$(whoami) $GIT_ROOT_DIR
