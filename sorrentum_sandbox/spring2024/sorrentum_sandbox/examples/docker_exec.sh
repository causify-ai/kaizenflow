#!/bin/bash -e

GIT_ROOT=$(git rev-parse --show-toplevel)
source ../docker_common/utils.sh

REPO_NAME=sorrentum
IMAGE_NAME=jupyter

exec_container
