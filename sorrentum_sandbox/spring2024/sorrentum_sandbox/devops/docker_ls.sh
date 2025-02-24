#!/bin/bash
echo "# Sorrentum"
docker images | grep sorrentum
echo "# Mongo"
docker images | grep mongo
echo "# Postgres"
docker images | grep postgres
echo "# Airflow"
docker images | grep airflow
