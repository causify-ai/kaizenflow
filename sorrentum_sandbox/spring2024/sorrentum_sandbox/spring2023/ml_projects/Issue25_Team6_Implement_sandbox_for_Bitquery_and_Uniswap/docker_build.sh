#!/bin/bash -e

IMAGE_NAME="sorrentum"
REPO_NAME="sorrentum"

#export DOCKER_BUILDKIT=1
#export DOCKER_BUILDKIT=0
OPTS="--progress plain $@"
(docker build $OPTS -t $REPO_NAME/$IMAGE_NAME . 2>&1 | tee docker_build.log; exit ${PIPESTATUS[0]})

docker image ls $REPO_NAME/$IMAGE_NAME
