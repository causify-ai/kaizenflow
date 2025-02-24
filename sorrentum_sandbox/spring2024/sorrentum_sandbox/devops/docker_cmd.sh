#!/bin/bash -e
#
# Execute a command in the Sorrentum container.
#

IMAGE_NAME="airflow_cont"

docker exec \
    -ti \
    $IMAGE_NAME \
    $@
