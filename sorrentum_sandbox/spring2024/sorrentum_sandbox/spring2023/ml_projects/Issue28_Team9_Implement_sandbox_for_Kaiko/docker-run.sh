#!/bin/bash -e

docker run -itd -p 8081:8081 --name kaiko kaiko:1.0 airflow webserver -p 8081
