#!/bin/bash -e

# Prune all the dangling Docker objects.
docker system prune --force

# Remove the Docker images used by the Sorrentum container.
for FULL_IMAGE_NAME in apache/airflow mongo postgres sorrentum/sorrentum 
do
    echo "# Delete $FULL_IMAGE_NAME"
    docker image ls | grep $FULL_IMAGE_NAME | awk '{print $3}' | xargs -n 1 -t docker image rm -f
done;

docker system prune --force

docker images
