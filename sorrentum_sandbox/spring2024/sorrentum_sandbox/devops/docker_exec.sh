#!/bin/bash -e

IMAGE_NAME="devops_airflow-webserver_1"

CONTAINER_ID=$(docker container ls | grep $IMAGE_NAME | awk '{print $1}')
echo $CONTAINER_ID

if [[ -z $CONTAINER_ID ]]; then
    echo "Can't find container for $IMAGE_NAME"
    exit -1
fi;

docker exec -it $CONTAINER_ID bash
