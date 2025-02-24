#!/bin/bash -xe
#
# Execute bash in the Sorrentum container.
#

GIT_ROOT=$(git rev-parse --show-toplevel)

REPO_NAME=sorrentum
IMAGE_NAME=sorrentum
FULL_IMAGE_NAME=$REPO_NAME/$IMAGE_NAME

docker image ls $FULL_IMAGE_NAME

CONTAINER_NAME=$IMAGE_NAME
docker run \
    --rm -ti \
    --name $CONTAINER_NAME \
    -v $GIT_ROOT:/cmamp \
    --env-file .env \
    $FULL_IMAGE_NAME \
    bash
