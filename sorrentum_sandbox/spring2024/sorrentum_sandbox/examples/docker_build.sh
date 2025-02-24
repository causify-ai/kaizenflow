#!/bin/bash -e

GIT_ROOT=$(git rev-parse --show-toplevel)
source ../docker_common/utils.sh

REPO_NAME=sorrentum
IMAGE_NAME=jupyter

# Build container.
#export DOCKER_BUILDKIT=1
export DOCKER_BUILDKIT=0
build_container_image
