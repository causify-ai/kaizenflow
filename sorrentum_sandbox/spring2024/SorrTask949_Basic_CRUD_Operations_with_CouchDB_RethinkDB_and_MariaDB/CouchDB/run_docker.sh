#!/bin/bash

echo "Building and running Docker containers..."

# Stop all running containers (optional)
docker-compose down

# Build the containers
docker-compose build

# Run the containers
docker-compose up

echo "Containers are up and running!"

# use ./run_docker.sh to run it
