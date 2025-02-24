#!/bin/bash -e
#
# Execute bash in the container.
#

GIT_ROOT=$(git rev-parse --show-toplevel)
source $GIT_ROOT/docker_common/utils.sh

# Find the name of the container.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
DOCKER_NAME="$SCRIPT_DIR/docker_name.sh"
if [[ ! -e $SCRIPT_DIR ]]; then
    echo "Can't find $DOCKER_NAME"
    exit -1
fi;
source $DOCKER_NAME

docker image ls $FULL_IMAGE_NAME
docker manifest inspect $FULL_IMAGE_NAME | grep arch

JUPYTER_HOST_PORT=8889

CONTAINER_NAME=$IMAGE_NAME
OPTS="--user $(id -u):$(id -g)"
# TODO(gp): Not sure --net bridge is needed.
docker run \
    --rm -ti \
    $OPTS \
    --net bridge \
    --name $CONTAINER_NAME \
    -p 3001:3000 \
    -p 5920:5920 \
    -p 7545:7545 \
    -p 8545:8545 \
    -p $JUPYTER_HOST_PORT:8888 \
    -v $(pwd):/data \
    $FULL_IMAGE_NAME
