#!/bin/bash

echo "Building and running Docker containers for the Flask and MariaDB application..."

# Bring down any containers that might be up to ensure a clean state
docker-compose down

# Build the containers with no cache to ensure all updates are applied
docker-compose up --build -d

# Check if Flask app starts successfully
if [ $(docker inspect -f '{{.State.Running}}' mariadb-flaskapp-1) = "true" ]; then
  echo "Flask application is up and running!"
else
  echo "Flask application failed to start. Check the logs for more details."
  docker logs mariadb-flaskapp-1
fi

echo "MariaDB is running!"

# use ./run_docker.sh to run it
# use http://127.0.0.1:5000/ to test in a browser
