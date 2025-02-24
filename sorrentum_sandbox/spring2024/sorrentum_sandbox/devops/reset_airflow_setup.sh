#!/bin/bash -xe

CONTAINER_NAME="airflow_cont"

# Reset the Airflow DB.
docker exec \
    -ti \
    $CONTAINER_NAME \
    airflow db reset
