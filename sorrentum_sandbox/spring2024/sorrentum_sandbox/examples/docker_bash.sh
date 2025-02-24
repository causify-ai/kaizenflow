#!/bin/bash -xe

GIT_ROOT=$(git rev-parse --show-toplevel)

REPO_NAME=sorrentum
IMAGE_NAME=jupyter
FULL_IMAGE_NAME=$REPO_NAME/$IMAGE_NAME

docker image ls $FULL_IMAGE_NAME

CONTAINER_NAME=$IMAGE_NAME
docker run \
    --rm -ti \
    --name $CONTAINER_NAME \
    -p 8888:8888 \
    -v $GIT_ROOT:/data \
    $FULL_IMAGE_NAME \
    /bin/bash -c "source /data/sorrentum_sandbox/examples/set_env.sh; bash"
