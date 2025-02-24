#!/bin/bash -xe
#
# Execute bash in the container.
#

GIT_ROOT=$(git rev-parse --show-toplevel)

# Find the name of the container.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
DOCKER_NAME="$SCRIPT_DIR/docker_name.sh"
if [[ ! -e $SCRIPT_DIR ]]; then
    echo "Can't find $DOCKER_NAME"
    exit -1
fi;
source $DOCKER_NAME

docker image ls $FULL_IMAGE_NAME
# docker manifest inspect $FULL_IMAGE_NAME | grep arch

CONTAINER_NAME=$IMAGE_NAME
docker run \
    --rm -ti \
    --name $CONTAINER_NAME \
    -v $GIT_ROOT:/cmamp \
    --env-file .env \
    $FULL_IMAGE_NAME \
    bash
