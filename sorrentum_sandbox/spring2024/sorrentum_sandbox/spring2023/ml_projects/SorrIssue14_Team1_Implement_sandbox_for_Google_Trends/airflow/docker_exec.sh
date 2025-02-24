#!/bin/bash -e

IMAGE_NAME="airflow_cont"

CONTAINER_ID=$(docker container ls | grep $IMAGE_NAME | awk '{print $1}')
docker exec -u default -it $CONTAINER_ID bash
