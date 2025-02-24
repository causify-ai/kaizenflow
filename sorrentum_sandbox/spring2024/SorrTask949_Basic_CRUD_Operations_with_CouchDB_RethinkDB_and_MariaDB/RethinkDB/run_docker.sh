#!/bin/bash

echo "Building and running Docker containers for the Flask and RethinkDB application..."

# Bring down any containers that might be up to ensure a clean state
docker-compose down

# Build the containers with no cache option to ensure fresh build
docker-compose up --build -d

echo "Containers are up and running in detached mode!"


# use ./run_docker.sh to run it
# use http://127.0.0.1:5000/ to test in a browser